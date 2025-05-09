<!-- buttons -->
<p align="center">
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-v3-brightgreen.svg"
            alt="python"></a> &nbsp;
    <a href="https://opensource.org/licenses/MIT">
        <img src="https://img.shields.io/badge/license-MIT-brightgreen.svg"
            alt="MIT license"></a> &nbsp;
    <a href="https://github.com/psf/black">
        <img src="https://img.shields.io/badge/code%20style-black-000000.svg"
            alt="Code style: black"></a> &nbsp;
    <a href="http://mypy-lang.org/">
        <img src="http://www.mypy-lang.org/static/mypy_badge.svg"
            alt="Checked with mypy"></a> &nbsp;
</p>

A biblioteca **comparar_fundos_br** possui uma série de funções que permitem:

- Capturar dados diários de fundos de investimento;
- Filtrar fundos por classe CVM (ex Fundos de Ações, Fundos de Renda Fixa, etc);
- Calcular risco (volatilidade) e retorno dos fundos;
- Cálculo de rentabilidade no período selecionado, rentabilidade diária, rentabilidade acumulada, rentabilidade anualizada;
- Filtrar fundos por CNPJ ou por nome (ex: fundos que contenham a palavra Bradesco);
- Comparar fundos com benchmarks como: CDI, Índice Bovespa, IMA-B, IMA-B 5 e IMA-B 5+;
- Comparar fundos com sua carteira de investimentos;
- Plotar gráficos de comparação e evolução dos fundos em período específico juntamente com seus benchmarks.

### Instalação

```sh
pip install comparar_fundos_br
```

Caso necessite utilizar proxy, inicie com o código abaixo:

```python
import getpass

user = getpass.getuser().lower()
pwd = getpass.getpass(prompt="Senha: ")
proxy = "10.10.1.10"
porta = 3128
proxies = {
    "http": f"http://{user}:{pwd}@{proxy}:{porta}",
    "https": f"http://{user}:{pwd}@{proxy}:{porta}",
        }
```

Veja a seguir um exemplo para capturar dados dos Fundos de Investimento com seus respectivos filtros. Repare que é possível obter um formato de dataframe em `pandas` ou `polars` (auxilia para trabalhar com grandes dataframes).

```python
import comparar_fundos_br as comp

informe_diario_fundos_historico = comp.fundosbr(anos=range(2021,2022), #somente 2021
                                                  meses=range(1,3), #somente Jan e Fev
                                                  num_minimo_cotistas=10, 
                                                  patriminio_liquido_minimo=1e6, 
                                                  proxy=proxies,
                                                  output_format='pandas')
informe_diario_fundos_historico.head()
```

```
| DT_COMPTC           | CNPJ_FUNDO         |   NR_COTST | VL_PATRIM_LIQ   | VL_QUOTA   | VL_TOTAL       | CAPTC_DIA   | RESG_DIA   |
|---------------------|--------------------|------------|-----------------|------------|----------------|-------------|------------|
| 2022-01-03 00:00:00 | 41.778.228/0001-94 |         23 | 22.282.945,45   | 1,03       | 22.366.555,70  | 0,00        | 0,00       |
| 2022-01-03 00:00:00 | 05.090.905/0001-13 |         65 | 1.645.439,95    | 5,39       | 1.624.983,60   | 0,00        | 0,00       |
| 2022-01-03 00:00:00 | 34.271.097/0001-99 |         12 | 15.971.287,49   | 1,06       | 15.998.464,03  | 0,00        | 0,00       |
| 2022-01-03 00:00:00 | 18.298.411/0001-70 |         71 | 287.276.414,66  | 3,31       | 288.767.536,79 | 0,00        | 200.000,00 |
| 2022-01-03 00:00:00 | 40.905.548/0001-03 |         17 | 28.068.429,23   | 1.083,46   | 28.207.991,86  | 35.200,00   | 0,00       |
```

Os dados históricos dos fundos contém alguns problemas como: repetição do mesmo fundo em classes iguais com nomes diferentes e
alterações em nome das colunas ou, até mesmo, ausência de alguma coluna. Para contornar, filtramos os tipos de fundos como:
`'FI', 'FIF' ou'CLASSES - FIF` e não retornamos com essa coluna, mas a informação pode ser obtida a posteriori, veja a seguir.

