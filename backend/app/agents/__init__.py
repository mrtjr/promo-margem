"""
Agents — escopo Sprint S0.

Apenas 1 agente concreto: Reconciliator V0.
Runner generico (`runner.py`) instrumenta cada execucao.

Proximas sprints adicionam: Cataloger, MarginSentinel, Forecaster,
PricingStrategist, MemoryCurator, AuditQA, Orchestrator.
"""
from .runner import AgentRunner, run_agent
from .reconciliator import ReconciliatorAgent
from .briefing import BriefingAgent

__all__ = [
    "AgentRunner",
    "run_agent",
    "ReconciliatorAgent",
    "BriefingAgent",
]
