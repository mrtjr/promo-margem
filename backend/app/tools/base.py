"""
Tool base + registry global.

Todo tool herda de `Tool` e implementa schema, dry_run, apply, rollback.
Registro auto via `tool.register()` — chamado nos __init__ dos modulos.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session


class AutonomyLevel(str, Enum):
    """
    Nivel de autonomia permitido para a tool. Configurado por padrao,
    pode ser sobrescrito por tenant/contexto futuramente.
    """
    OBSERVE = "observe"                          # so registra, nao executa
    SUGGEST = "suggest"                          # propoe via dry_run, humano aplica
    EXECUTE_WITH_APPROVAL = "execute_with_approval"  # agente prepara, humano aprova com 1 click
    EXECUTE_AUTONOMOUS = "execute_autonomous"    # agente executa direto (reservado)


@dataclass
class ToolDryRunResult:
    """
    Resultado de dry_run — descricao do que ACONTECERIA se apply rodasse.
    Nao muta nada no DB.
    """
    will_change: bool                       # algo de fato muda?
    summary: str                            # descricao curta humana
    diff: dict[str, Any]                    # before/after estruturado
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """
    Resultado de apply — o que foi feito + handle pra rollback se aplicavel.
    """
    success: bool
    summary: str
    output: dict[str, Any]
    execution_id: Optional[str] = None      # opaque handle pra rollback
    can_rollback: bool = False
    event_id: Optional[int] = None          # id do event canonico publicado
    error: Optional[str] = None


# Registry global. Singleton-ish — modulo eh carregado uma vez no startup
# e tools sao registradas por side-effect de import.
_REGISTRY: dict[str, "Tool"] = {}


class Tool(ABC):
    """
    Base abstrata. Cada tool concreta:
      - define `name` (string unica, snake_case)
      - define `description` (frase curta — visivel a agentes)
      - define `domain` (ex. 'produtos', 'csv', 'cliente') — agrupa tools
      - define `default_autonomy: AutonomyLevel`
      - define `input_schema: type[BaseModel]` e `output_schema: type[BaseModel]`
      - implementa dry_run, apply, rollback (rollback opcional)

    Convencao de erro: ToolResult com success=False + error preenchido.
    NAO levantar exception em apply — agentes precisam tratar resultado
    estruturado.
    """
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    domain: ClassVar[str] = ""
    default_autonomy: ClassVar[AutonomyLevel] = AutonomyLevel.SUGGEST
    input_schema: ClassVar[type[BaseModel]]
    output_schema: ClassVar[type[BaseModel]]
    supports_rollback: ClassVar[bool] = False

    def register(self) -> None:
        """Registra esta tool no registry global. Idempotente."""
        if not self.name:
            raise ValueError(f"Tool {self.__class__.__name__} sem name")
        _REGISTRY[self.name] = self

    @abstractmethod
    def dry_run(self, db: Session, args: dict) -> ToolDryRunResult:
        """
        Simula apply sem mutar DB. Retorna diff estruturado.
        Caller responsabilizo: NAO commitar a sessao (este metodo nao
        deve gerar mudancas persistidas; idealmente faz apenas SELECTs).
        """
        ...

    @abstractmethod
    def apply(
        self,
        db: Session,
        args: dict,
        *,
        actor: str = "tool",
        correlation_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Executa mutacao + emite event. Caller controla commit (a tool
        adiciona objetos a sessao mas espera que caller commite).
        """
        ...

    def rollback(self, db: Session, execution_id: str) -> ToolResult:
        """
        Override quando supports_rollback=True. Default: nao implementado.
        """
        return ToolResult(
            success=False,
            summary=f"Tool {self.name} nao suporta rollback",
            output={},
            error="rollback_not_supported",
        )

    def metadata(self) -> dict[str, Any]:
        """
        Schema descritivo para discovery. Usado por GET /tools e por
        agentes pra decidir qual tool chamar.
        """
        return {
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "default_autonomy": self.default_autonomy.value,
            "supports_rollback": self.supports_rollback,
            "input_schema": self.input_schema.model_json_schema()
                if self.input_schema else None,
            "output_schema": self.output_schema.model_json_schema()
                if self.output_schema else None,
        }


def list_tools() -> list[Tool]:
    """Retorna todas tools registradas, ordenadas por nome."""
    return sorted(_REGISTRY.values(), key=lambda t: t.name)


def get_tool(name: str) -> Optional[Tool]:
    """Recupera tool pelo nome ou None."""
    return _REGISTRY.get(name)
