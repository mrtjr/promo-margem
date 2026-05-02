from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
from ..utils.tz import hoje_brt, agora_brt
from typing import List, Optional, Dict, Any
from .. import models, schemas
import uuid

def _primeiro_grupo_id(db: Session) -> int:
    """
    Retorna o ID do primeiro grupo cadastrado (menor id). Usado como fallback
    quando entrada não especifica grupo. Levanta ValueError se não há nenhum
    — caller traduz pra 4xx adequado.
    """
    g = db.query(models.Grupo).order_by(models.Grupo.id.asc()).first()
    if not g:
        raise ValueError(
            "Nenhum grupo cadastrado no sistema. Cadastre pelo menos um grupo "
            "antes de registrar entradas."
        )
    return g.id


def registrar_entrada(db: Session, entrada: schemas.EntradaCreate):
    # Determine which product. Camadas de matching:
    #   1) produto_id explícito  2) código ERP  3) nome exato
    produto = None
    if entrada.produto_id:
        produto = db.query(models.Produto).filter(models.Produto.id == entrada.produto_id).first()

    codigo_norm = (entrada.codigo or "").strip() or None
    if not produto and codigo_norm:
        produto = db.query(models.Produto).filter(models.Produto.codigo == codigo_norm).first()

    if not produto and entrada.nome_produto:
        # Check if already exists by name
        produto = db.query(models.Produto).filter(models.Produto.nome == entrada.nome_produto).first()

        if not produto:
            # Create new product automatically. Aceita código se enviado —
            # fica disponível para matching futuro (ex.: CSV do ERP).
            # Fallback de grupo: se não enviou, usa o primeiro grupo cadastrado
            # (ordem por id), nunca um id hardcoded — evita FK órfã se grupo
            # 1 foi deletado historicamente.
            grupo_id_final = entrada.grupo_id or _primeiro_grupo_id(db)
            new_sku = f"AUTO-{uuid.uuid4().hex[:6].upper()}"
            produto = models.Produto(
                sku=new_sku,
                codigo=codigo_norm,
                nome=entrada.nome_produto,
                grupo_id=grupo_id_final,
                custo=entrada.custo_unitario,
                preco_venda=entrada.custo_unitario * 1.2, # Markup inicial de 20%
                estoque_qtd=0,
                estoque_peso=0
            )
            db.add(produto)
            db.commit()
            db.refresh(produto)

    # Se casou por nome/id mas o usuário informou código e o produto ainda
    # não tinha, aproveita pra adotar (sem quebrar unicidade).
    if produto and codigo_norm and not produto.codigo:
        conflito = db.query(models.Produto).filter(
            models.Produto.codigo == codigo_norm,
            models.Produto.id != produto.id,
        ).first()
        if not conflito:
            produto.codigo = codigo_norm

    if produto:
        # Se o produto estava inativo (soft-deleted por _desativar_se_orfao numa
        # exclusão anterior), reativa agora que chegou nova ENTRADA. Sem isso,
        # o produto soma estoque + movimentação mas continua invisível em
        # GET /produtos (que filtra ativo=True) — some de "Gestão de SKUs".
        if not produto.ativo:
            produto.ativo = True

        # Calculate new weighted average cost based on Total Weight
        total_peso_novo = entrada.quantidade * entrada.peso
        
        peso_atual = produto.estoque_peso
        custo_atual = produto.custo
        
        novo_peso_total = peso_atual + total_peso_novo
        
        if novo_peso_total > 0:
            # Custo Médio Ponderado (CMP) baseado no peso total
            novo_custo_medio = ((peso_atual * custo_atual) + (total_peso_novo * entrada.custo_unitario)) / novo_peso_total
            produto.custo = novo_custo_medio
        
        # Update Stock
        produto.estoque_qtd += entrada.quantidade
        produto.estoque_peso += total_peso_novo
        
        # Log movement
        mov = models.Movimentacao(
            produto_id=produto.id,
            tipo="ENTRADA",
            quantidade=entrada.quantidade,
            peso=entrada.peso,
            custo_unitario=entrada.custo_unitario,
            cidade=entrada.cidade,
        )
        db.add(mov)
        db.commit()
        return True
    return False

