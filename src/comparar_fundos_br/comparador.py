# -*- coding: utf-8 -*-
"""
@author: Rafael
"""
from comparar_fundos_br.benchmarks import *
import warnings
from typing import Any, List, Tuple, Union, Optional
from tqdm import tqdm
import numpy as np
import pandas as pd
from itertools import cycle

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, rgb_to_hsv

def _get_valores_iniciais(df: pd.DataFrame) -> List[float]:
    if isinstance(df, pd.DataFrame):
        return [df[df[col].notnull()][col].iloc[0] for col in df.columns]
    else:
        return [value for value in df.values if np.isnan(value)==False][0]
    
def _get_valores_finais(df: pd.DataFrame) -> List[float]:
    if isinstance(df, pd.DataFrame):
        return [df[df[col].notnull()][col].iloc[-1] for col in df.columns]
    else:
        return [value for value in df.values if np.isnan(value)==False][-1]

def _get_cotas_normalizadas(df: pd.DataFrame) -> pd.DataFrame:
    valor_inicial = _get_valores_iniciais(df)
    cotas_normalizadas = df/valor_inicial
    return cotas_normalizadas

def calcula_retorno_janelas_moveis(cotas_diarias: pd.DataFrame, HP: int, dados_diarios_benchmark: pd.DataFrame) -> pd.DataFrame:
    '''Função que calcula o retorno em janelas móveis de periodo HP (holding period) de um ou mais fundos e seu benchmark.
    Parâmetros:
    -cotas_diarias (dataframe): com valor das cotas;
    -HP (int): periodo da janela móvel, em dias;
    -dados_diarios_benchmark (dataframe): índice diário do benchmark
    Retorno:
    -retorno_janelas_moveis (dataframe): retorno na janela móvel HP'''
    dados = pd.concat([cotas_diarias, dados_diarios_benchmark], axis=1).dropna()
    cotas_normalizadas = _get_cotas_normalizadas(dados)
    retorno_janelas_moveis = cotas_normalizadas.dropna().pct_change(HP)
    return retorno_janelas_moveis.sort_index().dropna()
   
