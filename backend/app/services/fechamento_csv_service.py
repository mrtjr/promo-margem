"""
Importação de Fechamento de Vendas via CSV (formato ERP: xRelVendaAnalitica).

Pipeline:
  1. parse_csv()         → decodifica (latin-1), extrai linhas "Pedido"
  2. build_preview()     → matching por código / nome + validação aritmética
  3. commit_importacao() → aplica resoluções, cria vendas, substitui fechamento do dia

Camadas de verificação:
  Identidade:
    - Match por `codigo` (exato)   → camada 1
    - Fallback por nome normalizado → camada 2
    - Conflito (código casa A, nome casa B) → "conflito" (user resolve)
    - Sem match → "sem_match" (user resolve)

  Aritmética:
    - |qtd × v_unit − total| ≤ 0,02
    - qtd > 0 e qtd < 10000

Custo usado nas vendas = `produto.custo` atual (CMP). CMV do CSV é ignorado
por decisão de produto (entrada manual é a fonte de verdade pro custo).
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import StringIO
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

@dataclass
class LinhaCSV:
    """Linha parseada do CSV, uma por 'Pedido'."""
    idx: int
    pedido: Optional[str]
    codigo: Optional[str]
    nome: str
    quantidade: float
    preco_unitario: float
    total: float
    data: Optional[date]


def _parse_num_br(s: str) -> float:
    """Converte '1.234,56' ou '26,00' em float. Retorna 0.0 se vazio/inválido."""
    if not s:
        return 0.0
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_data_br(s: str) -> Optional[date]:
    """DD/MM/YYYY → date. Retorna None em falha."""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_csv(conteudo_bytes: bytes) -> List[LinhaCSV]:
    """
    Parse do CSV ERP. Expectativa:
      - encoding latin-1 (ISO-8859-1)
      - separador ';'
      - linhas relevantes começam com 'Pedido'; as alternativas (detalhe com
        vendedor/margem) são ignoradas
      - colunas de interesse na linha 'Pedido':
          0: 'Pedido'
          1: nº pedido
          2: data (DD/MM/YYYY)
          3: código do produto (ERP)
          4: nome do produto
          10: quantidade (BR decimal)
          11: valor unitário (BR decimal)
          12: total (BR decimal)

    Tentamos latin-1 → utf-8 como fallback silencioso.
    """
    for enc in ("latin-1", "utf-8", "cp1252"):
        try:
            texto = conteudo_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Não foi possível decodificar o CSV (latin-1/utf-8/cp1252).")

    linhas: List[LinhaCSV] = []
    idx = 0
    for raw in StringIO(texto):
        parts = raw.rstrip("\r\n").split(";")
        if len(parts) < 13:
            continue
        if parts[0].strip() != "Pedido":
            continue

        nome = parts[4].strip()
        if not nome:
            continue  # linha sem produto — ignora

        idx += 1
        linhas.append(LinhaCSV(
            idx=idx,
            pedido=parts[1].strip() or None,
            codigo=(parts[3].strip() or None),
            nome=nome,
            quantidade=_parse_num_br(parts[10]),
            preco_unitario=_parse_num_br(parts[11]),
            total=_parse_num_br(parts[12]),
            data=_parse_data_br(parts[2]),
        ))
    return linhas


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def normalizar_nome(s: str) -> str:
    """Remove acentos, lowercase, colapsa espaços. Usado no fallback de matching."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def _indices_produtos(db: Session) -> Tuple[Dict[str, models.Produto], Dict[str, models.Produto]]:
    """Retorna (por_codigo, por_nome_normalizado). Inclui produtos inativos."""
    por_codigo: Dict[str, models.Produto] = {}
    por_nome: Dict[str, models.Produto] = {}
    for p in db.query(models.Produto).all():
        if p.codigo:
            por_codigo[p.codigo.strip()] = p
        por_nome[normalizar_nome(p.nome)] = p
    return por_codigo, por_nome


