# -*- coding: utf-8 -*-
"""
@author: Rafael
"""
import io
import warnings
from typing import Dict, List, Tuple, Union, Optional

import pandas as pd
import polars as pl
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

def get_cdi(inicio: str, fim: str, metodo_cdi: str ='bacen',  proxies: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    '''Função que provê o retorno do CDI usada como referência especialmente para Renda Fixa.
    Esta função usa os métodos: tesouro, anbima ou bacen para extrair a rentabilidade.
    Tesouro = usa-se o rendimento diário dos titulos Tesouro Selic de vencimentos mais longos;
    Anbima = usa-se o índice IMA-S que usa rendimentos de Tesouro Selic;
    BACEN = usa-se a série diária do CDI.
    As datas devem ser no formato string '2025-01-02', ou seja, 'ANO-MES-DIA'.
    A saída gera o retorno diário e o acumulado.
    Os valores resultantes são próximos, mas não iguais. Divergem em função da metodologia.'''
    if metodo_cdi.lower()=='tesouro':
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
        cdi = selic_longa[["PU Base Manha"]]
        cdi.columns = ['CDI']
        cdi['Retorno CDI'] = cdi["CDI"].pct_change()
        cdi['Retorno Acumulado CDI'] = (1+cdi['Retorno CDI']).cumprod()-1
    elif metodo_cdi.lower()=='anbima':
        imas = pl.read_excel('https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IMAS-HISTORICO.xls',
                             engine='calamine', columns=[1,2])
        imas = imas.filter((pl.col('Data de Referência')>=pd.to_datetime(inicio)) & (pl.col('Data de Referência')<=pd.to_datetime(fim)))
        imas = imas.rename({'Número Índice': 'CDI'})
        imas = imas.with_columns(pl.col('CDI').pct_change().alias("Retorno CDI"))
        imas = imas.with_columns(((pl.col('Retorno CDI')+1).cum_prod()-1).alias("Retorno Acumulado CDI"))
        cdi = imas.to_pandas().set_index('Data de Referência')
    elif metodo_cdi.lower()=="bacen":
        codigo_bcb = 12
        anoi, mesi, diai = inicio.split('-')
        anof, mesf, diaf = fim.split('-')
        iniciob = '/'.join([diai, mesi, anoi])
        fimb = '/'.join([diaf, mesf, anof])
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bcb}/dados?formato=json&dataInicial={iniciob}&dataFinal={fimb}"
        if proxies:
            dados_bacen = requests.get(url, proxies=proxies, verify=False).text
        else:
            dados_bacen = requests.get(url).text
        cdi = pd.read_json(io.StringIO(dados_bacen))
        cdi["data"] = pd.to_datetime(cdi["data"], dayfirst=True)
        cdi = cdi.set_index("data")
        cdi = cdi[(cdi.index>=inicio) & (cdi.index<=fim)] / 100
        cdi.columns = ['CDI']
        cdi['Retorno CDI'] = cdi["CDI"]
        cdi['Retorno Acumulado CDI'] = (1+cdi['Retorno CDI']).cumprod()-1
    else:
        raise ValueError("Método não permitido")
    return cdi

