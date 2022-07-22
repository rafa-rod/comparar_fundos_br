# -*- coding: utf-8 -*-
"""
@author: Rafael
"""
import io
import warnings
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd
import requests
import yfinance as yf

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)


def get_cdi(
            data_inicio: str, 
            data_fim: str, 
            proxy: Union[Dict[str, str], None] = None
            ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    codigo_bcb = 12
    url = (
        f"http://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bcb}/dados?formato=json"
    )
    if proxy:
        dados_cvm = requests.get(url, proxies=proxy, verify=False).text
        cdi = pd.read_json(io.StringIO(dados_cvm))
    cdi["data"] = pd.to_datetime(cdi["data"], dayfirst=True)
    cdi = cdi.set_index("data")
    cdi = cdi[data_inicio:data_fim] / 100
    cdi.columns = ["CDI"]
    cdi_acumulado = (1 + cdi).cumprod() - 1
    # cdi_acumulado.iloc[0] = 1
    cdi_acumulado.columns = ["CDI"]
    return cdi, cdi_acumulado


import getpass
import os

user = os.getenv("userid").lower()  # getpass.getuser().lower()
pwd = getpass.getpass(prompt="Senha: ")
proxies = {
    "http": f"http://{user}:{pwd}@proxy.inf.bndes.net:8080",
    "https": f"https://{user}:{pwd}@proxy.inf.bndes.net:8080",
}

data_inicio = "2018-01-01"
data_fim = "2022-07-19"
cdi, cdi_acumulado = get_cdi(data_inicio, data_fim, proxy=proxies)
cota_cdi = (cdi["CDI"] / cdi["CDI"].iloc[0]) * 100

ret_cdi = cdi.pct_change().dropna()
retorno_acumulado = ((1 + ret_cdi).cumprod() - 1) * 100  # idem cota, mas significa que subiu x vezes o valor inicial. a cota compara com valor inicial de 100.

T = cdi.shape[0]
retorno_periodo_anualizado_cdi = ((cdi["CDI"].iloc[-1] / cdi["CDI"].iloc[0]) ** (252 / T) - 1) * 100
rentabilidade_fundos_acumulada = ((cdi.iloc[-1].values[0])) * 100
volatilidade_cdi = ret_cdi.std().dropna().values[0] * np.sqrt(252) * 100


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
    return indice_ibov
