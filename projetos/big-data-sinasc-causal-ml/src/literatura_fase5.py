"""Organiza referências revisadas e tenta obter PDFs públicos, sem contornar bloqueios."""
import argparse
import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from pypdf import PdfReader
from src.entrega_fase5 import ROOT, gravar, tabela_md


def obter(ref):
    pasta=ROOT/'docs/literature/pdfs'; pasta.mkdir(parents=True,exist_ok=True)
    arquivo=pasta/(ref['id']+'.pdf')
    registro=dict(id=ref['id'],origem=ref['url'],url=ref['pdf_url'],arquivo='',disponivel=False,motivo='',tentativas=[])
    try:
        if arquivo.exists():
            conteudo=arquivo.read_bytes()
        else:
            url=ref['pdf_url']
            if not url:
                pagina=requests.get(ref['url'],timeout=25)
                pagina.raise_for_status()
                links=re.findall(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',pagina.text,re.I)
                if not links:
                    raise ValueError('Página pública não forneceu link PDF; possível desafio de acesso. Nenhum bloqueio contornado.')
                url=urljoin(ref['url'],links[0])
            registro['url']=url
            r=requests.get(url,timeout=35); registro['tentativas'].append(dict(url=url,status=r.status_code))
            r.raise_for_status(); conteudo=r.content
        if not conteudo.startswith(b'%PDF-'): raise ValueError('Resposta não é PDF (HTML/desafio de acesso).')
        leitor=PdfReader(io.BytesIO(conteudo)); texto='\n'.join(p.extract_text() or '' for p in leitor.pages)
        if len(texto)<300: raise ValueError('PDF sem texto suficiente para conferir identidade.')
        if not arquivo.exists(): arquivo.write_bytes(conteudo)
        registro.update(disponivel=True,arquivo='pdfs/'+arquivo.name,bytes=len(conteudo),paginas=len(leitor.pages),sha256=hashlib.sha256(conteudo).hexdigest(),motivo='PDF público obtido; identidade conferida pelo texto extraído.')
        # Texto local auxilia a leitura; não será incluído no Git.
        (pasta/(ref['id']+'.txt')).write_text(texto,encoding='utf-8')
    except Exception as e:
        registro['motivo']=str(e)
    return registro


def documentar(refs,manifesto):
    blocos=['# Referências centrais\n\nSeleção dirigida de 12 referências, não revisão sistemática. O mapa inicial e a auditoria do gate permanecem preservados. Priorizados pré-natal/SINASC, predição, AIPW, ajuste cruzado, heterogeneidade, clusters e seleção. Títulos e citações mantêm o idioma original; a análise está em PT-BR. DOIs de versões públicas estão identificados quando distintos do publicado.\n']
    for r in refs:
        blocos.append('## '+r['id']+'\n\n'+r['citacao']+'\n\nDOI: ['+r['doi']+'](https://doi.org/'+r['doi']+'). [Fonte]('+r['url']+').\n\n'+tabela_md(['Dimensão','Síntese'],[[k.capitalize(),r[k]] for k in ['problema','populacao','dados','metodo','resultado','limitacoes','uso']]))
        # Ficha curta: síntese bibliográfica, sem alegação de leitura integral quando apenas resumo disponível.
        m=next(x for x in manifesto if x['id']==r['id'])
        acesso='PDF público obtido; leitura dirigida de resumo, métodos e discussão.' if m['disponivel'] else 'Síntese limitada ao resumo/trechos públicos e mapa já auditado; PDF não obtido nesta sessão.'
        gravar('docs/literature/fichas/'+r['id']+'.md','# Ficha — '+r['id']+'\n\n'+r['citacao']+'\n\n[Fonte consultada]('+r['url']+'). '+acesso+'\n\n'+tabela_md(['Item','Leitura'],[['Pergunta',r['problema']],['População',r['populacao']],['Dados',r['dados']],['Método',r['metodo']],['Principais resultados',r['resultado']],['Limitações',r['limitacoes']],['Relação com o projeto',r['uso']]])+'\nNão transportar efeitos ou garantias deste artigo automaticamente para o SINASC 2024.\n')
    gravar('docs/literature/REFERENCIAS_CENTRAIS.md','\n'.join(blocos)+'\n[Manifesto de PDFs](MANIFESTO_ARTIGOS.md) · [Fichas](fichas/).\n')
    gravar('docs/literature/manifesto_artigos.json',json.dumps(manifesto,ensure_ascii=False,indent=2)+'\n')
    gravar('docs/literature/MANIFESTO_ARTIGOS.md','# Manifesto dos artigos\n\nPDFs obtidos somente por URLs públicas de editoras, PMC, instituições ou autores. Falhas HTTP, respostas HTML e desafios de acesso são registrados, sem contornar paywalls ou bloqueios. PDFs e textos extraídos permanecem locais; o staging inclui apenas manifesto, referências e fichas. Não se exige PDF para navegar no relatório.\n\n'+tabela_md(['Referência','PDF obtido?','Origem','URL tentada','Arquivo local','Motivo'],[[m['id'],'Sim' if m['disponivel'] else 'Não',m['origem'],m['url'],m['arquivo'] or '—',m['motivo']] for m in manifesto])+'\nHashes, páginas e tamanhos: [manifesto estruturado](manifesto_artigos.json). Fichas sem PDF deixam explícita a limitação de leitura.\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--baixar',action='store_true');args=p.parse_args()
    refs=json.loads((ROOT/'docs/literature/referencias_centrais.json').read_text(encoding='utf-8'))
    if args.baixar:
        with ThreadPoolExecutor(max_workers=4) as pool: manifesto=list(pool.map(obter,refs))
    else:
        manifesto=json.loads((ROOT/'docs/literature/manifesto_artigos.json').read_text(encoding='utf-8'))
    documentar(refs,manifesto)
    print(json.dumps([dict(id=m['id'],pdf=m['disponivel'],motivo=m['motivo']) for m in manifesto],ensure_ascii=False,indent=2))