def get_indices_anbima(data_inicio: str, data_fim: str, benchmark: str = "imas") -> pd.DataFrame:
    '''Função que provê o retorno de alguns indices ANBIMA usada como referência, especialmente para Renda Fixa.
    Esta função implementa os seguintes índices: 
    -IMA-S (imas);
    -IMA-B5 (imab5);
    -IMA-B5+ (imab5+)
    -IMA-B5 P2 (imab5p2);
    -IRFM (irfm);
    -IRFM P2 (irfmp2);
    -IHFA (ihfa).
    As datas devem ser no formato string '2025-01-02', ou seja, 'ANO-MES-DIA'.
    Mais informações em https://data.anbima.com.br/indices'''
    if benchmark.lower()=="imas":
        indice = pl.read_excel('https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IMAS-HISTORICO.xls',
                             engine='calamine', columns=[1,2])
    elif benchmark.lower()=="imab5":
        indice = pl.read_excel('https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IMAB5-HISTORICO.xls',
                     engine='calamine', columns=[1,2])
    elif benchmark.lower()=="imab5+":
        indice = pl.read_excel('https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IMAB5MAIS-HISTORICO.xls',
                     engine='calamine', columns=[1,2])
    elif benchmark.lower()=="imab5p2":
        indice = pl.read_excel('https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IMAB5P2-HISTORICO.xls',
                     engine='calamine', columns=[1,2])
    elif benchmark.lower()=="irfm":
        indice = pl.read_excel('https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IRFM-HISTORICO.xls',
                     engine='calamine', columns=[1,2])
    elif benchmark.lower()=="irfmp2":
        indice = pl.read_excel('https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IRFMP2-HISTORICO.xls',
                     engine='calamine', columns=[1,2])
    elif benchmark.lower()=="ihfa":
        indice = pl.read_excel('https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IHFA-HISTORICO.xls',
                     engine='calamine', columns=[1,2])
    else:
        raise ValueError('Benchmark não encontrado.')
    indice = indice.filter((pl.col('Data de Referência')>=pd.to_datetime(data_inicio)) & (pl.col('Data de Referência')<=pd.to_datetime(data_fim)))
    indice = indice.rename({'Número Índice': benchmark.upper()})
    return indice.to_pandas().set_index('Data de Referência')

def get_benchmarks(data_inicio: str, data_fim: str, benchmark: str = "CDI", metodo_cdi = 'bacen', proxy=None) -> pd.DataFrame:
    '''Função que provê o retorno de alguns indices ANBIMA, CDI e renda variável: ibov, divo11 (similar ao IDIV) e sp500.
    Esta função implementa os seguintes índices anbima: 
    -IMA-S (imas);
    -IMA-B5 (imab5);
    -IMA-B5+ (imab5+)
    -IMA-B5 P2 (imab5p2);
    -IRFM (irfm);
    -IRFM P2 (irfmp2);
    -IHFA (ihfa).
    As datas devem ser no formato string '2025-01-02', ou seja, 'ANO-MES-DIA'.
    A saída gera o retorno diário e o acumulado.'''
    if benchmark.upper()=="CDI":
        df_benchmark = get_cdi(data_inicio, data_fim, metodo_cdi, proxy)
    else:
        if benchmark.upper()=="IBOV":
            df_benchmark = yf.download("^BVSP", start=data_inicio, end=data_fim, interval="1d", proxy=proxy)["Close"]
            df_benchmark.columns = ["IBOV"]
        elif benchmark.upper()=="DIVO11":
            df_benchmark = yf.download("DIVO11.SA", start=data_inicio, end=data_fim, interval="1d", proxy=proxy)["Close"]
            df_benchmark.columns = ["DIVO11"]
        elif benchmark.upper()=="SP500":
            df_benchmark = yf.download("^GSPC", start=data_inicio, end=data_fim, interval="1d", proxy=proxy)["Close"]
            df_benchmark.columns = ["SP500"]
        else:
            df_benchmark = get_indices_anbima(data_inicio, data_fim, benchmark)
        df_benchmark[f'Retorno {benchmark.upper()}'] = df_benchmark[benchmark.upper()].pct_change()
        df_benchmark[f'Retorno Acumulado {benchmark.upper()}'] = (1+df_benchmark[f'Retorno {benchmark.upper()}']).cumprod()-1
    return df_benchmark

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
                df = yf.download(st, start=data_inicio, end=data_fim, proxy=proxy)['Adj Close']
            else:
                df = yf.download(st, start=data_inicio, end=data_fim)['Adj Close']
            df1 = pd.concat([df, df1], axis=1)
    else:
        if not acoes.endswith(".SA"): acoes = acoes+".SA"
        if proxy:
            df1 = yf.download(acoes, start=data_inicio, end=data_fim, proxy=proxy)['Adj Close']
        else:
            df1 = yf.download(acoes, start=data_inicio, end=data_fim)['Adj Close']
    df1.index = pd.to_datetime(df1.index)
    for cols in df1.columns:
        df1[f'Retorno {cols}'] = df1[cols].pct_change()
        df1[f'Retorno Acumulado {cols}'] = (1+df1[f'Retorno {cols}']).cumprod()-1
    return df1