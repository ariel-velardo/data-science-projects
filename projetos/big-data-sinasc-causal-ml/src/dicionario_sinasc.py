"""Metadados transcritos do dicionário oficial SINASC: Estrutura 1996 a 2019."""

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
