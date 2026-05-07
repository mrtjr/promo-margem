"""
Importação de Fechamento de Vendas via CSV (formato ERP: xRelVendaAnalitica).

Pipeline:
  1. parse_csv()         → decodifica (latin-1), extrai linhas "Pedido"
  2. _agregar_linhas()   → soma qty e calcula preço médio ponderado por SKU
                           (mesmo produto vendido em N pedidos diferentes vira
                            1 linha agregada no preview — facilita revisão)
  3. build_preview()     → matching por código / nome + validação aritmética
  4. commit_importacao() → aplica resoluções, cria vendas, substitui fechamento do dia

Camadas de verificação:
  Identidade:
    - Match por `codigo` (exato)   → camada 1
    - Fallback por nome normalizado → camada 2
    - Conflito (código casa A, nome casa B) → "conflito" (user resolve)
    - Sem match → "sem_match" (user resolve)

  Aritmética (na linha agregada):
    - |qtd × v_unit − total| ≤ max(0,05, total × 0,1%)
        → tolerância 5 centavos absoluta OU 0,1 % relativa, o maior dos dois.
        Cobre arredondamento do ERP em pedidos grandes (ex: 30 × 9,47 = 284,10
        mas total CSV = 284,00) sem mascarar erros materiais.
    - qtd > 0 e qtd < 10000

  Janela temporal:
    - Linhas com data fora de `data_alvo` recebem status "fora_periodo" e NÃO
      entram no totalizador nem viram venda. Aparecem no preview separadas.

Custo usado nas vendas = `produto.custo` atual (CMP). CMV do CSV é ignorado
por decisão de produto (entrada manual é a fonte de verdade pro custo).
"""
from __future__ import annotations

import re
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


def _detectar_formato(texto: str) -> str:
    """
    Retorna 'analitico' (xRelVendaAnalitica — col0 == 'Pedido') ou
    'dinamico' (xRelatorioDinamico — col0 == 'NNNN / PV / Emp: N').

    Default 'analitico' mantém retrocompat com instalações antigas.
    """
    for linha in texto.splitlines()[:30]:
        col0 = linha.split(";", 1)[0].strip()
        if col0 == "Pedido":
            return "analitico"
        if "/ PV /" in col0 or "/ NF /" in col0:
            return "dinamico"
        if col0 == "Documento":
            # header do xRelatorioDinamico
            return "dinamico"
    return "analitico"


_PRODUTO_DINAMICO_RE = re.compile(r"^(\S+?)-(.+)$")


def _parse_csv_analitico(texto: str) -> List[LinhaCSV]:
    """
    Parser para o formato xRelVendaAnalitica (legado). 13+ colunas:
      0: 'Pedido'
      1: nº pedido
      2: data (DD/MM/YYYY)
      3: código do produto (ERP)
      4: nome do produto
      10: quantidade (BR decimal)
      11: valor unitário (BR decimal)
      12: total (BR decimal)
    """
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
            continue

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


