from __future__ import annotations

import hashlib
from pathlib import Path

from src.baixa_dados_sinasc import calcular_sha256, verificar_arquivo_existente


def test_calcula_sha256_em_fluxo(tmp_path: Path) -> None:
    caminho = tmp_path / "fonte.bin"
    conteudo = b"sinasc-fase-0"
    caminho.write_bytes(conteudo)

    assert calcular_sha256(caminho) == hashlib.sha256(conteudo).hexdigest()


def test_verifica_arquivo_existente_sem_alterar_bytes(tmp_path: Path) -> None:
    caminho = tmp_path / "fonte.bin"
    caminho.write_bytes(b"conteudo-oficial")
    hash_esperado = calcular_sha256(caminho)

    resultado = verificar_arquivo_existente(caminho, hash_esperado)

    assert resultado["bytes"] == len(b"conteudo-oficial")
    assert resultado["sha256"] == hash_esperado
    assert caminho.read_bytes() == b"conteudo-oficial"