def registrar_entrada_bulk(db: Session, entradas: list) -> Dict[str, Any]:
    """
    Registra um lote de entradas. NÃO transacional — cada entrada tem commit
    próprio em registrar_entrada(). Falha de uma não afeta as outras.

    Retorna {registradas, total, erros}, no padrão BulkOperationResponse.
    """
    registradas = 0
    erros: List[Dict[str, Any]] = []
    for i, e in enumerate(entradas):
        try:
            ok = registrar_entrada(db, e)
            if ok:
                registradas += 1
            else:
                erros.append({
                    "indice": i,
                    "erro": "produto não pôde ser identificado nem criado (faltam dados)",
                })
        except ValueError as exc:
            erros.append({"indice": i, "erro": str(exc)})
        except Exception as exc:
            erros.append({"indice": i, "erro": f"falha inesperada: {exc}"})
    return {"registradas": registradas, "total": len(entradas), "erros": erros}


def backfill_vendas_diarias_sku(db: Session) -> dict:
    """
    Popula VendaDiariaSKU a partir do histórico de `Venda` existente.

    Idempotente: se VendaDiariaSKU já tiver dados, retorna sem alterar nada.
    Útil após migração do schema (Sprint 3) para habilitar análises e
    projeções sobre vendas anteriores sem perder histórico.

    Retorna dict com contadores: {skipped, vendas_lidas, dias_criados}.
    """
    if db.query(models.VendaDiariaSKU).count() > 0:
        return {"skipped": True, "vendas_lidas": 0, "dias_criados": 0}

    vendas = db.query(models.Venda).all()
    if not vendas:
        return {"skipped": False, "vendas_lidas": 0, "dias_criados": 0}

    agregado: dict = defaultdict(lambda: {"qtd": 0.0, "receita": 0.0, "custo": 0.0})
    for v in vendas:
        if v.data is None:
            continue
        dia = v.data.date() if hasattr(v.data, "date") else v.data
        key = (v.produto_id, dia)
        qtd = v.quantidade or 0
        preco = v.preco_venda or 0.0
        agregado[key]["qtd"] += qtd
        agregado[key]["receita"] += qtd * preco
        agregado[key]["custo"] += v.custo_total or 0.0

    dias_criados = 0
    for (produto_id, dia), vals in agregado.items():
        preco_medio = vals["receita"] / vals["qtd"] if vals["qtd"] > 0 else 0.0
        db.add(models.VendaDiariaSKU(
            produto_id=produto_id,
            data=dia,
            quantidade=vals["qtd"],
            receita=vals["receita"],
            custo=vals["custo"],
            preco_medio=preco_medio,
        ))
        dias_criados += 1
    db.commit()
    return {"skipped": False, "vendas_lidas": len(vendas), "dias_criados": dias_criados}