def _parse_csv_dinamico(texto: str) -> List[LinhaCSV]:
    """
    Parser para o formato xRelatorioDinamico (novo, 11 colunas):
      0: Documento  → 'NNNN / PV / Emp: N'
      1: Data       → DD/MM/YYYY
      2: Cliente
      3: Vend.
      4: Produto    → '<codigo>-<nome>' (ex: '54-CEBOLA ROXA CX1')
      5: Unid       → 'SC', 'KG', 'UN'...
      6: Qtd        → BR decimal
      7: CMV Total  → BR decimal (ignorado: custo vem do CMP no banco)
      8: Liquido Total → total real cobrado (entra como `total`)
      9: (vazio)
      10: Lista Total → preço de tabela (ignorado)

    Preço unitário não vem explícito no CSV — calculado como
    `total_liquido / qtd`. Tolerância aritmética (±0,1%) em _validar_linha
    absorve diferenças de arredondamento do ERP.
    """
    linhas: List[LinhaCSV] = []
    idx = 0
    for raw in StringIO(texto):
        parts = raw.rstrip("\r\n").split(";")
        if len(parts) < 9:
            continue
        col0 = parts[0].strip()
        # Filtros: ignora header / linhas de relatorio / branco
        if not col0 or col0 == "Documento":
            continue
        if "Emiss" in col0 or "Vendas" in parts[0] or "Página" in raw:
            continue
        if "/ PV /" not in col0 and "/ NF /" not in col0:
            continue

        produto_str = parts[4].strip()
        if not produto_str:
            continue

        # Extrai <codigo>-<nome>; se nao bater, mantem nome puro sem codigo
        m = _PRODUTO_DINAMICO_RE.match(produto_str)
        if m:
            codigo = m.group(1).strip()
            nome = m.group(2).strip()
        else:
            codigo = None
            nome = produto_str

        qtd = _parse_num_br(parts[6])
        total = _parse_num_br(parts[8])  # Liquido Total
        preco_unit = (total / qtd) if qtd > 0 else 0.0

        # numero do pedido = parte antes do primeiro '/'
        pedido_num = col0.split("/", 1)[0].strip() or None

        idx += 1
        linhas.append(LinhaCSV(
            idx=idx,
            pedido=pedido_num,
            codigo=codigo,
            nome=nome,
            quantidade=qtd,
            preco_unitario=round(preco_unit, 4),
            total=total,
            data=_parse_data_br(parts[1]),
        ))
    return linhas


def parse_csv(conteudo_bytes: bytes) -> List[LinhaCSV]:
    """
    Parser dispatcher. Detecta automaticamente entre dois formatos do ERP:
      - xRelVendaAnalitica (legado, col0 = 'Pedido', 13+ colunas com v_unit)
      - xRelatorioDinamico (novo,  col0 = 'NNNN / PV / Emp: N', 11 colunas)

    Tenta latin-1 → utf-8 → cp1252 como fallback silencioso de encoding.
    """
    for enc in ("latin-1", "utf-8", "cp1252"):
        try:
            texto = conteudo_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Não foi possível decodificar o CSV (latin-1/utf-8/cp1252).")

    formato = _detectar_formato(texto)
    if formato == "dinamico":
        return _parse_csv_dinamico(texto)
    return _parse_csv_analitico(texto)





# ---------------------------------------------------------------------------
# Agregação por SKU
# ---------------------------------------------------------------------------

@dataclass
class LinhaAgregada:
    """
    Soma de N linhas do CSV que apontam para o mesmo SKU.
    Preserva idx originais para auditoria. preco_unitario é a média ponderada
    pela quantidade.
    """
    idx: int                 # idx do primeiro grupo (estável p/ resolução)
    pedidos: List[str]       # lista de números de pedido envolvidos
    codigo: Optional[str]
    nome: str
    quantidade: float        # soma
    preco_unitario: float    # média ponderada
    total: float             # soma
    data: Optional[date]     # data da janela (todas as linhas têm data == data_alvo após filtro)
    ocorrencias: int         # nº de linhas CSV que viraram este agregado
    idx_originais: List[int] # auditoria


def _chave_agregacao(linha: LinhaCSV) -> str:
    """
    Chave para agrupar linhas do mesmo SKU. Prioridade:
      1. código ERP, se preenchido (sem ambiguidade)
      2. nome normalizado (sem acento, lowercase) como fallback
    Linhas sem código nem nome ficariam num bucket "" — descartadas.
    """
    if linha.codigo and linha.codigo.strip():
        return f"COD::{linha.codigo.strip()}"
    if linha.nome:
        return f"NOM::{normalizar_nome(linha.nome)}"
    return ""


