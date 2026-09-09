"""Reconstrucao da lista de cidades-polo da Expansao Fase II da Rede Federal.

Fonte primaria: Chamada Publica MEC/SETEC no 001/2007, Anexo I
("Relacao Nominal das Cidades Polo"), assinada por Fernando Haddad
(Ministro da Educacao) e Eliezer Moreira Pacheco (Secretario/SETEC),
Brasilia, 24/04/2007.

O arquivo foi obtido via espelho institucional preservado pelo IFRS
("memoria.ifrs.edu.br"), nao pelo dominio original do MEC/SETEC (que nao
mantem mais o documento acessivel -- ver source_manifest.json). O
conteudo textual e o do documento primario; o dominio de hospedagem e um
espelho institucional.

Preservado em:
    data/raw/institutional/fase_ii/edital_001_2007_ADREI_00011.pdf

Extracao de texto via `pdftotext -layout` (poppler/xpdf, ja instalado no
sistema -- nenhuma biblioteca Python de PDF foi adicionada). O layer de
texto deste PDF esta em cp1252 (confirmado por inspecao byte-a-byte: o
byte 0xC9 decodifica para "E" com acento agudo, condizente com
"MINISTERIO"); pdftotext preserva os bytes originais na saida, entao a
decodificacao cp1252 e feita aqui, nao pelo pdftotext.

O Anexo I ocupa as paginas 9-10 do PDF (confirmado por inspecao), em
layout de duas colunas com quebra fixa na coluna 27 (confirmado
empiricamente: toda linha com duas entradas numeradas tem a segunda
comecando exatamente na posicao 27).

Associacao de codigo IBGE via data/raw/institutional/fase_ii/ibge_municipios.json
(espelho local, mesmo dia, da API oficial de localidades do IBGE),
por correspondencia exata de nome normalizado (maiusculas, sem acento)
dentro da mesma UF. Nenhuma correspondencia fuzzy e aceita
automaticamente -- o que nao bater exatamente fica sinalizado como
ambiguo/sem correspondencia, nunca corrigido em silencio.

Saidas:
    data/interim/fase_ii_unidades.parquet     (1 linha por cidade-polo do Anexo I)
    data/processed/fase_ii_municipios.parquet (agregado por municipio IBGE)

Uso:
    python src/constroi_lista_fase_ii.py
"""
from __future__ import annotations

import json
import re
import subprocess
import unicodedata
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/institutional/fase_ii")
INTERIM = Path("data/interim")
PROC = Path("data/processed")

EDITAL_PDF = RAW / "edital_001_2007_ADREI_00011.pdf"
IBGE_MUNICIPIOS_JSON = RAW / "ibge_municipios.json"

UNIDADES_OUT = INTERIM / "fase_ii_unidades.parquet"
MUNICIPIOS_OUT = PROC / "fase_ii_municipios.parquet"

COL_SPLIT = 27  # confirmado empiricamente na inspecao das paginas 9-10

# Nomes por extenso exatamente como aparecem nos cabecalhos do Anexo I
# (apos decodificacao cp1252), mapeados para a sigla da UF.
UF_SIGLA = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAPÁ": "AP", "AMAZONAS": "AM",
    "BAHIA": "BA", "CEARÁ": "CE", "DISTRITO FEDERAL": "DF",
    "ESPÍRITO SANTO": "ES", "GOIÁS": "GO", "MARANHÃO": "MA",
    "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS", "MINAS GERAIS": "MG",
    "PARÁ": "PA", "PARAÍBA": "PB", "PARANÁ": "PR", "PERNAMBUCO": "PE",
    "PIAUÍ": "PI", "RIO DE JANEIRO": "RJ", "RIO GRANDE DO NORTE": "RN",
    "RIO GRANDE DO SUL": "RS", "RONDÔNIA": "RO", "RORAIMA": "RR",
    "SANTA CATARINA": "SC", "SÃO PAULO": "SP", "SERGIPE": "SE",
    "TOCANTINS": "TO",
}

ENTRADA_RE = re.compile(r"^(\d+)\s*-\s*(.+)$")
NOTA_PARENTESE_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")

# Correcoes manuais, revisadas uma a uma (nao e um mecanismo fuzzy
# generico): grafia da fonte diverge da grafia oficial IBGE para o MESMO
# municipio, sem ambiguidade de candidato dentro da UF.
CORRECOES_MANUAIS = {
    ("SC", "SAO MIGUEL D'OESTE"): "São Miguel do Oeste",  # grafia oficial IBGE usa "do Oeste"
}


def normaliza(nome: str) -> str:
    """Maiusculas, sem acento, espacos colapsados -- somente p/ comparacao."""
    s = unicodedata.normalize("NFKD", nome)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s


def extrai_texto_pdf(pdf: Path) -> str:
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                        capture_output=True, check=True)
    return r.stdout.decode("cp1252")