def registrar_venda_bulk(db: Session, vendas: list, data_fechamento: date = None) -> Dict[str, Any]:
    """
    Registra lote de vendas (fechamento do dia), baixa estoque, grava:
      - Venda (linha por item lançado)
      - Movimentacao (log SAIDA)
      - VendaDiariaSKU (agregado diário por SKU — upsert)
      - HistoricoMargem (snapshot consolidado do dia)

    data_fechamento: data alvo do fechamento (default = hoje). Permite refazer
    fechamento de dia retroativo sem perder histórico.

    Retorna {registradas, total, erros}, no padrão BulkOperationResponse.
    Vendas com produto_id inexistente são puladas e listadas em `erros`.
    """
    if data_fechamento is None:
        data_fechamento = hoje_brt()

    # Acumulador por produto para consolidar agregado diário
    agg_por_produto = {}
    registradas = 0
    erros: List[Dict[str, Any]] = []

    for i, v in enumerate(vendas):
        v_schema = schemas.VendaBulkItem(**v)
        produto = db.query(models.Produto).filter(models.Produto.id == v_schema.produto_id).first()
        if not produto:
            erros.append({
                "indice": i,
                "erro": f"produto_id {v_schema.produto_id} não encontrado",
            })
            continue
        registradas += 1

        custo_unit = produto.custo if produto.custo else 0.0
        receita_item = v_schema.quantidade * v_schema.preco_venda
        custo_item = v_schema.quantidade * custo_unit

        # Baixa estoque proporcional ao peso médio atual
        peso_baixado = 0.0
        if produto.estoque_qtd > 0:
            peso_medio_volume = produto.estoque_peso / produto.estoque_qtd
            peso_baixado = v_schema.quantidade * peso_medio_volume

            produto.estoque_qtd -= v_schema.quantidade
            produto.estoque_peso -= peso_baixado

            if produto.estoque_qtd < 0:
                produto.estoque_qtd = 0
            if produto.estoque_peso < 0:
                produto.estoque_peso = 0

        # Registro da venda individual
        # data_fechamento = dia contábil (fonte de verdade pros agregados).
        # data = timestamp do INSERT (log de auditoria), server_default preenche.
        venda_mod = models.Venda(
            produto_id=produto.id,
            quantidade=v_schema.quantidade,
            preco_venda=v_schema.preco_venda,
            custo_total=custo_item,
            data_fechamento=data_fechamento,
        )
        db.add(venda_mod)

        # Log de movimentação — `peso` guarda o peso_baixado total da venda,
        # assim a reversão (excluir venda) devolve exatamente o que foi tirado.
        mov = models.Movimentacao(
            produto_id=produto.id,
            tipo="SAIDA",
            quantidade=v_schema.quantidade,
            peso=peso_baixado,
            custo_unitario=v_schema.preco_venda
        )
        db.add(mov)

        # Acumula agregado diário
        if produto.id not in agg_por_produto:
            agg_por_produto[produto.id] = {
                "quantidade": 0.0,
                "receita": 0.0,
                "custo": 0.0,
            }
        agg_por_produto[produto.id]["quantidade"] += v_schema.quantidade
        agg_por_produto[produto.id]["receita"] += receita_item
        agg_por_produto[produto.id]["custo"] += custo_item

    # Upsert VendaDiariaSKU (por produto, na data_fechamento)
    for produto_id, agg in agg_por_produto.items():
        existente = db.query(models.VendaDiariaSKU).filter(
            models.VendaDiariaSKU.produto_id == produto_id,
            models.VendaDiariaSKU.data == data_fechamento
        ).first()

        if existente:
            existente.quantidade += agg["quantidade"]
            existente.receita += agg["receita"]
            existente.custo += agg["custo"]
            existente.preco_medio = (existente.receita / existente.quantidade) if existente.quantidade > 0 else 0
        else:
            nova = models.VendaDiariaSKU(
                produto_id=produto_id,
                data=data_fechamento,
                quantidade=agg["quantidade"],
                receita=agg["receita"],
                custo=agg["custo"],
                preco_medio=(agg["receita"] / agg["quantidade"]) if agg["quantidade"] > 0 else 0
            )
            db.add(nova)

    # Snapshot consolidado em HistoricoMargem (tipo=dia)
    total_receita = sum(a["receita"] for a in agg_por_produto.values())
    total_custo = sum(a["custo"] for a in agg_por_produto.values())
    margem_pct = (total_receita - total_custo) / total_receita if total_receita > 0 else 0
    alerta = margem_pct < 0.17 and total_receita > 0

    hist_existente = db.query(models.HistoricoMargem).filter(
        func.date(models.HistoricoMargem.data) == data_fechamento,
        models.HistoricoMargem.tipo == "dia"
    ).first()

    if hist_existente:
        hist_existente.faturamento += total_receita
        hist_existente.custo_total += total_custo
        hist_existente.margem_pct = (
            (hist_existente.faturamento - hist_existente.custo_total) / hist_existente.faturamento
            if hist_existente.faturamento > 0 else 0
        )
        hist_existente.alerta_disparado = hist_existente.margem_pct < 0.17
    else:
        hist = models.HistoricoMargem(
            data=datetime.combine(data_fechamento, datetime.min.time()),
            tipo="dia",
            margem_pct=margem_pct,
            faturamento=total_receita,
            custo_total=total_custo,
            alerta_disparado=alerta
        )
        db.add(hist)

    db.commit()
    return {
        "registradas": registradas,
        "total": len(vendas),
        "erros": erros,
    }


# ============================================================================
# Reversão de movimentações — exclusão com integridade de estoque, custo e
# agregados. Cada função é atômica: se falhar antes do commit, nada muda.
# ============================================================================

