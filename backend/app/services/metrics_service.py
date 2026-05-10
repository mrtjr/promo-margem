"""
Metrics service — Sprint S1.5.

Agrega telemetria de adocao agentic LENDO event log + agent_runs.
NAO cria nova tabela — events sao a fonte da verdade.

Funcoes principais:
  - resumo_adocao(db, dias): metricas agregadas em janela
  - resumo_por_agente(db, dias): por agent_name
  - serie_diaria(db, dias): timeseries para grafico

Sem dependencias novas, sem cron, sem persistencia adicional.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, date as date_type
from typing import Any

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from .. import models


def resumo_adocao(db: Session, dias: int = 7) -> dict[str, Any]:
    """
    Resumo agregado de adocao agentic em janela de N dias.
    Janela default 7 dias (alinhado com fechamento semanal do produto).
    """
    desde = datetime.utcnow() - timedelta(days=dias)

    # Reconciliator runs no periodo
    reconciliator_runs = (
        db.query(models.AgentRun)
        .filter(
            models.AgentRun.agent_name == "reconciliator",
            models.AgentRun.started_at >= desde,
        )
        .all()
    )

    # Briefing runs no periodo
    briefing_runs = (
        db.query(models.AgentRun)
        .filter(
            models.AgentRun.agent_name == "briefing",
            models.AgentRun.started_at >= desde,
        )
        .all()
    )

    # AuditQA runs
    audit_runs = (
        db.query(models.AgentRun)
        .filter(
            models.AgentRun.agent_name == "auditqa",
            models.AgentRun.started_at >= desde,
        )
        .all()
    )

    # CSV commits — todos (via classico ou via Reconciliator). Distinguimos
    # via correlation_id: se commit.correlation_id bate com algum
    # reconciliator run -> via_reconciliator; senao via_wizard.
    commits = (
        db.query(models.Event)
        .filter(
            models.Event.entity == "csv_import",
            models.Event.action == "committed",
            models.Event.ts >= desde,
        )
        .all()
    )
    cids_reconciliator = {r.correlation_id for r in reconciliator_runs if r.correlation_id}

    via_reconciliator = sum(1 for c in commits if c.correlation_id in cids_reconciliator)
    via_wizard = len(commits) - via_reconciliator

    # Latency p95 do Reconciliator
    latencias = sorted(
        [r.latency_ms for r in reconciliator_runs if r.latency_ms is not None]
    )
    p95 = latencias[int(len(latencias) * 0.95)] if latencias else 0
    p50 = latencias[int(len(latencias) * 0.50)] if latencias else 0

    # Custo total LLM-judge (vindo de agent_run.cost_estimate quando llm_used)
    cost_total = sum(
        (r.cost_estimate or 0) for r in reconciliator_runs
    )

    # Findings AuditQA agregados via output_summary
    audit_total_findings = 0
    audit_blocker_total = 0
    for r in audit_runs:
        out = r.output_summary or {}
        resumo = out.get("resumo") or {}
        audit_total_findings += int(resumo.get("total", 0) or 0)
        audit_blocker_total += int(resumo.get("n_blocker", 0) or 0)

    return {
        "janela_dias": dias,
        "desde": desde.isoformat() + "Z",
        "reconciliator": {
            "runs": len(reconciliator_runs),
            "success": sum(1 for r in reconciliator_runs if r.status == "success"),
            "errors": sum(1 for r in reconciliator_runs if r.status == "error"),
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "llm_cost_usd_total": round(cost_total, 6),
            "llm_used_runs": sum(1 for r in reconciliator_runs if (r.cost_estimate or 0) > 0),
        },
        "briefing": {
            "runs": len(briefing_runs),
            "success": sum(1 for r in briefing_runs if r.status == "success"),
        },
        "auditqa": {
            "runs": len(audit_runs),
            "total_findings": audit_total_findings,
            "blocker_findings": audit_blocker_total,
        },
        "imports": {
            "total": len(commits),
            "via_reconciliator": via_reconciliator,
            "via_wizard_classico": via_wizard,
            "taxa_reconciliator_pct": round(
                (via_reconciliator / len(commits) * 100) if commits else 0, 1
            ),
        },
    }


def serie_diaria(db: Session, dias: int = 14) -> list[dict[str, Any]]:
    """
    Timeseries diaria de execucoes agenticas (eixo X = data, eixo Y = count
    por agente). Util pra ver crescimento de adocao no tempo.
    """
    desde = datetime.utcnow() - timedelta(days=dias)

    runs = (
        db.query(models.AgentRun)
        .filter(models.AgentRun.started_at >= desde)
        .all()
    )

    # Agrega por (data, agent_name)
    bucket: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in runs:
        d = r.started_at.date().isoformat()
        bucket[d][r.agent_name] += 1

    # Materializa lista densa (1 entry por dia)
    out: list[dict[str, Any]] = []
    base = datetime.utcnow().date() - timedelta(days=dias)
    for i in range(dias + 1):
        d = (base + timedelta(days=i)).isoformat()
        out.append({
            "data": d,
            "reconciliator": bucket[d].get("reconciliator", 0),
            "briefing": bucket[d].get("briefing", 0),
            "auditqa": bucket[d].get("auditqa", 0),
            "total": sum(bucket[d].values()),
        })
    return out


def resumo_por_agente(db: Session, dias: int = 7) -> list[dict[str, Any]]:
    """
    Resumo por agent_name na janela. Ordenado por runs desc.
    """
    desde = datetime.utcnow() - timedelta(days=dias)

    rows = (
        db.query(
            models.AgentRun.agent_name,
            func.count(models.AgentRun.id).label("runs"),
            func.sum(
                # status = 'success' -> 1 else 0 (compat SQLite)
                func.iif(models.AgentRun.status == "success", 1, 0)
                if hasattr(func, "iif") else 0
            ).label("success_count"),
            func.avg(models.AgentRun.latency_ms).label("avg_latency_ms"),
            func.sum(models.AgentRun.cost_estimate).label("cost_total"),
        )
        .filter(models.AgentRun.started_at >= desde)
        .group_by(models.AgentRun.agent_name)
        .order_by(func.count(models.AgentRun.id).desc())
        .all()
    )

    # SQLite nao tem func.iif uniformemente — fallback manual
    # Recalcula success_count em Python para confiabilidade.
    out: list[dict[str, Any]] = []
    for nome, runs, _ignored_success, avg_latency, cost in rows:
        # Reconta success_count via segunda query (rapido)
        success = (
            db.query(func.count(models.AgentRun.id))
            .filter(
                models.AgentRun.agent_name == nome,
                models.AgentRun.started_at >= desde,
                models.AgentRun.status == "success",
            )
            .scalar() or 0
        )
        out.append({
            "agent_name": nome,
            "runs": int(runs or 0),
            "success": int(success),
            "taxa_success_pct": round((success / runs * 100) if runs else 0, 1),
            "avg_latency_ms": int(avg_latency or 0),
            "cost_usd_total": round(float(cost or 0), 6),
        })
    return out