def _agregar_linhas(linhas: List[LinhaCSV]) -> List[LinhaAgregada]:
    """
    Agrupa linhas por SKU (código ou nome normalizado), soma quantidades e
    calcula preço unitário médio ponderado pela quantidade.

    Por que agregar antes do preview?
      Um único dia tem várias vendas para o mesmo SKU (caixas, cliente A,
      cliente B…). Mostrar 8× MANGA PALMER no preview força o usuário a
      resolver match 8 vezes. Agregando, ele resolve 1 vez.

    Idempotência aritmética: a média ponderada permite que o `total_agg ≈
    qtd_agg × preco_agg` valide igual ao raw — mantém a checagem de sanidade
    útil mesmo após agregação.
    """
    grupos: Dict[str, Dict] = {}
    ordem_chaves: List[str] = []

    for l in linhas:
        chave = _chave_agregacao(l)
        if not chave:
            # linha sem identidade — preserva como agregado isolado
            chave = f"ORF::{l.idx}"

        if chave not in grupos:
            ordem_chaves.append(chave)
            grupos[chave] = {
                "idx_primeiro": l.idx,
                "pedidos": [],
                "codigo": l.codigo,
                "nome": l.nome,
                "qtd_total": 0.0,
                "soma_receita": 0.0,    # Σ(qtd × preco)
                "soma_total_csv": 0.0,  # Σ(total CSV)
                "data_primeira": l.data,
                "ocorrencias": 0,
                "idx_originais": [],
            }

        g = grupos[chave]
        if l.pedido and l.pedido not in g["pedidos"]:
            g["pedidos"].append(l.pedido)
        g["qtd_total"] += l.quantidade
        g["soma_receita"] += l.quantidade * l.preco_unitario
        g["soma_total_csv"] += l.total
        g["ocorrencias"] += 1
        g["idx_originais"].append(l.idx)

    # Materializa em LinhaAgregada (preço médio ponderado pela quantidade)
    result: List[LinhaAgregada] = []
    for chave in ordem_chaves:
        g = grupos[chave]
        qtd = g["qtd_total"]
        preco_medio = (g["soma_receita"] / qtd) if qtd > 0 else 0.0
        result.append(LinhaAgregada(
            idx=g["idx_primeiro"],
            pedidos=g["pedidos"],
            codigo=g["codigo"],
            nome=g["nome"],
            quantidade=qtd,
            preco_unitario=round(preco_medio, 4),
            total=round(g["soma_total_csv"], 2),
            data=g["data_primeira"],
            ocorrencias=g["ocorrencias"],
            idx_originais=g["idx_originais"],
        ))
    return result


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
    """Retorna (por_codigo, por_nome_normalizado). APENAS produtos ativos.

    Produtos soft-deleted (ativo=false) não devem ressuscitar silenciosamente
    via SAÍDA de CSV — a reativação só acontece por ENTRADA explícita (ver
    estoque_service.registrar_entrada). Incluir inativos aqui fazia o usuário
    enxergar match em fantasma depois de "apagar histórico"."""
    por_codigo: Dict[str, models.Produto] = {}
    por_nome: Dict[str, models.Produto] = {}
    for p in db.query(models.Produto).filter(models.Produto.ativo == True).all():
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