def _match(
    linha: LinhaCSV,
    por_codigo: Dict[str, models.Produto],
    por_nome: Dict[str, models.Produto],
) -> Tuple[str, Optional[models.Produto], List[str]]:
    """
    Casa uma linha com um produto. Retorna (status, produto, mensagens).
    status: "ok" | "conflito" | "sem_match"
    """
    msgs: List[str] = []
    p_por_cod = por_codigo.get(linha.codigo.strip()) if linha.codigo else None
    p_por_nome = por_nome.get(normalizar_nome(linha.nome))

    if p_por_cod and p_por_nome:
        if p_por_cod.id == p_por_nome.id:
            return "ok", p_por_cod, msgs
        msgs.append(
            f"Código {linha.codigo} aponta para '{p_por_cod.nome}' "
            f"mas nome '{linha.nome}' aponta para '{p_por_nome.nome}'."
        )
        return "conflito", p_por_cod, msgs

    if p_por_cod:
        return "ok", p_por_cod, msgs

    if p_por_nome:
        if linha.codigo:
            msgs.append(
                f"Código {linha.codigo} não encontrado; casou por nome com "
                f"'{p_por_nome.nome}' (SKU {p_por_nome.sku})."
            )
        return "ok", p_por_nome, msgs

    msgs.append(
        f"Produto não encontrado: código={linha.codigo or '-'} nome='{linha.nome}'."
    )
    return "sem_match", None, msgs


# ---------------------------------------------------------------------------
# Validação aritmética
# ---------------------------------------------------------------------------

def _validar_linha(linha: LinhaCSV) -> List[str]:
    """Retorna lista de erros. Vazia = linha aritmeticamente válida."""
    erros: List[str] = []
    if linha.quantidade <= 0:
        erros.append(f"Quantidade inválida: {linha.quantidade}.")
    if linha.quantidade >= 10000:
        erros.append(f"Quantidade absurdamente alta: {linha.quantidade}.")
    if linha.preco_unitario <= 0:
        erros.append(f"Preço unitário inválido: {linha.preco_unitario}.")
    esperado = round(linha.quantidade * linha.preco_unitario, 2)
    if abs(esperado - linha.total) > 0.02:
        erros.append(
            f"Aritmética inconsistente: {linha.quantidade} × {linha.preco_unitario} "
            f"= {esperado:.2f}, mas total no CSV = {linha.total:.2f}."
        )
    return erros


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def build_preview(db: Session, conteudo_bytes: bytes, data_alvo: date) -> Dict:
    """
    Retorna dict compatível com schemas.CSVImportPreview.
    """
    linhas_csv = parse_csv(conteudo_bytes)
    por_codigo, por_nome = _indices_produtos(db)

    linhas_out: List[Dict] = []
    receita_total = 0.0
    qtd_total = 0.0
    skus_distintos: set = set()
    ok = pend = erro = 0

    for l in linhas_csv:
        mensagens: List[str] = []
        status = "ok"

        # Validação aritmética
        erros_arit = _validar_linha(l)
        if erros_arit:
            mensagens.extend(erros_arit)
            status = "erro"

        # Matching
        status_match, produto, msgs_match = _match(l, por_codigo, por_nome)
        mensagens.extend(msgs_match)
        if status != "erro":  # só sobrescreve se não tem erro aritmético
            status = status_match

        if status == "ok":
            ok += 1
            if produto:
                skus_distintos.add(produto.id)
        elif status == "erro":
            erro += 1
        else:
            pend += 1

        # Alerta de data
        if l.data and l.data != data_alvo:
            mensagens.append(
                f"Data da linha ({l.data.isoformat()}) diferente da data alvo ({data_alvo.isoformat()})."
            )

        # Totais só contam linhas OK (resto o user resolve)
        if status == "ok":
            receita_total += l.total
            qtd_total += l.quantidade

        linhas_out.append({
            "idx": l.idx,
            "pedido": l.pedido,
            "codigo_csv": l.codigo,
            "nome_csv": l.nome,
            "quantidade": l.quantidade,
            "preco_unitario": l.preco_unitario,
            "total": l.total,
            "data_csv": l.data.isoformat() if l.data else None,
            "status": status,
            "produto_id": produto.id if produto and status == "ok" else None,
            "produto_nome": produto.nome if produto and status == "ok" else None,
            "mensagens": mensagens,
        })

    # Verifica se já existe fechamento do dia
    ja_existe = db.query(models.Venda).filter(
        models.Venda.data_fechamento == data_alvo
    ).first() is not None

    return {
        "data_alvo": data_alvo.isoformat(),
        "total_linhas": len(linhas_out),
        "linhas_ok": ok,
        "linhas_pendentes": pend,
        "linhas_erro": erro,
        "receita_total": round(receita_total, 2),
        "qtd_total": round(qtd_total, 2),
        "skus_distintos": len(skus_distintos),
        "ja_existe_fechamento": ja_existe,
        "linhas": linhas_out,
    }


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

