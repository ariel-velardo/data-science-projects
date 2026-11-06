"""Evidências (pistas) que o jogador investiga em Verídia."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class TipoEvidencia(str, Enum):
    DOCUMENTO = "DOCUMENTO"
    LOG_URNA = "LOG_URNA"
    LACRE = "LACRE"
    TESTEMUNHO = "TESTEMUNHO"
    REGISTRO_HORARIO = "REGISTRO_HORARIO"


class EstadoEvidencia(str, Enum):
    OCULTA = "OCULTA"          # ainda não encontrada
    COLETADA = "COLETADA"      # o jogador já a possui
    ANALISADA = "ANALISADA"    # já foi usada em uma dedução
    DESCARTADA = "DESCARTADA"  # revelou-se irrelevante


@dataclass(frozen=True)
class Evidencia:
    """Pista identificada por ``id`` único (usado como chave na AVL)."""

    id: str
    tipo: TipoEvidencia
    descricao: str
    estado: EstadoEvidencia = EstadoEvidencia.OCULTA

    def com_estado(self, novo_estado: EstadoEvidencia) -> "Evidencia":
        """Devolve uma cópia com outro estado (a evidência original não muda)."""
        return replace(self, estado=novo_estado)


def validar_evidencia(evidencia: Evidencia) -> list[str]:
    erros: list[str] = []
    if not isinstance(evidencia.id, str) or not evidencia.id.strip():
        erros.append("id deve ser um texto não vazio")
    if not isinstance(evidencia.tipo, TipoEvidencia):
        erros.append(f"tipo inválido: {evidencia.tipo!r}")
    if not isinstance(evidencia.descricao, str) or not evidencia.descricao.strip():
        erros.append("descrição deve ser um texto não vazio")
    if not isinstance(evidencia.estado, EstadoEvidencia):
        erros.append(f"estado inválido: {evidencia.estado!r}")
    return erros