def _validar_linha(linha) -> List[str]:
    """
    Retorna lista de erros. Vazia = linha aritmeticamente válida.

    Aceita LinhaCSV ou LinhaAgregada (mesmos campos relevantes:
    quantidade, preco_unitario, total).

    Tolerância aritmética: max(0,05 absoluto, 0,1% relativo do total).
    Reduz falso-positivo em pedidos grandes onde o ERP arredonda preço
    unitário antes de gravar (ex: 30 × 9,47 = 284,10 mas total = 284,00 —
    diferença 0,10 é aceitável).
    """
    erros: List[str] = []
    if linha.quantidade <= 0:
        erros.append(f"Quantidade inválida: {linha.quantidade}.")
    if linha.quantidade >= 10000:
        erros.append(f"Quantidade absurdamente alta: {linha.quantidade}.")
    if linha.preco_unitario <= 0:
        erros.append(f"Preço unitário inválido: {linha.preco_unitario}.")
    esperado = round(linha.quantidade * linha.preco_unitario, 2)
    diff = abs(esperado - linha.total)
    tolerancia = max(0.05, abs(linha.total) * 0.001)
    if diff > tolerancia:
        erros.append(
            f"Aritmética inconsistente: {linha.quantidade} × {linha.preco_unitario} "
            f"= {esperado:.2f}, mas total no CSV = {linha.total:.2f} "
            f"(diferença {diff:.2f}, tolerância {tolerancia:.2f})."
        )
    return erros


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def build_preview(db: Session, conteudo_bytes: bytes, data_alvo: date) -> Dict:
    """
    Retorna dict compatível com schemas.CSVImportPreview.

    Pipeline:
      1. parse: linhas CSV individuais (1 por item de pedido)
      2. filtro temporal: linhas com data != data_alvo viram itens
         "fora_periodo" (não entram no total nem viram venda).
      3. agregação por SKU: mesmo produto vendido em vários pedidos vira
         uma linha de preview com qty somada e preço médio ponderado.
      4. matching + validação aritmética por agregado.
    """
    raw_linhas = parse_csv(conteudo_bytes)
    por_codigo, por_nome = _indices_produtos(db)

    # 1. separa as linhas que estão dentro / fora da janela alvo
    linhas_no_periodo: List[LinhaCSV] = []
    linhas_fora: List[LinhaCSV] = []
    for l in raw_linhas:
        if l.data is None or l.data == data_alvo:
            linhas_no_periodo.append(l)
        else:
            linhas_fora.append(l)

    # 2. agrega por SKU as que entrarão no fechamento
    agregadas = _agregar_linhas(linhas_no_periodo)

    linhas_out: List[Dict] = []
    receita_total = 0.0
    qtd_total = 0.0
    skus_distintos: set = set()
    ok = pend = erro = 0

    def _ocorrencias_label(n: int) -> str:
        return "" if n <= 1 else f" (×{n} pedidos)"

    for ag in agregadas:
        mensagens: List[str] = []
        status = "ok"

        # Validação aritmética (no agregado)
        erros_arit = _validar_linha(ag)
        if erros_arit:
            mensagens.extend(erros_arit)
            status = "erro"

        # Matching (LinhaAgregada compartilha .codigo e .nome com LinhaCSV
        # — _match só lê esses dois campos)
        status_match, produto, msgs_match = _match(ag, por_codigo, por_nome)
        mensagens.extend(msgs_match)
        if status != "erro":
            status = status_match

        if status == "ok" and produto and (produto.custo or 0) <= 0:
            status = "sem_custo"
            mensagens.append(
                f"Produto '{produto.nome}' (SKU {produto.sku}) está sem custo unitário. "
                "Informe o custo para gerar a venda."
            )

        if ag.ocorrencias > 1:
            mensagens.insert(
                0,
                f"Linha agregada de {ag.ocorrencias} ocorrência(s) do mesmo SKU "
                f"(qtd somada, preço médio ponderado).",
            )

        if status == "ok":
            ok += 1
            if produto:
                skus_distintos.add(produto.id)
        elif status == "erro":
            erro += 1
        else:
            pend += 1

        if status == "ok":
            receita_total += ag.total
            qtd_total += ag.quantidade

        linhas_out.append({
            "idx": ag.idx,
            "pedido": ", ".join(ag.pedidos[:3]) + ("…" if len(ag.pedidos) > 3 else "") if ag.pedidos else None,
            "codigo_csv": ag.codigo,
            "nome_csv": ag.nome + _ocorrencias_label(ag.ocorrencias),
            "quantidade": ag.quantidade,
            "preco_unitario": ag.preco_unitario,
            "total": ag.total,
            "data_csv": ag.data.isoformat() if ag.data else None,
            "status": status,
            "produto_id": produto.id if produto and status in ("ok", "sem_custo") else None,
            "produto_nome": produto.nome if produto and status in ("ok", "sem_custo") else None,
            "mensagens": mensagens,
            "ocorrencias": ag.ocorrencias,
            "idx_originais": ag.idx_originais,
        })

    # 3. linhas fora_periodo: entram no preview como referência (não somam)
    for l in linhas_fora:
        linhas_out.append({
            "idx": l.idx,
            "pedido": l.pedido,
            "codigo_csv": l.codigo,
            "nome_csv": l.nome,
            "quantidade": l.quantidade,
            "preco_unitario": l.preco_unitario,
            "total": l.total,
            "data_csv": l.data.isoformat() if l.data else None,
            "status": "fora_periodo",
            "produto_id": None,
            "produto_nome": None,
            "mensagens": [
                f"Data {l.data.isoformat() if l.data else '—'} fora da janela alvo "
                f"({data_alvo.isoformat()}); ignorada no fechamento."
            ],
            "ocorrencias": 1,
            "idx_originais": [l.idx],
        })

    ja_existe = db.query(models.Venda).filter(
        models.Venda.data_fechamento == data_alvo
    ).first() is not None

    return {
        "data_alvo": data_alvo.isoformat(),
        "total_linhas": len(linhas_out),
        "linhas_ok": ok,
        "linhas_pendentes": pend,
        "linhas_erro": erro,
        "linhas_fora_periodo": len(linhas_fora),
        "linhas_csv_brutas": len(raw_linhas),
        "linhas_agregadas": len(agregadas),
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

    # Apaga ENTRADAs-espelho criadas pelo próprio CSV import. Identificadas
    # pelo timestamp exato 00:00:00 do dia (commit_importacao usa
    # `datetime.combine(data_alvo, datetime.min.time())`); entradas manuais
    # via estoque_service.registrar_entrada caem em func.now() do banco e
    # nunca batem o midnight exato. Sem isso, re-importar o mesmo dia deixa
    # ENTRADAs órfãs (caso o user marque a linha original como IGNORAR no
    # 2º import) e o estoque vira positivo fantasma após recálculo.
    ts_csv_entrada = datetime.combine(dia, datetime.min.time())
    db.query(models.Movimentacao).filter(
        models.Movimentacao.tipo == "ENTRADA",
        models.Movimentacao.produto_id.in_(produtos_afetados),
        models.Movimentacao.data == ts_csv_entrada,
    ).delete(synchronize_session=False)

    # Apaga agregados do dia
    db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.data == dia
    ).delete(synchronize_session=False)

    db.query(models.HistoricoMargem).filter(
        func.date(models.HistoricoMargem.data) == dia,
        models.HistoricoMargem.tipo == "dia",
    ).delete(synchronize_session=False)

    db.flush()

    # Recalcula estoque dos produtos afetados a partir do log remanescente.
    # PRESERVA produto.custo quando o recalc zeraria por falta de ENTRADAS:
    # acabamos de deletar as ENTRADAs-espelho do CSV; o re-import vai
    # recompor o CMP com novas ENTRADAs. Sem o preserve, o re-import gera
    # SAIDAs com custo_unitario=0 (margem 100% errada).
    from . import estoque_service
    for pid in produtos_afetados:
        prod = db.query(models.Produto).filter(models.Produto.id == pid).first()
        if prod:
            custo_prev = prod.custo or 0
            estoque_service._recalcular_produto_do_zero(db, prod)
            if (prod.custo or 0) == 0 and custo_prev > 0:
                prod.custo = custo_prev

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
    # Linhas "fora_periodo" são ignoradas silenciosamente — nunca viram venda
    # nem precisam de resolução (estão fora da janela alvo por construção).
    for l in linhas:
        if l["status"] in ("ok", "fora_periodo"):
            continue
        res = res_by_idx.get(l["idx"])
        if not res:
            raise ValueError(
                f"Linha {l['idx']} ({l['nome_csv']}) tem status '{l['status']}' "
                "mas sem resolução enviada."
            )
        if res["acao"] not in ("associar", "criar", "ignorar", "corrigir_custo"):
            raise ValueError(f"Linha {l['idx']}: ação '{res['acao']}' inválida.")
        if res["acao"] == "associar" and not res.get("produto_id"):
            raise ValueError(f"Linha {l['idx']}: ação 'associar' exige produto_id.")
        if res["acao"] == "corrigir_custo":
            if not res.get("produto_id"):
                raise ValueError(f"Linha {l['idx']}: ação 'corrigir_custo' exige produto_id.")
            if float(res.get("novo_custo") or 0) <= 0:
                raise ValueError(f"Linha {l['idx']}: ação 'corrigir_custo' exige novo_custo > 0.")
        if res["acao"] == "criar":
            faltando = [
                k for k in ("novo_nome", "novo_grupo_id", "novo_preco_venda", "novo_custo")
                if not res.get(k)
            ]
            if faltando:
                raise ValueError(
                    f"Linha {l['idx']}: ação 'criar' exige {', '.join(faltando)}."
                )

    # PRÉ-RESOLUÇÃO: identifica o produto de cada linha ANTES de mexer no
    # banco, e exige custo > 0. Regra do negócio: uma SAÍDA sem custo unitário
    # registrado distorce a margem para 100%. Toda venda precisa de custo —
    # vindo do CMP (entradas anteriores) ou informado no "criar".
    produtos_sem_custo: List[str] = []
    for l in linhas:
        if l["status"] == "fora_periodo":
            continue
        if l["status"] == "ok":
            p = db.query(models.Produto).filter(models.Produto.id == l["produto_id"]).first()
            if not p:
                raise ValueError(f"Linha {l['idx']}: produto_id {l['produto_id']} não existe mais.")
            if (p.custo or 0) <= 0:
                produtos_sem_custo.append(f"{p.nome} (SKU {p.sku})")
        else:
            res = res_by_idx.get(l["idx"])
            if not res or res["acao"] == "ignorar":
                continue
            if res["acao"] == "associar":
                p = db.query(models.Produto).filter(models.Produto.id == res["produto_id"]).first()
                if not p:
                    raise ValueError(f"Linha {l['idx']}: produto_id {res['produto_id']} não existe.")
                if (p.custo or 0) <= 0:
                    produtos_sem_custo.append(f"{p.nome} (SKU {p.sku})")
            elif res["acao"] == "criar":
                if float(res.get("novo_custo") or 0) <= 0:
                    produtos_sem_custo.append(f"{res.get('novo_nome') or l['nome_csv']} (novo)")
            # corrigir_custo: o novo_custo já foi validado (>0) na validação de
            # resoluções acima; aqui nada a checar — custo será aplicado na
            # passagem principal antes de gerar a venda.

    if produtos_sem_custo:
        unicos = list(dict.fromkeys(produtos_sem_custo))
        raise ValueError(
            "Importação bloqueada: os produtos abaixo não têm custo unitário. "
            "Uma SAÍDA sem custo gera margem 100% (dado contábil errado). "
            "Registre primeiro uma Entrada de Estoque para definir o CMP "
            "ou informe o custo ao criar via CSV: " + "; ".join(unicos)
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
        # Sinaliza quando esta linha estabeleceu o custo do produto agora
        # (criar/reativar/corrigir_custo). Nestes casos, a SAÍDA precisa de
        # uma ENTRADA espelho — sem ela ficaria débito sem crédito no
        # Histórico de Movimentações e no CMP.
        estabeleceu_custo = False

        # Linhas fora_periodo nunca viram venda (estão fora da janela)
        if l["status"] == "fora_periodo":
            continue

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
            if res["acao"] == "corrigir_custo":
                # Produto existe mas estava com custo<=0. Atualiza o custo antes
                # de gerar a SAÍDA. (Origem correta do custo é a Entrada de
                # Estoque via CMP; esta é uma escotilha para destravar o
                # fechamento quando há dado legado sem histórico de entrada.)
                produto = db.query(models.Produto).filter(
                    models.Produto.id == res["produto_id"]
                ).first()
                if not produto:
                    raise ValueError(f"Linha {l['idx']}: produto_id {res['produto_id']} não existe.")
                produto.custo = float(res["novo_custo"])
                db.flush()
                estabeleceu_custo = True
            elif res["acao"] == "associar":
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
                # Resolução de unicidade do código:
                #   - Se já existe ATIVO com esse código → erro (provável duplicata na UI).
                #   - Se já existe INATIVO com esse código → reativa e atualiza (igual
                #     ao padrão de Entrada de Estoque). Evita o bloqueio "código já
                #     usado pelo SKU AUTO-…" causado por produtos soft-deleted que
                #     ainda detêm o código no índice UNIQUE.
                novo_codigo = (res["novo_codigo"].strip() if res.get("novo_codigo") else None)
                conflito = None
                if novo_codigo:
                    conflito = db.query(models.Produto).filter(
                        models.Produto.codigo == novo_codigo
                    ).first()
                if conflito and conflito.ativo:
                    raise ValueError(
                        f"Linha {l['idx']}: código '{novo_codigo}' já usado "
                        f"pelo SKU {conflito.sku} (ativo)."
                    )
                if conflito and not conflito.ativo:
                    # Reativa o produto fantasma com os dados do CSV
                    produto = conflito
                    produto.nome = res["novo_nome"].strip()
                    produto.grupo_id = res["novo_grupo_id"]
                    produto.custo = float(res["novo_custo"])
                    produto.preco_venda = float(res["novo_preco_venda"])
                    produto.ativo = True
                    db.flush()
                    produtos_criados += 1  # conta como "criado" do ponto de vista do user
                    estabeleceu_custo = True
                else:
                    produto = models.Produto(
                        sku=_proximo_sku_auto(db),
                        codigo=novo_codigo,
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
                    estabeleceu_custo = True

        if not produto:
            continue

        # Detecta produtos que ficaram sem ENTRADA histórica (cleanup de
        # re-import apagou as antigas, ou produto puro-CSV ainda virgem).
        # Sem ENTRADA-espelho a SAÍDA fica órfã no Histórico. Esta checagem
        # roda DEPOIS de _apagar_fechamento_do_dia, então enxerga o estado
        # pós-cleanup. Linhas "criar"/"corrigir_custo" já têm a flag setada
        # pela ação; aqui complementamos para "ok"/"associar" cujo histórico
        # foi limpo pela substituição.
        if not estabeleceu_custo:
            tem_entrada = db.query(models.Movimentacao).filter(
                models.Movimentacao.produto_id == produto.id,
                models.Movimentacao.tipo == "ENTRADA",
            ).first() is not None
            if not tem_entrada:
                estabeleceu_custo = True

        qtd = float(l["quantidade"])
        preco = float(l["preco_unitario"])
        custo_unit = produto.custo or 0.0
        custo_total = qtd * custo_unit
        receita = qtd * preco

        # Timestamp da venda: fim do dia para ficar após qualquer entrada do mesmo dia
        ts = datetime.combine(data_alvo, datetime.min.time()) + timedelta(hours=23, minutes=59)

        # ENTRADA espelho: quando o produto foi criado/reativado/teve custo
        # corrigido nesta importação OU quando ele perdeu o histórico de
        # ENTRADA na substituição, a SAÍDA da venda fica sem origem contábil.
        #
        # Regra (v0.13.1+): cria ENTRADA-espelho APENAS na quantidade que
        # falta para atender a venda — `max(0, qtd_venda - estoque_atual)`.
        # Quando o estoque já cobre a venda, não cria nada (evita poluir o
        # histórico com ENTRADAs fantasmas que não correspondem a compra real).
        #   - Caso 1 (produto novo): estoque=0 → entra qtd total da venda.
        #   - Caso 2 (estoque suficiente): nada é criado.
        #   - Caso 3 (estoque parcial): entra só o déficit.
        if estabeleceu_custo:
            estoque_atual = produto.estoque_qtd or 0
            qtd_entrada = max(0.0, qtd - estoque_atual)
            if qtd_entrada > 0:
                ts_entrada = datetime.combine(data_alvo, datetime.min.time())
                mov_in = models.Movimentacao(
                    produto_id=produto.id,
                    tipo="ENTRADA",
                    quantidade=qtd_entrada,
                    peso=0,  # CSV de fechamento não traz peso; entra zerado
                    custo_unitario=custo_unit,
                    data=ts_entrada,
                )
                db.add(mov_in)
                # Atualiza estoque para refletir a entrada parcial antes da
                # SAÍDA. Sem isso, a baixa abaixo deixaria o produto com
                # qtd negativa virtual quando estoque < venda.
                produto.estoque_qtd = estoque_atual + qtd_entrada

        # Baixa estoque proporcional ao peso médio atual
        peso_baixado = 0.0
        if (produto.estoque_qtd or 0) > 0:
            peso_medio = (produto.estoque_peso or 0) / produto.estoque_qtd if (produto.estoque_qtd or 0) > 0 else 0
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