def _recalcular_produto_do_zero(db: Session, produto: models.Produto) -> dict:
    """
    Recalcula estoque (qtd + peso) e CMP do produto a partir do zero, varrendo
    TODAS as Movimentacoes restantes. Fonte canônica de verdade pós-exclusão.

    Semântica de `Movimentacao.peso`:
      - ENTRADA: peso unitário (peso contribuído = qtd × peso)
      - SAIDA:   peso total baixado da venda (peso consumido = peso)
      - QUEBRA:  peso total perdido (peso consumido = peso)

    CMP = Σ(peso_entrada_i × custo_unit_i) / Σ(peso_entrada_i)
    Se não sobrar entrada, CMP=0.

    QUEBRA reduz estoque (qtd e peso) mas NÃO altera CMP — o produto perdido
    sai pelo CMP atual, não muda a média ponderada das entradas remanescentes.

    Retorna dict {qtd, peso, custo, entradas, saidas, quebras} com o estado.
    """
    # 1 query única particionada em Python (vs 3 round-trips). Beneficia
    # diretamente do índice ix_mov_produto_data (m_009).
    movs = db.query(models.Movimentacao).filter(
        models.Movimentacao.produto_id == produto.id,
        models.Movimentacao.tipo.in_(("ENTRADA", "SAIDA", "QUEBRA")),
    ).all()
    entradas = [m for m in movs if m.tipo == "ENTRADA"]
    saidas = [m for m in movs if m.tipo == "SAIDA"]
    quebras = [m for m in movs if m.tipo == "QUEBRA"]

    # Soma ENTRADAS
    qtd_entrada = 0.0
    peso_entrada = 0.0
    valor_entrada = 0.0
    for e in entradas:
        q = e.quantidade or 0
        p_unit = e.peso or 0
        c_unit = e.custo_unitario or 0
        peso_parcela = q * p_unit
        qtd_entrada += q
        peso_entrada += peso_parcela
        valor_entrada += peso_parcela * c_unit

    # Soma SAIDAS (peso já total)
    qtd_saida = sum((s.quantidade or 0) for s in saidas)
    peso_saida = sum((s.peso or 0) for s in saidas)

    # Soma QUEBRAS (peso já total — mesma semântica de SAIDA)
    qtd_quebra = sum((q.quantidade or 0) for q in quebras)
    peso_quebra = sum((q.peso or 0) for q in quebras)

    # Estoque efetivo
    produto.estoque_qtd = max(0.0, qtd_entrada - qtd_saida - qtd_quebra)
    produto.estoque_peso = max(0.0, peso_entrada - peso_saida - peso_quebra)
    # CMP inalterado por QUEBRA — só depende das ENTRADAS
    produto.custo = (valor_entrada / peso_entrada) if peso_entrada > 0 else 0.0

    return {
        "qtd": produto.estoque_qtd,
        "peso": produto.estoque_peso,
        "custo": produto.custo,
        "entradas": len(entradas),
        "saidas": len(saidas),
        "quebras": len(quebras),
    }


def _desativar_se_orfao(db: Session, produto: models.Produto) -> bool:
    """
    Se o produto ficou sem NENHUMA movimentação e sem NENHUMA venda histórica,
    marca como ativo=False (soft delete). Retorna True se desativou.
    """
    if not produto or not produto.ativo:
        return False
    tem_mov = db.query(models.Movimentacao).filter(
        models.Movimentacao.produto_id == produto.id
    ).first() is not None
    tem_venda = db.query(models.Venda).filter(
        models.Venda.produto_id == produto.id
    ).first() is not None
    tem_vds = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == produto.id
    ).first() is not None
    if not tem_mov and not tem_venda and not tem_vds:
        produto.ativo = False
        return True
    return False