Todas as informações adicionais sobre os fundos como: classificação ANBIMA, classe, Denominação Social (Nome do Fundo), Condomínio, Custodiante e outras estão disponíveis no cadastro dos fundos. Para obte-lo, basta invocar a função abaixo:

```python
cadastro = comp.get_cadastro_fundos(classe=comp.get_classes(), proxy=proxies,
                                    output_format='polars')
```
Caso deseje filtrar apenas algunas classes de Fundos, siga o exemplo abaixo que filtra por fundos de ações.

```python
print(comp.get_classes())
cadastro = comp.get_cadastro_fundos(classe=["Ações"], proxy=proxies,
                                    output_format='polars')
```

Importante ressaltar que todos os Fundos que são retornados do cadastro possuem situação CVM como "EM FUNCIONAMENTO NORMAL", além de retornar somente o tipo de classe `Classes de Cotas de Fundos FIF` e classificação não nula.

Para cruzar as informações diárias e de cadastro, execute:

```python
informe_completo = comp.mesclar_bases(cadastro, informe_diario_fundos_historico)
```

Os estudos com os fundos são executados sobre uma série temporal das cotas diárias dos fundos. Com `informe_completo` pode-se
filtrar os fundos que interessam para sua análise. Uma coluna adicional foi criada para conjugar CNPJ do Fundo a seu Nome (CNPJ - Nome).

Caso esteja utilizando `polars`, obtenha a série temporal da seguinte forma:

```python
serie_temporal_fundos = informe_completo.pivot(index="DT_COMPTC", columns="CNPJ - Nome",
                                                 values="VL_QUOTA", aggregate_function='first')
serie_temporal_fundos = serie_temporal_fundos.sort(['DT_COMPTC'])
```

Agora se estiver utilizando o `pandas`:

```python
serie_temporal_fundos = informe_completo.pivot_table(index="DT_COMPTC", columns="CNPJ - Nome",
                                                     values="VL_QUOTA", aggfunc='first')
serie_temporal_fundos = serie_temporal_fundos.sort_values(['DT_COMPTC'])
```

Para obter o retorno dos Fundos, chame a função `calcula_risco_retorno_fundos` passando os dados dos fundos que acabou de obter.
Caso esteja trabalhando até aqui com `polars`, deve-se mudar para `pandas` usando comando `serie_temporal_fundos.to_pandas().set_index('DT_COMPTC')`, pois as demais funções não foram implementadas em `polars`.

```python
(risco_retorno, rentabilidade_fundos_diaria, 
    cotas_normalizadas, rentabilidade_fundos_acumulada,
    rentabilidade_acumulada_por_ano) = comp.calcula_risco_retorno_fundos(serie_temporal_fundos)
```

O primeiro dataframe indica tanto o risco (volatidade padrão) de cada fundo, por CNPJ - Nome, quanto sua rentabilidade, ambos anualizados. O segundo dataframe provê os retornos diários de cada fundo. Já o terceiro dataframe retorna o valor das cotas dos fundos normalizadas no período selecionado. Os demais dataframes retornam as rentabilidades acumulada por ano e a rentabilidade total no período, respectivamente.

A forma mais eficiente para comparar o desempenho dos Fundos é usando gráficos. Você pode plotar o risco x retorno dos Fundos e comparar com seu benchmark ou sua carteira de investimentos. Aqui não vamos calcular pra você a rentabilidade da sua carteira, apenas usar esse dado para comparar com  os fundos selecionados. Veja o exemplo:

```python
risco_retorno_filtrado = risco_retorno[
                                    (risco_retorno["volatilidade"] <= 40)
                                    & (risco_retorno["rentabilidade"] >= 0)
                                    & (risco_retorno["rentabilidade"] <= 100)
                                    ]

comp.plotar_comparacao_risco_retorno(
                                risco_retorno_filtrado,
                                (21, 18), #(risco, retorno) da minha carteira
                                (19, 15), #(risco, retorno) do benchmark
                                nome_carteira="Minha Carteira",
                                nome_benchmark="Benchmark",
                                figsize=(15, 5),
                                posicao_texto_carteira=(30, 25),
                                posicao_texto_benchmark=(31, -25),
                                )
plt.suptitle("Risco x Retorno - Fundos de Ações")
plt.ylim(-10, 140)
plt.xlim(-3, 60)
plt.show()
```
<center>
<img src="https://github.com/rafa-rod/comparar_fundos_br/blob/main/media/figura3.png" style="width:100%;"/>
</center>

