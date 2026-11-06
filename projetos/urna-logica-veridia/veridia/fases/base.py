"""Contrato mínimo comum às cinco fases.

Cada fase é um CONTROLADOR em memória: guarda o progresso do enigma e expõe
ações (métodos) que devolvem um ``ResultadoAcao``. A interface futura
(NiceGUI) só precisa chamar essas ações e exibir ``mensagem`` e ``dados``.

Regras comuns:
- ação inválida → ``ResultadoAcao(sucesso=False, mensagem=explicação)`` e o
  estado da fase NÃO muda;
- ``reiniciar()`` volta a fase ao estado inicial sem afetar as outras fases;
- ``esta_concluida()`` é o objetivo verificável da fase (recalculado a
  partir do estado atual — não é um flag que se possa "forçar").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResultadoAcao:
    sucesso: bool
    mensagem: str
    dados: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, mensagem: str, **dados: Any) -> "ResultadoAcao":
        return cls(True, mensagem, dados)

    @classmethod
    def falha(cls, mensagem: str, **dados: Any) -> "ResultadoAcao":
        return cls(False, mensagem, dados)


class Fase(ABC):
    numero: int
    titulo: str
    objetivo: str
    # Nomes dos métodos que podem ser chamados pela sessão / interface.
    ACOES: tuple[str, ...] = ()

    @abstractmethod
    def reiniciar(self) -> None:
        """Volta ao estado inicial da fase."""

    @abstractmethod
    def esta_concluida(self) -> bool:
        """Objetivo verificável da fase."""

    @abstractmethod
    def consultar(self) -> dict[str, Any]:
        """Retrato do estado atual em tipos simples (para exibição)."""