def excluir_entrada(db: Session, movimentacao_id: int) -> dict:
    """
    Exclui uma Movimentacao tipo=ENTRADA:
      1. Deleta a Movimentacao
      2. Recalcula estoque e CMP do produto a partir das movimentações restantes
      3. Se produto ficou órfão (zero movimentações + zero vendas), desativa

    Retorna dict com produto afetado e estado resultante.
    Levanta ValueError se id não existe ou é tipo=SAIDA.
    """
    mov = db.query(models.Movimentacao).filter(
        models.Movimentacao.id == movimentacao_id
    ).first()
    if not mov:
        raise ValueError(f"Movimentação {movimentacao_id} não encontrada")
    if mov.tipo != "ENTRADA":
        raise ValueError(
            f"Movimentação {movimentacao_id} não é ENTRADA (é {mov.tipo}). "
            "Use DELETE /vendas/<id>."
        )

    produto = db.query(models.Produto).filter(models.Produto.id == mov.produto_id).first()
    produto_id = mov.produto_id

    db.delete(mov)
    db.flush()

    if not produto:
        db.commit()
        return {
            "produto_id": produto_id,
            "produto_nome": None,
            "estoque_qtd": 0,
            "custo": 0,
            "desativado": False,
        }

    estado = _recalcular_produto_do_zero(db, produto)
    desativado = _desativar_se_orfao(db, produto)

    db.commit()
    db.refresh(produto)
    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "estoque_qtd": produto.estoque_qtd,
        "estoque_peso": produto.estoque_peso,
        "custo": produto.custo,
        "entradas_restantes": estado["entradas"],
        "saidas_restantes": estado["saidas"],
        "desativado": desativado,
    }


def excluir_venda(db: Session, venda_id: int) -> dict:
    """
    Exclui uma Venda:
      1. Devolve quantidade + peso ao estoque do produto
      2. Decrementa (ou deleta) o VendaDiariaSKU correspondente
      3. Decrementa (ou deleta) o HistoricoMargem do dia
      4. Deleta a Movimentacao SAIDA irmã (match por produto+data+qtd)
      5. Deleta a Venda

    Retorna dict com produto afetado e estado pós.
    """
    venda = db.query(models.Venda).filter(models.Venda.id == venda_id).first()
    if not venda:
        raise ValueError(f"Venda {venda_id} não encontrada")

    produto = db.query(models.Produto).filter(models.Produto.id == venda.produto_id).first()
    qtd = venda.quantidade or 0
    receita_venda = qtd * (venda.preco_venda or 0)
    custo_venda = venda.custo_total or 0
    # Dia contábil: prioriza data_fechamento (novo campo). Fallback pro timestamp
    # do INSERT (legado) só se data_fechamento for NULL.
    dia_venda: date = (
        venda.data_fechamento
        or (venda.data.date() if venda.data else hoje_brt())
    )

    # 1. Tenta casar com Movimentacao SAIDA irmã (±2s e mesma qtd/produto)
    peso_devolver = 0.0
    mov_irma: Optional[models.Movimentacao] = None
    if venda.data:
        janela = timedelta(seconds=2)
        candidatas = db.query(models.Movimentacao).filter(
            models.Movimentacao.produto_id == venda.produto_id,
            models.Movimentacao.tipo == "SAIDA",
            models.Movimentacao.quantidade == qtd,
            models.Movimentacao.data >= venda.data - janela,
            models.Movimentacao.data <= venda.data + janela,
        ).all()
        if len(candidatas) == 1:
            mov_irma = candidatas[0]
        elif len(candidatas) > 1:
            # múltiplas vendas no mesmo instante — pega a mais próxima
            mov_irma = min(candidatas, key=lambda m: abs((m.data - venda.data).total_seconds()))
    if mov_irma:
        peso_devolver = mov_irma.peso or 0.0

    # 2. Decrementa VendaDiariaSKU
    vds = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == venda.produto_id,
        models.VendaDiariaSKU.data == dia_venda,
    ).first()
    if vds:
        vds.quantidade -= qtd
        vds.receita -= receita_venda
        vds.custo -= custo_venda
        if vds.quantidade <= 0.0001 or vds.receita <= 0.01:
            db.delete(vds)
        else:
            vds.preco_medio = vds.receita / vds.quantidade if vds.quantidade > 0 else 0

    # 3. Decrementa HistoricoMargem (tipo=dia)
    hist = db.query(models.HistoricoMargem).filter(
        func.date(models.HistoricoMargem.data) == dia_venda,
        models.HistoricoMargem.tipo == "dia",
    ).first()
    if hist:
        hist.faturamento = max(0.0, hist.faturamento - receita_venda)
        hist.custo_total = max(0.0, hist.custo_total - custo_venda)
        if hist.faturamento <= 0.01:
            db.delete(hist)
        else:
            hist.margem_pct = (hist.faturamento - hist.custo_total) / hist.faturamento
            hist.alerta_disparado = hist.margem_pct < 0.17

    # 4. Deleta movimentação irmã (se achou) e a venda
    if mov_irma:
        db.delete(mov_irma)
    db.delete(venda)
    db.flush()

    # 5. Recalcula estoque/custo a partir do log remanescente (fonte de verdade)
    desativado = False
    if produto:
        _recalcular_produto_do_zero(db, produto)
        desativado = _desativar_se_orfao(db, produto)

    db.commit()
    if produto:
        db.refresh(produto)

    return {
        "venda_id": venda_id,
        "produto_id": venda.produto_id,
        "produto_nome": produto.nome if produto else None,
        "estoque_qtd_apos": produto.estoque_qtd if produto else 0,
        "movimentacao_irma_encontrada": mov_irma is not None,
        "desativado": desativado,
    }