Uma outra forma de comparação é utilizando as cotas iniciando em um valor inicial de 1, arbitrário. Caso deseje visualizar a evolução do investimento, basta multiplicar o dataframe, assim a comparação fica facilitada.

A função `plotar_evolucao` encontra os Fundos tanto por CNPJ quanto por Nome, ou seja, se deseja obter todos os Fundos que possuam Bradesco no Nome, basta informa na variável `lista_fundos=["Bradesco"]`.

Para facilitar a comparação, você pode personalizar o gráfico para destacar o melhor e o pior Fundo, além de plotar o seu benchmark.

Os benchmarks disponíveis são: CDI, IMA-S, IMA-B5, IMA-B5+, IMA-B5 P2, IRFM, IRFM P2, IHFA, Ibovespa, DIVO11 (IDIV), SP500 e Ações diversas listadas na B3.
A função retorna os valores de cada ticker, retorno diário e retorno acumulado no período indicado.

```python
data_inicio, data_fim = serie_temporal_fundos.index[0], serie_temporal_fundos.index[-1]

cdi = comp.get_benchmarks(data_inicio, data_fim, benchmark="cdi", metodo_cdi='anbima', proxy=proxies)
ibov = comp.get_benchmarks(data_inicio, data_fim, benchmark="ibov", proxy=proxies)
sp500 = comp.get_benchmarks(data_inicio, data_fim, benchmark="sp500", proxy=proxies)
idiv = comp.get_benchmarks(data_inicio, data_fim, benchmark="divo11", proxy=proxies)
acoes = comp.get_stocks(['VALE3', 'PETR4'], data_inicio, data_fim, proxy=proxies)
df_benchmarks = pd.concat([cdi, ibov, sp500, idiv, acoes], axis=1).sort_index()

data = comp.plotar_evolucao(
                cotas_normalizadas*100,
                lista_fundos=["03.916.081/0001-62","06.916.384/0001-73"],
                figsize=(15, 5),
                color="darkblue",
                alpha=0.8
                )
plt.suptitle("Evolução dos Fundos")
plt.plot((1+df_benchmarks[['Retorno Acumulado CDI']].dropna().fillna(0))*100, label="CDI", color='red', linestyle='--')
plt.legend(frameon=False, loc="upper right")
plt.show()
```

<center>
<img src="https://github.com/rafa-rod/comparar_fundos_br/blob/main/media/figura1.png" style="width:100%;"/>
</center>

```python
data = comp.plotar_evolucao(
                            cotas_normalizadas*100,
                            lista_fundos=["Bradesco"],
                            figsize=(15, 5),
                            color="gray",
                            alpha=0.2,
                            color_maximo="orange",
                            color_minimo="blue",
                            color_seta_maximo="orange",
                            color_seta_minimo="blue",
                            posicao_texto_maximo=(-100, 35),
                            posicao_texto_minimo=(-100, 10),
                            )
plt.suptitle("Evolução dos Fundos que contenham Bradesco no nome")
plt.plot((1+ibov[['Retorno Acumulado IBOV']].fillna(0))*100, label="Ibovespa", color="red", lw=3)
plt.legend(frameon=False, loc="upper center")
plt.show()
```

<center>
<img src="https://github.com/rafa-rod/comparar_fundos_br/blob/main/media/figura2.png" style="width:100%;"/>
</center>

Ainda é possível listar os Fundos de maior e pior desempenho:

```python
melhores = data.iloc[-1:].T.dropna().sort_values(data.index[-1], ascending=False)
melhores.columns = ["Evolução"]
melhores.head()
```

