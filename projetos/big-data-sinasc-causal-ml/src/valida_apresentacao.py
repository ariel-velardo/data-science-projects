"""Rastreia números exibidos e exceções explícitas de apresentação autorizadas."""
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUTORIZADOS={'src/cria_notebook_fase2.py','notebooks/03_ml_preditivo_e_aipw.ipynb'}


def hash_arquivo(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hash_fontes_notebook(p):
    nb=json.loads(Path(p).read_text(encoding='utf-8'))
    fontes=[(c['cell_type'],''.join(c['source'])) for c in nb['cells']]
    return hashlib.sha256(json.dumps(fontes,ensure_ascii=False).encode()).hexdigest()


class NumerosTabela(HTMLParser):
    def __init__(self):
        super().__init__(); self.dentro=False; self.numeros=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('td','th'): self.dentro=True
    def handle_endtag(self,tag):
        if tag in ('td','th'): self.dentro=False
    def handle_data(self,data):
        if self.dentro and re.fullmatch(r'[-+]?\d[\d,.eE+%-]*',data.strip()):
            self.numeros.append(data.strip())


def numeros_notebook(p):
    nb=json.loads(p.read_text(encoding='utf-8')); numeros=[]
    for c in nb['cells']:
        for o in c.get('outputs',[]):
            html=o.get('data',{}).get('text/html')
            if html:
                parser=NumerosTabela(); parser.feed(''.join(html)); numeros.append(parser.numeros)
    return numeros


def verificar_preservacao(raiz,atual,original):
    """Mantém os hashes históricos; admite somente dois arquivos explicitamente traduzidos."""
    if atual==original: return
    p=raiz/'outputs/diagnostics/apresentacao_preservacao.json'
    if not p.exists(): raise ValueError('Histórico alterado sem manifesto de apresentação.')
    registro=json.loads(p.read_text(encoding='utf-8'))
    if set(atual)!=set(original): raise ValueError('Inventário histórico alterado.')
    for nome,h in original.items():
        if atual[nome]==h: continue
        r=registro['excecoes'].get(nome)
        valido=nome in AUTORIZADOS and r and r['antes']==h and r['depois']==atual[nome]
        if nome.endswith('.ipynb') and r and r.get('fontes_sha256'):
            valido=(nome in AUTORIZADOS and r['antes']==h and hash_fontes_notebook(raiz/nome)==r['fontes_sha256'])
        if not valido:
            raise ValueError(f'Alteração não autorizada ou não reconciliada: {nome}')


def registrar_base():
    destino=ROOT/'outputs/diagnostics/apresentacao_base.json'
    if destino.exists(): raise ValueError('Base já registrada; não sobrescrever.')
    base={'notebooks':{p.name:numeros_notebook(p) for p in sorted((ROOT/'notebooks').glob('0[1-4]*.ipynb'))},
          'diagnosticos':{p.name:hash_arquivo(p) for p in (ROOT/'outputs/diagnostics').glob('*.json')
             if not p.name.startswith('apresentacao') and '_ajustes' not in p.name},
          'checkpoint':'48ce06b1293924a3573adcce2564ab9416be60b5'}
    destino.write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def registrar_excecoes():
    original=json.loads((ROOT/'outputs/diagnostics/fase3_preservacao.json').read_text(encoding='utf-8'))['historico_sha256']
    excecoes={p:dict(antes=original[p],depois=hash_arquivo(ROOT/p)) for p in sorted(AUTORIZADOS)}
    for p,r in excecoes.items():
        if p.endswith('.ipynb'): r['fontes_sha256']=hash_fontes_notebook(ROOT/p)
    (ROOT/'outputs/diagnostics/apresentacao_preservacao.json').write_text(json.dumps(dict(
        motivo='Tradução PT-BR e reexecução expressamente solicitadas após publicação da Fase 3; hashes originais preservados.',
        excecoes=excecoes),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def validar():
    base=json.loads((ROOT/'outputs/diagnostics/apresentacao_base.json').read_text(encoding='utf-8'))
    for nome,numeros in base['notebooks'].items():
        novo=numeros_notebook(ROOT/'notebooks'/nome)
        assert novo==numeros, f'Números exibidos mudaram: {nome}'
    for nome,h in base['diagnosticos'].items():
        assert hash_arquivo(ROOT/'outputs/diagnostics'/nome)==h,f'Diagnóstico histórico modificado: {nome}'
    print('Quatro notebooks: números das tabelas e diagnósticos históricos preservados.')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--registrar-base',action='store_true'); p.add_argument('--registrar-excecoes',action='store_true')
    a=p.parse_args()
    if a.registrar_base: registrar_base()
    elif a.registrar_excecoes: registrar_excecoes()
    else: validar()
