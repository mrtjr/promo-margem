"""
Agent Runner — observabilidade minima de cada execucao agentica.

Cada chamada de agente abre 1 row em `agent_runs` com:
  - status: 'running' -> 'success' | 'error'
  - latency_ms calculado
  - input/output summaries (truncados pra evitar bloat)
  - tools_used (contagem por tool)
  - cost_estimate (definido pelo agente; LLM-based agents preencherao)
  - correlation_id propagado ao event log

Uso (context manager pattern):

    runner = AgentRunner(db, agent_name="reconciliator", correlation_id=cid)
    runner.input(linhas=78, ...)
    try:
        result = ...
        runner.tool_used("update_produto")
        runner.success(output={...})
    except Exception as e:
        runner.error(str(e))
        raise
"""
from __future__ import annotations

import time
import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from ..eventbus import new_correlation_id, publish_event


class AgentRunner:
    """
    Cada instance representa 1 execucao. Cria row de `agent_runs` no init,
    atualiza incrementalmente conforme agente progride, fecha em success/error.

    NAO commita a sessao — caller controla. Em caso de excecao no caller,
    runner ainda deve ser fechado via .error() pra status correto.
    """

    def __init__(
        self,
        db: Session,
        *,
        agent_name: str,
        correlation_id: Optional[str] = None,
        autonomy_level: str = "suggest",
    ):
        self.db = db
        self.agent_name = agent_name
        self.correlation_id = correlation_id or new_correlation_id()
        self.autonomy_level = autonomy_level
        self._t0 = time.monotonic()
        self._tools: dict[str, int] = {}
        self._input_summary: Optional[dict[str, Any]] = None

        # Cria row de agent_run em status 'running'. Flush sem commit pra
        # ter id imediato (caller decide commit final).
        self._run = models.AgentRun(
            agent_name=agent_name,
            status="running",
            correlation_id=self.correlation_id,
            autonomy_level=autonomy_level,
        )
        db.add(self._run)
        db.flush()

        # Evento de inicio — vai pro event log + agent_runs (dupla
        # observabilidade: stream cronologico + estado por run)
        publish_event(
            db,
            actor=f"agent:{agent_name}",
            entity="agent_run",
            entity_id=self._run.id,
            action="started",
            correlation_id=self.correlation_id,
            payload={"autonomy_level": autonomy_level},
        )

    @property
    def run_id(self) -> int:
        return self._run.id

    def input(self, **summary: Any) -> None:
        """Registra resumo do input. Truncado pra <2KB no JSON storage."""
        self._input_summary = _truncate_dict(summary, max_chars=2000)
        self._run.input_summary = self._input_summary

    def tool_used(self, name: str, n: int = 1) -> None:
        """Registra uso de tool. Soma contagem se chamada multiplas vezes."""
        self._tools[name] = self._tools.get(name, 0) + n

    def success(
        self,
        *,
        output: Optional[dict[str, Any]] = None,
        cost_estimate: Optional[float] = None,
    ) -> models.AgentRun:
        """Fecha run com status 'success'."""
        self._finalize(
            status="success",
            output=output,
            cost_estimate=cost_estimate,
        )
        publish_event(
            self.db,
            actor=f"agent:{self.agent_name}",
            entity="agent_run",
            entity_id=self._run.id,
            action="finished",
            correlation_id=self.correlation_id,
            payload={
                "status": "success",
                "latency_ms": self._run.latency_ms,
                "tools_used": list(self._tools.keys()),
            },
        )
        return self._run

    def error(self, message: str, *, output: Optional[dict[str, Any]] = None) -> models.AgentRun:
        """Fecha run com status 'error'."""
        self._finalize(
            status="error",
            output=output,
            error=message,
        )
        publish_event(
            self.db,
            actor=f"agent:{self.agent_name}",
            entity="agent_run",
            entity_id=self._run.id,
            action="failed",
            correlation_id=self.correlation_id,
            payload={"error": message, "latency_ms": self._run.latency_ms},
        )
        return self._run

    def rejected(self, reason: str) -> models.AgentRun:
        """
        Fecha run com status 'rejected' — agente decidiu NAO executar
        (ex.: fora do envelope de autonomia, dados insuficientes).
        Diferente de erro: nao indica falha tecnica.
        """
        self._finalize(status="rejected", error=reason)
        publish_event(
            self.db,
            actor=f"agent:{self.agent_name}",
            entity="agent_run",
            entity_id=self._run.id,
            action="rejected",
            correlation_id=self.correlation_id,
            payload={"reason": reason},
        )
        return self._run

    def _finalize(
        self,
        *,
        status: str,
        output: Optional[dict[str, Any]] = None,
        cost_estimate: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        from datetime import datetime
        elapsed_ms = int((time.monotonic() - self._t0) * 1000)
        self._run.finished_at = datetime.utcnow()
        self._run.latency_ms = elapsed_ms
        self._run.status = status
        if output is not None:
            self._run.output_summary = _truncate_dict(output, max_chars=4000)
        if cost_estimate is not None:
            self._run.cost_estimate = cost_estimate
        if error is not None:
            self._run.error = error[:500]
        if self._tools:
            self._run.tools_used = [
                {"tool": name, "count": count}
                for name, count in sorted(self._tools.items())
            ]
        self.db.flush()


def run_agent(
    db: Session,
    *,
    agent_name: str,
    correlation_id: Optional[str] = None,
    autonomy_level: str = "suggest",
) -> AgentRunner:
    """Helper de conveniencia. Equivale a `AgentRunner(...)`."""
    return AgentRunner(
        db,
        agent_name=agent_name,
        correlation_id=correlation_id,
        autonomy_level=autonomy_level,
    )


def _truncate_dict(d: dict[str, Any], max_chars: int) -> dict[str, Any]:
    """
    Trunca dict serializavel pra max_chars chars no JSON. Se exceder,
    remove progressivamente os valores maiores ate caber. Garante que
    rows de agent_runs nao explodam de tamanho.
    """
    serialized = json.dumps(d, default=str, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return d
    # Marca truncamento mas preserva chaves principais
    result = {k: ("[TRUNCATED]" if len(json.dumps(v, default=str)) > 200 else v) for k, v in d.items()}
    serialized = json.dumps(result, default=str, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return result
    return {"_truncated": True, "_keys": list(d.keys())}
