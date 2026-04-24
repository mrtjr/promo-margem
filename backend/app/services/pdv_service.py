"""
F7 — Serviço de integração com PDV.

Webhook handler:
  POST /webhooks/pdv-vendas
  Header: X-PDV-Token: <token da IntegracaoPDVConfig ativa>
  Body: PDVVendaEvento (idempotency_key + itens)

Fluxo:
  1. Valida token contra IntegracaoPDVConfig
  2. Checa idempotency_key no log → se existe, retorna duplicado
  3. Resolve produto por SKU (cria IntegracaoPDVLog erro se SKU desconhecido)
  4. Chama estoque_service.registrar_venda_bulk com data_fechamento
  5. Grava IntegracaoPDVLog(status=ok, venda_id=...)

Token é gerado no setup via secrets.token_urlsafe(24).
"""
from __future__ import annotations

import secrets
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from .. import models, schemas
from . import estoque_service


TOKEN_PREFIX = "pdv_"  # facilita identificação em logs


def obter_ou_criar_config(db: Session, *, nome_pdv: str = "Default PDV") -> models.IntegracaoPDVConfig:
    """Garante que existe UMA config (singleton). Se não, cria com token novo."""
    config = db.query(models.IntegracaoPDVConfig).first()
    if config:
        return config
    config = models.IntegracaoPDVConfig(
        token=TOKEN_PREFIX + secrets.token_urlsafe(24),
        nome_pdv=nome_pdv,
        ativa=True,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def rotacionar_token(db: Session) -> models.IntegracaoPDVConfig:
    """Gera novo token e invalida o anterior imediatamente."""
    config = obter_ou_criar_config(db)
    config.token = TOKEN_PREFIX + secrets.token_urlsafe(24)
    db.commit()
    db.refresh(config)
    return config


def atualizar_config(
    db: Session, *, nome_pdv: Optional[str] = None, ativa: Optional[bool] = None
) -> models.IntegracaoPDVConfig:
    config = obter_ou_criar_config(db)
    if nome_pdv is not None:
        config.nome_pdv = nome_pdv
    if ativa is not None:
        config.ativa = ativa
    db.commit()
    db.refresh(config)
    return config


def validar_token(db: Session, token_recebido: Optional[str]) -> Optional[models.IntegracaoPDVConfig]:
    """Retorna config se token válido e integração ativa. None caso contrário."""
    if not token_recebido:
        return None
    config = db.query(models.IntegracaoPDVConfig).filter(
        models.IntegracaoPDVConfig.token == token_recebido,
        models.IntegracaoPDVConfig.ativa == True,
    ).first()
    return config


def _resolver_skus(
    db: Session, itens: List[schemas.PDVVendaItem]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Converte [PDVVendaItem] em lista de dicts aceitos pelo registrar_venda_bulk.
    Retorna (vendas_resolvidas, skus_nao_encontrados).
    """
    vendas: List[Dict[str, Any]] = []
    nao_encontrados: List[str] = []
    for item in itens:
        prod = db.query(models.Produto).filter(models.Produto.sku == item.sku).first()
        if not prod:
            nao_encontrados.append(item.sku)
            continue
        vendas.append({
            "produto_id": prod.id,
            "quantidade": item.quantidade,
            "preco_venda": item.preco_venda,
        })
    return vendas, nao_encontrados


def processar_evento(
    db: Session, evento: schemas.PDVVendaEvento
) -> Tuple[str, str, Optional[int]]:
    """
    Processa um PDVVendaEvento. Retorna (status, mensagem, venda_id).

    status ∈ {"ok", "erro", "duplicado"}
    venda_id é None em erro/duplicado, ou id da primeira Venda criada.

    Idempotência: se idempotency_key já foi processado com sucesso, não faz
    nada e retorna 'duplicado'.
    """
    # 1. Checa duplicata
    existente = db.query(models.IntegracaoPDVLog).filter(
        models.IntegracaoPDVLog.idempotency_key == evento.idempotency_key,
        models.IntegracaoPDVLog.status == "ok",
    ).first()
    if existente:
        return "duplicado", f"idempotency_key {evento.idempotency_key} já processada", existente.venda_id

    # 2. Resolve SKUs
    vendas, nao_encontrados = _resolver_skus(db, evento.itens)
    if nao_encontrados:
        msg = f"SKUs desconhecidos: {', '.join(nao_encontrados[:5])}"
        return "erro", msg, None
    if not vendas:
        return "erro", "nenhum item no evento", None

    # 3. Registra vendas (usa data_venda ou hoje)
    data_alvo = evento.data_venda or date.today()
    try:
        resultado = estoque_service.registrar_venda_bulk(
            db, vendas, data_fechamento=data_alvo
        )
    except Exception as e:
        return "erro", f"falha ao registrar: {e}", None

    # 4. Retorna venda_id (pegamos o id da primeira venda criada)
    venda_id = None
    if isinstance(resultado, dict):
        vendas_criadas = resultado.get("vendas_criadas") or resultado.get("vendas") or []
        if vendas_criadas and isinstance(vendas_criadas, list) and len(vendas_criadas) > 0:
            primeiro = vendas_criadas[0]
            if hasattr(primeiro, "id"):
                venda_id = primeiro.id
            elif isinstance(primeiro, dict):
                venda_id = primeiro.get("id")

    return "ok", f"{len(vendas)} item(s) registrado(s)", venda_id


def registrar_log(
    db: Session,
    *,
    payload: Dict[str, Any],
    status: str,
    mensagem: str,
    venda_id: Optional[int],
    idempotency_key: Optional[str],
) -> models.IntegracaoPDVLog:
    log = models.IntegracaoPDVLog(
        payload=payload,
        status=status,
        mensagem=mensagem,
        venda_id=venda_id,
        idempotency_key=idempotency_key,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def listar_logs(db: Session, limit: int = 50) -> List[models.IntegracaoPDVLog]:
    return (
        db.query(models.IntegracaoPDVLog)
        .order_by(models.IntegracaoPDVLog.recebido_em.desc())
        .limit(limit)
        .all()
    )
