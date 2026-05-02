"""
Tests do helper de timezone (app.utils.tz).

Garante que `hoje_brt()` e `agora_brt()` retornam wall-clock em
America/Sao_Paulo independente do TZ do container, e que o efeito
prático é "vendas registradas às 22h BRT contam como dia atual,
mesmo se o container estiver em UTC (já passou da meia-noite)".
"""
import os
import sys
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime
from zoneinfo import ZoneInfo
from app.utils.tz import hoje_brt, agora_brt, TZ_BR


# ---------------------------------------------------------------------------
# 1) hoje_brt() retorna data em BRT, não UTC.
#    Cenário: 02:00 UTC do dia 2 → 23:00 BRT do dia 1.
# ---------------------------------------------------------------------------
def test_hoje_brt_madrugada_utc_eh_dia_anterior_em_brt():
    instante_utc = datetime(2026, 5, 2, 2, 0, 0, tzinfo=ZoneInfo("UTC"))

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return instante_utc.replace(tzinfo=None)
            return instante_utc.astimezone(tz)

    with patch("app.utils.tz.datetime", FakeDatetime):
        assert hoje_brt() == date(2026, 5, 1), \
            "às 02h UTC, em BRT (UTC-3) ainda é 23h do dia anterior"


# ---------------------------------------------------------------------------
# 2) hoje_brt() retorna data BRT mesmo quando UTC já mudou de dia.
#    Cenário inverso: 12:00 UTC do dia 2 → 09:00 BRT do dia 2 (mesmo dia).
# ---------------------------------------------------------------------------
def test_hoje_brt_meio_dia_utc_eh_mesmo_dia_em_brt():
    instante_utc = datetime(2026, 5, 2, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return instante_utc.replace(tzinfo=None)
            return instante_utc.astimezone(tz)

    with patch("app.utils.tz.datetime", FakeDatetime):
        assert hoje_brt() == date(2026, 5, 2)


# ---------------------------------------------------------------------------
# 3) agora_brt() retorna naive datetime com wall-clock em BRT.
# ---------------------------------------------------------------------------
def test_agora_brt_e_naive_e_em_brt():
    instante_utc = datetime(2026, 5, 2, 2, 30, 0, tzinfo=ZoneInfo("UTC"))

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return instante_utc.replace(tzinfo=None)
            return instante_utc.astimezone(tz)

    with patch("app.utils.tz.datetime", FakeDatetime):
        n = agora_brt()
        assert n.tzinfo is None, "deve ser naive para casar com colunas DateTime"
        assert n == datetime(2026, 5, 1, 23, 30, 0)


# ---------------------------------------------------------------------------
# 4) TZ_BR resolve America/Sao_Paulo (não UTC, não fixed-offset).
# ---------------------------------------------------------------------------
def test_tz_br_e_america_sao_paulo():
    # ZoneInfo.key existe em zoneinfo do Python 3.9+
    assert TZ_BR.key == "America/Sao_Paulo"


# ---------------------------------------------------------------------------
# 5) Smoke test sem mock: hoje_brt() ≤ agora_brt().date() (consistência).
# ---------------------------------------------------------------------------
def test_consistencia_real():
    h = hoje_brt()
    a = agora_brt().date()
    assert h == a, f"hoje_brt={h} divergiu de agora_brt.date()={a}"


if __name__ == "__main__":
    test_hoje_brt_madrugada_utc_eh_dia_anterior_em_brt()
    test_hoje_brt_meio_dia_utc_eh_mesmo_dia_em_brt()
    test_agora_brt_e_naive_e_em_brt()
    test_tz_br_e_america_sao_paulo()
    test_consistencia_real()
    print("OK — 5 testes de timezone passaram.")
