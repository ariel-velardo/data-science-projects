"""Entrega acadêmica offline baseada em agregados."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

DIAG = ROOT / 'outputs/diagnostics'

def ler(nome):
    return json.loads((DIAG / nome).read_text(encoding='utf-8'))

def gravar(caminho, texto):
    p = ROOT / caminho
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding='utf-8')

def numero(valor, casas=6):
    return f'{valor:,.{casas}f}'.replace(',', '_').replace('.', ',').replace('_', '.')

def auditar_dicionario():
    from src.validacao import validar_dicionario
    """Única leitura nova do Parquet: frequências de códigos documentados, sem modelagem."""
    import duckdb
    from pypdf import PdfReader
    from src.sinasc import CODIGOS_ESPECIAIS_DOCUMENTADOS
    from src.sinasc import X_PROVAVEL_PRE_TRATAMENTO
    from src.sinasc import POS_TRATAMENTO

    schema = ler('auditoria_schema_sinasc_2024.json')
    pdf = '\n'.join(p.extract_text() for p in PdfReader(ROOT / 'data/raw/SINASC_Estrutura.pdf').pages)
    # As linhas do layout contêm posição, nome, tipo C e tamanho, seguidos da descrição.
    descricoes = dict(re.findall(r'\d+\s+(\w+)\s+C\s+\d+\s+(.+?)(?=\s+\d{4}\s+C)', pdf, re.S))
    ignorados = {k: [v.split('=')[0]] for k, v in CODIGOS_ESPECIAIS_DOCUMENTADOS.items()}
    ignorados['MESPRENAT'] = ['99']  # Manual oficial 2022, não layout 1996–2019.
    expressoes = []
    for campo, codigos in ignorados.items():
        codigos_sql = ','.join(str(int(c)) for c in codigos)
        expressoes.append(f'count(*) FILTER (WHERE try_cast("{campo}" AS INTEGER) IN ({codigos_sql})) AS "{campo}"')
    with duckdb.connect() as con:
        con.read_parquet(str(ROOT / 'data/processed/sinasc_2024.parquet')).create_view('bruto')
        resultado = con.execute('SELECT ' + ','.join(expressoes) + ' FROM bruto').fetchone()
    contagens = dict(zip(ignorados, resultado))
    n = ler('fase1_amostra.json')['base']['n_registros']
    principais = {'IDADEMAE', 'ESCMAE2010', 'RACACORMAE', 'ESTCIVMAE', 'PARIDADE', 'QTDFILMORT', 'CODMUNRES'}
    linhas = []
    for s in schema:
        nome = s['coluna']; campo = nome.upper()
        descricao = s['descricao_oficial'] or 'NÃO_CONFIRMANDO_DOCUMENTALMENTE'
        dominio = ' '.join(descricoes.get(campo, 'NÃO_CONFIRMANDO_DOCUMENTALMENTE').split())
        if campo == 'KOTELCHUCK':
            dominio = 'Índice de Kotelchuck — avaliação da assistência pré-natal. Códigos: NÃO_CONFIRMANDO_DOCUMENTALMENTE.'
        papel, fases, nota = 'qualidade/auditoria', '0', 'Não integra X; manter códigos originais e zeros à esquerda.'
        if campo in principais:
            papel, fases, nota = 'covariável principal', '0–4', 'Proxy de condição prévia; mensuração no nascimento não demonstra temporalidade perfeita.'
        elif campo in X_PROVAVEL_PRE_TRATAMENTO or campo == 'SEXO':
            papel = 'covariável não utilizada'
            nota = 'Não selecionada para as sete X congeladas; não adicionar por importância preditiva.'
        elif campo in POS_TRATAMENTO or campo in {'CODESTAB', 'LOCNASC', 'TPMETESTIM'}:
            papel = 'pós-tratamento'
            nota = 'Não usar em X: informação do parto/assistência, possível mediação ou seleção.'
        if campo in {'CONSULTAS','CONSPRENAT','GESTACAO','SEMAGESTAC','KOTELCHUCK'}:
            papel = 'potencial mediadora'
        if campo == 'CONSPRENAT':
            fases = '0–1; sensibilidade 3'
            nota = 'Consultas acumuladas; zero não define T=0. Discordância avaliada separadamente.'
        if campo in {'CONTADOR','NUMEROLOTE'}:
            papel = 'identificador'; nota = 'contador é chave apenas nesta extração; lote não é chave individual.'
        if campo == 'CONTADOR': fases = '0–4'
        if campo == 'CODMUNRES': nota = 'Deriva UF em X; município agrupa incerteza e partições nas Fases 3–4, sem nova covariável.'
        if campo == 'MESPRENAT':
            papel, fases = 'tratamento', '0–4'
            dominio += ' Manual 2022: 99=ignorado. Regra do projeto: 1–3 precoce; 4–9 tardio.'
            nota = 'Retrospectivo; missing/99 excluídos. Controle é início tardio, não ausência de pré-natal.'
        if campo == 'PESO':
            papel, fases, nota = 'desfecho', '0–4', 'Y=1 se <2.500 g; elegibilidade principal 500–6.000 g. P0 (>0 g) é sensibilidade.'
        if campo == 'GRAVIDEZ':
            fases, nota = '0–4', 'Elegibilidade: única (1). Definida na concepção, porém registro final pode envolver seleção; não é X.'
        if campo == 'OPORT_DN':
            descricao = dominio = 'NÃO_CONFIRMANDO_DOCUMENTALMENTE'
            nota = 'Campo observado em 2024, ausente do layout oficial localizado; não inferir semântica pelo nome.'
        if campo in {'STDNEPIDEM','STDNNOVA'}:
            nota += ' O PDF escreve “DO”; sigla preservada como inconsistência documental, sem correção silenciosa.'
        ni = contagens.get(campo)
        linhas.append(dict(nome=nome, descricao=descricao, tipo=s['tipo_observado'], dominio=dominio,
            missing_pct=s['percentual_missing'], ignorado_pct=None if ni is None else 100*ni/n,
            missing_ignorado_pct=None if ni is None else 100*(s['n_missing']+ni)/n,
            regra_ignorado=' / '.join(ignorados[campo]) if campo in ignorados else 'NÃO_CONFIRMANDO_DOCUMENTALMENTE',
            exemplos=', '.join(s['exemplos_frequentes']), papel=papel, fases=fases, observacao=nota,
            fonte='Layout oficial 1996–2019; schema auditado 2024; manual 2022 para MESPRENAT'))
    validar_dicionario(linhas, [s['coluna'] for s in schema])
    gravar('outputs/tables/dicionario_analitico_sinasc_2024.json', json.dumps(linhas, ensure_ascii=False, indent=2)+'\n')
    with (ROOT / 'outputs/tables/dicionario_analitico_sinasc_2024.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0])); w.writeheader(); w.writerows(linhas)
    return linhas

def metricas():
    a, c, p, r = (ler(n) for n in ['fase1_amostra.json','fase2_aipw.json','fase2_modelagem_preditiva.json','fase4_resultados.json'])
    valores = {}; rotulos = {}
    def incluir(chave, rotulo, valor, casas=6):
        valores[chave] = numero(valor, casas) if isinstance(valor, (float, int)) else valor
        rotulos[chave] = rotulo
    incluir('bruto','Registros brutos',a['base']['n_registros'],0)
    incluir('colunas','Colunas originais',len(ler('auditoria_schema_sinasc_2024.json')),0)
    for k, label in [('n','Registros analíticos'),('n_t1','T=1: início até o terceiro mês'),('n_t0','T=0: início após o terceiro mês')]:
        incluir(k,label,r['populacao'][k],0)
    incluir('prevalencia','Baixo peso na população analítica (%)',100*r['populacao']['prevalencia'])
    ufs = {x['categoria'] for x in r['quintis_composicao_x'] if x['variavel']=='UF_RESIDENCIA' and x['categoria']!='IGNORADO'}
    incluir('ufs','UFs de residência',len(ufs),0)
    incluir('bruta','Associação bruta NÃO CAUSAL (pp)',c['associacao_bruta']['diferenca_pp'])
    for i,m in enumerate(p['modelos']):
        for k,label in [('roc_auc','ROC-AUC'),('pr_auc_ap','AP'),('brier','Brier')]:
            incluir(f'pred_{i}_{k}',f'{"Logística" if i==0 else "HGB"}: {label}',m[k])
    for s in c['resultados']:
        if s['populacao']=='sem_trimming':
            for k,label in [('estimativa_pp','estimativa'),('ic95_inferior_pp','IC95% inferior iid'),('ic95_superior_pp','IC95% superior iid')]:
                incluir(s['especificacao']+'_'+k,s['especificacao']+' AIPW: '+label+' (pp)',s[k])
    for s in ler('fase3_cluster.json')['resultados']:
        if s['populacao']=='sem_trimming':
            incluir(s['especificacao']+'_cluster',s['especificacao']+' EP municipal (pp)',s['se_cluster_pp'])
    for k in ['media_pp','mediana_pp','p05_pp','p25_pp','p75_pp','p95_pp']:
        incluir('cate_'+k,'CATE HGB '+{'media_pp':'média','mediana_pp':'mediana','p05_pp':'p5','p25_pp':'p25','p75_pp':'p75','p95_pp':'p95'}[k]+' (pp)',r['principal'][k])
    incluir('estabilidade','Correlação mediana dos perfis entre partições',r['estabilidade']['mediana_spearman_perfis'])
    incluir('modelos','Spearman HGB/Ridge',r['estabilidade']['spearman_hgb_ridge'])
    incluir('gate2','Gate histórico da Fase 2',c['gate'])
    incluir('gate3','Gate da Fase 3',ler('fase3_gate.json')['gate'])
    incluir('gate4','Gate da Fase 4',r['gate'])
    return valores, rotulos

def marcador(chave, valores):
    return f'<span data-metrica="{chave}">{html.escape(valores[chave])}</span>'

def tabela_md(cabecalhos, linhas):
    return '\n'.join(['| '+' | '.join(cabecalhos)+' |', '| '+' | '.join(['---']*len(cabecalhos))+' |'] +
        ['| '+' | '.join(str(x).replace('|',' / ').replace('\n',' ') for x in r)+' |' for r in linhas])+'\n'

def tabela_html(cabecalhos, linhas, id_tabela=''):
    return '<div class="tabela"><table '+(f'id="{id_tabela}"' if id_tabela else '')+'><thead><tr>'+''.join('<th>'+html.escape(c)+'</th>' for c in cabecalhos)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in r)+'</tr>' for r in linhas)+'</tbody></table></div>'

def figuras():
    import pandas as pd
    import plotly.graph_objects as go
    from src.visualizacao import aplicar_tema_base as aplicar_tema_ipt
    a=ler('fase1_amostra.json'); c=ler('fase2_aipw.json'); p=ler('fase2_modelagem_preditiva.json'); r=ler('fase4_resultados.json')
    saida=[]
    def add(id_,titulo,fig,fonte,nota):
        aplicar_tema_ipt(fig,titulo)
        fig.update_layout(autosize=True,height=440,font=dict(size=15),margin=dict(l=100,r=35,t=70,b=95),separators=',.')
        fig.update_xaxes(automargin=True); fig.update_yaxes(automargin=True)
        saida.append(dict(id=id_,titulo=titulo,fig=fig,fonte=fonte,nota=nota))
    add('fluxo','Da base à população analítica',go.Figure(go.Bar(x=['Bruto','T/Y válidos','Peso 500–6.000 g','Gestação única'],y=[a['base']['n_registros']]+[x['n_restante'] for x in a['fluxo_amostra'][:3]])).update_yaxes(title='Nascidos vivos (N)',rangemode='tozero'),'fase1_amostra.json','Filtros sequenciais; as sete X não excluem novos registros.')
    perfil=a['perfil_tratamento_amostra_principal']
    add('tratamento','Início precoce e tardio',go.Figure(go.Bar(x=['Precoce (T=1)','Tardio (T=0)'],y=[x['n'] for x in perfil])).update_yaxes(title='Nascidos vivos (N)',rangemode='tozero'),'fase1_amostra.json','Distribuição na população analítica; T=0 não significa ausência de pré-natal.')
    add('prevalencia','Baixo peso observado por grupo',go.Figure(go.Bar(x=['Precoce (T=1)','Tardio (T=0)'],y=[x['baixo_peso_pct_descritivo'] for x in perfil])).update_yaxes(title='Baixo peso (%)',rangemode='tozero'),'fase1_amostra.json','Descrição bruta; diferenças de composição impedem interpretar as barras como efeitos.')
    labels={'IDADEMAE_NUM':'Idade materna','ESCOLARIDADE_MAE':'Escolaridade','RACA_COR_MAE':'Raça/cor materna','SITUACAO_CONJUGAL':'Situação conjugal','PARIDADE_CAT':'Paridade','PERDAS_FETAIS_CAT':'Perdas fetais','UF_RESIDENCIA':'UF de residência'}
    smd=sorted(a['balanceamento_bruto'],key=lambda x:x['smd_abs'])
    f=go.Figure(go.Bar(x=[x['smd_abs'] for x in smd],y=[labels.get(x['variavel'],x['variavel']) for x in smd],orientation='h')); f.add_vline(x=.1,line_dash='dash'); f.update_xaxes(title='Diferença padronizada absoluta (SMD)',rangemode='tozero')
    add('smd','Desequilíbrio antes do ajuste',f,'fase1_amostra.json','Para categóricas, nível de maior SMD absoluto. Linha 0,1 é referência diagnóstica.')
    caminho_hist=ROOT/'outputs/tables/fase5_histograma_propensity.json'
    hist=pd.DataFrame(json.loads(caminho_hist.read_text(encoding='utf-8'))); f=go.Figure()
    for grupo,d in hist.groupby('grupo'):
        f.add_scatter(x=((d.limite_inferior+d.limite_superior)/2).tolist(),y=(100*d.n/d.n.sum()).tolist(),mode='lines',name=str(grupo))
    f.update_xaxes(title='Escore de propensão (probabilidade)'); f.update_yaxes(title='Frequência no grupo (%)')
    add('overlap','Suporte comum entre os grupos',f,'fase1_overlap.json; histograma_propensity.csv','Diagnóstico OOF de cinco partições da Fase 1; suporte observado não prova intercambialidade.')
    f=go.Figure()
    for i,m in enumerate(p['modelos']): f.add_scatter(x=m['roc']['x'],y=m['roc']['y'],mode='lines',name='Logística' if i==0 else 'HGB')
    f.add_scatter(x=[0,1],y=[0,1],mode='lines',name='Referência',line=dict(dash='dash'));f.update_xaxes(title='Taxa de falsos positivos',range=[0,1]);f.update_yaxes(title='Sensibilidade',range=[0,1])
    add('roc','Discriminação preditiva no teste',f,'fase2_modelagem_preditiva.json','Mesmas sete X, sem T. AP e Brier complementam a ROC na tabela de resultados.')
    f=go.Figure()
    for spec in ['C1','C2']:
        rows=[s for s in c['resultados'] if s['especificacao']==spec]
        f.add_scatter(x=[s['estimativa_pp'] for s in rows],y=[{'sem_trimming':'Integral','0.01_0.99':'Suporte 0,01–0,99','0.05_0.95':'Suporte 0,05–0,95'}[s['populacao']] for s in rows],mode='markers',name=spec,error_x=dict(array=[1.96*s['se_pp'] for s in rows]))
    f.add_vline(x=0,line_dash='dash');f.update_xaxes(title='Diferença estimada de risco (pp); IC95% iid')
    add('aipw','AIPW e sensibilidade ao suporte',f,'fase2_aipw.json','Recorte muda a população-alvo. ICs não incorporam viés de seleção ou confundimento.')
    f=go.Figure(); geo=ler('fase3_crossfit_geografico.json')
    for chave,nome in [('aleatorio','Partições aleatórias'),('agrupado','Partições municipais')]:
        rows=[s for s in geo[chave]['resultados'] if s['populacao']=='sem_trimming']
        f.add_scatter(x=[s['estimativa_pp'] for s in rows],y=[s['especificacao'] for s in rows],mode='markers',name=nome,error_x=dict(array=[s['ic95_cluster_superior_pp']-s['estimativa_pp'] for s in rows]))
    f.add_vline(x=0,line_dash='dash');f.update_xaxes(title='Diferença estimada de risco (pp); IC95% municipal')
    add('geografia','Robustez à separação municipal',f,'fase3_crossfit_geografico.json','ICs supõem independência entre municípios. Estabilidade numérica não elimina confundimento.')
    h=r['histograma']; lim=h['limites_pp']; f=go.Figure(go.Bar(x=[(a+b)/2 for a,b in zip(lim,lim[1:])],y=h['contagens'],width=[b-a for a,b in zip(lim,lim[1:])]))
    f.add_vline(x=0,line_dash='dash');f.update_xaxes(title='CATE previsto (pp)');f.update_yaxes(title='Previsões externas (N)')
    add('cate','Distribuição integral do CATE previsto',f,'fase4_resultados.json','Distribuição de previsões, não de efeitos individuais conhecidos. p5–p95 não é IC.')
    rows=[x for x in r['perfis'] if x['dimensao']=='Faixa etária' and x['grupo']!='Ausente'];f=go.Figure(go.Scatter(x=[x['media_pp'] for x in rows],y=[x['grupo'] for x in rows],mode='markers',error_x=dict(symmetric=False,array=[x['p95_pp']-x['media_pp'] for x in rows],arrayminus=[x['media_pp']-x['p05_pp'] for x in rows])))
    f.update_xaxes(title='CATE médio (pp); barras p5–p95, não IC');f.update_yaxes(title='Idade materna (anos)'); f.add_vline(x=0,line_dash='dash')
    add('perfis','Perfis de idade: exercício exploratório',f,'fase4_resultados.json','32 idades ausentes ficam fora deste gráfico, mas permanecem no N integral. Não indica prioridade clínica.')
    return saida

def linhas_robustez():
    """Todos os cenários previstos, sem selecionar especificação pela estimativa."""
    rows=[]
    sens=ler('fase3_sensibilidades.json')
    for nome,obj in [('Municipal',ler('fase3_crossfit_geografico.json')['agrupado']),
                     ('C3',sens['S0']),('Excluir discordância',sens['CONSPRENAT']),
                     ('Peso positivo',sens['P0']),('Incluir múltiplas',sens['MULTIPLAS'])]:
        for s in obj['resultados']:
            if s['populacao']=='sem_trimming' and (nome!='C3' or s['especificacao']=='C3'):
                rows.append([nome,s['especificacao'],numero(s['n'],0),numero(s['estimativa_pp']),
                             numero(s['se_cluster_pp']),numero(s['ic95_cluster_inferior_pp'])+' a '+numero(s['ic95_cluster_superior_pp'])])
    return rows

def gerar():
    from src.validacao import validar_dicionario
    valores, rotulos = metricas(); m=lambda k:marcador(k,valores)
    d=json.loads((ROOT/'outputs/tables/dicionario_analitico_sinasc_2024.json').read_text(encoding='utf-8'))
    validar_dicionario(d,[s['coluna'] for s in ler('auditoria_schema_sinasc_2024.json')])
    cab=['Indicador','Resultado']; linhas=[[rotulos[k],m(k)] for k in valores]
    tabela=tabela_md(cab,linhas)
    causal='O início precoce apresenta menor risco ajustado na população selecionada. A estabilidade numérica não comprova causalidade: confundimento residual, seleção de nascidos vivos e temporalidade das covariáveis continuam limitantes.'
    gates='Gates preservados: Fase 0 `VIAVEL_COM_RESSALVAS`; Fase 1 `PRONTO_COM_RESSALVAS`; Fase 2 `RESULTADO_NAO_INTERPRETAVEL`; Fase 3 `GATE_FASE2_EXCESSIVAMENTE_CONSERVADOR`; Fase 4 `HETEROGENEIDADE_SENSIVEL_A_MODELO`. A revisão da Fase 3 questiona o veto pela concentração de influência, sem apagar o gate histórico nem certificar identificação causal.'
    # Tabela adicional pequena, gerada de todas as sensibilidades relevantes, sem seleção por sinal.
    robustez=linhas_robustez()
    rcab=['Cenário','Modelo','N','Estimativa (pp)','EP municipal (pp)','IC95% municipal (pp)']
    gravar('docs/RESULTADOS_PRINCIPAIS.md','# Resultados principais — SINASC 2024\n\n'+causal+'\n\n'+tabela+'\n## Robustez\n\n'+tabela_md(rcab,robustez)+'\nMúltiplas e peso positivo definem outros alvos. ICs são condicionais e aproximados. Percentis de CATE são dispersão prevista, não confiança individual.\n\n'+gates+'\n\nFonte: JSONs históricos em `outputs/diagnostics/`; geração por `python -m src.entrega`. [Metodologia](METODOLOGIA_DO_PROJETO.md).\n')
    fluxo=ler('fase1_amostra.json')['fluxo_amostra']
    gravar('docs/dados/FLUXO_DOS_DADOS.md','# Fluxo dos dados\n\nSINASC bruto → Parquet textual → filtros → população principal → X/T/Y → propensity → AIPW → robustez → DR-Learner.\n\nBruto: '+valores['bruto']+' registros.\n\n'+tabela_md(['Etapa','Regra','Excluídos','Restantes'],[[x['etapa'],x['motivo'],numero(x['n_excluido'],0),numero(x['n_restante'],0)] for x in fluxo])+'\nUnidade: nascido vivo; chave `contador`, única nesta extração. Não há identificador longitudinal de mãe. T: meses 1–3 versus 4–9; Y: peso <2.500 g. X: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF maternas.\n\nO tempo zero é conceitual (início da gestação); o mês é retrospectivo. Outcome medido ao nascer em 2024. Consultas acumuladas, idade gestacional, parto e Apgar não entram em X. A amostra é selecionada por informação, sobrevivência e peso.\n\nPropensity de cinco partições diagnostica suporte (Fase 1). AIPW usa três partições (Fase 2). Auditoria e partições municipais compõem a Fase 3. DR-Learner usa três papéis municipais disjuntos por rodada (Fase 4). Nada foi reestimado na Fase 5.\n\nFonte: `fase1_amostra.json`, campo `fluxo_amostra`. [Contrato e limitações](../METODOLOGIA_DO_PROJETO.md).\n')
    dcab=['Campo','Descrição','Tipo','Domínio / códigos','Ausente (%)','Ignorado (%)','Ausente + ignorado (%)','Exemplos frequentes','Papel','Fases','Observação']
    dl=[]
    for x in d:
        pct=lambda v:'Não confirmado' if v is None else numero(v)
        dl.append([x['nome'],x['descricao'],x['tipo'],x['dominio'],pct(x['missing_pct']),pct(x['ignorado_pct']),pct(x['missing_ignorado_pct']),x['exemplos'],x['papel'],x['fases'],x['observacao']])
    dnota='62 colunas, uma linha por campo original, na ordem do schema auditado. Ausente é nulo/vazio segundo a auditoria da Fase 0. Ignorado conta apenas códigos documentalmente confirmados; quando não há código confirmado, o percentual combinado é desconhecido, não zero. Zero estrutural e “não se aplica” não são ignorados. Denominador: toda a base bruta. Os exemplos são valores frequentes independentes por coluna, nunca registros individuais.\n\nOPORT_DN: **NÃO_CONFIRMANDO_DOCUMENTALMENTE**. O layout disponível termina em 2019; não é um layout específico de 2024. Domínios numéricos e códigos não enumerados no layout não são inventados. PARIDADE e perdas seguem as regras operacionais do contrato, distintas da comprovação documental de todos os códigos.\n\n'
    gravar('docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md','# Dicionário analítico SINASC 2024\n\n'+dnota+'[Fontes oficiais](../sources/FONTES_OFICIAIS.md) · [Versão JSON versionada](../../outputs/tables/dicionario_analitico_sinasc_2024.json). CSV local no mesmo diretório do JSON, ignorado pela política geral.\n\n'+tabela_md(dcab,dl))
    essenciais=['bruto','colunas','n','n_t1','n_t0','prevalencia','ufs','C1_estimativa_pp','C2_estimativa_pp','cate_media_pp','gate4']
    resumo=tabela_md(cab,[[rotulos[k],m(k)] for k in essenciais])
    gravar('docs/SINTESE_EXECUTIVA.md','# Síntese executiva — Big Data & Analytics\n\n## Problema e dados\n\nInvestigar se início precoce do pré-natal está associado a menor risco de baixo peso entre registros comparáveis em características observáveis. Fonte: SINASC 2024, Ministério da Saúde.\n\n'+resumo+'\n## O que o trabalho entrega\n\nO volume nacional exige leitura seletiva, agregações e contratos reproduzíveis: DuckDB executa SQL sobre Parquet e Pandas materializa resumos. Big Data aqui é disciplina de processamento e veracidade, sem alegação de infraestrutura distribuída.\n\nA predição compara logística e HGB com as mesmas sete características maternas. A discriminação é modesta; prever risco não responde se mudar o início do cuidado mudaria o desfecho.\n\n'+causal+' O AIPW combina regressões de risco com o escore de propensão e avalia cada registro fora do treino. A auditoria municipal amplia a incerteza e mantém estimativas próximas.\n\nO DR-Learner produz ordenação parcial, mas exagera a separação entre extremos e apresenta instabilidade de perfis. CATE previsto não é benefício individual conhecido. Não há recomendação clínica ou ROI.\n\n## Conclusão\n\nA contribuição é uma análise nacional reproduzível que distingue descrição, predição e estimativas sob hipóteses causais. Os resultados justificam discussão acadêmica; não demonstram que antecipar o pré-natal cause a redução estimada.\n\n'+gates+'\n\n`MODELAGEM_CONCLUIDA = SIM`; `ARTIGO_COMPLETO = NAO`; `RELATORIO_HTML = SIM`; `CAUSALIDADE_PROVADA = NAO`.\n\n[Resultados e ICs](RESULTADOS_PRINCIPAIS.md) · [Métodos](METODOLOGIA_DO_PROJETO.md) · [Referências](literature/REFERENCIAS_CENTRAIS.md).\n')
    gravar('README.md','# SINASC 2024 — pré-natal, baixo peso e aprendizado de máquina\n\nTrabalho acadêmico de **Big Data & Analytics**. Fases 0–4 concluídas; Fase 5 consolida a entrega sem novos modelos.\n\n## Pergunta\n\nEntre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?\n\n'+causal+'\n\n## Comece aqui\n\n- Abra [o relatório interativo](apresentacao/relatorio_interativo_sinasc_2024.html) com dois cliques após baixar o arquivo. Funciona offline, sem Python ou servidor. O GitHub pode exibir o código em vez de renderizar.\n- Leia a [síntese executiva](docs/SINTESE_EXECUTIVA.md), os [resultados](docs/RESULTADOS_PRINCIPAIS.md) e a [metodologia](docs/METODOLOGIA_DO_PROJETO.md).\n- Consulte o [dicionário das 62 colunas](docs/dados/DICIONARIO_ANALITICO_SINASC_2024.md), o [fluxo](docs/dados/FLUXO_DOS_DADOS.md), as [referências](docs/literature/REFERENCIAS_CENTRAIS.md) e o [esqueleto do artigo](docs/artigo/ESQUELETO_ARTIGO.md).\n\n## Números centrais\n\n'+resumo+'\n## Fonte e arquitetura\n\nMinistério da Saúde, [SINASC — dados abertos](https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc), recurso Nascidos Vivos 2024. [Documentação oficial](docs/sources/FONTES_OFICIAIS.md).\n\n`data/raw/` preserva o ZIP e o dicionário; `data/processed/` guarda o Parquet; `src/` contém módulos conceituais; `scripts/` orquestra execução e validação; `outputs/diagnostics/` registra números e contratos; `notebooks/` contém cinco artefatos-fonte executáveis; `docs/` consolida métodos/literatura; `apresentacao/` contém o HTML. Dados grandes e caches ficam locais. [Arquitetura e módulos](docs/architecture/ARQUITETURA_FINAL.md).\n\n## Notebooks e reprodução\n\nSequência: 01 auditoria → 02 amostra/overlap → 03 predição/AIPW → 04 robustez → 05 heterogeneidade. Veja [entradas, objetivos e saídas](docs/REPRODUCAO.md). Os cinco notebooks já estão executados.\n\nNo PowerShell, dentro deste projeto:\n\n```powershell\n.\\.venv\\Scripts\\Activate.ps1\n$env:PYTHONUTF8 = "1"\npython -m pytest -q tests\npython -m src.entrega\npython scripts/validar_projeto.py --rapida\nStart-Process .\\apresentacao\\relatorio_interativo_sinasc_2024.html\n```\n\nPara configurar um ambiente novo e reproduzir as fases, siga [REPRODUCAO.md](docs/REPRODUCAO.md). Abrir o HTML não exige reinstalar ou recalcular.\n\n## Estado e limites\n\n'+gates+'\n\n[Estado atual e histórico](docs/playbooks/ESTADO_ATUAL.md). `CAUSALIDADE_PROVADA = NAO`. A modelagem terminou; o artigo completo ainda não foi escrito. Uma versão Streamlit pode ser desenvolvida futuramente para portfólio.\n')
    fs=figuras()
    refs=json.loads((ROOT/'docs/literature/referencias_centrais.json').read_text(encoding='utf-8'))
    # Um único runtime Plotly embutido; apenas agregados nos gráficos.
    from plotly.offline import get_plotlyjs
    def grafico(id_):
        x=next(f for f in fs if f['id']==id_)
        return '<figure>'+x['fig'].to_html(full_html=False,include_plotlyjs=False,div_id='fig-'+id_,config={'responsive':True,'displayModeBar':False})+'<figcaption>'+html.escape(x['nota'])+' <small>Fonte: '+html.escape(x['fonte'])+'</small></figcaption></figure>'
    secoes=[]
    def sec(id_,titulo,corpo): secoes.append((id_,titulo,corpo))
    sec('visao','Visão geral','<p class="eyebrow">IPT · Big Data & Analytics · SINASC 2024</p><h1>Pré-natal e baixo peso:<br>associação, predição e limites causais</h1><p class="lead">'+causal+'</p><div class="cards">'+''.join('<div><strong>'+m(k)+'</strong><span>'+rotulos[k]+'</span></div>' for k in ['bruto','colunas','n','n_t1','n_t0','prevalencia','ufs'])+'</div><p class="aviso">Heterogeneidade sensível ao modelo. Causalidade não comprovada. Sem recomendação clínica.</p>')
    sec('pergunta','Pergunta de pesquisa','<p>Entre gestantes comparáveis em características observáveis, iniciar o pré-natal até o terceiro mês de gestação está associado a uma redução no risco de baixo peso ao nascer?</p><p>A unidade observada é o registro de nascido vivo. A pergunta sobre gestantes não permite extrapolação automática para todas as concepções.</p>')
    sec('fonte','Fonte dos dados','<p>Ministério da Saúde, Sistema de Informações sobre Nascidos Vivos. Extração de 2024, adquirida em 25/09/2026; proveniência e hashes preservados no repositório.</p><p><a href="https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc">Portal oficial</a>. Layout estrutural até 2019 e manual da DNV de 2022; OPORT_DN permanece sem definição documental confirmada.</p>')
    sec('base','Base SINASC','<p>Uma linha por nascido vivo; contador único nesta extração. Não há chave longitudinal validada de mãe ou gestação. O processamento usa DuckDB/SQL e Parquet para preservar códigos e limitar a materialização em memória.</p><p>A cobertura desta extração não equivale a todas as concepções. Qualidade de registro, informação ausente e seleção precisam acompanhar os números.</p>')
    sec('dicionario','Dicionário de dados','<p>'+dnota.split('\n\n')[0]+'</p><label for="busca">Pesquisar campo, descrição ou papel</label><input id="busca" type="search" placeholder="Ex.: MESPRENAT, peso, covariável"><p id="contador-dicionario" aria-live="polite">62 campos</p>'+tabela_html(dcab,[[html.escape(str(v)) for v in row] for row in dl],'dicionario-tabela'))
    sec('amostra','Construção da amostra','<p>T=1: início nos meses 1–3; T=0: meses 4–9. Y=1: peso inferior a 2.500 g. Principal: gestação única, peso 500–6.000 g e T conhecido. Ausentes em X são tratados no processamento de cada treino.</p>'+grafico('fluxo'))
    sec('perfil','Perfil da população','<p>Sete X: idade, escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF maternas. Os grupos diferem antes do ajuste.</p>'+grafico('tratamento')+grafico('prevalencia')+grafico('smd'))
    sec('ml','Machine Learning preditivo','<p><b>Quem apresenta maior risco?</b> Logística e HGB usam as mesmas sete X, sem T; divisão 80/20 e teste separado. ROC-AUC modesta; AP é average precision e Brier mede erro das probabilidades (menor é melhor).</p>'+tabela_html(cab,[[rotulos[k],m(k)] for k in valores if k.startswith('pred_')])+grafico('roc')+'<p>Baixa ROC-AUC não invalida, por si só, AIPW; bom desempenho preditivo tampouco prova efeito causal.</p>')
    sec('causal','Inferência causal','<p><b>Qual seria a diferença média estimada sob tratamentos diferentes, condicionada às hipóteses adotadas?</b> O contraste observável padroniza associações na população selecionada.</p>'+grafico('overlap')+grafico('aipw')+'<details><summary>Como funciona o AIPW e o ajuste cruzado</summary><p>Combina riscos previstos m1 e m0 com correções dos resíduos pelo propensity e. Cada registro recebe previsões de modelos ajustados sem seu desfecho. C1 usa regressões logísticas; C2 compartilha e e usa HGB para os riscos.</p><code>psi = m1 − m0 + T(Y−m1)/e − (1−T)(Y−m0)/(1−e)</code><p>A média de psi estima o contraste. Consistência, ausência de confundimento, positividade, temporalidade, mensuração e seleção defensável continuam necessárias. Dupla robustez não remove confundidores ausentes.</p></details>')
    sec('robustez','Robustez','<p>O agrupamento municipal aumenta a incerteza; a separação municipal de treino/avaliação altera pouco as estimativas. Sensibilidades de elegibilidade mudam a população-alvo.</p>'+grafico('geografia')+tabela_html(rcab,robustez)+'<details><summary>Por que o gate da Fase 2 foi revisto?</summary><p>'+gates.replace('`','')+'</p><p>Concentração de IF² no 1% extremo não equivale à dominância individual nem constitui teste universal de invalidade. Auditoria, literatura e simulações motivaram a revisão adicional.</p></details>')
    sec('heterogeneidade','Heterogeneidade','<p><b>Esse efeito estimado parece variar sistematicamente entre perfis?</b> O DR-Learner separa municípios em três papéis: ajustar auxiliares, aprender CATE e avaliar externamente. Há ordenação parcial, mas perfis instáveis e separação prevista excessiva.</p>'+grafico('cate')+grafico('perfis')+'<p>Gate: '+m('gate4')+'. Spearman mediano entre perfis: '+m('estabilidade')+'. CATE variável não significa benefício individual conhecido. Barras de percentis não são intervalos de confiança.</p>')
    sec('limites','Limitações','<ul><li>Renda, tabagismo, nutrição, morbidades e acesso/qualidade não estão adequadamente controlados.</li><li>Seleção por nascido vivo, peso e mês informado pode induzir viés.</li><li>Covariáveis registradas no parto são proxies de condições anteriores.</li><li>ICs não incorporam todos os erros de mensuração, aprendizagem e dependência espacial.</li><li>Instabilidade dos perfis impede uso clínico ou priorização individual.</li></ul>')
    sec('conclusoes','Conclusões','<p>'+causal+'</p><p>A contribuição é separar três perguntas com dados nacionais e validação reproduzível. A modelagem terminou; o material é base para o artigo da disciplina, ainda não escrito.</p><details><summary>Todos os resultados centrais e gates</summary>'+tabela_html(cab,linhas)+'</details><p>MODELAGEM_CONCLUIDA = SIM · ARTIGO_COMPLETO = NAO · RELATORIO_HTML = SIM · CAUSALIDADE_PROVADA = NAO</p>')
    sec('referencias','Referências','<p>Seleção dirigida, não sistemática. Os estudos diferem em população, exposição e desenho; não se transportam diretamente seus efeitos para o SINASC 2024.</p><ol>'+''.join('<li>'+html.escape(rf['citacao'])+' <a href="'+html.escape(rf['url'])+'">Fonte</a> · DOI: '+html.escape(rf['doi'])+'</li>' for rf in refs)+'</ol>')
    css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f7f9;color:#133c5a;font:17px/1.65 Arial,sans-serif}nav{position:fixed;inset:0 auto 0 0;width:245px;overflow:auto;background:#133c5a;padding:28px 20px}nav b{color:#04b4e3;display:block;margin-bottom:20px}nav a{display:block;color:white;text-decoration:none;padding:8px 10px;font-size:14px;border-radius:5px}nav a:hover,nav a:focus{background:#226986}main{margin-left:245px;max-width:1450px;padding:30px 55px}section{padding:35px 0;border-bottom:1px solid #d9e7ee;scroll-margin-top:15px}h1{font-size:clamp(30px,3.5vw,52px);line-height:1.15;letter-spacing:-1px}h2{font-size:27px;color:#00598e}.eyebrow{font-size:13px;font-weight:bold;letter-spacing:2px}.lead{font-size:21px;max-width:950px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.cards>div{background:white;padding:19px;border-top:4px solid #04b4e3}.cards strong{display:block;font-size:29px;color:#00598e}.cards span{font-size:14px}.cards strong span{font-size:inherit}.aviso{border-left:5px solid #00598e;padding:14px;background:#e7f1f6}figure{background:white;margin:25px 0;padding:12px;border:1px solid #d9e7ee;border-radius:8px;overflow:hidden}figcaption{padding:5px 20px;font-size:15px}small{display:block;color:#526576}.tabela{overflow:auto;max-width:100%;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:14px;background:white}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #d9e7ee}th{background:#e7f1f6;position:sticky;top:0}#dicionario-tabela{min-width:1750px}#dicionario-tabela td:nth-child(4){min-width:280px}#dicionario .tabela{max-height:600px}input{display:block;width:100%;padding:14px;font-size:17px;border:1px solid #82b0c6;border-radius:5px}details{background:#e7f1f6;padding:18px;margin:20px 0}summary{cursor:pointer;font-weight:bold}a{color:#00598e}code{white-space:normal}footer{padding:30px 0;font-size:13px}@media(max-width:900px){nav{position:static;width:auto;max-height:220px}main{margin:0;padding:20px}.cards{grid-template-columns:repeat(2,1fr)}}@media(max-width:480px){.cards{grid-template-columns:1fr}main{padding:14px}h1{font-size:30px}}@media print{nav,input{display:none}main{margin:0;padding:0}section,figure{break-inside:avoid}}'''
    doc='<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SINASC 2024 — entrega acadêmica</title><style>'+css+'</style><script>'+get_plotlyjs()+'</script></head><body><nav aria-label="Seções do relatório"><b>SINASC 2024</b>'+''.join('<a href="#'+id_+'">'+titulo+'</a>' for id_,titulo,_ in secoes)+'</nav><main>'+''.join('<section id="'+id_+'">'+('' if id_=='visao' else '<h2>'+titulo+'</h2>')+corpo+'</section>' for id_,titulo,corpo in secoes)+'<footer>Entrega acadêmica · dados agregados de 2024 · Fases 0–4 preservadas · não é ferramenta clínica.</footer></main><script>document.getElementById("busca").addEventListener("input",function(){const q=this.value.normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase();let n=0;document.querySelectorAll("#dicionario-tabela tbody tr").forEach(r=>{r.hidden=!r.textContent.normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().includes(q);if(!r.hidden)n++});document.getElementById("contador-dicionario").textContent=n+" campos"});</script></body></html>'
    doc='\n'.join(linha.rstrip(' \t') for linha in doc.split('\n'))
    gravar('apresentacao/relatorio_interativo_sinasc_2024.html',doc)
    gravar('docs/GRAFICOS_FINAIS.md','# Gráficos finais\n\nDez gráficos selecionados entre os temas dos notebooks e redesenhados dos mesmos agregados para leitura offline. Tema IPT do projeto; fontes históricas preservadas.\n\n'+tabela_md(['ID','Gráfico','Fonte','Leitura'],[[f['id'],f['titulo'],f['fonte'],f['nota']] for f in fs])+'\nO HTML embute uma única cópia do Plotly. Não embute observações individuais. Os gráficos históricos permanecem em `outputs/figures/` e nos notebooks.\n')
    gravar('outputs/diagnostics/fase5_metricas.json',json.dumps(valores,ensure_ascii=False,indent=2)+'\n')
    print('Entrega gerada; execute --validar para conferir os artefatos.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--auditar-dicionario', action='store_true')
    parser.add_argument('--validar', action='store_true')
    args = parser.parse_args()
    if args.auditar_dicionario:
        auditar_dicionario()
    elif args.validar:
        from src.validacao import validar_entrega
        validar_entrega()
    else:
        gerar()
