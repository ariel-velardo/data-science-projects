"""Valida artefatos existentes sem refazer modelos."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument('--rapida', action='store_true')
    modo.add_argument('--completa', action='store_true')
    args = parser.parse_args(argv)
    from src.validacao import validar_projeto
    validar_projeto(completa=args.completa)


if __name__ == '__main__':
    main()
