"""Baixa apenas as fontes oficiais já declaradas pelo projeto."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-acesso', default=None)
    args = parser.parse_args(argv)
    from src.sinasc import baixar_fontes_e_gerar_manifesto
    print(json.dumps(baixar_fontes_e_gerar_manifesto(ROOT, args.data_acesso),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
