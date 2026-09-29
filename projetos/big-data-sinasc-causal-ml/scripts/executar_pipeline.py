"""Orquestra as etapas existentes; não contém cálculos científicos."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ETAPAS = ('dados', 'amostra', 'preditivo', 'causal', 'robustez', 'heterogeneidade')


def acoes_projeto():
    from src.sinasc import converter_zip_para_parquet
    from src.auditoria_dados import executar_auditoria_projeto, executar_auditoria_amostra
    from src.modelagem_preditiva import executar_preditivo
    from src.inferencia_causal import executar_causal
    from src.robustez import executar_robustez
    from src.heterogeneidade import executar_heterogeneidade, resumir_heterogeneidade

    def dados():
        converter_zip_para_parquet(ROOT/'data/raw/SINASC_2024_csv.zip',
                                  ROOT/'data/processed/sinasc_2024.parquet')
        executar_auditoria_projeto(ROOT)

    def heterogeneidade():
        executar_heterogeneidade()
        return resumir_heterogeneidade()

    return {'dados': dados, 'amostra': lambda: executar_auditoria_amostra(ROOT),
            'preditivo': lambda: executar_preditivo(ROOT),
            'causal': lambda: executar_causal(ROOT),
            'robustez': lambda: executar_robustez(ROOT),
            'heterogeneidade': heterogeneidade}


def executar_etapa(etapa, acoes=None):
    if etapa not in (*ETAPAS, 'todas'):
        raise ValueError('Etapa desconhecida: '+etapa)
    acoes = acoes_projeto() if acoes is None else acoes
    for nome in ETAPAS if etapa == 'todas' else (etapa,):
        acoes[nome]()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--etapa', choices=(*ETAPAS, 'todas'), required=True)
    args = parser.parse_args(argv)
    executar_etapa(args.etapa)


if __name__ == '__main__':
    main()
