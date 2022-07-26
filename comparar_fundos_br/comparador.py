# -*- coding: utf-8 -*-
"""
@author: Rafael
"""
import warnings
from typing import Any, List, Tuple, Union

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)

import seaborn as sns; sns.set()
import matplotlib.pyplot as plt


def calcula_rentabilidade_fundos(
    dados_fundos_cvm: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    copia = dados_fundos_cvm.copy()
    fundo_acoes_filtrado_transformed = copia.pivot_table(
        index="DT_COMPTC", columns="CNPJ - Nome", values=["VL_QUOTA", "VL_PATRIM_LIQ"]
    )
    fundo_acoes_filtrado_transformed.index = pd.to_datetime(fundo_acoes_filtrado_transformed.index)
    fundo_acoes_filtrado_transformed = fundo_acoes_filtrado_transformed.sort_index()

    cotas_normalizadas = (fundo_acoes_filtrado_transformed["VL_QUOTA"]/ fundo_acoes_filtrado_transformed["VL_QUOTA"].iloc[0])

    rentabilidade_fundos_diaria = fundo_acoes_filtrado_transformed["VL_QUOTA"].pct_change()

    rentabilidade_fundos_acumulada = (1 + rentabilidade_fundos_diaria).cumprod() - 1
    rentabilidade_fundos_total = rentabilidade_fundos_acumulada.iloc[-1].to_frame()
    rentabilidade_fundos_total.columns = ["rentabilidade"]

    rentabilidade_media_anualizada = (rentabilidade_fundos_diaria * (252)).mean(axis=0).dropna().to_frame()
    rentabilidade_media_anualizada.columns = ["rentabilidade"]

    T = fundo_acoes_filtrado_transformed.shape[0]
    retorno_periodo_anualizado = (((fundo_acoes_filtrado_transformed["VL_QUOTA"].iloc[-1]/ fundo_acoes_filtrado_transformed["VL_QUOTA"].iloc[0])** (252 / T)- 1)* 100).dropna().to_frame()
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
                            df: pd.DataFrame(), num: int = 5
                            ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    return df.nlargest(num, df.columns[0]), df.nsmallest(num, df.columns[0])


def plotar_comparacao_risco_retorno(
                                    df: pd.DataFrame(),
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
                    df: pd.DataFrame(), lista_fundos: List[str], **opcionais: Any
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