"""
Tool Registry — interface unica para acoes mutaveis do dominio.

Sprint S0 — Fundacoes Agentic.

Cada tool implementa contrato:
  - schema tipado (Pydantic) para input/output
  - dry_run(args) -> ProposedDiff (simula sem mutar)
  - apply(args) -> Result (aplica + emite event)
  - rollback(execution_id) -> Result (quando viavel)
  - idempotencia (apply mesma input N vezes = mesmo estado final)
  - emite Event canonico em apply() (actor=tool:<name>)

Por que tool registry, nao chamada direta de servico?
  - Agentes precisam descobrir capacidades via metadata uniforme
  - dry_run habilita "simular antes de aplicar" (essencial pra autonomia)
  - rollback eh requisito de governanca pra L2/L3 (acao reversivel)
  - emissao de event automatica garante audit trail

Tools desta sprint (escopo narrow, deliberado):
  - update_produto: PATCH parcial em Produto
  - commit_csv:     POST /fechamento/importar-csv/commit (wrapper)

Proximas sprints expandem registry sem mudar interface.
"""
from .base import (
    Tool,
    ToolResult,
    ToolDryRunResult,
    AutonomyLevel,
    list_tools,
    get_tool,
)
from .produto_tool import UpdateProdutoTool
from .csv_tool import CommitCsvTool

__all__ = [
    "Tool",
    "ToolResult",
    "ToolDryRunResult",
    "AutonomyLevel",
    "list_tools",
    "get_tool",
    "UpdateProdutoTool",
    "CommitCsvTool",
]

# Auto-registra tools no import — chamadas posteriores a list_tools()
# devolvem instances. Idempotente (registry usa nome como chave).
UpdateProdutoTool().register()
CommitCsvTool().register()