def parse_coluna(linhas: list[str]) -> list[tuple[str, int, str]]:
    """Devolve [(uf_extenso, numero_no_anexo, municipio_fonte), ...]."""
    out: list[tuple[str, int, str]] = []
    uf_atual: str | None = None
    for raw in linhas:
        t = raw.strip()
        if not t:
            continue
        m = ENTRADA_RE.match(t)
        if m:
            if uf_atual is None:
                raise ValueError(f"entrada sem UF corrente na coluna: {raw!r}")
            out.append((uf_atual, int(m.group(1)), m.group(2).strip()))
        else:
            uf_atual = t
    return out


def extrai_anexo_i(texto_completo: str) -> tuple[list[dict], dict]:
    paginas = texto_completo.split("\f")
    idx_relacao = next(i for i, p in enumerate(paginas)
                        if "RELAÇÃO NOMINAL" in p)
    # Observado diretamente: a lista ocupa a pagina do titulo + a seguinte.
    pags_lista = paginas[idx_relacao:idx_relacao + 2]

    registros: list[dict] = []
    total_declarado = None
    for offset, pagina in enumerate(pags_lista):
        num_pagina = idx_relacao + offset + 1  # 1-indexado
        m_total = re.search(r"TOTAL:\s*(\d+)\s*CIDADES", pagina)
        if m_total:
            total_declarado = int(m_total.group(1))

        linhas = pagina.splitlines()
        esquerda = [ln[:COL_SPLIT] for ln in linhas]
        direita = [ln[COL_SPLIT:] for ln in linhas]

        for uf_ext, num, nome in parse_coluna(esquerda) + parse_coluna(direita):
            municipio_fonte = nome
            observacao = ""
            m_nota = NOTA_PARENTESE_RE.match(nome)
            if m_nota:
                municipio_fonte = m_nota.group(1).strip()
                observacao = (f"anotacao entre parenteses na fonte: "
                              f"'{m_nota.group(2)}' (nao e nome de "
                              f"municipio adicional)")
            registros.append({
                "nome_unidade_fonte": nome,
                "municipio_fonte": municipio_fonte,
                "uf_fonte": UF_SIGLA.get(uf_ext, uf_ext),
                "fase": "Fase II",
                "pagina_fonte": num_pagina,
                "documento_fonte": ("Chamada Publica MEC/SETEC no 001/2007, "
                                    "Anexo I - Relacao Nominal das Cidades Polo"),
                "metodo_extracao": "pdftotext -layout (texto nativo do PDF)",
                "observacao": observacao,
                "numero_no_anexo": num,
            })
    return registros, {"total_declarado_documento": total_declarado}


