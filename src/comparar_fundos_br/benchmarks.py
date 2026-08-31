"""
@author: Rafael
"""

import io
import warnings
from io import BytesIO

import pandas as pd
import polars as pl
import requests
import tesouro_direto_br as tesouro_direto
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import time

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)

import seaborn as sns

sns.set_theme()


def get_cdi(
    inicio: str,
    fim: str,
    metodo_cdi: str = "bacen",
    proxies: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Função que provê o retorno do CDI usada como referência especialmente para Renda Fixa.
    Esta função usa os métodos: tesouro, anbima ou bacen para extrair a rentabilidade.
    Tesouro = usa-se o rendimento diário dos titulos Tesouro Selic de vencimentos mais longos;
    Anbima = usa-se o índice IMA-S que usa rendimentos de Tesouro Selic;
    BACEN = usa-se a série diária do CDI.
    As datas devem ser no formato string '2025-01-02', ou seja, 'ANO-MES-DIA'.
    A saída gera o retorno diário e o acumulado.
    Os valores resultantes são próximos, mas não iguais. Divergem em função da metodologia."""
    if metodo_cdi.lower() == "tesouro":
        titulos_ofertados = tesouro_direto.busca_tesouro_direto(
            tipo="taxa", proxies=proxies, agrupar=True
        ).reset_index()

        excluir = ["Juros Semestrais", "Renda+", "Educa+"]
        titulos_ofertados_filtrado = titulos_ofertados[
            (titulos_ofertados["Data Base"] >= inicio)
            & (titulos_ofertados["Data Base"] < fim)
            & (~titulos_ofertados["Tipo Titulo"].str.contains("&".join(excluir)))
        ].set_index(["Tipo Titulo", "Data Vencimento"])
        selic = titulos_ofertados_filtrado.loc[["Tesouro Selic"], :].sort_values("Data Base", ascending=False)
        selic_longa = (
            selic.reset_index()
            .groupby(["Data Base"])[
                [
                    "Data Vencimento",
                    "Taxa Compra Manha",
                    "Taxa Venda Manha",
                    "PU Compra Manha",
                    "PU Venda Manha",
                    "PU Base Manha",
                ]
            ]
            .max()
        )
        cdi = selic_longa[["PU Base Manha"]]
        cdi.columns = ["CDI"]
        cdi["Retorno CDI"] = cdi["CDI"].pct_change()
        cdi["Retorno Acumulado CDI"] = (1 + cdi["Retorno CDI"]).cumprod() - 1
    elif metodo_cdi.lower() == "anbima":
        imas = pl.read_excel(
            "https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/IMAS-HISTORICO.xls",
            engine="calamine",
            columns=[1, 2],
        )
        imas = imas.filter(
            (pl.col("Data de Referência") >= pd.to_datetime(inicio))
            & (pl.col("Data de Referência") <= pd.to_datetime(fim))
        )
        imas = imas.rename({"Número Índice": "CDI"})
        imas = imas.with_columns(pl.col("CDI").pct_change().alias("Retorno CDI"))
        imas = imas.with_columns(((pl.col("Retorno CDI") + 1).cum_prod() - 1).alias("Retorno Acumulado CDI"))
        cdi = imas.to_pandas().set_index("Data de Referência")
    elif metodo_cdi.lower() == "bacen":
        codigo_bcb = 12
        anoi, mesi, diai = inicio.split("-")
        anof, mesf, diaf = fim.split("-")
        iniciob = "/".join([diai, mesi, anoi])
        fimb = "/".join([diaf, mesf, anof])
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bcb}/dados?formato=json&dataInicial={iniciob}&dataFinal={fimb}"
        if proxies:
            dados_bacen = requests.get(url, proxies=proxies, verify=False).text
        else:
            dados_bacen = requests.get(url).text
        cdi = pd.read_json(io.StringIO(dados_bacen))
        cdi["data"] = pd.to_datetime(cdi["data"], dayfirst=True)
        cdi = cdi.set_index("data")
        cdi = cdi[(cdi.index >= inicio) & (cdi.index <= fim)] / 100
        cdi.columns = ["CDI"]
        cdi["Retorno CDI"] = cdi["CDI"]
        cdi["Retorno Acumulado CDI"] = (1 + cdi["Retorno CDI"]).cumprod() - 1
    else:
        raise ValueError("Método não permitido")
    return cdi


def get_indices_anbima(
    data_inicio: str,
    data_fim: str,
    benchmark: str = "imas",
    proxy: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Função que provê o retorno de alguns indices ANBIMA usada como referência, especialmente para Renda Fixa.
    Esta função implementa os seguintes índices:
    -IMA-S (imas);
    -IMA-B (imab);
    -IMA-B5 (imab5);
    -IMA-B5+ (imab5+)
    -IMA-B5 P2 (imab5p2);
    -IRFM (irfm);
    -IRFM P2 (irfmp2);
    -IHFA (ihfa);
    -IDA-DI (ida-di);
    -IDA-IPCA (ida-ipca);
    -IDA-GERAL (ida-geral);
    As datas devem ser no formato string '2025-01-02', ou seja, 'ANO-MES-DIA'.
    Mais informações em https://data.anbima.com.br/indices"""

    BASE_ANBIMA = "https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/{arquivo}"

    ARQUIVOS_ANBIMA = {
        "imas": "IMAS-HISTORICO.xls",
        "imab": "IMAB-HISTORICO.xls",
        "imab5": "IMAB5-HISTORICO.xls",
        "imab5+": "IMAB5MAIS-HISTORICO.xls",
        "imab5p2": "IMAB5P2-HISTORICO.xls",
        "irfm": "IRFM-HISTORICO.xls",
        "irfmp2": "IRFMP2-HISTORICO.xls",
        "ihfa": "IHFA-HISTORICO.xls",
        "ida-di": "IDADI-HISTORICO.xls",  # debentures indexadas ao DI
        "ida-ipca": "IDAIPCA-HISTORICO.xls",  # debentures indexadas ao IPCA
        "ida-geral": "IDAGERAL-HISTORICO.xls",
    }

    def check_proxy(url, proxy):
        response = requests.get(url, proxies=proxy, stream=True)
        response.raise_for_status()
        file_like_object = BytesIO(response.content)
        return file_like_object

    chave = benchmark.lower().strip()
    if chave in ARQUIVOS_ANBIMA:
        encontrado = [ARQUIVOS_ANBIMA[chave]]
        for arquivo in encontrado:
            url = BASE_ANBIMA.format(arquivo=arquivo)
            file_object = check_proxy(url, proxy)
    else:
        raise ValueError(f"Benchmark não encontrado: {chave}")

    indice = pl.read_excel(file_object, engine="calamine", columns=[1, 2])
    indice = indice.filter(
        (pl.col("Data de Referência") >= pd.to_datetime(data_inicio))
        & (pl.col("Data de Referência") <= pd.to_datetime(data_fim))
    )
    indice = indice.rename({"Número Índice": benchmark.upper()})
    return indice.to_pandas().set_index("Data de Referência")


def get_benchmarks(
    data_inicio: str,
    data_fim: str,
    benchmark: str = "CDI",
    metodo_cdi: str = "bacen",
    compra: bool = False,
    proxy: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Função que provê o retorno de alguns indices ANBIMA, CDI e renda variável: ibov, divo11 (similar ao IDIV) e sp500.
    Esta função implementa os seguintes índices anbima:
    -IMA-S (imas);
    -IMA-B5 (imab5);
    -IMA-B5+ (imab5+)
    -IMA-B5 P2 (imab5p2);
    -IRFM (irfm);
    -IRFM P2 (irfmp2);
    -IHFA (ihfa);
    -IDA-DI (ida-di);
    -IDA-IPCA (ida-ipca);
    -IDA-GERAL (ida-geral).
    As datas devem ser no formato string '2025-01-02', ou seja, 'ANO-MES-DIA'.
    A saída gera o retorno diário e o acumulado."""
    if proxy:
        yf.set_config(proxy=proxy)
    if benchmark.upper() == "CDI":
        df_benchmark = get_cdi(data_inicio, data_fim, metodo_cdi, proxy)
    else:
        if benchmark.upper() == "IBOV":
            df_benchmark = yf.download(
                "^BVSP",
                start=data_inicio,
                end=data_fim,
                interval="1d",
                auto_adjust=True,
            )["Close"]
            df_benchmark.columns = ["IBOV"]
        elif benchmark.upper() == "DIVO11":
            df_benchmark = yf.download(
                "DIVO11.SA",
                start=data_inicio,
                end=data_fim,
                interval="1d",
                auto_adjust=True,
            )["Close"]
            df_benchmark.columns = ["DIVO11"]
        elif benchmark.upper() == "SP500":
            df_benchmark = yf.download(
                "^GSPC",
                start=data_inicio,
                end=data_fim,
                interval="1d",
                auto_adjust=True,
            )["Close"]
            df_benchmark.columns = ["SP500"]
        elif benchmark.upper() == "USD":
            df_benchmark = yf.download(
                "BRL=X",
                start=data_inicio,
                end=data_fim,
                interval="1d",
                auto_adjust=True,
            )["Close"]
            df_benchmark.columns = ["USD"]
        elif benchmark.upper() == "PTAX":
            df_benchmark = get_cambio_ptax(data_inicio, data_fim, compra=compra)
            df_benchmark.columns = ["PTAX"]
        else:
            df_benchmark = get_indices_anbima(data_inicio, data_fim, benchmark, proxy)
        df_benchmark[f"Retorno {benchmark.upper()}"] = df_benchmark[benchmark.upper()].pct_change()
        df_benchmark[f"Retorno Acumulado {benchmark.upper()}"] = (
            1 + df_benchmark[f"Retorno {benchmark.upper()}"]
        ).cumprod() - 1
    return df_benchmark

def get_cambio_ptax(
    data_inicio: str,
    data_fim: str,
    compra: bool = False,
    proxy: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Usa dados do Sistema de Gestao de Series do Banco Central:
    https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries
    para obter os dados do dólar oficial (PTAX, fonte Sisbacen PTAX800) fazendo requisicoes em janelas de ate 10 anos.

    Se desejar valores de venda, colocar compra = False e para compra, compra = True.
    """
    if isinstance(data_inicio, str):
        inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
    else:
        inicio = data_inicio
    if isinstance(data_fim, str):
        fim = datetime.strptime(data_fim, '%Y-%m-%d')
    else:
        fim = data_fim

    codigo_bcb = 10813 if compra else 1

    todos_dados = []
    data_atual = inicio
    while data_atual <= fim:
        data_limite = min(data_atual + timedelta(days=365 * 10 - 1), fim)
        inicio_str = data_atual.strftime('%d/%m/%Y')
        fim_str = data_limite.strftime('%d/%m/%Y')

        url = (
            f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bcb}/dados'
            f'?formato=json&dataInicial={inicio_str}&dataFinal={fim_str}'
        )
        try:
            if proxy:
                response = requests.get(url, proxies=proxy, timeout=30, verify=False)
            else:
                response = requests.get(url, timeout=30)
            dados = response.json()
            if dados and isinstance(dados, list):
                todos_dados.extend(dados)
                print(f"Baixados dados de {inicio_str} a {fim_str}: {len(dados)} registros")
            time.sleep(0.5)
        except Exception as e:
            print(f"Erro ao baixar dados para o periodo {inicio_str} a {fim_str}: {e}")

        data_atual = data_limite + timedelta(days=1)

    if todos_dados:
        df = pd.DataFrame(todos_dados)
        df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
        df['valor'] = df['valor'].astype(float)
        df = df.set_index('data').sort_index()
        df.columns = ['Cambio']
        return df
    return pd.DataFrame(columns=['Cambio'])

def get_stocks(
    acoes: list[str] | str,
    data_inicio: str,
    data_fim: str,
    proxy: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Função para capturar dados de Ações ou Índices Listados."""
    if proxy:
        yf.set_config(proxy=proxy)
    df1 = pd.DataFrame()
    if isinstance(acoes, list):
        for st in acoes:
            if not st.endswith(".SA"):
                st = st + ".SA"
            if proxy:
                df = yf.download(st, start=data_inicio, end=data_fim, auto_adjust=True)["Close"]
            else:
                df = yf.download(st, start=data_inicio, end=data_fim)["Close"]
            df1 = pd.concat([df, df1], axis=1)
    else:
        if not acoes.endswith(".SA"):
            acoes = acoes + ".SA"
        if proxy:
            df1 = yf.download(acoes, start=data_inicio, end=data_fim, auto_adjust=True)["Close"]
        else:
            df1 = yf.download(acoes, start=data_inicio, end=data_fim)["Close"]
    df1.index = pd.to_datetime(df1.index)
    for cols in df1.columns:
        df1[f"Retorno {cols}"] = df1[cols].pct_change()
        df1[f"Retorno Acumulado {cols}"] = (1 + df1[f"Retorno {cols}"]).cumprod() - 1
    return df1
