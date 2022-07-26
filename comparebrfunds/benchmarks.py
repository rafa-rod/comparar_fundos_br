# -*- coding: utf-8 -*-
"""
@author: Rafael
"""
import io
import warnings
from typing import Dict, List, Tuple, Union

import pandas as pd
import requests
import yfinance as yf

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)

import seaborn as sns

sns.set()
import matplotlib.pyplot as plt


def get_cdi(
            data_inicio: str, 
            data_fim: str,
            benchmark: str = "cdi",
            proxy: Union[Dict[str, str], None] = None
            ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if benchmark.upper()=="CDI": codigo_bcb = 12
    elif benchmark.upper()=="IMA-B": codigo_bcb = 12466
    elif benchmark.upper()=="IMA-B 5": codigo_bcb = 12467
    elif benchmark.upper()=="IMA-B 5+": codigo_bcb = 12468
    url = (
        f"http://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bcb}/dados?formato=json"
    )
    if proxy:
        dados_cvm = requests.get(url, proxies=proxy, verify=False).text
    else:
        dados_cvm = requests.get(url).text
    dados_benchmark = pd.read_json(io.StringIO(dados_cvm))       
    dados_benchmark["data"] = pd.to_datetime(dados_benchmark["data"], dayfirst=True)
    dados_benchmark = dados_benchmark.set_index("data")
    dados_benchmark = dados_benchmark[data_inicio:data_fim] / 100
    dados_benchmark.columns = ["CDI"]
    dados_benchmark_acumulado = (1 + dados_benchmark).cumprod()
    dados_benchmark_acumulado.columns = ["CDI"]
    dados_benchmark_acumulado.iloc[0] = 1
    return dados_benchmark, dados_benchmark_acumulado


# import getpass
# import os

# user = os.getenv("userid").lower()  # getpass.getuser().lower()
# pwd = getpass.getpass(prompt="Senha: ")
# proxies = {
#     "http": f"http://{user}:{pwd}@proxy.inf.bndes.net:8080",
#     "https": f"https://{user}:{pwd}@proxy.inf.bndes.net:8080",
# }

# df = pd.read_csv("/Users/Rafael/Desktop/cotas_normalizadas.csv",index_col=0)

# data_inicio = df.index[0]
# data_fim = df.index[-1]
# cdi, cdi_acumulado = get_cdi(data_inicio, data_fim, proxy=None)
# cota_cdi = (cdi["CDI"] / cdi["CDI"].iloc[0]) * 100

# data = plotar_evolucao(
#                 df,
#                 lista_fundos=["XP "],
#                 figsize=(15, 5),
#                 ylim=(0, 380),
#                 color="gray",
#                 alpha=0.2,
#                 color_maximo="orange",
#                 color_minimo="red",
#                 color_seta_maximo="orange",
#                 color_seta_minimo="red",
#                 posicao_texto_maximo=(10, 17),
#                 posicao_texto_minimo=(10, -20),
#                 )
# plt.plot(cota_cdi)
# plt.title("Evolução dos Fundos")
# plt.show()

# ret_cdi = cdi.pct_change().dropna()
# retorno_acumulado = ((1 + ret_cdi).cumprod() - 1) * 100  # idem cota, mas significa que subiu x vezes o valor inicial. a cota compara com valor inicial de 100.

# T = cdi.shape[0]
# retorno_periodo_anualizado_cdi = ((cdi["CDI"].iloc[-1] / cdi["CDI"].iloc[0]) ** (252 / T) - 1) * 100
# rentabilidade_fundos_acumulada = ((cdi.iloc[-1].values[0])) * 100
# volatilidade_cdi = ret_cdi.std().dropna().values[0] * np.sqrt(252) * 100


def get_stocks(
                acoes: Union[List[str], str],
                data_inicio: str,
                data_fim: str,
                proxy: Union[Dict[str, str], None] = None,
                ) -> pd.DataFrame:
    """Função para capturar dados de Ações ou Índices Listados.
    """
    df1 = pd.DataFrame()
    if isinstance(acoes, list):
        for st in acoes:
            if proxy:
                df = yf.download(st, start=data_inicio, end=data_fim, proxy=proxy)
            else:
                df = yf.download(st, start=data_inicio, end=data_fim)
            df1 = pd.concat([df, df1], axis=1)
    else:
        if proxy:
            df = yf.download(st, start=data_inicio, end=data_fim, proxy=proxy)
        else:
            df = yf.download(st, start=data_inicio, end=data_fim)
    return df1


def get_ibovespa(
            data_inicio: str, 
            data_fim: str, 
            proxy: Union[Dict[str, str], None] = None
            ) -> pd.DataFrame:
    if proxy:
        indice_ibov = yf.download("^BVSP", start=data_inicio, end=data_fim, proxy=proxy)
    else:
        indice_ibov = yf.download("^BVSP", start=data_inicio, end=data_fim)
    indice_ibov = indice_ibov[["Adj Close"]]
    retorno_ibov = indice_ibov.pct_change()
    indice_ibov_acumulado = (1 + retorno_ibov).cumprod()
    indice_ibov_acumulado.iloc[0] = 1
    indice_ibov_acumulado.index = pd.to_datetime(indice_ibov_acumulado.index)
    indice_ibov.index = pd.to_datetime(indice_ibov.index)
    return indice_ibov, indice_ibov_acumulado

# dados_benchmark, dados_benchmark_acumulado = get_cdi(data_inicio="2018-01-01",
#                                                      data_fim="2022-07-22",
#                                                      benchmark="cdi")
# indice_ibov, indice_ibov_acumulado = get_ibovespa(data_inicio="2018-01-01",
#                                                   data_fim="2022-07-22")
# plt.figure(figsize=(15,5))
# plt.plot(indice_ibov_acumulado*100)
# plt.plot(dados_benchmark_acumulado*100)
# plt.box(False)
# plt.grid(axis="y")
# plt.show()