def _apagar_fechamento_do_dia(db: Session, dia: date) -> int:
    """
    Remove todas as vendas + movimentacoes SAIDA + VDS + HistoricoMargem tipo=dia
    do `dia`, e recalcula estoque/custo dos produtos afetados.

    Retorna nº de vendas removidas.
    """
    vendas = db.query(models.Venda).filter(
        models.Venda.data_fechamento == dia
    ).all()
    n = len(vendas)
    if n == 0:
        return 0

    produtos_afetados: set = {v.produto_id for v in vendas if v.produto_id}

    # Casa movimentacoes SAIDA irmãs (±2s, mesma qtd+produto) e deleta
    for v in vendas:
        if not v.data:
            db.delete(v)
            continue
        janela = timedelta(seconds=2)
        mov_irmas = db.query(models.Movimentacao).filter(
            models.Movimentacao.produto_id == v.produto_id,
            models.Movimentacao.tipo == "SAIDA",
            models.Movimentacao.quantidade == v.quantidade,
            models.Movimentacao.data >= v.data - janela,
            models.Movimentacao.data <= v.data + janela,
        ).all()
        for m in mov_irmas:
            db.delete(m)
        db.delete(v)

    # Apaga agregados do dia
    db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.data == dia
    ).delete(synchronize_session=False)

    db.query(models.HistoricoMargem).filter(
        func.date(models.HistoricoMargem.data) == dia,
        models.HistoricoMargem.tipo == "dia",
    ).delete(synchronize_session=False)

    db.flush()

    # Recalcula estoque dos produtos afetados a partir do log remanescente
    from . import estoque_service
    for pid in produtos_afetados:
        prod = db.query(models.Produto).filter(models.Produto.id == pid).first()
        if prod:
            estoque_service._recalcular_produto_do_zero(db, prod)

    return n


def _proximo_sku_auto(db: Session) -> str:
    """Gera um SKU AUTO-xxxxxx que ainda não existe."""
    import uuid
    while True:
        candidato = f"AUTO-{uuid.uuid4().hex[:6].upper()}"
        if not db.query(models.Produto).filter(models.Produto.sku == candidato).first():
            return candidato


def _grupo_fallback_id(db: Session) -> int:
    """Retorna um grupo_id razoável para fallback (primeiro grupo existente)."""
    g = db.query(models.Grupo).order_by(models.Grupo.id).first()
    if not g:
        raise ValueError("Nenhum grupo cadastrado — crie pelo menos um antes de importar.")
    return g.id


