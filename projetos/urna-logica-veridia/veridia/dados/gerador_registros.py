"""Geração reproduzível de registros de votação FICTÍCIOS.

Usa ``random.Random(seed)`` — um gerador próprio, isolado do estado global
do módulo ``random`` — para que a mesma seed produza sempre os mesmos
registros, em qualquer máquina e em qualquer ordem de execução dos testes.
"""

from __future__ import annotations

import random
from datetime import time

from veridia.modelos.registro import (
    CODIGOS_OPCAO,
    HORARIO_ABERTURA,
    HORARIO_FECHAMENTO,
    RegistroVotacao,
    StatusRegistro,
)

SEED_PADRAO = 2026

_STATUS = (StatusRegistro.VALIDO, StatusRegistro.SUSPEITO, StatusRegistro.DUPLICADO, StatusRegistro.ANULADO)
_PESOS_STATUS = (85, 8, 4, 3)


def _segundos(horario: time) -> int:
    return horario.hour * 3600 + horario.minute * 60 + horario.second


def gerar_registros(
    quantidade: int,
    seed: int = SEED_PADRAO,
    num_zonas: int = 5,
    secoes_por_zona: int = 4,
) -> list[RegistroVotacao]:
    """Gera ``quantidade`` registros com IDs únicos (R00001, R00002, ...).

    Os registros são produzidos em ordem de ID, e não ordenados por zona,
    seção ou horário — servindo de entrada para os algoritmos de ordenação.
    """
    if quantidade < 0:
        raise ValueError("quantidade não pode ser negativa")
    if num_zonas <= 0 or secoes_por_zona <= 0:
        raise ValueError("num_zonas e secoes_por_zona devem ser positivos")

    rng = random.Random(seed)
    inicio, fim = _segundos(HORARIO_ABERTURA), _segundos(HORARIO_FECHAMENTO)
    registros: list[RegistroVotacao] = []
    for numero in range(1, quantidade + 1):
        total = rng.randint(inicio, fim)
        registros.append(
            RegistroVotacao(
                id=f"R{numero:05d}",
                zona=rng.randint(1, num_zonas),
                secao=rng.randint(1, secoes_por_zona),
                codigo_opcao=rng.choice(CODIGOS_OPCAO),
                horario=time(total // 3600, (total % 3600) // 60, total % 60),
                status=rng.choices(_STATUS, weights=_PESOS_STATUS, k=1)[0],
            )
        )
    return registros