```
| CNPJ - Nome                                                                                                  |   Evolução |
|--------------------------------------------------------------------------------------------------------------|------------|
| 03.916.081/0001-62 // BRADESCO FIF - CLASSE DE INVESTIMENTO EM AÇÕES PETROBRAS - RESPONSABILIDADE LIMITADA   |    141.402 |
| 03.922.006/0001-04 // BRADESCO H FIF - CLASSE DE INVESTIMENTO EM AÇÕES PETROBRAS - RESPONSABILIDADE LIMITADA |    141.294 |
| 04.884.567/0001-29 // BRADESCO BA FIF - CLASSE DE INVESTIMENTO EM AÇÕES VALE -RESP LIMITADA                  |    124.039 |
| 04.882.617/0001-39 // BRADESCO FIF - CLASSE DE INVESTIMENTO EM AÇÕES VALE - RESPONSABILIDADE LIMITADA        |    123.804 |
| 04.892.107/0001-42 // BRADESCO H FIF - CLASSE DE INVESTIMENTO EM AÇÕES VALE DO RIO DOCE - RESP LIMITADA      |    123.724 |
```

Uma forma eficiente de avaliar o desempenho dos fundos, é por meio de janelas móveis. Ao invocar a função `plotar_rentabilidade_janela_movel` informando a série temporal das cotas diárias, os benchmarks específicos e a janela de tempo ou *holding period (HP)*, veja:

```python
import random, matplotlib
random.seed(12)
matplotlib.style.use("fivethirtyeight")
seleciona_um_fundo_aleatoriamente = random.sample(serie_temporal_fundos.iloc[0].dropna().index.tolist(), 1)

comp.plotar_rentabilidade_janela_movel(serie_temporal_fundos[seleciona_um_fundo_aleatoriamente], 
                                       3*252, df_benchmarks[['CDI', 'IBOV']] )
```
No exemplo acima, um fundo foi sorteado aleatoriamente; mas você pode ter outro critério para selecioná-lo. Importante a série dde benchmarks ter a mesma janela histórica disponível. **O HP escolhido foi de 3 anos, repare se o fundo selecionado tem dado suficiente para fazer essa análise.**

<center>
<img src="https://github.com/rafa-rod/comparar_fundos_br/blob/main/media/plotar_rentabilidade_janela_movel.png" style="width:100%;"/>
</center>

Outra forma de avaliação é uma visão mais geral em períodos específicos padronizados como: mensal (M), trimestral (Q), semestral (sem) ou anual (Y) destacando as cores do retornos mais positivos e negativos. Basta informar os retornos diários e selecionar o período:

```python
comp.plotar_heatmap_rentabilidade(serie_temporal_fundos[seleciona_um_fundo_aleatoriamente], period='M')
```

<center>
<img src="https://github.com/rafa-rod/comparar_fundos_br/blob/main/media/plotar_heatmap_rentabilidade.png"
style="width:100%;"/>
</center>

De forma complementar ao gráfico *heatmap* anterior, pode ser exibido uma figura que compara os retornos do período com seu benchmark. A última coluna *Ultrapassa Retorno CDI* (CDI escolhido no exemplo) representa o número de vezes que o fundo ultrapassou o benchmark sobre o total de períodos (se mensal, doze periodos).

```python
comp.plotar_heatmap_comparar_benchmark(serie_temporal_fundos[seleciona_um_fundo_aleatoriamente],
                                          df_benchmarks[['Retorno CDI']],
                                          "M")
```

<center>
<img src="https://github.com/rafa-rod/comparar_fundos_br/blob/main/media/plotar_heatmap_comparar_benchmark.png"
style="width:100%;"/>
</center>

Agora fazendo de forma mais objetiva e menos visual, pode-se avaliar o desempenho de vários fundos com diversos benchmarks simultaneamente estabelecendo um limite de corte para exibir aqueles que superem os benchmarks em 60% das vezes, por exemplo.
Veja o exemplo abaixo com 15 fundos e 3 benchmarks, em janela de 3 anos com limite de 60%:

