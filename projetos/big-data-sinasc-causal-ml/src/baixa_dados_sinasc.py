"""Aquisição idempotente e verificação de integridade das fontes oficiais."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import requests


FONTES_OFICIAIS = (
    {
        "nome": "Nascidos Vivos - 2024",
        "instituicao": "Ministério da Saúde - Portal de Dados Abertos do SUS",
        "url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv/SINASC_2024_csv.zip",
        "arquivo": "SINASC_2024_csv.zip",
        "formato": "ZIP contendo CSV",
        "observacao": "Recurso atualizado no portal em 08/05/2026; arquivo bruto preservado.",
    },
    {
        "nome": "Dicionário de Dados - SINASC: Estrutura de 1996 a 2019",
        "instituicao": "Ministério da Saúde - Portal de Dados Abertos do SUS",
        "url": "https://diaad.s3.sa-east-1.amazonaws.com/sinasc/SINASC+-+Estrutura.pdf",
        "arquivo": "SINASC_Estrutura.pdf",
        "formato": "PDF",
        "observacao": "Recurso oficial atualizado no portal em 22/02/2024; cobertura documental até 2019.",
    },
)


def calcular_sha256(caminho: str | Path, tamanho_bloco: int = 1024 * 1024) -> str:
    """Calcula SHA-256 sem carregar o arquivo inteiro em memória."""

    digest = hashlib.sha256()
    with Path(caminho).open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(tamanho_bloco), b""):
            digest.update(bloco)
    return digest.hexdigest()


def verificar_arquivo_existente(
    caminho: str | Path, sha256_esperado: str | None = None
) -> dict[str, Any]:
    """Retorna tamanho/hash e falha se um hash esperado não coincidir."""

    arquivo = Path(caminho)
    if not arquivo.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")
    sha256 = calcular_sha256(arquivo)
    if sha256_esperado and sha256.lower() != sha256_esperado.lower():
        raise ValueError(
            f"SHA-256 divergente para {arquivo}: observado {sha256}, "
            f"esperado {sha256_esperado.lower()}"
        )
    return {"arquivo": str(arquivo), "bytes": arquivo.stat().st_size, "sha256": sha256}


def baixar_arquivo_oficial(
    url: str,
    destino: str | Path,
    sha256_esperado: str | None = None,
    tamanho_bloco: int = 1024 * 1024,
) -> dict[str, Any]:
    """Baixa uma fonte ausente; se já existir, apenas verifica seus bytes."""

    caminho = Path(destino)
    if caminho.exists():
        resultado = verificar_arquivo_existente(caminho, sha256_esperado)
        resultado["reutilizado"] = True
        return resultado

    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".part")
    if temporario.exists():
        raise FileExistsError(
            f"Download parcial encontrado em {temporario}; revise antes de continuar."
        )

    digest = hashlib.sha256()
    total = 0
    with requests.get(url, stream=True, timeout=(30, 300)) as resposta:
        resposta.raise_for_status()
        with temporario.open("xb") as arquivo:
            for bloco in resposta.iter_content(chunk_size=tamanho_bloco):
                if not bloco:
                    continue
                arquivo.write(bloco)
                digest.update(bloco)
                total += len(bloco)

    sha256 = digest.hexdigest()
    if sha256_esperado and sha256.lower() != sha256_esperado.lower():
        raise ValueError(
            f"SHA-256 divergente no download: observado {sha256}, "
            f"esperado {sha256_esperado.lower()}; parcial preservado em {temporario}."
        )
    temporario.replace(caminho)
    return {
        "arquivo": str(caminho),
        "bytes": total,
        "sha256": sha256,
        "reutilizado": False,
    }


def baixar_fontes_e_gerar_manifesto(
    raiz_projeto: str | Path, data_acesso: str | None = None
) -> dict[str, Any]:
    """Baixa/reutiliza as fontes oficiais e grava seu manifesto de provenance."""

    raiz = Path(raiz_projeto).resolve()
    pasta_raw = raiz / "data" / "raw"
    fontes = []
    for fonte in FONTES_OFICIAIS:
        resultado = baixar_arquivo_oficial(fonte["url"], pasta_raw / fonte["arquivo"])
        fontes.append(
            {
                **fonte,
                "data_acesso": data_acesso or date.today().isoformat(),
                "tamanho_bytes": resultado["bytes"],
                "sha256": resultado["sha256"],
                "arquivo_local": f"data/raw/{fonte['arquivo']}",
                "reutilizado": resultado["reutilizado"],
            }
        )
    manifesto = {
        "dataset": "Sistema de Informação sobre Nascidos Vivos - SINASC",
        "pagina_oficial": "https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc",
        "fontes": fontes,
    }
    (pasta_raw / "source_manifest.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifesto


if __name__ == "__main__":
    manifesto = baixar_fontes_e_gerar_manifesto(
        Path(__file__).resolve().parents[1], data_acesso="2026-09-25"
    )
    print(json.dumps(manifesto, ensure_ascii=False, indent=2))