def commit_importacao(
    db: Session,
    linhas: List[Dict],
    resolucoes: List[Dict],
    data_alvo: date,
) -> Dict:
    """
    Aplica as resoluções do user e grava as vendas.

    `linhas`: payload do preview.
    `resolucoes`: lista de {idx, acao, produto_id?, novo_codigo?, novo_nome?, novo_grupo_id?, novo_preco_venda?, novo_custo?}
    """
    mensagens: List[str] = []

    # Mapa idx → resolução
    res_by_idx: Dict[int, Dict] = {r["idx"]: r for r in resolucoes}

    # Valida resoluções: todas pendentes/erro precisam ter resolução
    for l in linhas:
        if l["status"] == "ok":
            continue
        res = res_by_idx.get(l["idx"])
        if not res:
            raise ValueError(
                f"Linha {l['idx']} ({l['nome_csv']}) tem status '{l['status']}' "
                "mas sem resolução enviada."
            )
        if res["acao"] not in ("associar", "criar", "ignorar"):
            raise ValueError(f"Linha {l['idx']}: ação '{res['acao']}' inválida.")
        if res["acao"] == "associar" and not res.get("produto_id"):
            raise ValueError(f"Linha {l['idx']}: ação 'associar' exige produto_id.")
        if res["acao"] == "criar":
            faltando = [
                k for k in ("novo_nome", "novo_grupo_id", "novo_preco_venda", "novo_custo")
                if not res.get(k)
            ]
            if faltando:
                raise ValueError(
                    f"Linha {l['idx']}: ação 'criar' exige {', '.join(faltando)}."
                )

    # Substitui fechamento do dia se necessário
    n_removidas = _apagar_fechamento_do_dia(db, data_alvo)
    if n_removidas:
        mensagens.append(f"{n_removidas} venda(s) do dia {data_alvo.isoformat()} removida(s) antes de reimportar.")

    produtos_criados = 0
    produtos_associados = 0
    linhas_ignoradas = 0
    vendas_criadas = 0

    # Acumulador pra VendaDiariaSKU
    agg_sku: Dict[int, Dict] = {}

    for l in linhas:
        produto: Optional[models.Produto] = None

        if l["status"] == "ok":
            produto = db.query(models.Produto).filter(
                models.Produto.id == l["produto_id"]
            ).first()
        else:
            res = res_by_idx.get(l["idx"])
            if not res:
                continue
            if res["acao"] == "ignorar":
                linhas_ignoradas += 1
                continue
            if res["acao"] == "associar":
                produto = db.query(models.Produto).filter(
                    models.Produto.id == res["produto_id"]
                ).first()
                if not produto:
                    raise ValueError(f"Linha {l['idx']}: produto_id {res['produto_id']} não existe.")
                produtos_associados += 1
                # Se o user escolheu associar e o produto não tem código, adota o código do CSV
                if l.get("codigo_csv") and not produto.codigo:
                    # Valida unicidade antes de setar
                    conflito = db.query(models.Produto).filter(
                        models.Produto.codigo == l["codigo_csv"],
                        models.Produto.id != produto.id,
                    ).first()
                    if not conflito:
                        produto.codigo = l["codigo_csv"]
            elif res["acao"] == "criar":
                # Valida código único
                if res.get("novo_codigo"):
                    conflito = db.query(models.Produto).filter(
                        models.Produto.codigo == res["novo_codigo"].strip()
                    ).first()
                    if conflito:
                        raise ValueError(
                            f"Linha {l['idx']}: código '{res['novo_codigo']}' já usado "
                            f"pelo SKU {conflito.sku}."
                        )
                produto = models.Produto(
                    sku=_proximo_sku_auto(db),
                    codigo=(res["novo_codigo"].strip() if res.get("novo_codigo") else None),
                    nome=res["novo_nome"].strip(),
                    grupo_id=res["novo_grupo_id"],
                    custo=float(res["novo_custo"]),
                    preco_venda=float(res["novo_preco_venda"]),
                    estoque_qtd=0,
                    estoque_peso=0,
                    ativo=True,
                )
                db.add(produto)
                db.flush()
                produtos_criados += 1

        if not produto:
            continue

        qtd = float(l["quantidade"])
        preco = float(l["preco_unitario"])
        custo_unit = produto.custo or 0.0
        custo_total = qtd * custo_unit
        receita = qtd * preco

        # Timestamp da venda: fim do dia para ficar após qualquer entrada do mesmo dia
        ts = datetime.combine(data_alvo, datetime.min.time()) + timedelta(hours=23, minutes=59)

        # Baixa estoque proporcional ao peso médio atual
        peso_baixado = 0.0
        if (produto.estoque_qtd or 0) > 0:
            peso_medio = (produto.estoque_peso or 0) / produto.estoque_qtd
            peso_baixado = qtd * peso_medio
            produto.estoque_qtd = max(0.0, (produto.estoque_qtd or 0) - qtd)
            produto.estoque_peso = max(0.0, (produto.estoque_peso or 0) - peso_baixado)

        # Registra venda
        venda = models.Venda(
            produto_id=produto.id,
            quantidade=qtd,
            preco_venda=preco,
            custo_total=custo_total,
            data=ts,
            data_fechamento=data_alvo,
        )
        db.add(venda)

        # Movimentação SAIDA espelho
        mov = models.Movimentacao(
            produto_id=produto.id,
            tipo="SAIDA",
            quantidade=qtd,
            peso=peso_baixado,
            custo_unitario=preco,
            data=ts,
        )
        db.add(mov)

        # Agregado para VDS
        agg = agg_sku.setdefault(produto.id, {"qtd": 0.0, "receita": 0.0, "custo": 0.0})
        agg["qtd"] += qtd
        agg["receita"] += receita
        agg["custo"] += custo_total

        vendas_criadas += 1

    # VendaDiariaSKU (upsert por produto na data)
    for pid, agg in agg_sku.items():
        existente = db.query(models.VendaDiariaSKU).filter(
            models.VendaDiariaSKU.produto_id == pid,
            models.VendaDiariaSKU.data == data_alvo,
        ).first()
        if existente:
            existente.quantidade += agg["qtd"]
            existente.receita += agg["receita"]
            existente.custo += agg["custo"]
            existente.preco_medio = existente.receita / existente.quantidade if existente.quantidade > 0 else 0
        else:
            db.add(models.VendaDiariaSKU(
                produto_id=pid,
                data=data_alvo,
                quantidade=agg["qtd"],
                receita=agg["receita"],
                custo=agg["custo"],
                preco_medio=(agg["receita"] / agg["qtd"]) if agg["qtd"] > 0 else 0,
            ))

    # HistoricoMargem tipo=dia (consolidado)
    total_receita = sum(a["receita"] for a in agg_sku.values())
    total_custo = sum(a["custo"] for a in agg_sku.values())
    margem_pct = (total_receita - total_custo) / total_receita if total_receita > 0 else 0.0
    alerta = margem_pct < 0.17 and total_receita > 0

    ts_dia = datetime.combine(data_alvo, datetime.min.time())
    hist = db.query(models.HistoricoMargem).filter(
        func.date(models.HistoricoMargem.data) == data_alvo,
        models.HistoricoMargem.tipo == "dia",
    ).first()
    if hist:
        hist.faturamento = total_receita
        hist.custo_total = total_custo
        hist.margem_pct = margem_pct
        hist.alerta_disparado = alerta
    elif total_receita > 0:
        db.add(models.HistoricoMargem(
            data=ts_dia,
            tipo="dia",
            margem_pct=margem_pct,
            faturamento=total_receita,
            custo_total=total_custo,
            alerta_disparado=alerta,
        ))

    db.commit()

    return {
        "data_alvo": data_alvo.isoformat(),
        "vendas_criadas": vendas_criadas,
        "vendas_removidas_antes": n_removidas,
        "produtos_criados": produtos_criados,
        "produtos_associados": produtos_associados,
        "linhas_ignoradas": linhas_ignoradas,
        "mensagens": mensagens,
    }
