# -*- coding: utf-8 -*-
"""
@author: Rafael
"""
from comparar_fundos_br.benchmarks import *
import warnings
from typing import Any, List, Tuple, Union, Dict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)

import matplotlib.pyplot as plt
import matplotlib
matplotlib.style.use("fivethirtyeight")

def _get_valores_iniciais(df: pd.DataFrame) -> pd.Series:
    return df[~df.isnull()].iloc[0]

def get_cotas_normalizadas(df: pd.DataFrame) -> pd.DataFrame:
    valor_inicial = _get_valores_iniciais(df)
    cotas_normalizadas = df/valor_inicial
    return cotas_normalizadas

def get_benchmarks(data_inicio: str, data_fim: str, proxies: Union[Dict[str, str], None] = None, benchmark: str="cdi") -> pd.DataFrame:
    if benchmark.upper()=="CDI":
        df_benchmark = get_selic(data_inicio, data_fim, proxies)
        df_benchmark.columns = [benchmark.upper()]
    else:
        df_benchmark, _ = get_benchmark(data_inicio, 
                                        data_fim, 
                                        benchmark = benchmark.upper(), proxy=proxies)
        df_benchmark.columns = [benchmark.upper()]
    return df_benchmark

def calcula_retorno(df: pd.DataFrame, fundo: List[str], HP: int, benchmark: pd.DataFrame) -> pd.DataFrame:
    cotas_normalizadas = get_cotas_normalizadas(df[fundo])
    retorno_cotas_normalizadas = pd.concat([cotas_normalizadas, benchmark], axis=1)
    retorno_cotas_normalizadas = retorno_cotas_normalizadas.pct_change(HP)
    return retorno_cotas_normalizadas

def fundos_eficientes(df: pd.DataFrame, fundos: List[str], HP: int, benchmarks: pd.DataFrame) -> pd.DataFrame:
    melhores = pd.DataFrame()
    for fundo in fundos:
        retorno = calcula_retorno(df, fundo, HP, benchmarks)
        df2 = pd.DataFrame()
        for benc in benchmarks.columns:
            retorno[f"Bateu {benc}"] = np.where(retorno[fundo]>retorno[benc], 1, 0)
            df1 = pd.DataFrame({"Fundo": [fundo],
                               f"Num. vezes superou {benc}": [retorno[f"Bateu {benc}"].sum()]}).set_index("Fundo")
            df1[f"Eficiência {benc} (%)"] = 100*(df1[f"Num. vezes superou {benc}"]/retorno.dropna().shape[0])
            df2 = pd.concat([df1, df2], axis=1)    
        melhores = pd.concat([melhores, df2])
    return melhores
    
def calcula_rentabilidade_fundos(
    dados_fundos_cvm: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fundo_acoes_filtrado_transformed = dados_fundos_cvm.copy()
    #fundo_acoes_filtrado_transformed = copia.pivot_table(
    #    index="DT_COMPTC", columns="CNPJ - Nome", values="VL_QUOTA"
    #)
    #fundo_acoes_filtrado_transformed.index = pd.to_datetime(fundo_acoes_filtrado_transformed.index)
    #fundo_acoes_filtrado_transformed = fundo_acoes_filtrado_transformed.sort_index()

    cotas_normalizadas = (fundo_acoes_filtrado_transformed/ _get_valores_iniciais(fundo_acoes_filtrado_transformed))

    rentabilidade_fundos_diaria = fundo_acoes_filtrado_transformed.pct_change()

    rentabilidade_fundos_acumulada = (1 + rentabilidade_fundos_diaria).cumprod() - 1
    rentabilidade_fundos_total = rentabilidade_fundos_acumulada.iloc[-1].to_frame()
    rentabilidade_fundos_total.columns = ["rentabilidade"]

    rentabilidade_media_anualizada = (rentabilidade_fundos_diaria * (252)).mean(axis=0).dropna().to_frame()
    rentabilidade_media_anualizada.columns = ["rentabilidade"]

    T = fundo_acoes_filtrado_transformed.shape[0]
    retorno_periodo_anualizado = (((fundo_acoes_filtrado_transformed.iloc[-1]/ _get_valores_iniciais(fundo_acoes_filtrado_transformed))** (252 / T)- 1)).dropna().to_frame()
    retorno_periodo_anualizado.columns = ["rentabilidade"]

    rentabilidade_acumulada_por_ano = (rentabilidade_fundos_acumulada.groupby(pd.Grouper(freq="Y")).last(1).T.dropna())
    rentabilidade_acumulada_por_ano.columns = [str(x)[:4] for x in rentabilidade_acumulada_por_ano.columns]

    volatilidade_fundos = rentabilidade_fundos_diaria.std().dropna().to_frame() * np.sqrt(252)
    volatilidade_fundos.columns = ["volatilidade"]

    risco_retorno = pd.concat([volatilidade_fundos, retorno_periodo_anualizado], axis=1)
    return (
            risco_retorno.dropna() * 100,
            cotas_normalizadas * 100,
            rentabilidade_media_anualizada * 100,
            rentabilidade_acumulada_por_ano * 100,
            rentabilidade_fundos_total * 100,
            )

def melhores_e_piores_fundos(
                            df: pd.DataFrame, num: int = 5
                            ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    return df.nlargest(num, df.columns[0]), df.nsmallest(num, df.columns[0])

def remove_outliers(df: pd.DataFrame, col: str, q: float = 0.05) -> pd.DataFrame:
    df1 = df.copy()
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
    plt.box(False)
    plt.grid(True, axis="y")
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
        plt.grid(True, axis="y")
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
        plt.grid(True, axis="y")
        plt.ylim(opcionais.get("ylim"))
        plt.xlim(opcionais.get("xlim"))
        return data
    elif not colunas:
        print("Fundo não encontrado")
        return None

def plotar_rentabilidade_janela_movel(df, fundos, HP, benchmarks):
    for fundo in fundos:
        retorno = calcula_retorno(df, fundo, HP, benchmarks)
        
        plt.figure(figsize=(15, 6))
        cols = [fundo] + benchmarks.columns.tolist()
        plt.suptitle(f"Retorno de {HP} dias")
        plt.plot(retorno[cols].multiply(100))
        plt.xticks(rotation=45)
        plt.xlabel('')
        plt.ylabel("%", rotation=0, labelpad=-15, loc="top")
        plt.legend([fundo.split("//")[-1]]+benchmarks.columns.tolist(), loc="upper right", frameon=False,
                     bbox_to_anchor=(0.5, 0.67, 0.5, 0.5))
        plt.tight_layout()
        plt.box(False)
        plt.grid(axis="x")
    plt.show()