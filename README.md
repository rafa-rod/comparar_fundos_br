<p align="center">
  <img width=60% src="https://github.com/rafa-rod/comparebrfunds/blob/main/media/maxdd_area.png">
</p>

A biblioteca `comparar_fundos_br` possui uma série de funções que permitem:

- Capturar dados diários de fundos de investimento;
- Filtrar fundos por classe CVM (ex Fundos de Ações, Fundos de Renda Fixa, etc);
- Calcular risco (volatilidade) e retorno dos fundos;
- Cálculo de rentabilidade no período selecionado, rentabilidade diária, rentabilidade acumulada, rentabilidade anualizada;
- Filtrar fundos por CNPJ ou por nome (ex: fundos que contenham a palavra Bradesco);
- Comparar fundos com benchmarks como: CDI, Índice Bovespa, IMA-B, IMA-B 5 e IMA-B 5+;
- Comparar fundos com sua carteira de investimentos;
- Plotar gráficos de comparação e evolução dos fundos em período específico juntamente com seus benchmarks.

```
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

```
cadastro_fundos = get_fundsregistration(classe="Fundo de Ações")

informe_diario_fundos_historico = pd.DataFrame()
for ano in range(2018, 2023):
    for mes in range(1, 13):
        try:
            if ano == datetime.now().year and mes <= datetime.now().month:
                print(f"ano {ano} mes {mes}")
                informe_diario_fundos = get_brfunds(ano, mes, proxy=proxies)
                informe_diario_fundos_filtrado = filtrar_fundos(cadastro_fundos, informe_diario_fundos)
                informe_diario_fundos_filtrado = informe_diario_fundos_filtrado.set_index(["DT_COMPTC"])
                informe_diario_fundos_historico = pd.concat([informe_diario_fundos_historico, informe_diario_fundos_filtrado])
            elif ano < datetime.now().year:
                print(f"ano {ano} mes {mes}")
                informe_diario_fundos = get_brfunds(ano, mes, proxy=proxies)
                informe_diario_fundos_filtrado = filtrar_fundos(cadastro_fundos, informe_diario_fundos)
                informe_diario_fundos_filtrado = informe_diario_fundos_filtrado.set_index(["DT_COMPTC"])
                informe_diario_fundos_historico = pd.concat([informe_diario_fundos_historico, informe_diario_fundos_filtrado])
        except:
            continue
informe_diario_fundos_historico.index = pd.to_datetime(informe_diario_fundos_historico.index)
informe_diario_fundos_historico = informe_diario_fundos_historico.sort_index()
```


```python
data = plotar_evolucao(
                df,
                lista_fundos=["03.916.081/0001-62","06.916.384/0001-73"],
                figsize=(15, 5),
                color="gray",
                alpha=0.2,
                color_maximo="orange",
                color_minimo="red",
                color_seta_maximo="orange",
                color_seta_minimo="red",
                posicao_texto_maximo=(10, 17),
                posicao_texto_minimo=(10, -20),
                )
plt.title("Evolução dos Fundos")
#plt.plot(indice_ibov_acumulado*100, label="Ibovespa")
plt.plot(dados_benchmark_acumulado*100, label="CDI")
plt.legend(frameon=False, loc="center right")
plt.show()
```

```
data = plotar_evolucao(
                df,
                lista_fundos=["XP "],
                figsize=(15, 5),
                color="gray",
                alpha=0.2,
                color_maximo="orange",
                color_minimo="red",
                color_seta_maximo="orange",
                color_seta_minimo="red",
                posicao_texto_maximo=(-20, 17),
                posicao_texto_minimo=(-20, 17),
                )
plt.title("Evolução dos Fundos que contenham XP no nome")
plt.plot(indice_ibov_acumulado*100, label="Ibovespa")
plt.legend(frameon=False, loc="lower right")
plt.show()
```