```python
quinze_fundos_aleatorios = random.sample(serie_temporal_fundos_completo.iloc[0].dropna().index.tolist(), 15)
fundos_selecionados_por_corte = comp.supera_benchmark(serie_temporal_fundos[quinze_fundos_aleatorios],
                                                         df_benchmarks[['SP500', 'IBOV', 'CDI']], 3*252, 0.6)
fundos_selecionados_por_corte
```
```
| Fundo                                                                                                                   |   Supera IBOV (%) |   Supera CDI (%) |
|-------------------------------------------------------------------------------------------------------------------------|-------------------|------------------|
| 08.418.132/0001-40 // ITAU FLEXPREV VÉRTICE PRÉ FUNDO DE INVESTIMENTO FINANCEIRO RENDA FIXA - RESPONSABILIDADE LIMITADA |           67.7575 |          68.3916 |
| 00.977.449/0001-04 // BNP PARIBAS GERDAU PREVIDÊNCIA 1 CLASSE DE INVESTIMENTO RENDA FIXA CREDITO PRIVADO RESP LIMITADA  |           66.4209 |          97.8812 |
| 03.545.843/0001-61 // CARGILLPREV CD PREVIDENCIÁRIO MULTIMERCADO CRÉDITO PRIVADO - FUNDO DE INVESTIMENTO                |           66.2223 |          85.8377 |
```
Repare que apenas 3 fundos superaram seus benchmarks, exceto SP500, mais que 60% das vezes em janela móvel de 3 anos.

Complementando, a análise acima, veja quantas vezes esses fundos ultrapassaram, em média, seus benchmarks e também quanto, em média, ficaram abaixo dos benchmarks. Além disso, exibe quanto o fundo superou, em média, seu benchmark no período.

```python
corte_benchmark = 100
bench_corte = 'CDI'
janela_movel = 3*252 #3 anos
indice_superacao = comp.qto_supera_benchmark(serie_temporal_fundos[fundos_selecionados_por_corte.index.tolist()],
                                             df_benchmarks[['IBOV', 'CDI']], janela_movel, corte_benchmark, bench_corte)
indice_superacao
```
```
| Fundo                                                                                                                   |   % de vezes, em média, acima IBOV (%) |   % de vezes, em média, abaixo IBOV (%) |   % do IBOV, em média |   % de vezes, em média, acima CDI (%) |   % de vezes, em média, abaixo CDI (%) |   % do CDI, em média |
|-------------------------------------------------------------------------------------------------------------------------|----------------------------------------|-----------------------------------------|-----------------------|---------------------------------------|----------------------------------------|----------------------|
| 00.977.449/0001-04 // BNP PARIBAS GERDAU PREVIDÊNCIA 1 CLASSE DE INVESTIMENTO RENDA FIXA CREDITO PRIVADO RESP LIMITADA  |                                35.1578 |                                -33.5267 |              55.9516  |                               2.10514 |                              -0.822388 |              107.204 |
| 08.418.132/0001-40 // ITAU FLEXPREV VÉRTICE PRÉ FUNDO DE INVESTIMENTO FINANCEIRO RENDA FIXA - RESPONSABILIDADE LIMITADA |                                33.008  |                                -23.7353 |              30.8463  |                              10.0789  |                              -7.12265  |              118.918 |
| 03.545.843/0001-61 // CARGILLPREV CD PREVIDENCIÁRIO MULTIMERCADO CRÉDITO PRIVADO - FUNDO DE INVESTIMENTO                |                                34.4475 |                                -33.8336 |               5.45296 |                               1.63382 |                              -0.470723 |              104.487 |
```

Para Fundos de Participação (FIPs) e Fundos de Direitos Creditórios (FIDCs), a sistemática é diferente. Enquanto os FIPs tem seus resultados divulgados trimestralmente, os FIDCs são mensalmente divulgados. Assim, para obte-los, basta codar:

```python
#Informe apenas o ano para obter os dados de FIPs disponíveis
fip = comp.get_fip(2022)

#Para FIDCs informe ano e mês
from tqdm import tqdm

informe_fidcs_all = pd.DataFrame()
for ano in [2020, 2021]:
   for mes in tqdm(range(1, 13)):
        informe_fidcs = comp.get_fidc(ano, mes, tabela = 'X', subtabela = 3, proxy=None)
        if not informe_fidcs.empty:
            informe_fidcs_all = pd.concat([informe_fidcs_all, informe_fidcs])
```

*Os fundos exibidos acima são apenas exemplos mostrados aleatoriamente, não é recomendação de investimento ou desinvestimento.*