def reconciliar_agregados(db: Session) -> dict:
    """
    Recria VendaDiariaSKU e HistoricoMargem do zero a partir de Venda.

    Venda é a única fonte de verdade. Os agregados são caches recalculáveis.
    Esta função:
      1. Apaga TODOS os VendaDiariaSKU e HistoricoMargem (tipo=dia)
      2. Agrega Venda por (produto_id, data_fechamento) → VDS
      3. Agrega Venda por data_fechamento → HistoricoMargem tipo=dia

    Corrige automaticamente qualquer órfão: se não tem Venda na base, nenhum
    agregado é criado.

    Retorna: {vendas_lidas, vds_criados, hist_criados, vds_antes, hist_antes}
    """
    # Estado "antes" (só pra log)
    vds_antes = db.query(models.VendaDiariaSKU).count()
    hist_antes = db.query(models.HistoricoMargem).filter(
        models.HistoricoMargem.tipo == "dia"
    ).count()

    # 1. Wipe agregados (só tipo=dia do HistoricoMargem — semana/mes ficam intactos)
    db.query(models.VendaDiariaSKU).delete(synchronize_session=False)
    db.query(models.HistoricoMargem).filter(
        models.HistoricoMargem.tipo == "dia"
    ).delete(synchronize_session=False)
    db.flush()

    vendas = db.query(models.Venda).all()
    if not vendas:
        db.commit()
        return {
            "vendas_lidas": 0,
            "vds_criados": 0,
            "hist_criados": 0,
            "vds_antes": vds_antes,
            "hist_antes": hist_antes,
        }

    # 2. Agrega por (produto_id, data_fechamento)
    from collections import defaultdict
    agg_sku: dict = defaultdict(lambda: {"qtd": 0.0, "receita": 0.0, "custo": 0.0})
    agg_dia: dict = defaultdict(lambda: {"receita": 0.0, "custo": 0.0})

    for v in vendas:
        # Fallback robusto: data_fechamento > data::date > hoje
        dia = v.data_fechamento
        if dia is None and v.data:
            dia = v.data.date() if hasattr(v.data, "date") else v.data
        if dia is None:
            continue
        qtd = v.quantidade or 0
        preco = v.preco_venda or 0.0
        receita = qtd * preco
        custo = v.custo_total or 0.0
        agg_sku[(v.produto_id, dia)]["qtd"] += qtd
        agg_sku[(v.produto_id, dia)]["receita"] += receita
        agg_sku[(v.produto_id, dia)]["custo"] += custo
        agg_dia[dia]["receita"] += receita
        agg_dia[dia]["custo"] += custo

    # 3. Recria VendaDiariaSKU
    for (produto_id, dia), vals in agg_sku.items():
        preco_medio = vals["receita"] / vals["qtd"] if vals["qtd"] > 0 else 0.0
        db.add(models.VendaDiariaSKU(
            produto_id=produto_id,
            data=dia,
            quantidade=vals["qtd"],
            receita=vals["receita"],
            custo=vals["custo"],
            preco_medio=preco_medio,
        ))

    # 4. Recria HistoricoMargem tipo=dia
    for dia, vals in agg_dia.items():
        margem = (vals["receita"] - vals["custo"]) / vals["receita"] if vals["receita"] > 0 else 0.0
        db.add(models.HistoricoMargem(
            data=datetime.combine(dia, datetime.min.time()),
            tipo="dia",
            margem_pct=margem,
            faturamento=vals["receita"],
            custo_total=vals["custo"],
            alerta_disparado=margem < 0.17 and vals["receita"] > 0,
        ))

    db.commit()
    return {
        "vendas_lidas": len(vendas),
        "vds_criados": len(agg_sku),
        "hist_criados": len(agg_dia),
        "vds_antes": vds_antes,
        "hist_antes": hist_antes,
    }


