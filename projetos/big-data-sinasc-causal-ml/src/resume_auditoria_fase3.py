"""Tabelas do relatório Fase 3 derivadas dos artefatos validados."""
import json
from pathlib import Path
import pandas as pd
from scipy.stats import binomtest
from src.executa_fase1 import _markdown_tabela


def gerar(raiz=None):
    raiz=Path(raiz or Path(__file__).resolve().parents[1]); pasta=raiz/'outputs/diagnostics'
    ler=lambda nome:json.loads((pasta/nome).read_text(encoding='utf-8'))
    inf=ler('fase3_influencia.json'); cluster=ler('fase3_cluster.json')
    geo=ler('fase3_crossfit_geografico.json'); mc=ler('fase3_monte_carlo.json')
    sens=ler('fase3_sensibilidades.json'); gate=ler('fase3_gate.json'); validacao=ler('fase3_validacao.json')
    assert validacao['status']=='APROVADO'
    partes=[]
    def texto(s): partes.append(s.strip()+'\n')
    def tabela(rows,cols=None):
        df=pd.DataFrame(rows)
        partes.append(_markdown_tabela(df if cols is None else df[cols]))
    texto('''# Robustez e auditoria metodológica — Fase 3

AUDITORIA / SENSIBILIDADE FASE 3, 26/09/2026. Histórico Fase 2 preservado byte a byte. População principal e T/Y/X congelados. Não houve Causal Forest, CATE, meta-learners, uplift ou busca por um resultado mais favorável.
''')
    texto('**GATE_REVISAO_FASE3 = '+gate['gate']+'**.\n\n'+gate['sintese'])
    texto('''## 1. Auditoria da implementação

Score: `psi=m1−m0+T(Y−m1)/e−(1−T)(Y−m0)/(1−e)`; `IF=psi−média(psi)`.
Estimativa: média por nascido vivo, não média por município. SE iid: `sqrt(sum(IF²)/[N(N−1)])`; IC histórico ±1,96 SE. Não houve clipping ou normalização Hájek oculta. Pesos observados: 1/e para tratados, 1/(1−e) para controles; ESS por grupo `(sum w)²/sum(w²)`.

`aipw_independente` usa correções separadas por grupo sem chamar `calcular_aipw`. Reconciliação de todos os pseudo-outcomes com atol=1e−12; estimativas/SE históricos coincidem exatamente. Top 1% usa ceil(N×0,01), ordenação por |IF| equivalente a IF²; ESS coincide com a implementação histórica. Testes analíticos verificam sinal, centralização e escala. Nenhum erro material foi encontrado no AIPW original.
''')
    tabela(inf['reconciliacao'])
    texto('''## 2. Literatura e status do limiar

A [revisão dirigida](../literature/AUDITORIA_GATE_INFLUENCIA.md) reúne 13 referências sobre IF/AIPW, dupla robustez, positivity, ESS, outcomes raros, inferência agrupada e seleção perinatal. Não foi localizada recomendação formal para o critério top1%/50%; trata-se da heurística do exercício. A busca não é uma revisão sistemática nem prova de inexistência absoluta.

Kennedy e Chernozhukov et al. fundamentam IF/ortogonalidade; Petersen et al. tratam positivity; Balzer et al. discutem informação com outcomes raros; Cameron–Miller e MacKinnon et al. discutem inferência agrupada; Chiang et al. fundamentam divisões que respeitam clusters. A derivação própria de um AIPW oráculo com e=0,85, m0=0,08 e m1=0,07 produz top1% ≈66,3% com IF limitada e overlap. Portanto, ultrapassar 50% não constitui invalidade universal.
''')
    texto('## 3. Concentração da influência')
    tabela([dict(especificacao=s,**{k:v for k,v in f.items() if k!='propensity'})
            for s,d in inf['especificacoes'].items() for f in d['faixas']],
           ['especificacao','top_pct','n','fracao_if2','fracao_abs_if','contribuicao_psi_pp','contribuicao_if_pp'])
    texto('''Faixas cumulativas; frações entre 0 e 1. `contribuicao_psi_pp=100×sum(psi_top)/N` e `contribuicao_if_pp=100×sum(IF_top)/N`. Estas contribuições líquidas não são efeitos causais dos extremos. A curva do notebook ordena do maior para o menor |IF| e explicita o sentido dos eixos.
''')
    tabela([dict(especificacao=s,max_fracao_IF2=d['max_fracao_if2'],
                  max_contribuicao_pp=d['max_contribuicao_individual_pp']) for s,d in inf['especificacoes'].items()])
    texto('''O top 1% contém 22.516 registros, e o top 0,01% contém 226. O máximo individual responde por menos de 0,06% de IF². A concentração é coletiva, com contribuição especialmente forte de controles com Y=1; não há evidência de uma única observação dominar a estimativa. Isso não constitui prova de regularidade assintótica.

## 4. Perfil dos extremos
''')
    tabela([dict(especificacao=s,**{k:v for k,v in f.items() if k!='propensity'})
            for s,d in inf['especificacoes'].items() for f in d['faixas'] if f['top_pct'] in (.1,1.,5.)],
           ['especificacao','top_pct','n','prop_t0','prop_y1'])
    tabela([dict(especificacao=s,top_pct=pct,idade_mediana=d['perfis'][pct]['idade']['0.5'],
                  e_mediano=d['perfis'][pct]['propensity']['0.5'],e_p99=d['perfis'][pct]['propensity']['0.99'])
            for s,d in inf['especificacoes'].items() for pct in ['100.0','0.1','1.0','5.0']])
    texto('''No top 0,1%, a idade mediana é 33 anos (27 no conjunto), e e mediano ≈0,939. Escolaridade código 5, raça/cor código 1 e situação conjugal código 2 são mais frequentes nesse extremo; o JSON e notebook preservam os códigos e distribuições completas. No top 1%, a composição aproxima-se mais do conjunto: mediana de idade 27 anos, maioria nos códigos de escolaridade 3, raça/cor 4, situação conjugal 1, paridade 1 e zero perdas fetais. Essas descrições não identificam mecanismos causais.

A probabilidade pequena relevante é **1−e entre controles**, não e pequeno. O top 1% tem mediana e≈0,856, menor que 0,873 no conjunto; o top 0,1% mostra a cauda de e alto. São Paulo responde por cerca de 20,7% do top 1%, próximo de sua participação amostral; os extremos aparecem em todas as 27 UFs. A combinação outcome pouco frequente + grupo minoritário + pesos explica aritmeticamente o padrão, sem interpretação causal dessa seleção.

## 5. Dependência e inferência municipal

CODMUNRES recuperado na própria projeção SQL da base, com ORDER BY contador. Sem join que expanda N. Chave completa e única; nenhuma data de nascimento inválida ou fora de 2024. T permanece meses 1–3 versus 4–9; outcome é medido ao nascer. O mês de decisão e a temporalidade pré-tratamento das X não são observados diretamente.
''')
    a=cluster['amostra']; d=cluster['resultados'][0]
    texto(f"N={a['n']:,}; T=1={a['n_t1']:,}; T=0={a['n_t0']:,}; {a['n_clusters']:,} códigos de residência. Destes, 11 códigos terminados em 0000 representam município não especificado: {sum(a['codigos_municipio_nao_especificado'].values())} registros. Assim, são 5.570 códigos municipais e 11 agrupamentos residuais, sem alegar validação cadastral individual dos 5.570 códigos. Os códigos residuais ficam juntos por UF no cálculo integral e nos folds; sua exclusão é uma sensibilidade separada.")
    tabela([dict(quantil=k,n_cluster=v) for k,v in d['tamanhos'].items()])
    texto(f"Há {d['clusters_n_menor_10']} agrupamentos com N<10. O maior contém {int(d['tamanhos']['1']):,} registros ({100*d['max_fracao_n']:.2f}% de N). A maior participação de um cluster na soma dos scores municipais ao quadrado é {100*d['max_fracao_variancia_cluster']:.2f}% em C1, código {d['cluster_maior_if2']}. Não se confunde tamanho de cluster com influência.")
    texto('''Para `U_g=sum_i IF_i`, `V_cluster=[G/(G−1)] sum_g U_g²/N²`. IC95% por t_(G−1). Independência entre municípios permanece assumida. A sensibilidade municipal não incorpora dependência espacial entre municípios, confundimento ou seleção. UF não foi usada como cluster principal.
''')
    cols=['especificacao','populacao','n','estimativa_pp','se_iid_pp','se_cluster_pp','ic95_cluster_inferior_pp','ic95_cluster_superior_pp']
    tabela(cluster['resultados'],cols)
    texto('Exclusão somente dos 37 registros de município não especificado, sem refazer nuisances:')
    tabela(cluster['sensibilidade_sem_municipio_nao_especificado']['resultados'],cols)
    texto('''## 6. Bootstrap por clusters

500 réplicas, seed 20240925; G sorteios uniformes com reposição. Estimativa por réplica `sum_g K_g sum_i psi_i / sum_g K_g n_g`. Denominador variável preserva o alvo por nascido vivo. Nuisances e trimming fixos: não incorpora sua incerteza completa. SE/bootstrap e percentis são sensibilidades condicionais, não uma inferência completa validada.
''')
    tabela([dict(especificacao=r['especificacao'],populacao=r['populacao'],se_iid_pp=r['se_iid_pp'],
        se_cluster_pp=r['se_cluster_pp'],se_bootstrap_pp=r['bootstrap']['se_bootstrap_pp'],
        ic_percentil_inf=r['bootstrap']['ic95_percentil_pp'][0],ic_percentil_sup=r['bootstrap']['ic95_percentil_pp'][1]) for r in cluster['resultados']])
    texto('''## 7. Cross-fitting geográfico

StratifiedGroupKFold em três folds, estratificação conjunta T/Y, seed 20240925. Mesmo código de residência nunca aparece em treino e validação. Nuisances e codificações são aprendidos no treino externo; HGB mantém early stopping interno ao treino. Município não entra em X. C1 usa logística e C2 outcomes HGB. Sem tuning.
''')
    tabela([{k:v for k,v in f.items() if k not in ('ajustes','validacao_ty')} for f in geo['folds']])
    tabela([dict(fold=f['fold'],**{'T'+str(int(k)//2)+'_Y'+str(int(k)%2):v for k,v in f['validacao_ty'].items()}) for f in geo['folds']])
    tabela([dict(folds=k,**r) for k in ('aleatorio','agrupado') for r in geo[k]['resultados']],['folds']+cols)
    tabela([dict(folds=k,especificacao=s,AUC_propensity=d['propensity']['roc_auc'],Brier_propensity=d['propensity']['brier'])
            for k in ('aleatorio','agrupado') for s,d in geo[k]['nuisance'].items()])
    tabela([dict(folds=k,especificacao=r['especificacao'],populacao=r['populacao'],ESS_T0=r['ess']['0']['ess'],
                  ESS_T1=r['ess']['1']['ess'],top1_IF2=r['top1_if2']) for k in ('aleatorio','agrupado') for r in geo[k]['resultados']])
    texto('Performance preditiva OOF dos outcomes, avaliada somente no grupo de tratamento observado:')
    tabela([dict(folds=k,especificacao=s,grupo=g,AUC=m['roc_auc'],AP=m['pr_auc_ap'],Brier=m['brier'])
        for k in ('aleatorio','agrupado') for s,d in geo[k]['nuisance'].items() for g,m in d['outcomes'].items()])
    texto('''Essas métricas não avaliam identificação causal. O cross-fitting agrupado altera C1/C2 em menos de 0,005 pp no contraste sem trimming; o propensity AUC cai ligeiramente. A estabilidade é observada nesta divisão única, não prova de invariância a todas as partições ou ausência de dependência espacial. A UF Distrito Federal ficou inteiramente no fold 3 (32.039 registros), por ser representada por um único município; categorias não vistas recebem o tratamento já definido no pipeline (one-hot desconhecido ignorado; HGB desconhecido como missing), sem adicionar informação da validação. Nenhuma outra UF ficou ausente dos respectivos treinos externos.

## 8. Leave-one-UF-out

Pseudo-outcomes históricos fixos. Retirar UF muda composição e alvo; não estima CATE regional e não refaz nuisance models.
''')
    tabela(inf['leave_one_uf_out'])
    for s in ('C1','C2'):
        rows=[r for r in inf['leave_one_uf_out'] if r['especificacao']==s]; maior=max(rows,key=lambda r:abs(r['mudanca_pp']))
        texto(f"{s}: faixa [{min(r['estimativa_pp'] for r in rows):.6f}; {max(r['estimativa_pp'] for r in rows):.6f}] pp; maior mudança UF {maior['grupo']}, {maior['mudanca_pp']:+.6f} pp, N removido={maior['n_removido']:,}. Nenhuma exclusão inverte o sinal ou elimina a maior parte da magnitude nacional.")
    texto('''## 9. Monte Carlo do gate

N=50.000, 200 réplicas/cenário, efeito verdadeiro −1 pp. X~Uniforme(−1,1). S1: e=.5, m0=.105; S2: e=.85, m0=.1085; S3: e=.85+.10X, m0=.0885+.02X; S4: e=.995 se X>.6 e .81375 caso contrário, m0=.0885+.02X. Todos: m1=m0−.01, T~Bernoulli(e), Y~Bernoulli(mT). E[Y]=10% S1/S2 e 8% S3/S4. Seed base 20240925+j. Nuisances verdadeiros, não ajustados: a simulação isola a regra, não modela erros ML ou seleção do estudo.
''')
    rows=[]
    for s in mc['cenarios']:
        ci=binomtest(round(s['prob_gate']*s['n_replicas']),s['n_replicas']).proportion_ci()
        rows.append(dict(cenario=s['cenario'],bias_pp=100*s['bias'],MCSE_bias_pp=100*s['mcse_bias'],
            RMSE_pp=100*s['rmse'],cobertura=s['cobertura'],MCSE_cobertura=s['mcse_cobertura'],
            P_gate=s['prob_gate'],IC_MC_P_inf=ci.low,IC_MC_P_sup=ci.high,ESS_T0=s['ess_t0_medio']))
    tabela(rows)
    texto('''S3 aciona o gate em todas as réplicas, com cobertura 97,5%; S4 também o aciona em todas, mas a cobertura cai para 89,5%. A heurística não separa adequadamente concentração típica de um caso com precisão/cobertura prejudicadas. S4 tem em média apenas cerca de cinco controles com evento no estrato e=.995; isso ajuda a entender a aproximação finita pior, mesmo com oráculo.

Frequências empíricas 0/1 não têm incerteza nula: a tabela usa intervalo binomial exato para P(gate). O bias estimado de S3 é −0,0731 pp (MCSE 0,0261 pp), cerca de 2,8 MCSE, e foi mantido sem novas seeds ou seleção de resultados. Com 200 réplicas, não se afirma recuperação exata ou garantia de cobertura. As réplicas individuais (estimativa, erro, erro quadrático, cobertura, concentração e ESS) estão no JSON.

## 10. Sensibilidades de elegibilidade

S0=P1 histórica. Excluir CONSPRENAT=0 preserva T e reajusta nuisances C1/C2. P0 mantém gestação única, relaxando peso para todo valor numérico positivo. MULTIPLAS mantém P1 e inclui GRAVIDEZ 1/2/3. A projeção de X é reutilizada exatamente do SQL congelado; só filtros e regra de peso mudam. Todas são sensibilidades com populações-alvo diferentes, nunca substituições da principal.
''')
    tabela([v for v in sens['amostras'].values()],['cenario','n','n_t1','n_t0','prevalencia','n_consprenat_zero','n_peso_fora_p1','n_multipla'])
    tabela([dict(cenario=k,**r) for k in ('CONSPRENAT','P0','MULTIPLAS') for r in sens[k]['resultados']],
           ['cenario']+cols+['diferenca_p1_pp','diferenca_relativa_abs_p1'])
    texto('''`diferenca_relativa_abs_p1 = (estimativa_sens−estimativa_P1)/abs(estimativa_P1)`. Na versão com trimming, o comparador é o P1 da mesma regra; limiares OOF podem selecionar indivíduos diferentes. A prevalência usa o denominador da própria amostra sem trimming.

Múltiplas podem gerar vários nascidos vivos correlacionados da mesma gestação, sem ID de mãe/gestação para verificar a dependência. Município provavelmente reúne muitos irmãos, mas não permite demonstrar isso nem resolve todos os vínculos. Os SE são apresentados como sensibilidade computacional; a conclusão substantiva restringe-se a direção e magnitude.

## 11. C3: dependência da especificação do propensity

HGB com hiperparâmetros já congelados para o projeto, sem tuning. Propensity OOF nos mesmos três folds aleatórios da Fase 2; outcomes HGB C2 OOF reutilizados. Isso isola a mudança de e e não reutiliza treinamento que contenha o registro avaliado. As sete X são validadas explicitamente. C3 não foi selecionada como novo resultado principal.
''')
    tabela(sens['S0']['resultados'],cols)
    tabela([dict(especificacao=s,AUC=d['propensity']['roc_auc'],Brier=d['propensity']['brier'],
        suporte_min=d['overlap']['suporte_comum_observado']['inferior'],suporte_max=d['overlap']['suporte_comum_observado']['superior'])
        for s,d in sens['S0']['nuisance'].items()])
    tabela([dict(especificacao=r['especificacao'],populacao=r['populacao'],ESS_T0=r['ess']['0']['ess'],
        ESS_T1=r['ess']['1']['ess'],top1_IF2=r['top1_if2'],peso_max_T0=r['ess']['0']['max']) for r in sens['S0']['resultados']])
    texto('''## 12. Estimando e interpretação

Ver [auditoria do estimando](AUDITORIA_ESTIMANDO_FASE3.md). Alvo estatístico: padronização da diferença de médias condicionais na população selecionada `S=1`. Nascimento vivo, peso observado/P1 e MESPRENAT observado podem induzir seleção dependente da exposição e de determinantes do outcome. Restrição a gestação única conhecida ao final não equivale automaticamente a uma elegibilidade basal conhecida.

Defensável: contraste ajustado exploratório entre pré-natal precoce e tardio nos registros selecionados, com hipóteses explícitas. Não defensável: efeito identificado em todas as gestantes/concepções, efeito no estrato que nasceria vivo sob ambos os tratamentos ou recomendação individual de política/ROI. Nuisances, clusters e sensibilidades não resolvem confundimento residual nem seleção. Esse risco já constava da Fase 2; não é novo erro material de implementação.

## 13. Gate adicional e achados por severidade
''')
    tabela(gate['evidencias'])
    texto('''- **Alto, bloqueador de promoção causal:** seleção, confundimento e temporalidade de X não demonstrados. Correção recomendada: manter interpretação exploratória e declarar o alvo selecionado; não há correção identificada nesta extração.
- **Médio, ressalva inferencial:** dependência entre municípios e nuisances estimados não são eliminados pelos ICs. Correção aplicada: sandwich, bootstrap condicional e folds agrupados; não alegar inferência completa.
- **Médio, interpretação do diagnóstico:** top1/50 é excessivo como veto universal; corrigida a interpretação em registro adicional, preservado o gate histórico.
- **Baixo, qualidade geográfica:** 37 registros em 11 códigos sem município especificado. Correção aplicada: identificação explícita e sensibilidade por exclusão; sem exclusão silenciosa.

## 14. Artefatos, reprodução e validação

Na raiz deste projeto, ative `.venv` (`.\\.venv\\Scripts\\Activate.ps1`). Nenhum pacote foi instalado ou ambiente alterado.

```powershell
python -m src.executa_robustez_fase3
python -m src.valida_resultados_fase3
python -m src.resume_auditoria_fase3
python -m src.cria_notebook_fase3
python -m nbconvert --execute --to notebook --inplace --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=600 notebooks/04_robustez_e_auditoria_metodologica.ipynb
python -m pytest tests -q
python -m pip check
git diff --check
```

O kernel python3 deve resolver para o Python da `.venv`; o notebook verifica isso. Caches completos ficam em outputs/tables, ignorados pelo Git. O executor valida hashes de cache, chaves, dados e código antes de reutilizar; não aceita silenciosamente cache incompatível. Gate é decisão metodológica explícita em fase3_gate.json, não algoritmo que escolhe o efeito desejado.

O validador herdado Fase 2 é executado com sua rotina de persistência interceptada: compara o JSON gerado ao histórico sem sobrescrevê-lo. Os hashes de fontes, Parquet, bruto, predições e artefatos Fase 2 são conferidos antes e depois. A validação Fase 3 recalcula estimativas/SE com implementação independente e sandwich via SQL.
''')
    texto(f"Validação numérica: {validacao['linhas_reconciliadas']} linhas Fase 3 reconciliadas com atol=1e−12; seis resultados históricos Fase 2 reproduzidos. Folds geográficos respeitam clusters. A execução e inspeção visual do notebook e os checks finais são registrados no estado do projeto.")
    tabela([
        dict(artefato='fase3_influencia.json',granularidade='especificação/faixa/perfil/UF',chave='C1/C2 + top_pct ou UF',validacao='reconciliação independente',limitacao='descrição de extremos',proximo_passo='interpretar com contexto'),
        dict(artefato='fase3_cluster.json',granularidade='especificação/regra',chave='spec + trimming',validacao='sandwich analítico/SQL',limitacao='clusters independentes; nuisances fixos',proximo_passo='reportar SE alternativo'),
        dict(artefato='fase3_crossfit_geografico.json',granularidade='fold/spec/regra',chave='tipo_fold + spec + regra',validacao='cluster exclusivo por fold',limitacao='uma partição; espaço entre municípios',proximo_passo='manter como sensibilidade'),
        dict(artefato='fase3_monte_carlo.json',granularidade='cenário/réplica',chave='cenário + réplica',validacao='DGP conhecido e seed fixa',limitacao='oráculo iid',proximo_passo='não extrapolar cobertura ao SINASC'),
        dict(artefato='fase3_sensibilidades.json',granularidade='população/spec/regra',chave='população + spec + regra',validacao='N e efeitos reconciliados',limitacao='novos alvos selecionados',proximo_passo='reportar magnitude/direção'),
    ])
    texto('''## 15. Recomendação para o artigo — até cinco pontos

1. Apresentar o contraste como ajustado e exploratório na população selecionada, sem linguagem de efeito identificado em todas as gestantes.
2. Preservar o gate original e explicar sua revisão adicional com literatura, contraexemplo e Monte Carlo, sem reescrever a história.
3. Mostrar C1/C2, SE municipal e cross-fitting agrupado; C3 e elegibilidades como sensibilidades, sem selecionar pelo sinal/significância.
4. Usar concentração completa, perfil T/Y e contribuição máxima individual para distinguir eventos coletivamente influentes de registros dominantes.
5. Dar espaço explícito a seleção de nascidos vivos, mensuração e confundimento residual; adiar heterogeneidade causal e recomendação de política.
''')
    destino=raiz/'docs/methodology/ROBUSTEZ_FASE3.md'
    destino.write_text('\n'.join(partes),encoding='utf-8')
    return destino


if __name__=='__main__':
    print(gerar())
