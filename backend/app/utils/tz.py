"""
Helpers de timezone para o PromoMargem.

O backend roda em container Docker. Sem TZ explícito (caso anterior), o
`date.today()` do Python retornava UTC, fazendo vendas registradas após
21h BRT caírem no "dia seguinte" do banco. Este módulo centraliza o
conceito de "hoje" e "agora" em America/Sao_Paulo, independente do TZ
do container — `zoneinfo` lê /usr/share/zoneinfo diretamente.

Uso:
    from app.utils.tz import hoje_brt, agora_brt
    h = hoje_brt()        # date em fuso BRT (substitui date.today())
    n = agora_brt()       # datetime naive em BRT (substitui datetime.now()
                          # mantendo compatibilidade com colunas DateTime
                          # naive já existentes no banco)
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ_BR = ZoneInfo("America/Sao_Paulo")


def hoje_brt() -> date:
    """Data atual em America/Sao_Paulo. Substitui `date.today()`."""
    return datetime.now(TZ_BR).date()


def agora_brt() -> datetime:
    """
    Datetime atual em America/Sao_Paulo, retornado naive (sem tzinfo) para
    manter compatibilidade com colunas DateTime existentes no banco que
    foram gravadas como naive. Wall-clock equivalente a `datetime.now()`
    rodando em servidor BRT.
    """
    return datetime.now(TZ_BR).replace(tzinfo=None)
