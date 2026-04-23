"""
Seed idempotente do plano de contas padrão + config tributária default.
Rodado no startup; só cria o que falta.

Plano de contas simplificado (atacado/varejo brasileiro):
  3.x  RECEITAS (natureza CREDITO)
  4.x  DEDUÇÕES / CMV (natureza DEBITO)
  5.x  DESPESAS OPERACIONAIS (natureza DEBITO)
  6.x  DEPRECIAÇÃO (natureza DEBITO)
  7.x  RESULTADO FINANCEIRO (natureza variável)
  8.x  IR / CSLL (natureza DEBITO)
"""
from datetime import date
from sqlalchemy.orm import Session

from .. import models


PLANO_CONTAS_PADRAO = [
    # (codigo, nome, tipo, natureza)
    ("3.1",   "Receita Bruta de Vendas",         "RECEITA",    "CREDITO"),
    ("3.2",   "Devoluções de Venda",             "DEDUCAO",    "DEBITO"),
    ("3.3",   "Descontos Comerciais",            "DEDUCAO",    "DEBITO"),

    ("4.1",   "CMV - Custo Mercadoria Vendida",  "CMV",        "DEBITO"),

    ("5.1.1", "Comissão de Vendas",              "DESP_VENDA", "DEBITO"),
    ("5.1.2", "Frete de Saída",                  "DESP_VENDA", "DEBITO"),
    ("5.1.3", "Marketing e Publicidade",         "DESP_VENDA", "DEBITO"),
    ("5.1.4", "Embalagem para Venda",            "DESP_VENDA", "DEBITO"),

    ("5.2.1", "Aluguel",                         "DESP_ADMIN", "DEBITO"),
    ("5.2.2", "Folha de Pagamento",              "DESP_ADMIN", "DEBITO"),
    ("5.2.3", "Encargos Trabalhistas",           "DESP_ADMIN", "DEBITO"),
    ("5.2.4", "Energia Elétrica",                "DESP_ADMIN", "DEBITO"),
    ("5.2.5", "Água e Saneamento",               "DESP_ADMIN", "DEBITO"),
    ("5.2.6", "Internet e Telefonia",            "DESP_ADMIN", "DEBITO"),
    ("5.2.7", "Material de Escritório",          "DESP_ADMIN", "DEBITO"),
    ("5.2.8", "Contabilidade",                   "DESP_ADMIN", "DEBITO"),
    ("5.2.9", "Software e Assinaturas",          "DESP_ADMIN", "DEBITO"),
    ("5.2.10","Manutenção e Limpeza",            "DESP_ADMIN", "DEBITO"),
    ("5.2.99","Outras Despesas Administrativas", "DESP_ADMIN", "DEBITO"),

    ("6.1",   "Depreciação de Equipamentos",     "DEPREC",     "DEBITO"),
    ("6.2",   "Amortização de Intangíveis",      "DEPREC",     "DEBITO"),

    ("7.1",   "Juros Recebidos",                 "FIN",        "CREDITO"),
    ("7.2",   "Juros Pagos",                     "FIN",        "DEBITO"),
    ("7.3",   "Tarifas Bancárias",               "FIN",        "DEBITO"),

    ("8.1",   "IRPJ",                            "IR",         "DEBITO"),
    ("8.2",   "CSLL",                            "IR",         "DEBITO"),
]


def seed_plano_contas(db: Session) -> int:
    """Cria contas que ainda não existem. Retorna quantas foram criadas."""
    criadas = 0
    for codigo, nome, tipo, natureza in PLANO_CONTAS_PADRAO:
        existe = db.query(models.ContaContabil).filter(
            models.ContaContabil.codigo == codigo
        ).first()
        if existe:
            continue
        db.add(models.ContaContabil(
            codigo=codigo,
            nome=nome,
            tipo=tipo,
            natureza=natureza,
            ativa=True,
        ))
        criadas += 1
    if criadas > 0:
        db.commit()
    return criadas


def seed_config_tributaria_default(db: Session) -> bool:
    """
    Se não houver nenhuma config vigente (vigencia_fim IS NULL), cria uma
    default: Simples Nacional 8% (anexo I, faixa intermediária do comércio).
    Retorna True se criou.
    """
    existe = db.query(models.ConfigTributaria).filter(
        models.ConfigTributaria.vigencia_fim.is_(None)
    ).first()
    if existe:
        return False

    config = models.ConfigTributaria(
        regime="SIMPLES_NACIONAL",
        aliquota_simples=0.08,  # 8% sobre receita bruta (comércio, faixa média)
        aliquota_icms=0.0,
        aliquota_pis=0.0,
        aliquota_cofins=0.0,
        aliquota_irpj=0.0,
        aliquota_csll=0.0,
        presuncao_lucro_pct=0.08,
        vigencia_inicio=date.today().replace(day=1),
        vigencia_fim=None,
    )
    db.add(config)
    db.commit()
    return True


def seed_tudo(db: Session) -> dict:
    """Atalho para rodar os dois seeds. Retorna contadores."""
    contas = seed_plano_contas(db)
    config = seed_config_tributaria_default(db)
    return {"contas_criadas": contas, "config_criada": config}