def calcula_risco_retorno_fundos(
                                dados_fundos_cvm: pd.DataFrame,
                                ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    '''Função que extrai diversas informações de retorno e risco para uma primeira análise dos fundos.
    Parâmetros:
    -dados_fundos_cvm (dataframe): série temporal contendo as cotas diarias dos fundos. Cada coluna deve ser a cota de um fundo e índice as datas.
    Retorno:
    -risco_retorno (dataframe): contém volatilidade anualizada e retorno de todo o periodo também anualizado;
    -rentabilidade_fundos_diaria (dataframe): retorno diário dos fundos;
    -cotas_normalizadas (dataframe): valor das cotas diárias normalizada começando com valor unitário;
    -rentabilidade_fundos_acumulada (dataframe): rentabilidade acumulada de todo o período;
    -rentabilidade_acumulada_por_ano (dataframe): rentabilidade acumulada por cada ano;
    -rentabilidade_fundos_total (dataframe): rentabilidade total de todo o periodo'''
    serie_fundos = dados_fundos_cvm.copy()
    cotas_normalizadas = _get_cotas_normalizadas(serie_fundos)
    rentabilidade_fundos_diaria = cotas_normalizadas.pct_change()
    rentabilidade_fundos_acumulada = (1 + rentabilidade_fundos_diaria).cumprod() - 1

    T = serie_fundos.shape[0]
    valores_finais_nao_nulos = pd.DataFrame(_get_valores_finais(cotas_normalizadas), index=cotas_normalizadas.columns).T
    retorno_periodo_anualizado = (((valores_finais_nao_nulos/ _get_valores_iniciais(cotas_normalizadas))** (252 / T)- 1)).T
    retorno_periodo_anualizado.columns = ["rentabilidade"]

    rentabilidade_acumulada_por_ano = rentabilidade_fundos_acumulada.groupby(pd.Grouper(freq="Y")).last(1).T
    rentabilidade_acumulada_por_ano.columns = [str(x)[:4] for x in rentabilidade_acumulada_por_ano.columns]

    volatilidade_fundos = rentabilidade_fundos_diaria.std().to_frame() * np.sqrt(252)
    volatilidade_fundos.columns = ["volatilidade"]

    risco_retorno = pd.concat([volatilidade_fundos, retorno_periodo_anualizado], axis=1)
    return (
            risco_retorno.dropna().sort_values("rentabilidade", ascending=False),
            rentabilidade_fundos_diaria,
            cotas_normalizadas,
            rentabilidade_fundos_acumulada,
            rentabilidade_acumulada_por_ano
            )

def remove_outliers(df: pd.DataFrame, q: float = 0.05) -> pd.DataFrame:
    '''Remove outliers ao informar usando método do range interquartil, ou seja, retira os dados 
    acima de 1.5*Q3 (1-q) e abaixo de 1.5*Q1 (q), onde q é o quantil.
    Quanto maior o valor de q, mais dados serão removidos.'''
    df1 = df.copy()
    col = df1.columns.tolist()
    upper = df1[col].quantile(1-q)
    lower = df1[col].quantile(q)
    df2 =  df1[(df1[col] < upper) & (df1[col] > lower)]
    return df2

def plotar_comparacao_risco_retorno(
                                    df: pd.DataFrame,
                                    risco_retorno_carteira: Union[Tuple[int, int], None] = None,
                                    risco_retorno_benchmark: Union[Tuple[int, int], None] = None,
                                    nome_carteira: Union[str, None] = None,
                                    nome_benchmark: Union[str, None] = None,
                                    **opcionais: Any
                                    ) -> None:
    if risco_retorno_carteira:
        risco_carteira, retorno_carteira = risco_retorno_carteira
    if risco_retorno_benchmark:
        risco_benchmark, retorno_benchmark = risco_retorno_benchmark

    plt.figure(figsize=(opcionais.get("figsize")))
    sns.scatterplot(
        data=df, y="rentabilidade", x="volatilidade", alpha=0.45, color="gray"
    )
    if risco_retorno_carteira:
        plt.scatter(x=risco_carteira, y=retorno_carteira, marker="o", color="blue", s=200)
    if risco_retorno_benchmark:
        plt.scatter(x=risco_benchmark, y=retorno_benchmark, marker="o", color="red", s=200)
    plt.ylabel("Retorno (%aa)\n", rotation=0, labelpad=-70, loc="top")
    plt.xlabel("Volatilidade (%aa)")
    plt.suptitle('Risco x Retorno')
    plt.box(False)
    plt.grid(axis="y")
    plt.ylim(opcionais.get("ylim"))
    plt.xlim(opcionais.get("xlim"))
    if risco_retorno_carteira:
        plt.annotate(
            nome_carteira,
            xy=(risco_carteira + 0.5, retorno_carteira),
            xycoords="data",
            xytext=opcionais.get("posicao_texto_carteira"),
            textcoords="offset points",
            color="darkblue",
            weight="bold",
            arrowprops=dict(arrowstyle="->", color="blue", connectionstyle="arc3,rad=-0.1"),
        )
    if risco_retorno_benchmark:
        plt.annotate(
            nome_benchmark,
            xy=(risco_benchmark + 0.5, retorno_benchmark),
            xycoords="data",
            xytext=opcionais.get("posicao_texto_benchmark"),
            textcoords="offset points",
            color="darkred",
            weight="bold",
            arrowprops=dict(arrowstyle="->", color="r", connectionstyle="arc3,rad=-0.1"),
        )


def plotar_evolucao(
                    df: pd.DataFrame, lista_fundos: List[str], **opcionais: Any
                    ) -> Union[pd.DataFrame, None]:

    lista_fundos = [x.upper() for x in lista_fundos]
    cnpj = [x for x in df.columns.tolist() if x.split(" // ")[0] in lista_fundos]
    nome = [x for x in df.columns.tolist() if x.split(" // ")[1] in lista_fundos]
    if len(nome) == 0:
        for fundos in df.columns.tolist():
            fd = fundos.split(" // ")[1]
            for fds in lista_fundos:
                if fds in fd:
                    nome.append(fundos)
    colunas = nome + cnpj
    if len(colunas) > 2:
        data = df[colunas].dropna(axis=1, how="all")
        data = data[data > 0].dropna()
        maximo, minimo = (
            data.iloc[-1:].idxmax(axis=1).values[0],
            data.iloc[-1:].idxmin(axis=1).values[0],
        )
        legenda_maximo = maximo.split(" // ")[0]
        legenda_minimo = minimo.split(" // ")[0]
        data.index = pd.to_datetime(data.index)
        plt.figure(figsize=(opcionais.get("figsize")))
        plt.plot(
            data.drop([maximo, minimo], axis=1),
            color=opcionais.get("color"),
            alpha=opcionais.get("alpha"),
        )
        plt.plot(data[maximo], color=opcionais.get("color_maximo"))
        plt.plot(data[minimo], color=opcionais.get("color_minimo"))
        plt.ylabel("Cotas\n", rotation=0, labelpad=-20, loc="top")
        plt.xlabel("")
        plt.box(False)
        plt.grid(axis="y")
        plt.ylim(opcionais.get("ylim"))
        plt.xlim(opcionais.get("xlim"))
        plt.annotate(
            legenda_maximo,
            xy=(data.index[-1], data.iloc[-1:].max(axis=1).values[0]),
            xycoords="data",
            xytext=opcionais.get("posicao_texto_maximo"),
            textcoords="offset points",
            color=opcionais.get("color_maximo"),
            weight="bold",
            arrowprops=dict(
                arrowstyle="->",
                color=opcionais.get("color_seta_maximo"),
                connectionstyle="arc3,rad=-0.1",
            ),
        )
        plt.annotate(
            legenda_minimo,
            xy=(data.index[-1], data.iloc[-1:].min(axis=1).values[0]),
            xycoords="data",
            xytext=opcionais.get("posicao_texto_minimo"),
            textcoords="offset points",
            color=opcionais.get("color_minimo"),
            weight="bold",
            arrowprops=dict(
                arrowstyle="->",
                color=opcionais.get("color_seta_minimo"),
                connectionstyle="arc3,rad=-0.1",
            ),
        )
        return data
    elif len(colunas) <=2:
        data = df[colunas].dropna(axis=1, how="all")
        data = data[data > 0].dropna()
        data.index = pd.to_datetime(data.index)
        plt.figure(figsize=(opcionais.get("figsize")))
        plt.plot(
            data,
            color=opcionais.get("color"),
            alpha=opcionais.get("alpha"),
        )
        plt.ylabel("Cotas\n", rotation=0, labelpad=-20, loc="top")
        plt.xlabel("")
        plt.box(False)
        plt.grid(axis="y")
        plt.ylim(opcionais.get("ylim"))
        plt.xlim(opcionais.get("xlim"))
        return data
    elif not colunas:
        print("Fundo não encontrado")
        return None

def plotar_rentabilidade_janela_movel(df: pd.DataFrame, HP: int, benchmarks: pd.DataFrame) -> None:
    for fundo in df.columns:
        retorno = calcula_retorno_janelas_moveis(df[[fundo]], HP, benchmarks)

        plt.figure(figsize=(15, 6))
        plt.suptitle(f"Retorno de {HP} dias")
        plt.plot(retorno[fundo].multiply(100), lw=2)
        plt.plot(retorno[benchmarks.columns.tolist()].multiply(100), lw=1, alpha=0.8)
        plt.xticks(rotation=45)
        plt.xlabel('')
        plt.ylabel("%\n", rotation=0, labelpad=-15, loc="top")
        plt.legend([fundo.split("//")[-1]]+benchmarks.columns.tolist(), loc="upper right", frameon=False,
                     bbox_to_anchor=(0.5, 0.67, 0.5, 0.5))
        plt.tight_layout()
        plt.box(False)
        plt.grid(axis="x")
    plt.show()

def plotar_comparacao_risco_retorno(
                                    df: pd.DataFrame,
                                    risco_retorno_carteira: Union[Tuple[int, int], None] = None,
                                    risco_retorno_benchmark: Union[Tuple[int, int], None] = None,
                                    nome_carteira: Union[str, None] = None,
                                    nome_benchmark: Union[str, None] = None,
                                    **opcionais: Any
                                    ) -> None:
    if risco_retorno_carteira:
        risco_carteira, retorno_carteira = risco_retorno_carteira
    if risco_retorno_benchmark:
        risco_benchmark, retorno_benchmark = risco_retorno_benchmark

    plt.figure(figsize=(opcionais.get("figsize")))
    sns.scatterplot(
        data=df, y="rentabilidade", x="volatilidade", alpha=0.45, color="gray"
    )
    if risco_retorno_carteira:
        plt.scatter(x=risco_carteira, y=retorno_carteira, marker="o", color="blue", s=200)
    if risco_retorno_benchmark:
        plt.scatter(x=risco_benchmark, y=retorno_benchmark, marker="o", color="red", s=200)
    plt.ylabel("Retorno (%aa)\n", rotation=0, labelpad=-70, loc="top")
    plt.xlabel("Volatilidade (%aa)")
    plt.box(False)
    plt.grid(axis="y")
    plt.ylim(opcionais.get("ylim"))
    plt.xlim(opcionais.get("xlim"))
    if risco_retorno_carteira:
        plt.annotate(
            nome_carteira,
            xy=(risco_carteira + 0.5, retorno_carteira),
            xycoords="data",
            xytext=opcionais.get("posicao_texto_carteira"),
            textcoords="offset points",
            color="darkblue",
            weight="bold",
            arrowprops=dict(arrowstyle="->", color="blue", connectionstyle="arc3,rad=-0.1"),
        )
    if risco_retorno_benchmark:
        plt.annotate(
            nome_benchmark,
            xy=(risco_benchmark + 0.5, retorno_benchmark),
            xycoords="data",
            xytext=opcionais.get("posicao_texto_benchmark"),
            textcoords="offset points",
            color="darkred",
            weight="bold",
            arrowprops=dict(arrowstyle="->", color="r", connectionstyle="arc3,rad=-0.1"),
        )

def supera_benchmark(dados: pd.DataFrame, benchmarks: pd.DataFrame, HP: int,
                     limit: float = 0.6, janela_analise: int = 252) -> pd.DataFrame:
    '''Função que indica a porcentagem de vezes em que o fundo supera o benchmark no periodo selecionado.
    O corte é dado pelo parâmetro limit.'''
    percentuais = pd.DataFrame()
    lista_benchmarks = [x for x in benchmarks.columns if 'Retorno' not in x]
    for i, fundo in enumerate(tqdm(dados.columns.tolist())):
        df1 = pd.DataFrame()
        for bench in lista_benchmarks:
            retorno = calcula_retorno_janelas_moveis(dados[[fundo]], HP, benchmarks[[bench]])
            retorno = retorno.sort_index().dropna()
            if retorno.empty: break
            elif retorno.shape[0] < janela_analise: continue
            eventos = (retorno[fundo] - retorno[bench])
            percentual_sobre_bench = len(eventos[eventos>0])/len(eventos)
            if percentual_sobre_bench >= limit:
                df = pd.DataFrame([fundo, percentual_sobre_bench*100], index=["Fundo", f"Supera {bench} (%)"]).T.set_index("Fundo")
                df1 = pd.concat([df1, df], axis=1)
        percentuais = pd.concat([percentuais, df1], axis=0)
    return percentuais[(percentuais>=limit*100)].dropna().sort_values(percentuais.columns.tolist(), ascending=False)

def qto_supera_benchmark(dados: pd.DataFrame, benchmarks: pd.DataFrame, HP: int, corte_bench: float=100, bench_corte='CDI') -> pd.DataFrame:
    '''Enquanto a função *supera_benchmark* indica se um fundo supera o benchmark.
    Essa função exibe quantas vezes os fundos superaram o benchmark, em média, e o quanto eles 
    ficam abaixo do benchmark, em média.
    Os fundos são ranqueados por % do benchmark. O parâmetro corte_bench filtra os fundos que performam,
    pelo menos, o mesmo que o fundo.'''
    percentuais = pd.DataFrame()
    lista_benchmarks = [x for x in benchmarks.columns if 'Retorno' not in x]
    for i, fundo in enumerate(tqdm(dados.columns.tolist())):
        df1 = pd.DataFrame()
        for bench in lista_benchmarks:
            retorno = comp.calcula_retorno_janelas_moveis(dados[[fundo]], HP, benchmarks[[bench]])
            retorno = retorno.sort_index().dropna()
            if retorno.empty: break
            eventos = (retorno[fundo] - retorno[bench])
            media_sup = eventos[eventos>=0].mean()
            media_inf = eventos[eventos<0].mean()
            em_rel_cdi = (retorno[fundo]/retorno[bench]).mean()
            df = pd.DataFrame([fundo, media_sup, media_inf, em_rel_cdi], index=["Fundo", f"% de vezes, em média, acima {bench} (%)",
                                                                        f"% de vezes, em média, abaixo {bench} (%)",
                                                                        f'% do {bench}, em média']).T.set_index("Fundo")
            df1 = pd.concat([df1, df], axis=1)
        percentuais = pd.concat([percentuais, df1], axis=0)
    cols1 = [x for x in percentuais.columns if 'acima' not in x and 'abaixo' not in x]
    percentuais = (percentuais.sort_values(cols1, ascending=False)*100).fillna(0)
    if not bench_corte:
        for bench in lista_benchmarks:
            percentuais = percentuais[percentuais[f'% do {bench}, em média']>=corte_bench]
    else:
        percentuais = percentuais[percentuais[f'% do {bench_corte}, em média']>=corte_bench]
    return percentuais

def _repetir_elemento(seq):
    return cycle(seq)

def _traduz_frequencia(frequencia: str) -> List[str]:
    if 'month' in frequencia.lower().split(' ')[0]:
        freq = ["Meses", "Mensais"]
    elif 'year' in frequencia.lower().split(' ')[0]:
        freq = ["Anos", "Anuais"]
    elif 'sem' in frequencia.lower().split(' ')[0]:
        freq = ["Semestres", "Semestrais"]
    elif 'quarter' in frequencia.lower().split(' ')[0]:
        freq = ["Trimestres", "Trimestrais"]
    else:
        freq = [frequencia]
    return freq

def _calcula_rentabilidade_periodo(rentabilidade_diaria: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    if freq.lower()=="sem":
        freq = "Q"
        inicio = rentabilidade_diaria.resample(f"{freq}S").first()
        fim = rentabilidade_diaria.resample(f"{freq}E").last()
        inicio = inicio[inicio.index.month.isin([1,7])]
        fim = fim[fim.index.month.isin([6,12])]
    else:
        inicio = rentabilidade_diaria.resample(f"{freq}S").first()
        fim = rentabilidade_diaria.resample(f"{freq}E").last()
    rentabilidade_periodo_total = pd.DataFrame()
    for (init, end) in zip(inicio.index, fim.index):
        df = rentabilidade_diaria[(rentabilidade_diaria.index>=init) & (rentabilidade_diaria.index<=end)].fillna(0)
        rentabilidade_periodo = ((1 + df).cumprod() - 1).tail(1)
        rentabilidade_periodo.index = [end]
        rentabilidade_periodo_total = pd.concat([rentabilidade_periodo_total, rentabilidade_periodo])
    return rentabilidade_periodo_total.asfreq(f"{freq}E")

def _retorno_heatmap(retorno_diario: pd.DataFrame, period: str, nome: str) -> Union[pd.DataFrame, List[str]]:
    returns = _calcula_rentabilidade_periodo(retorno_diario, period.upper())*100
    frequencia = period if period=='sem' else str(returns.index.freq).replace('<','').replace('>','')
    freq = _traduz_frequencia(frequencia)
    f = _repetir_elemento(list(range(1, returns.index.month[:-1].nunique()+1)))
    lista_repeticao = [next(f) for x in range(returns.shape[0])]
    
    returns["Ano"] = returns.index.year
    returns[f"{freq[0]}"] = lista_repeticao
    returns = returns.pivot_table(index=f"{freq[0]}", columns="Ano", values=nome, aggfunc="last").fillna(0).T
    return returns, freq

def plotar_heatmap_rentabilidade(retorno_diario: pd.DataFrame, period: str = 'M') -> None:
    '''Função que plota gráfico tipo heatmap que exibe o desempenho do fundo ou do benchmark no periodo indicado, que pode ser:
    -mensal (M), 
    -trimestral (Q), 
    -semestral (sem) ou 
    -anual (Y)
    Como entrada de dados, a função precisa do dataframe do retorno diário do fundo ou do benchmark.
    '''
    cmap = LinearSegmentedColormap.from_list(name='t',
        colors=["red", "white", 'green']
    )
    nome = retorno_diario.columns[0]
    returns, freq = _retorno_heatmap(retorno_diario, period, nome)

    grayscale=False
    ylabel=True
    fontname="Arial"
    annot_size=10

    fig, ax = plt.subplots(figsize=(10,5))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)

    fig.set_facecolor("white")
    ax.set_facecolor("white")

    ax.set_title(
         f"Retornos {freq[1]} (%) - {nome.title()}\n",
        fontsize=14,
        y=0.995,
        fontname=fontname,
        fontweight="bold",
        color="black",
    )
    ax = sns.heatmap(
                returns,
                ax=ax,
                annot=True,
                center=0,
                annot_kws={"size": 10},
                fmt="0.2f",
                linewidths=0.5,
                square=False,
                cbar=True,
                cmap=cmap,
                cbar_kws={"format": "%.0f%%"},
            )

    # align plot to match other
    if ylabel:
        ax.set_ylabel("Ano", fontname=fontname, fontweight="bold", fontsize=12, rotation=0)
        ax.yaxis.set_label_coords(-0.1, 0.5)

    ax.tick_params(colors="#808080")
    plt.xticks(rotation=0, fontsize=annot_size * 1.2)
    plt.yticks(rotation=0, fontsize=annot_size * 1.2)

    try:
        plt.subplots_adjust(hspace=0, bottom=0, top=1)
    except Exception:
        pass
    try:
        fig.tight_layout(w_pad=0, h_pad=0)
    except Exception:
        pass

    plt.show(block=False)
    plt.close()

def plotar_heatmap_comparar_benchmark(rentabilidade_diaria_fundos: pd.DataFrame,
                                      rentabilidade_diaria_benchmarks: pd.DataFrame,
                                      period: str = "M") -> None:
    '''Função que exibe gráfico heatmap para facilitar a comparação de desempenho de um fundo com seu benchmark.
    O gráfico uma coluna Ultrapassa Benchmark onde indica, em %, quanto o fundo superou o benchmark no periodo (period), que pode ser:
    -mensal (M), 
    -trimestral (Q), 
    -semestral (sem) ou 
    -anual (Y)
    superou = 100 * num_vezes_que_superou_no_periodo/total_de_periodos
    As cores do gráfico auxiliam na indicação dos periodos em que houve superação.
    '''
    bench = rentabilidade_diaria_benchmarks.columns[0]
    nome = rentabilidade_diaria_fundos.columns[0]
    returns1, freq = _retorno_heatmap(rentabilidade_diaria_fundos, period, nome)
    returns2, freq2 = _retorno_heatmap(rentabilidade_diaria_benchmarks, period, bench)
    
    df4 = returns1 - returns2
    df4['nao_superou'] = (df4 < 0).sum(axis=1)
    df4['superou'] = (df4[[df4.columns[0]]] > 0).sum(axis=1)
    df4[f'Ultrapassa {bench}'] = np.where(df4['superou']>0, 100*(df4['superou']/(df4['superou']+df4['nao_superou'])), 0)
    
    df = pd.concat([returns1, df4[f'Ultrapassa {bench}']], axis=1)
    colors = ["darkred", "red", 'lightcoral', "lightpink", "pink",  "lightgreen", 'limegreen','forestgreen', "darkgreen"]
    cmap_gradient = LinearSegmentedColormap.from_list("cmap", colors)

    last_column = df.iloc[:, -1]
    norm = plt.Normalize(last_column.min(), last_column.max())
    row_colors = cmap_gradient(norm(last_column))

    ylabel = True
    fontname = "Arial"
    annot_size = 10
    
    # Criar o gráfico
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    
    fig.set_facecolor("white")
    ax.set_facecolor("white")

    ax.set_title(
        f"Retornos {freq[1]} (%) - {nome.title()}\n",
        fontsize=14,
        y=1.04,
        fontname=fontname,
        fontweight="bold",
        color="black",
    )

    heatmap = sns.heatmap(
        df,
        ax=ax,
        annot=False,  # Anotar os valores nas células
        fmt=".2f",  # Formato dos números anotados
        cmap=cmap_gradient,  # Usar o colormap personalizado
        cbar=True,  # Adicionar barra de cores lateral
        linewidths=1.5,  # Espaçamento entre as células
        linecolor="gray",  # Cor das bordas das células
        cbar_kws={"format": "%.0f%%"}, #"ticks": [-100, -50, 0, 50, 100]},
        square=False
    )

    def get_text_color(cell_color):
        """Retorna 'white' se a cor de fundo for escura, caso contrário 'black'."""
        # Converte a cor para HSV e verifica a luminância (V)
        hsv = rgb_to_hsv(np.array(cell_color)[:3])
        luminance = hsv[2]  # Valor V em HSV
        return "white" if luminance < 0.5 else "black"
    
    # Ajustar as anotações para incluir '%'
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            value = df.iloc[i, j]
            text = f"{value:.2f}%"  # Adicionar o símbolo '%'
            cell_color = cmap_gradient(norm(df.iloc[i, -1]))
            text_color = get_text_color(cell_color)
            heatmap.text(
                j + 0.58,  # Posição x (coluna atual)
                i + 0.5,  # Posição y (linha atual)
                text,  # Valor formatado
                ha="center",  # Alinhamento horizontal
                va="center",  # Alinhamento vertical
                color=text_color,
                #color="black" if j == df.shape[1] - 1 else "darkslategray",  # Cor do texto
                fontsize=annot_size,  # Tamanho da fonte
                weight="bold" if j == df.shape[1] - 1 else "normal",  # Negrito na última coluna
            )

    for i, color in enumerate(row_colors):
        plt.gca().add_patch(plt.Rectangle((0, i), df.shape[1], 1, fill=True, color=color, lw=0))
    
    for i in range(df.shape[0] + 1):
        plt.axhline(i, color="white", linewidth=.5, linestyle="-")
    for j in range(df.shape[1] + 1):
        plt.axvline(j, color="white", linewidth=.5, linestyle="-")

    ax.set_xticks(np.arange(df.shape[1]-1)+0.45)
    ax.set_xticklabels(df.columns[:-1], rotation=0, fontsize=annot_size * 1.2)
    ax.tick_params(axis="x", which="major", pad=5)  # Aumentar o espaçamento da última coluna

    ax.text(
        df.shape[1] - 0.5,  # Posição x (última coluna)
        -.6,  # Posição y (acima do heatmap)
        df.columns[-1],  # Texto do rótulo
        ha="center",  # Alinhamento horizontal
        va="center",  # Alinhamento vertical
        fontsize=11,  # Tamanho da fonte
        fontweight="bold",  # Negrito
        color="black",  # Cor do texto
    )

    if ylabel:
        ax.set_ylabel("Ano", fontname=fontname, fontweight="bold", fontsize=12, rotation=0)
        ax.yaxis.set_label_coords(-0.1, 0.5)

    ax.tick_params(colors="#808080")
    plt.xticks(rotation=0, fontsize=annot_size * 1.2)
    plt.yticks(rotation=0, fontsize=annot_size * 1.2)
    
    try:
        plt.subplots_adjust(hspace=0, bottom=0, top=1)
    except Exception:
        pass
    try:
        fig.tight_layout(w_pad=0, h_pad=0)
    except Exception:
        pass
    
    plt.show(block=False)
    plt.close()