def reconciliar_estoques(db: Session) -> dict:
    """
    Reconciliação global: para cada produto ativo, recalcula estoque e CMP a
    partir do log de Movimentacoes. Corrige estado legado inconsistente.
    Não apaga produtos, só normaliza os números (e desativa órfãos puros).

    Retorna {produtos_verificados, produtos_ajustados, produtos_desativados,
    detalhes: [{id, nome, antes, depois}]}
    """
    produtos = db.query(models.Produto).all()
    ajustados = 0
    desativados = 0
    detalhes = []

    for p in produtos:
        antes = {"qtd": p.estoque_qtd, "peso": p.estoque_peso, "custo": p.custo, "ativo": p.ativo}
        _recalcular_produto_do_zero(db, p)
        if _desativar_se_orfao(db, p):
            desativados += 1
        depois = {"qtd": p.estoque_qtd, "peso": p.estoque_peso, "custo": p.custo, "ativo": p.ativo}
        mudou = any(abs(antes[k] - depois[k]) > 0.0001 for k in ("qtd", "peso", "custo")) or antes["ativo"] != depois["ativo"]
        if mudou:
            ajustados += 1
            detalhes.append({
                "produto_id": p.id,
                "produto_nome": p.nome,
                "antes": antes,
                "depois": depois,
            })

    db.commit()
    return {
        "produtos_verificados": len(produtos),
        "produtos_ajustados": ajustados,
        "produtos_desativados": desativados,
        "detalhes": detalhes,
    }


def listar_historico_movimentacoes(
    db: Session,
    dias: int = 30,
    tipo: Optional[str] = None,
    produto_id: Optional[int] = None,
) -> List[dict]:
    """
    Lista movimentações recentes unificando ENTRADAS e SAÍDAS, com produto_nome
    resolvido. Para SAÍDAS inclui o venda_id (quando encontrado), assim a UI
    pode chamar DELETE /vendas/<id> em vez de DELETE /entradas/<id>.

    dias: janela (default 30). tipo: ENTRADA | SAIDA | None (ambos).
    """
    cutoff = agora_brt() - timedelta(days=dias)
    q = db.query(models.Movimentacao, models.Produto).outerjoin(
        models.Produto, models.Produto.id == models.Movimentacao.produto_id
    ).filter(models.Movimentacao.data >= cutoff)
    if tipo in ("ENTRADA", "SAIDA"):
        q = q.filter(models.Movimentacao.tipo == tipo)
    if produto_id:
        q = q.filter(models.Movimentacao.produto_id == produto_id)
    q = q.order_by(models.Movimentacao.data.desc())

    resultado = []
    for mov, prod in q.all():
        venda_id: Optional[int] = None
        if mov.tipo == "SAIDA" and mov.data:
            janela = timedelta(seconds=2)
            cand = db.query(models.Venda).filter(
                models.Venda.produto_id == mov.produto_id,
                models.Venda.quantidade == mov.quantidade,
                models.Venda.data >= mov.data - janela,
                models.Venda.data <= mov.data + janela,
            ).first()
            if cand:
                venda_id = cand.id

        resultado.append({
            "movimentacao_id": mov.id,
            "venda_id": venda_id,
            "tipo": mov.tipo,
            "produto_id": mov.produto_id,
            "produto_nome": prod.nome if prod else "(produto excluído)",
            "produto_sku": prod.sku if prod else None,
            "quantidade": mov.quantidade or 0,
            "peso": mov.peso or 0,
            "custo_unitario": mov.custo_unitario or 0,
            "valor_total": (mov.quantidade or 0) * (mov.custo_unitario or 0),
            "cidade": mov.cidade,
            "motivo": mov.motivo,
            "data": mov.data.isoformat() if mov.data else None,
        })
    return resultado