def carrega_ibge_por_uf() -> dict[str, dict[str, tuple[str, str]]]:
    """{sigla_uf: {nome_normalizado: (codigo_ibge, nome_oficial)}}"""
    dados = json.loads(IBGE_MUNICIPIOS_JSON.read_text(encoding="utf-8"))
    por_uf: dict[str, dict[str, tuple[str, str]]] = {}
    for m in dados:
        # A grande maioria tem microrregiao; um punhado (ex.: municipios
        # criados apos a ultima reforma de microrregioes) so tem
        # regiao-imediata -- usamos esse caminho como alternativa.
        if m.get("microrregiao"):
            sigla = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
        else:
            sigla = m["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]
        codigo = str(m["id"])
        nome = m["nome"]
        por_uf.setdefault(sigla, {})[normaliza(nome)] = (codigo, nome)
    return por_uf


def associa_codigo_ibge(unidades: pd.DataFrame,
                         ibge_por_uf: dict) -> pd.DataFrame:
    # DF nao e dividido em municipios (fato estrutural do IBGE, nao nome
    # fuzzy-casado): ha exatamente 1 entrada de UF=DF na base de
    # municipios, que cobre todo o territorio. Gama/Planaltina/Samambaia/
    # Taguatinga sao Regioes Administrativas do DF, nao municipios.
    df_unico = list(ibge_por_uf.get("DF", {}).values())
    codigo_df = nome_df = None
    if len(df_unico) == 1:
        codigo_df, nome_df = df_unico[0]

    codigos, nomes_oficiais, status, obs_extra = [], [], [], []
    for _, row in unidades.iterrows():
        sigla = row["uf_fonte"]
        chave = normaliza(row["municipio_fonte"])
        tabela_uf = ibge_por_uf.get(sigla, {})
        if chave in tabela_uf:
            codigo, nome_oficial = tabela_uf[chave]
            codigos.append(codigo); nomes_oficiais.append(nome_oficial)
            status.append("exata"); obs_extra.append("")
        elif (sigla, chave) in CORRECOES_MANUAIS:
            nome_corrigido = CORRECOES_MANUAIS[(sigla, chave)]
            codigo, nome_oficial = tabela_uf[normaliza(nome_corrigido)]
            codigos.append(codigo); nomes_oficiais.append(nome_oficial)
            status.append("corrigida")
            obs_extra.append(f"grafia da fonte ('{row['municipio_fonte']}') "
                             f"difere da grafia oficial IBGE "
                             f"('{nome_oficial}'); correcao manual revisada")
        elif sigla == "DF" and codigo_df is not None:
            codigos.append(codigo_df); nomes_oficiais.append(nome_df)
            status.append("corrigida_administrativa")
            obs_extra.append("Distrito Federal nao e dividido em "
                             "municipios; esta e uma Regiao Administrativa, "
                             f"associada ao unico municipio-equivalente do "
                             f"DF ({nome_df}, {codigo_df})")
        else:
            codigos.append(None); nomes_oficiais.append(None)
            status.append("ambigua_sem_correspondencia"); obs_extra.append("")
    unidades = unidades.copy()
    unidades["codigo_municipio_ibge"] = codigos
    unidades["municipio_ibge"] = nomes_oficiais
    unidades["status_validacao"] = status
    unidades["observacao"] = [
        "; ".join(x for x in (o, e) if x)
        for o, e in zip(unidades["observacao"], obs_extra)
    ]
    return unidades


def constroi_tabela_municipios(unidades: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    # Agrupa por codigo IBGE quando existe; entradas sem codigo viram um
    # grupo por (uf_fonte, municipio_fonte) para nao perder nenhuma no
    # relatorio, mas continuam sinalizadas como sem correspondencia.
    unidades = unidades.copy()
    unidades["chave_grupo"] = unidades["codigo_municipio_ibge"].fillna(
        "SEMCOD:" + unidades["uf_fonte"] + ":" + unidades["municipio_fonte"])
    for chave, grupo in unidades.groupby("chave_grupo", sort=False):
        primeiro = grupo.iloc[0]
        linhas.append({
            "codigo_municipio_ibge": primeiro["codigo_municipio_ibge"],
            "municipio": primeiro["municipio_ibge"] or primeiro["municipio_fonte"],
            "uf": primeiro["uf_fonte"],
            "quantidade_unidades_fase_ii": len(grupo),
            "nomes_unidades": "; ".join(grupo["nome_unidade_fonte"].tolist()),
            "fonte_primaria": "Chamada Publica MEC/SETEC no 001/2007, Anexo I",
            "paginas_fonte": "; ".join(sorted(set(
                str(p) for p in grupo["pagina_fonte"]))),
            "status_validacao": (grupo["status_validacao"].iloc[0]
                                  if grupo["status_validacao"].nunique() == 1
                                  else "status_misto:" + ",".join(
                                      sorted(grupo["status_validacao"].unique()))),
            "observacao": "; ".join(o for o in grupo["observacao"] if o) or "",
        })
    return pd.DataFrame(linhas)


def main() -> None:
    texto = extrai_texto_pdf(EDITAL_PDF)
    registros, meta = extrai_anexo_i(texto)
    print(f"Total declarado no documento (linha 'TOTAL: N CIDADES'): "
          f"{meta['total_declarado_documento']}")
    print(f"Registros extraidos do Anexo I: {len(registros)}")

    unidades = pd.DataFrame(registros)
    ibge_por_uf = carrega_ibge_por_uf()
    unidades = associa_codigo_ibge(unidades, ibge_por_uf)

    # Sobral/CE e Campinas/SP: sinalizacao explicita pedida.
    for uf, nome in [("CE", "SOBRAL"), ("SP", "CAMPINAS")]:
        achou = unidades[(unidades["uf_fonte"] == uf) &
                         (unidades["municipio_fonte"].str.upper() == nome)]
        print(f"Caso especial {nome}/{uf}: "
              f"{'ENCONTRADO no Anexo I' if len(achou) else 'AUSENTE do Anexo I'}"
              f" ({len(achou)} linha(s))")

    INTERIM.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    unidades.to_parquet(UNIDADES_OUT, index=False)
    print(f"Gravado: {UNIDADES_OUT} ({len(unidades)} linhas)")

    municipios = constroi_tabela_municipios(unidades)
    municipios.to_parquet(MUNICIPIOS_OUT, index=False)
    print(f"Gravado: {MUNICIPIOS_OUT} ({len(municipios)} linhas)")

    print("\n--- Reconciliacoes ---")
    print("Unidades extraidas:", len(unidades))
    print("Municipios/grupos distintos:", len(municipios))
    print("Unidades sem codigo IBGE:",
          int((unidades["codigo_municipio_ibge"].isna()).sum()))
    print("Grupos com mais de 1 unidade:",
          int((municipios["quantidade_unidades_fase_ii"] > 1).sum()))
    print("\nContagem por UF (unidades extraidas):")
    print(unidades["uf_fonte"].value_counts().sort_index().to_string())
    dup = unidades.duplicated(["uf_fonte", "municipio_fonte"], keep=False)
    print("\nNomes duplicados (mesma UF, mesmo nome de municipio_fonte):",
          int(dup.sum()))
    if dup.any():
        print(unidades.loc[dup, ["uf_fonte", "municipio_fonte", "pagina_fonte"]]
              .to_string(index=False))


if __name__ == "__main__":
    main()
