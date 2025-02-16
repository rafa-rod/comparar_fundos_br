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
import tesouro_direto_br as tesouro_direto

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)

import seaborn as sns; sns.set()
import matplotlib.pyplot as plt

def get_selic(inicio: str, fim: str, proxies: Union[Dict[str, str], None] = None) -> pd.DataFrame:
    titulos_ofertados = tesouro_direto.busca_tesouro_direto(tipo="taxa", proxies=proxies, agrupar=True).reset_index()

    excluir = ["Juros Semestrais", "Renda+", "Educa+"]
    titulos_ofertados_filtrado = titulos_ofertados[(titulos_ofertados["Data Base"]>=inicio) &
                                       (titulos_ofertados["Data Base"]<fim) &
                                       (~titulos_ofertados["Tipo Titulo"].str.contains("&".join(excluir)))].set_index(["Tipo Titulo",
                                                                                        "Data Vencimento"])
    selic = titulos_ofertados_filtrado.loc[["Tesouro Selic"], :].sort_values("Data Base", ascending=False)
    selic_longa = selic.reset_index().groupby(["Data Base"])[["Data Vencimento", 
                                                'Taxa Compra Manha', 'Taxa Venda Manha', 
                                                'PU Compra Manha', 'PU Venda Manha', 'PU Base Manha']].max()
    return selic_longa[["PU Base Manha"]]

def get_ibovespa(
            data_inicio: str, 
            data_fim: str, 
            proxy: Union[Dict[str, str], None] = None
            ) -> pd.DataFrame:
    if proxy:
        indice_ibov = yf.download("^BVSP", start=data_inicio, end=data_fim, proxy=proxy)
    else:
        indice_ibov = yf.download("^BVSP", start=data_inicio, end=data_fim)
    indice_ibov = indice_ibov[["Close"]]
    retorno_ibov = indice_ibov.pct_change()
    indice_ibov_acumulado = (1 + retorno_ibov).cumprod()
    indice_ibov_acumulado.iloc[0] = 1
    indice_ibov_acumulado.index = pd.to_datetime(indice_ibov_acumulado.index)
    indice_ibov.index = pd.to_datetime(indice_ibov.index)
    return indice_ibov, indice_ibov_acumulado

def get_benchmark(
            data_inicio: str, 
            data_fim: str,
            benchmark: str = "cdi",
            proxy: Union[Dict[str, str], None] = None
            ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if benchmark.upper()=="CDI":
        dados_benchmark = get_selic(data_inicio, data_fim, proxy)
        dados_benchmark = dados_benchmark.reset_index()
        dados_benchmark.columns = ["data","CDI"]
    elif benchmark.upper()=="IMA-B": codigo_bcb = 12466
    elif benchmark.upper()=="IMA-B 5": codigo_bcb = 12467
    elif benchmark.upper()=="IMA-B 5+": codigo_bcb = 12468
    elif benchmark.upper()=="IBOV":
        indice_ibov, indice_ibov_acumulado = get_ibovespa(data_inicio, data_fim, proxy)
        return indice_ibov, indice_ibov_acumulado
    else: raise ValueError("Benchmark não encontrado.")
    if benchmark.upper()!="CDI":
        url = (
            f"http://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bcb}/dados?formato=json"
            )
        if proxy:
            dados_cvm = requests.get(url, proxies=proxy, verify=False).text
        else:
            dados_cvm = requests.get(url).text
        try:
            dados_benchmark = pd.read_json(io.StringIO(dados_cvm))
        except ValueError:
            raise ValueError('Dados não disponíveis')
    dados_benchmark["data"] = pd.to_datetime(dados_benchmark["data"], dayfirst=True)
    dados_benchmark = dados_benchmark.set_index("data")
    dados_benchmark = dados_benchmark[(dados_benchmark.index>=data_inicio) & (dados_benchmark.index<=data_fim)] / 100
    dados_benchmark.columns = [f"{benchmark.upper()}"]
    dados_benchmark_acumulado = (1 + dados_benchmark).cumprod()
    dados_benchmark_acumulado.columns = [f"{benchmark.upper()}"]
    dados_benchmark_acumulado.iloc[0] = 1
    return dados_benchmark, dados_benchmark_acumulado

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
            if not st.endswith(".SA"): st = st+".SA"
            if proxy:
                df = yf.download(st, start=data_inicio, end=data_fim, proxy=proxy)
            else:
                df = yf.download(st, start=data_inicio, end=data_fim)
            df1 = pd.concat([df, df1], axis=1)
    else:
        if not acoes.endswith(".SA"): acoes = acoes+".SA"
        if proxy:
            df1 = yf.download(acoes, start=data_inicio, end=data_fim, proxy=proxy)
        else:
            df1 = yf.download(acoes, start=data_inicio, end=data_fim)
    df1.index = pd.to_datetime(df1.index)
    return df1