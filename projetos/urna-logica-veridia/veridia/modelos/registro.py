"""Registro de votação fictício.

Cada registro representa um evento de votação em uma urna de uma eleição
FICTÍCIA de Verídia. Não há candidatos, partidos ou resultados reais: a
opção votada é apenas um código como ``"OPC-A"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from enum import Enum
from typing import Iterable

# Códigos fictícios de opção. Não correspondem a nenhuma pessoa ou partido.
CODIGOS_OPCAO: tuple[str, ...] = ("OPC-A", "OPC-B", "OPC-C", "OPC-D", "OPC-E", "BRANCO", "NULO")

# Janela de funcionamento das seções em Verídia (fictícia).
HORARIO_ABERTURA = time(8, 0, 0)
HORARIO_FECHAMENTO = time(17, 0, 0)


class StatusRegistro(str, Enum):
    """Situação do registro após a apuração do jogo."""

    VALIDO = "VALIDO"
    SUSPEITO = "SUSPEITO"      # anomalia a investigar (ex.: horário atípico)
    DUPLICADO = "DUPLICADO"    # mesmo evento registrado mais de uma vez
    ANULADO = "ANULADO"        # descartado pela auditoria


@dataclass(frozen=True)
class RegistroVotacao:
    """Um evento de votação.

    ``frozen=True`` torna o registro imutável: os algoritmos de ordenação
    reorganizam *referências* para registros, sem nunca alterar o conteúdo.
    """

    id: str
    zona: int
    secao: int
    codigo_opcao: str
    horario: time
    status: StatusRegistro = StatusRegistro.VALIDO

    def chave_zona_secao_horario(self) -> tuple[int, int, time]:
        """Chave composta principal do jogo: (zona, seção, horário)."""
        return (self.zona, self.secao, self.horario)


def validar_registro(registro: RegistroVotacao) -> list[str]:
    """Retorna a lista de problemas encontrados (lista vazia = registro válido)."""
    erros: list[str] = []
    if not isinstance(registro.id, str) or not registro.id.strip():
        erros.append("id deve ser um texto não vazio")
    if not isinstance(registro.zona, int) or isinstance(registro.zona, bool) or registro.zona <= 0:
        erros.append("zona deve ser um inteiro positivo")
    if not isinstance(registro.secao, int) or isinstance(registro.secao, bool) or registro.secao <= 0:
        erros.append("seção deve ser um inteiro positivo")
    if registro.codigo_opcao not in CODIGOS_OPCAO:
        erros.append(f"código de opção desconhecido: {registro.codigo_opcao!r}")
    if not isinstance(registro.horario, time):
        erros.append("horário deve ser um datetime.time")
    elif not (HORARIO_ABERTURA <= registro.horario <= HORARIO_FECHAMENTO):
        erros.append(f"horário fora da janela de votação: {registro.horario}")
    if not isinstance(registro.status, StatusRegistro):
        erros.append(f"status inválido: {registro.status!r}")
    return erros


def validar_registros(registros: Iterable[RegistroVotacao]) -> list[str]:
    """Valida cada registro e a unicidade dos IDs do conjunto."""
    erros: list[str] = []
    ids_vistos: set[str] = set()
    for registro in registros:
        for erro in validar_registro(registro):
            erros.append(f"{registro.id}: {erro}")
        if registro.id in ids_vistos:
            erros.append(f"{registro.id}: id repetido")
        ids_vistos.add(registro.id)
    return erros
