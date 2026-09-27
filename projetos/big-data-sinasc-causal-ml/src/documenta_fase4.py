"""Acrescenta resultados validados ao protocolo da Fase 4, sem refazer modelos."""
import json
from src.executa_fase4 import ROOT


def tabela(linhas,campos):
    def fmt(v):
        if isinstance(v,float): return f'{v:.6f}'
        return str(v)
    cab='| '+' | '.join(titulo for _,titulo in campos)+' |\n'
    cab+='| '+' | '.join('---' for _ in campos)+' |\n'
    return cab+'\n'.join('| '+' | '.join(fmt(r[k]) for k,_ in campos)+' |' for r in linhas)+'\n'


def documentar():
    ler=lambda nome:json.loads((ROOT/'outputs/diagnostics'/nome).read_text(encoding='utf-8'))
    r=ler('fase4_resultados.json'); v=ler('fase4_validacao.json'); logs=ler('fase4_ajustes.json')
    assert v['status']=='APROVADO'
    p=r['principal']; e=r['estabilidade']
    texto=f'''
### Conclusão

**{r['gate']}**. Há ordenação parcial nos dados externos, mas os perfis não se mantêm suficientemente estáveis entre partições geográficas. A correlação mediana das médias de perfis é {e['mediana_spearman_perfis']:.6f}, abaixo do critério exploratório 0,5. A concordância entre HGB e Ridge é moderada (Spearman {e['spearman_hgb_ridge']:.6f}); isso não compensa a instabilidade geográfica.

Os contrastes DR externos Q5−Q1 são positivos nas três partições, porém bem menores que a separação prevista pelo modelo. Não confundir algum sinal de ordenação com calibração adequada da magnitude. O exercício não sustenta uma classificação estável de benefício por perfil e não autoriza uso clínico.

### População, execução e honestidade

N={p['n']:,}; tratados=1.942.045; controles=309.525. As datas, chave única, amostra, regras e sete covariáveis foram validadas antes de qualquer ajuste. Todas as regressões logísticas convergiram. Cada registro recebeu uma previsão externa, com município exclusivo em cada papel da rodada. Sem instalação de pacotes.

'''.replace(f"N={p['n']:,}",f"N={p['n']:,}".replace(',','.'))
    texto+=tabela(logs['contrato']['particoes'],[('particao','Partição'),('n','N'),('n_t1','T=1'),('n_t0','T=0'),('n_y1','Y=1'),('n_municipios','Agrupamentos municipais')])
    texto+='''
Os 5.581 códigos incluem os 11 códigos de município não especificado já auditados na Fase 3; não equivalem a 5.581 municípios identificados. A UF 53 está somente na partição 3; na avaliação dessa partição, é uma categoria nova tanto para os auxiliares quanto para o CATE. O HGB trata categoria desconhecida como ausente; a codificação indicadora do Ridge não aprende coeficiente próprio. Essa limitação de generalização para o DF é mantida explícita, sem excluir seus registros.

### Distribuição prevista

'''
    texto+=tabela([dict(modelo='HGB principal',**p),dict(modelo='Ridge',**r['alternativo'])],
        [('modelo','Modelo'),('media_pp','Média pp'),('mediana_pp','Mediana pp'),('p05_pp','p5 pp'),('p25_pp','p25 pp'),('p75_pp','p75 pp'),('p95_pp','p95 pp'),('amplitude_robusta_pp','p95−p5 pp')])
    texto+=f'''
HGB: {100*p['proporcao_negativa']:.3f}% das previsões negativas e {100*p['proporcao_positiva']:.3f}% positivas; nenhuma exatamente zero. Extremos: {p['min_pp']:.6f} a {p['max_pp']:.6f} pp. As caudas são muito mais amplas que o intervalo robusto e reforçam a inadequação de interpretar sinais individuais como verdade. Nenhum valor ficou fora de [−100,100] pp, mas respeitar esse limite matemático não demonstra plausibilidade causal ou calibração. Não houve recorte nem limitação artificial de previsões.

### Perfis pré-especificados

As tabelas seguem códigos/ordem de categorias, sem ordenação por suposto benefício. p5/p95 são percentis da distribuição prevista, **não ICs**. O contraste DR e seu IC são diagnósticos externos aproximados; não são ICs da média do CATE aprendido. Não houve correção para comparações múltiplas.

'''
    for dim in ('Faixa etária','Escolaridade','Raça/cor','Paridade'):
        texto+='#### '+dim+'\n\n'
        texto+=tabela([x for x in r['perfis'] if x['dimensao']==dim],
            [('grupo','Categoria'),('n','N'),('media_pp','CATE médio pp'),('p05_pp','p5 pp'),('p95_pp','p95 pp'),('contraste_dr_pp','Contraste DR pp'),('ic95_dr_inferior_pp','IC inferior pp'),('ic95_dr_superior_pp','IC superior pp')])+'\n'
    texto+='''
A categoria de idade ausente contém somente 32 registros: seu contraste DR é muito impreciso e não deve sustentar interpretação substantiva isolada. Ela permanece nas tabelas para reconciliar a população e fica fora das correlações de grandes perfis pelo critério N≥1.000 já definido.

Entre idades observadas, a média prevista varia aproximadamente de −1,19 pp (30–34 anos) a −1,75 pp (≥35 anos). Essa diferença descreve o modelo; a instabilidade entre partições impede convertê-la em afirmação de benefício causal diferencial. As demais dimensões também devem ser lidas com essa restrição, sem priorização por escolaridade, raça/cor ou paridade.

### Quintis globais — descrição

'''
    texto+=tabela(r['quintis'],[('quintil','Quintil'),('n','N'),('cate_medio_pp','CATE HGB pp'),('ridge_medio_pp','Ridge pp'),('idade_media','Idade média'),('prevalencia_observada_pct','Y observado %'),('proporcao_t1_pct','T=1 %')])
    texto+='''
As proporções completas de escolaridade, raça/cor, situação conjugal, paridade, perdas fetais e UF, dentro de cada quintil, estão no notebook 05 e em `fase4_resultados.json` (`quintis_composicao_x`). Cada distribuição reconcilia N e 100%. Essas características descrevem composição; nenhuma proporção observada de Y é interpretada como efeito causal.

### Estabilidade entre modelos e partições

'''
    texto+=f"Spearman HGB/Ridge={e['spearman_hgb_ridge']:.6f}; diferença absoluta média={e['diferenca_absoluta_media_pp']:.6f} pp; concordância de sinal={100*e['concordancia_sinal']:.3f}%. Concordância de sinal é diagnóstico entre modelos, não acurácia individual.\n\n"
    texto+=tabela(e['distribuicao_particao'],[('particao','Partição'),('n','N'),('media_pp','CATE HGB pp'),('media_ridge_pp','CATE Ridge pp'),('media_psi_pp','Média psi externo pp'),('p05_pp','p5 pp'),('p95_pp','p95 pp')])+'\n'
    texto+=tabela(e['correlacoes_perfis'],[('particao1','Partição A'),('particao2','Partição B'),('n_categorias','Categorias comparáveis'),('spearman','Spearman dos perfis')])
    texto+='''
A correlação de perfis combina as dimensões pré-especificadas e não corresponde a uma replicação em pessoas idênticas: a composição geográfica também varia. Essa diferença é parte do diagnóstico de transporte/estabilidade, não uma prova de que a instabilidade decorre exclusivamente do algoritmo.

### Avaliação externa dos quintis extremos

Quintis recalculados dentro de cada conjunto C para evitar que limites globais incorporem indiretamente desfechos de C através das demais rotações. Nenhum desfecho de C participa do ajuste da regra avaliada em C.

'''
    texto+=tabela(e['contrastes_externos'],[('particao','Partição'),('contraste_cate_q5_q1_pp','Separação prevista pp'),('contraste_dr_q5_q1_pp','Separação DR externa pp'),('se_municipal_pp','EP municipal pp'),('ic95_inferior_pp','IC inferior pp'),('ic95_superior_pp','IC superior pp')])
    texto+='''
Para cada conjunto externo, a contribuição da diferença é `I(Q5)(psi−media5)/N5 − I(Q1)(psi−media1)/N1`; somam-se essas contribuições por município. A variância é `G/(G−1) × soma(Ug²)`, com quantil t de G−1 graus de liberdade. A contribuição já inclui os denominadores N5/N1; não há divisão adicional por N². A validação reconstrói essa conta independentemente.

Os intervalos pressupõem regularidade, municípios independentes e funções fixas. Não são inferência pós-seleção completa, não incluem o viés de aprendizagem e não removem confundimento. As três rotações não devem ser combinadas como estudos independentes. Mesmo com IC externo positivo, a separação prevista é excessiva; não promover a dispersão do modelo a heterogeneidade causal estabelecida.

### ATE versus média de CATE

'''
    texto+=f"Média CATE HGB={p['media_pp']:.6f} pp; média psi externo={r['media_psi_pp']:.6f} pp; C2 histórico={r['ate_fase2_c2_pp']:.6f} pp. A diferença CATE−psi é {r['diferenca_media_cate_psi_pp']:.6f} pp. Regularização, amostras de treino menores e separação geográfica explicam por que os estimadores não têm igualdade algébrica em amostra finita. Não se forçou concordância por recentralização.\n\n"
    texto+='''### Validação e reprodução

- Pré-validação: `outputs/diagnostics/fase4_preflight.json`.
- Contrato e histórico: `fase4_ajustes.json` e `fase4_preservacao.json`.
- Reconciliação: `fase4_validacao.json`; pseudo-desfechos com tolerância absoluta 1e−12 e resumos com 1e−10; cobertura única, chaves, partições, quintis, perfis e composição reconciliados.
- Testes: fórmula DR, caso constante binário e regressão constante, heterogeneidade sintética conhecida, reprodutibilidade, guardas de covariáveis, ausência de interseção entre etapas, agregação, quintis e regras do critério exploratório.
- Artefatos: uma linha por registro no cache local ignorado `outputs/tables/fase4_predicoes_oof.npz`; resumos agregados e rastreáveis em JSON; notebook 05 executável. Limitação: sem CATE individual identificado, sem IC individual e sem recomendação clínica.

Na `.venv` do projeto:

```powershell
python -m src.executa_fase4
python -m src.resume_fase4
python -m src.valida_resultados_fase4
python -m src.documenta_fase4
python -m src.cria_notebook_fase4
python -m nbconvert --execute --to notebook --inplace --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=600 notebooks/05_heterogeneidade_causal.ipynb
python -m pytest -q tests
python -m src.valida_resultados_fase3
python -m src.valida_apresentacao
python -m src.apresentacao_pt
python -m pip check
git diff --check
```

Próximo passo metodológico possível, fora desta entrega: validação independente/prospectiva e avaliação de confundimento e seleção antes de qualquer uso operacional. Não escolher uma nova especificação apenas para melhorar o critério de decisão. Nenhuma política clínica, ROI, artigo completo ou Fase 5 foi produzido.
'''
    caminho=ROOT/'docs/methodology/HETEROGENEIDADE_FASE4.md'
    protocolo=caminho.read_text(encoding='utf-8').split('<!-- RESULTADOS_EXECUTADOS -->')[0]
    caminho.write_text(protocolo+'<!-- RESULTADOS_EXECUTADOS -->\n'+texto,encoding='utf-8')
    print(caminho)


if __name__=='__main__': documentar()
