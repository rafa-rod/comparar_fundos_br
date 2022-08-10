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
    "https": f"https://{user}:{pwd}@{proxy}:{porta}",
        }
```

Veja a seguir um exemplo para capturar dados dos Fundos de Investimento com seus respectivos filtros.

```python
import comparar_fundos_br as comp

informe_diario_fundos_historico = comp.get_brfunds(anos=range(2021,2022), #somente 2021
                                              meses=range(1,3), #somente Jan e Fev
                                              classe="Fundo de Ações", 
                                              num_minimo_cotistas=10, 
                                              patriminio_liquido_minimo=1e6, 
                                              proxy=proxies)
informe_diario_fundos_historico.head()
```

```
| DT_COMPTC  | CNPJ - Nome                                       |   CLASSE        |   VL_QUOTA  |  NR_COTST |   VL_PATRIM_LIQ |
|:-----------|:-------------------------------------------------:|----------------:|------------:|----------:|----------------:|
| 2022-01-03 | 28.144.770/0001-27 // SAFRA FARADAY AÇÕES FUND... |  Fundo de Ações |  147.689974 |      7144 |   1085967556.96 | 
| 2022-01-03 | 28.122.142/0001-40 // XP INVESTOR IBOVESPA ATI... |  Fundo de Ações |  1.402952   |      7401 |     59237924.90 |
| 2022-01-03 | 28.098.599/0001-67 // HAWK FUNDO DE INVESTIMEN... |  Fundo de Ações |  1.963080   |        12 |     94788040.60 |
| 2022-01-03 | 28.076.506/0001-01 // CSHG ALLOCATION EQUITAS ... |  Fundo de Ações |  1.099504   |        78 |     24340094.17 |
| 2022-01-03 | 28.075.715/0001-22 // CSHG ALLOCATION MILES VI... |  Fundo de Ações |  1.577636   |       107 |    148464847.88 |
```

Importante ressaltar que todos os Fundos que são retornados possuem SIT ou situação CVM como "EM FUNCIONAMENTO NORMAL".

Se desejar capturar todas as classes de fundos, basta não restringir a variável classe. No exemplo seguinte,
também não há restrições sobre fundos com número de cotistas, tampouco sobre o patrimônio líquido. Nesse exemplo, não está sendo utilizada a configuração da proxy.

```python
informe_diario_fundos_historico = comp.get_brfunds(anos=range(2021,2022), #somente 2021
                                              meses=range(1,3), #somente Jan e Fev)
```
O exemplo acima demora mais para ser executado, uma vez que obtém todos os Fundos dentro do período selecionado. 
Caso deseje, por exemplo, apenas algunas classes de Fundos, como: Fundos de Ações e de Renda Fixa, siga o exemplo abaixo.

Também é possível consultar os tipos de classe disponíveis.

```python
informe_diario_fundos_historico = comp.get_brfunds(anos=range(2021,2022), #somente 2021
                                              meses=range(1,3), #somente Jan e Fev,
                                              classe=["Fundo de Renda Fixa","Fundo de Ações"])

#Para obter as classes disponíveis:
comp.get_classes()
```

Para obter o retorno dos Fundos, chame a função `calcula_rentabilidade_fundos` passando os dados dos fundos que acabou de obter.

```python
(  risco_retorno,
    cotas_normalizadas,
    rentabilidade_media_anualizada,
    rentabilidade_acumulada_por_ano,
    rentabilidade_fundos_total,
) = comp.calcula_rentabilidade_fundos(informe_diario_fundos_historico)
```

O primeiro dataframe indica tanto o risco (volatidade padrão) de cada fundo, por CNPJ, quanto sua rentabilidade, ambos anualizados. Já o segundo dataframe retorna o valor das cotas dos fundos normalizadas no período selecionado, o que facilita para comparação (veja a seguir nos gráficos).

Os demais dataframes retornam as rentabilidades média anualizada, acumulada por ano e a rentabilidade total no período, respectivamente.

A forma mais eficiente para comparar o desempenho dos Fundos é usando gráficos. Você pode plotar o risco x retorno dos Fundos e comparar com seu benchmark ou sua carteira de investimentos. Aqui não vamos calcular pra você a rentabilidade da sua carteira, apenas usar esse dado para comparar com  os fundos selecionados. Veja o exemplo:

```python
df4 = risco_retorno[
                    (risco_retorno["volatilidade"] <= 40)
                    & (risco_retorno["rentabilidade"] >= 0)
                    & (risco_retorno["rentabilidade"] <= 100)
                    ]

comp.plotar_comparacao_risco_retorno(
                                df4,
                                (21, 18), #(risco, retorno) da minha carteira
                                (19, 15), #(risco, retorno) do benchmark
                                nome_carteira="Minha Carteira",
                                nome_benchmark="Benchmark",
                                figsize=(15, 5),
                                posicao_texto_carteira=(30, 25),
                                posicao_texto_benchmark=(31, -25),
                                )
plt.title("Risco x Retorno - Fundos de Ações")
plt.ylim(-10, 140)
plt.xlim(-3, 60)
plt.show()
```
<center>
<img src="https://github.com/rafa-rod/comparar_fundos_br/blob/main/media/figura3.png" style="width:100%;"/>
</center>

Uma outra forma de comparação é utilizando as cotas iniciando em um valor inicial de 100, arbitrário. Assim a comparação fica facilitada.

A função `plotar_evolucao` encontra os Fundos tanto por CNPJ quanto por Nome, ou seja, se deseja obter todos os Fundos que possuam Bradesco no Nome, basta informa na variável `lista_fundos=["Bradesco"]`.

Para facilitar a comparação, você pode personalizar o gráfico para destacar o melhor e o pior Fundo, além de plotar o seu benchmark.

Os benchmarks disponíveis são: CDI, IMA-B, IMA-B 5, IMA-B 5+, Ibovespa e Ações diversas listadas na B3.

```python
cdi, cdi_acumulado = comp.get_benchmark("2022-01-01", 
                                        "2022-07-22", 
                                        benchmark = "cdi", 
                                        proxy=proxies)

data = comp.plotar_evolucao(
                cotas_normalizadas,
                lista_fundos=["03.916.081/0001-62","06.916.384/0001-73"],
                figsize=(15, 5),
                color="darkblue",
                alpha=0.8
                )
plt.title("Evolução dos Fundos")
plt.plot(cdi_acumulado*100, label="CDI")
plt.legend(frameon=False, loc="center right")
plt.show()
```

<center>
<img src="https://github.com/rafa-rod/comparar_fundos_br/blob/main/media/figura1.png" style="width:100%;"/>
</center>

```python
indice_ibov, indice_ibov_acumulado = comp.get_benchmark("2022-01-01", 
                                                        "2022-07-25", 
                                                        benchmark = "ibov",
                                                        proxy=proxies)

data = comp.plotar_evolucao(
                cotas_normalizadas,
                lista_fundos=["Bradesco"],
                figsize=(15, 5),
                color="gray",
                alpha=0.2,
                color_maximo="orange",
                color_minimo="blue",
                color_seta_maximo="orange",
                color_seta_minimo="blue",
                posicao_texto_maximo=(-100, -45),
                posicao_texto_minimo=(-100, 40),
                )
plt.title("Evolução dos Fundos que contenham Bradesco no nome")
plt.plot(indice_ibov_acumulado*100, label="Ibovespa", color="red", lw=3)
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
melhores = melhores.reset_index()
melhores[['CNPJ', 'DENOM SOCIAL']] = melhores['CNPJ - Nome'].str.split(' // ', 1, expand=True)
melhores = melhores.drop('CNPJ - Nome', axis=1)
melhores.head()
```

```
| Evolução   |         CNPJ       |   DENOM SOCIAL                                       |
|:-----------|:------------------:|-----------------------------------------------------:|
| 172.542213 | 10.590.125/0001-72 |  BRADESCO FUNDO DE INVESTIMENTO EM AÇÕES CIELO       | 
| 127.689792 | 03.916.081/0001-62 |  BRADESCO FUNDO DE INVESTIMENTO EM AÇÕES PETROBRAS   |
| 127.658068 | 03.922.006/0001-04 |  BRADESCO H FUNDO DE INVESTIMENTO AÇÕES PETROBRAS    |
| 127.449134 | 17.489.100/0001-26 |  BRADESCO FUNDO DE INVESTIMENTO EM AÇÕES BB SEG...   |
| 127.296598 | 11.504.894/0001-73 |  BRADESCO FUNDO DE INVESTIMENTO EM AÇÕES - PETR...   |
```

Também há a possibilidade de listar os piores e melhores Fundos em termos de risco e retorno:

```python
melhores_fundos, piores_fundos = comp.melhores_e_piores_fundos(rentabilidade_fundos_total, num=10)

fundos_maior_risco, fundos_menor_risco = comp.melhores_e_piores_fundos(risco_retorno[["volatilidade"]], num=10)
```

Para Fundos de Participação (FIPs) e Fundos de Direitos Creditórios (FIDCs), a sistemática é diferente. Enquanto os FIPs tem seus resultados divulgados trimestralmente, os FIDCs são mensalmente divulgados. Assim, para obte-los, basta codar:

```python
#Informe apenas o ano para obter os dados de FIPs disponíveis
fip = comp.get_fip(2022)

#Para FIDCs informe ano e mês
informe_fidcs_all = pd.DataFrame()
for ano in [2020, 2021]:
    for mes in range(1, 13):
        print(f"Data {mes}/{ano}")
        informe_fidcs = comp.get_fidc(ano, mes)
        if not informe_fidcs.empty:
            informe_fidcs_all = pd.concat([informe_fidcs_all, informe_fidcs])
```
