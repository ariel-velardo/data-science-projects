"""Fontes oficiais, leitura textual, conversão e serialização."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any
import requests
import csv
import zipfile
from collections.abc import Iterator, Sequence, Set
from dataclasses import dataclass
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np

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


@dataclass(frozen=True)
class FormatoCSV:
    """Formato observado no CSV interno do arquivo oficial."""

    arquivo_interno: str
    encoding: str
    separador: str
    colunas: tuple[str, ...]

def descobrir_csv_no_zip(caminho_zip: str | Path) -> str:
    """Retorna o único CSV interno e rejeita ZIPs ausentes ou ambíguos."""

    caminho = Path(caminho_zip)
    if not caminho.exists():
        raise FileNotFoundError(f"ZIP não encontrado: {caminho}")

    with zipfile.ZipFile(caminho) as arquivo_zip:
        candidatos = [
            nome
            for nome in arquivo_zip.namelist()
            if not nome.endswith("/") and nome.lower().endswith(".csv")
        ]

    if len(candidatos) != 1:
        raise ValueError(
            f"Esperado exatamente um CSV no ZIP; encontrados {len(candidatos)}: {candidatos}"
        )
    return candidatos[0]

def _detectar_encoding(amostra: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            amostra.decode(encoding)
        except UnicodeDecodeError:
            continue
        return "utf-8" if encoding == "utf-8-sig" else encoding
    raise UnicodeError("Não foi possível detectar um encoding compatível.")

def detectar_formato_csv(caminho_zip: str | Path, bytes_amostra: int = 131_072) -> FormatoCSV:
    """Detecta encoding, separador e cabeçalho a partir de uma amostra limitada."""

    arquivo_interno = descobrir_csv_no_zip(caminho_zip)
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        with arquivo_zip.open(arquivo_interno) as fluxo:
            amostra = fluxo.read(bytes_amostra)

    encoding = _detectar_encoding(amostra)
    texto = amostra.decode(encoding)
    dialect = csv.Sniffer().sniff(texto[:65_536], delimiters=";,|\t,")
    cabecalho = next(csv.reader(texto.splitlines(), dialect))
    colunas = tuple(coluna.lstrip("\ufeff").strip() for coluna in cabecalho)
    return FormatoCSV(arquivo_interno, encoding, dialect.delimiter, colunas)

def iterar_csv_em_chunks(
    caminho_zip: str | Path,
    tamanho_chunk: int = 250_000,
    colunas: Sequence[str] | None = None,
) -> Iterator[pd.DataFrame]:
    """Lê o CSV interno em chunks, mantendo todos os campos originais como texto."""

    formato = detectar_formato_csv(caminho_zip)
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        with arquivo_zip.open(formato.arquivo_interno) as fluxo:
            yield from pd.read_csv(
                fluxo,
                sep=formato.separador,
                encoding=formato.encoding,
                dtype="string",
                usecols=colunas,
                chunksize=tamanho_chunk,
                keep_default_na=True,
                low_memory=False,
            )

def validar_schema_minimo(colunas: Sequence[str], obrigatorias: Set[str]) -> None:
    """Falha explicitamente quando o schema mínimo necessário não está presente."""

    ausentes = sorted(set(obrigatorias) - set(colunas))
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(ausentes)}")


@dataclass(frozen=True)
class ResultadoConversao:
    caminho: Path
    registros: int
    colunas: int
    reutilizado: bool

def _resultado_existente(caminho: Path) -> ResultadoConversao:
    metadados = pq.ParquetFile(caminho).metadata
    return ResultadoConversao(
        caminho=caminho,
        registros=metadados.num_rows,
        colunas=metadados.num_columns,
        reutilizado=True,
    )

def converter_zip_para_parquet(
    caminho_zip: str | Path,
    caminho_parquet: str | Path,
    tamanho_chunk: int = 250_000,
    colunas_obrigatorias: set[str] | None = None,
) -> ResultadoConversao:
    """Converte em fluxo e não sobrescreve um Parquet já existente."""

    origem = Path(caminho_zip)
    destino = Path(caminho_parquet)
    if destino.exists():
        return _resultado_existente(destino)

    formato = detectar_formato_csv(origem)
    validar_schema_minimo(
        formato.colunas,
        colunas_obrigatorias or {"contador", "MESPRENAT", "PESO"},
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    if temporario.exists():
        raise FileExistsError(
            f"Parquet temporário encontrado em {temporario}; revise antes de continuar."
        )

    escritor: pq.ParquetWriter | None = None
    registros = 0
    try:
        for chunk in iterar_csv_em_chunks(origem, tamanho_chunk=tamanho_chunk):
            tabela = pa.Table.from_pandas(chunk, preserve_index=False)
            if escritor is None:
                escritor = pq.ParquetWriter(
                    temporario,
                    tabela.schema,
                    compression="zstd",
                    use_dictionary=True,
                )
            escritor.write_table(tabela)
            registros += len(chunk)
    finally:
        if escritor is not None:
            escritor.close()

    if registros == 0:
        raise ValueError("O CSV não contém registros de dados.")
    temporario.replace(destino)
    return ResultadoConversao(destino, registros, len(formato.colunas), False)

DESCRICOES_OFICIAIS = {
    "CONTADOR": "Número identificador do registro.",
    "LOCNASC": "Local de nascimento.",
    "CODMUNNASC": "Código IBGE do município de nascimento.",
    "IDADEMAE": "Idade da mãe.",
    "ESTCIVMAE": "Situação conjugal da mãe.",
    "ESCMAE": "Escolaridade, em anos de estudo concluídos.",
    "CODOCUPMAE": "Código de ocupação da mãe conforme a CBO.",
    "QTDFILVIVO": "Número de filhos vivos.",
    "QTDFILMORT": "Número de perdas fetais e abortos.",
    "CODMUNRES": "Código IBGE do município de residência.",
    "GESTACAO": "Faixa de semanas de gestação.",
    "GRAVIDEZ": "Tipo de gravidez.",
    "PARTO": "Tipo de parto.",
    "CONSULTAS": "Faixa do número de consultas de pré-natal.",
    "DTNASC": "Data de nascimento.",
    "SEXO": "Sexo do recém-nascido.",
    "APGAR1": "Apgar no primeiro minuto.",
    "APGAR5": "Apgar no quinto minuto.",
    "RACACOR": "Raça/cor do nascido.",
    "PESO": "Peso ao nascer em gramas.",
    "CODANOMAL": "Código da anomalia segundo a CID-10.",
    "HORANASC": "Horário de nascimento.",
    "IDANOMAL": "Indicador de anomalia identificada.",
    "CODESTAB": "Código do estabelecimento de saúde onde ocorreu o nascimento.",
    "DTCADASTRO": "Data do cadastro da DN no sistema.",
    "DTRECEBIM": "Data do último recebimento do lote pelo Sisnet.",
    "ORIGEM": "Banco de dados de origem.",
    "CODPAISRES": "Código do país de residência.",
    "NUMEROLOTE": "Número do lote.",
    "VERSAOSIST": "Versão do sistema.",
    "DIFDATA": "Diferença entre a data de nascimento e a data de recebimento original da DN.",
    "DTRECORIGA": "Data de primeiro recebimento, com regras de preenchimento derivadas.",
    "NATURALMAE": "Código do país de nascimento da mãe quando estrangeira.",
    "CODMUNNATU": "Código do município de naturalidade da mãe.",
    "CODUFNATU": "Código da UF de naturalidade da mãe.",
    "SERIESCMAE": "Série escolar da mãe.",
    "DTNASCMAE": "Data de nascimento da mãe.",
    "RACACORMAE": "Raça/cor da mãe.",
    "QTDGESTANT": "Número de gestações anteriores.",
    "QTDPARTNOR": "Número de partos vaginais anteriores.",
    "QTDPARTCES": "Número de partos cesáreos anteriores.",
    "IDADEPAI": "Idade do pai.",
    "DTULTMENST": "Data da última menstruação.",
    "SEMAGESTAC": "Número de semanas de gestação.",
    "TPMETESTIM": "Método utilizado para estimar a gestação.",
    "CONSPRENAT": "Número de consultas de pré-natal.",
    "MESPRENAT": "Mês de gestação em que iniciou o pré-natal.",
    "TPAPRESENT": "Tipo de apresentação do recém-nascido.",
    "STTRABPART": "Indicador de trabalho de parto induzido.",
    "STCESPARTO": "Indicador de cesárea antes do início do trabalho de parto.",
    "TPROBSON": "Código do grupo de Robson gerado pelo sistema.",
    "STDNEPIDEM": "Status de DN epidemiológica.",
    "STDNNOVA": "Status de DN nova.",
    "ESCMAE2010": "Escolaridade da mãe segundo categorias de 2010.",
    "TPNASCASSI": "Profissional que assistiu o nascimento.",
    "ESCMAEAGR1": "Escolaridade 2010 agregada.",
    "TPFUNCRESP": "Função do responsável pelo preenchimento.",
    "TPDOCRESP": "Tipo de documento do responsável pelo preenchimento.",
    "DTDECLARAC": "Data da declaração.",
    "PARIDADE": "Indicador de nuliparidade ou multiparidade.",
    "KOTELCHUCK": "Índice de Kotelchuck para avaliação da assistência pré-natal.",
}

CODIGOS_ESPECIAIS_DOCUMENTADOS = {
    "ESTCIVMAE": "9=Ignorada",
    "ESCMAE": "9=Ignorado",
    "GESTACAO": "9=Ignorado",
    "GRAVIDEZ": "9=Ignorado",
    "PARTO": "9=Ignorado",
    "CONSULTAS": "9=Ignorado",
    "SEXO": "0=Ignorado",
    "IDANOMAL": "9=Ignorado",
    "TPMETESTIM": "9=Ignorado",
    "TPAPRESENT": "9=Ignorado",
    "STTRABPART": "9=Ignorado",
    "STCESPARTO": "9=Ignorado",
    "TPNASCASSI": "9=Ignorado",
    "ESCMAE2010": "9=Ignorado",
    "ESCMAEAGR1": "09=Ignorado",
}

X_PROVAVEL_PRE_TRATAMENTO = {
    "IDADEMAE", "ESTCIVMAE", "ESCMAE", "ESCMAE2010", "ESCMAEAGR1",
    "SERIESCMAE", "RACACORMAE", "QTDFILVIVO", "QTDFILMORT", "QTDGESTANT",
    "QTDPARTNOR", "QTDPARTCES", "PARIDADE", "CODMUNRES", "CODPAISRES",
    "NATURALMAE", "CODMUNNATU", "CODUFNATU", "DTNASCMAE", "IDADEPAI",
}

POS_TRATAMENTO = {
    "CONSULTAS", "CONSPRENAT", "GESTACAO", "SEMAGESTAC", "PARTO", "DTNASC",
    "HORANASC", "SEXO", "APGAR1", "APGAR5", "RACACOR", "IDANOMAL",
    "CODANOMAL", "TPAPRESENT", "STTRABPART", "STCESPARTO", "TPNASCASSI",
    "TPROBSON", "KOTELCHUCK",
}

TEMPORALIDADE_DUVIDOSA = {
    "CODOCUPMAE", "GRAVIDEZ", "DTULTMENST", "TPMETESTIM", "LOCNASC", "CODESTAB",
}

IDENTIFICADORES = {"CONTADOR", "NUMEROLOTE"}

def papel_analitico(nome: str) -> str:
    campo = nome.upper()
    if campo == "MESPRENAT":
        return "T candidato"
    if campo == "PESO":
        return "Y candidato"
    if campo in IDENTIFICADORES:
        return "identificador"
    if campo in X_PROVAVEL_PRE_TRATAMENTO:
        return "X candidato"
    if campo in POS_TRATAMENTO:
        return "pós-tratamento"
    if campo in {"ORIGEM", "DTCADASTRO", "DTRECEBIM", "DTRECORIGA", "DIFDATA", "VERSAOSIST", "STDNEPIDEM", "STDNNOVA", "OPORT_DN", "DTDECLARAC"}:
        return "contextual"
    return "ainda não classificado"

def grupo_temporal(nome: str) -> str | None:
    campo = nome.upper()
    if campo in X_PROVAVEL_PRE_TRATAMENTO:
        return "A. provavelmente pré-tratamento"
    if campo in POS_TRATAMENTO:
        return "B. provavelmente pós-tratamento/mediadora"
    if campo in TEMPORALIDADE_DUVIDOSA:
        return "C. temporalidade ou papel causal duvidoso"
    return None

def _normalizar_json(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {str(chave): _normalizar_json(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_normalizar_json(item) for item in valor]
    if isinstance(valor, (np.integer,)):
        return int(valor)
    if isinstance(valor, (np.floating,)):
        return None if np.isnan(valor) else float(valor)
    if isinstance(valor, (pd.Timestamp,)):
        return valor.isoformat()
    if pd.isna(valor):
        return None
    return valor

def _salvar_json(caminho: Path, conteudo: dict[str, Any]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(_normalizar_json(conteudo), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

def _registros(tabela: pd.DataFrame) -> list[dict[str, Any]]:
    return _normalizar_json(tabela.to_dict(orient="records"))

def _markdown_tabela(tabela: pd.DataFrame) -> str:
    exibicao = tabela.copy()
    for coluna in exibicao.select_dtypes(include="float").columns:
        exibicao[coluna] = exibicao[coluna].map(
            lambda valor: "" if pd.isna(valor) else f"{valor:.6f}"
        )
    cabecalho = "| " + " | ".join(map(str, exibicao.columns)) + " |"
    separador = "| " + " | ".join(["---"] * len(exibicao.columns)) + " |"
    linhas = [
        "| " + " | ".join(str(valor) for valor in linha) + " |"
        for linha in exibicao.itertuples(index=False, name=None)
    ]
    return "\n".join([cabecalho, separador, *linhas]) + "\n"
