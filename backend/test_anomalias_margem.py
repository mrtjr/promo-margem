"""
Tests da nova classificação de anomalias de margem global (5 faixas).

Cobre o gap deixado pela versão anterior, que tratava simétricamente "abaixo"
e "acima" da faixa-alvo como mesma anomalia. Agora:
  < 17%             → margem_global_baixa_critica (alta)
  17% .. 17.5%      → margem_global_baixa (media)
  17.5% .. 19.5%    → silencioso (sem anomalia)
  > 19.5%           → margem_global_alta (info)
  >> média 30d      → margem_global_suspeita (media)
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from app import models
from app.services import analise_service


def setup_db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def _anomalias_margem_global(anomalias):
    """Filtra apenas anomalias do bloco 1 (margem global)."""
    tipos_globais = {
        "margem_global_baixa_critica",
        "margem_global_baixa",
        "margem_global_alta",
        "margem_global_suspeita",
    }
    return [a for a in anomalias if a.tipo in tipos_globais]


# ---------------------------------------------------------------------------
# 1) Margem < 17% → crítica (alta)
# ---------------------------------------------------------------------------
def test_margem_critica_abaixo_17():
    _, db = setup_db()
    anomalias = analise_service.detectar_anomalias(
        db, date(2026, 5, 1), classificacoes=[],
        margem_dia=0.14, faturamento_dia=10000.0, faturamento_media_7d=10000.0,
        margem_media_30d=0.18, margem_std_30d=0.01,
    )
    globais = _anomalias_margem_global(anomalias)
    assert len(globais) == 1
    assert globais[0].tipo == "margem_global_baixa_critica"
    assert globais[0].severidade == "alta"
    assert "abaixo da meta mínima" in globais[0].descricao


# ---------------------------------------------------------------------------
# 2) Margem entre 17% e 17.5% → baixa (media)
# ---------------------------------------------------------------------------
def test_margem_atencao_baixa():
    _, db = setup_db()
    anomalias = analise_service.detectar_anomalias(
        db, date(2026, 5, 1), classificacoes=[],
        margem_dia=0.172, faturamento_dia=10000.0, faturamento_media_7d=10000.0,
        margem_media_30d=0.18, margem_std_30d=0.01,
    )
    globais = _anomalias_margem_global(anomalias)
    assert len(globais) == 1
    assert globais[0].tipo == "margem_global_baixa"
    assert globais[0].severidade == "media"


# ---------------------------------------------------------------------------
# 3) Margem dentro da faixa-alvo (17.5% .. 19.5%) → silenciosa
# ---------------------------------------------------------------------------
def test_margem_saudavel_silenciosa():
    _, db = setup_db()
    for margem in (0.175, 0.18, 0.185, 0.19, 0.195):
        anomalias = analise_service.detectar_anomalias(
            db, date(2026, 5, 1), classificacoes=[],
            margem_dia=margem, faturamento_dia=10000.0, faturamento_media_7d=10000.0,
            margem_media_30d=0.18, margem_std_30d=0.01,
        )
        globais = _anomalias_margem_global(anomalias)
        assert len(globais) == 0, f"margem {margem} disparou anomalia indevida"


# ---------------------------------------------------------------------------
# 4) Margem acima de 19.5% mas dentro de 2σ → info (positivo, não alerta)
# ---------------------------------------------------------------------------
def test_margem_acima_meta_info():
    _, db = setup_db()
    # Margem 22% — acima da meta mas histórico volátil cobre essa faixa
    anomalias = analise_service.detectar_anomalias(
        db, date(2026, 5, 1), classificacoes=[],
        margem_dia=0.22, faturamento_dia=10000.0, faturamento_media_7d=10000.0,
        margem_media_30d=0.20, margem_std_30d=0.03,  # 22% < 20% + 2*3% = 26%
    )
    globais = _anomalias_margem_global(anomalias)
    assert len(globais) == 1
    assert globais[0].tipo == "margem_global_alta"
    assert globais[0].severidade == "info"
    assert "Resultado positivo" in globais[0].descricao


# ---------------------------------------------------------------------------
# 5) Margem muito acima do histórico → suspeita (provável erro de cadastro)
# ---------------------------------------------------------------------------
def test_margem_suspeita_com_historico():
    _, db = setup_db()
    # Margem 35% com histórico estável em 18% (σ=0.5pp): 35% >> 18% + 2*0.5%
    # E 35% > META_MAX (19%) × 1.3 = 24.7% → ambos critérios batem.
    anomalias = analise_service.detectar_anomalias(
        db, date(2026, 5, 1), classificacoes=[],
        margem_dia=0.35, faturamento_dia=10000.0, faturamento_media_7d=10000.0,
        margem_media_30d=0.18, margem_std_30d=0.005,
    )
    globais = _anomalias_margem_global(anomalias)
    assert len(globais) == 1
    assert globais[0].tipo == "margem_global_suspeita"
    assert globais[0].severidade == "media"
    assert "muito acima do histórico" in globais[0].descricao


# ---------------------------------------------------------------------------
# 5b) Sem histórico (std=0): margem alta NUNCA é "suspeita" — vira info.
# ---------------------------------------------------------------------------
def test_margem_alta_sem_historico_eh_info():
    _, db = setup_db()
    anomalias = analise_service.detectar_anomalias(
        db, date(2026, 5, 1), classificacoes=[],
        margem_dia=0.35, faturamento_dia=10000.0, faturamento_media_7d=10000.0,
        margem_media_30d=0.0, margem_std_30d=0.0,
    )
    globais = _anomalias_margem_global(anomalias)
    assert len(globais) == 1
    assert globais[0].tipo == "margem_global_alta"
    assert globais[0].severidade == "info"


# ---------------------------------------------------------------------------
# 6) _status_meta: acima da faixa NÃO é mais "atencao" — é "acima_meta"
# ---------------------------------------------------------------------------
def test_status_meta_acima_nao_eh_atencao():
    assert analise_service._status_meta(0.14, 1000) == "alerta"
    assert analise_service._status_meta(0.172, 1000) == "atencao"
    assert analise_service._status_meta(0.18, 1000) == "saudavel"
    assert analise_service._status_meta(0.195, 1000) == "saudavel"  # limite incl.
    assert analise_service._status_meta(0.22, 1000) == "acima_meta"
    assert analise_service._status_meta(0.35, 1000) == "acima_meta"
    assert analise_service._status_meta(0.18, 0) == "sem_vendas"


if __name__ == "__main__":
    test_margem_critica_abaixo_17()
    test_margem_atencao_baixa()
    test_margem_saudavel_silenciosa()
    test_margem_acima_meta_info()
    test_margem_suspeita_com_historico()
    test_margem_alta_sem_historico_eh_info()
    test_status_meta_acima_nao_eh_atencao()
    print("OK — 7 testes de anomalia de margem passaram.")
