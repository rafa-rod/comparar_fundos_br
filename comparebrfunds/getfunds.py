# -*- coding: utf-8 -*-
"""
@author: Rafael
"""
import getpass
import io
import os
import time
import warnings
import zipfile
from datetime import datetime
from typing import List, Union, Dict

import pandas as pd
import requests

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)


def get_brfunds(
			    ano: int,
			    mes: int,
			    num_minimo_cotistas: Union[int, None] = None,
			    patriminio_liquido_minimo: Union[int, None] = None,
			    proxy: Union[Dict[str, str], None] = None,
				) -> pd.DataFrame:
    start = time.time()
    arquivo = "inf_diario_fi_{:02d}{:02d}.csv".format(ano, mes)
    try:
        url = "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{:02d}{:02d}.zip".format(ano, mes)
        if proxy:
            dados_cvm = requests.get(url, proxies=proxy, verify=False)
        else:
            dados_cvm = requests.get(url)
        zf = zipfile.ZipFile(io.BytesIO(dados_cvm.content))
    except:
        url = "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/HIST/inf_diario_fi_{:02d}.zip".format(ano)
        if proxy:
            dados_cvm = requests.get(url, proxies=proxy, verify=False)
        else:
            dados_cvm = requests.get(url)	
        zf = zipfile.ZipFile(io.BytesIO(dados_cvm.content))
    zf = zf.open(arquivo)
    lines = zf.readlines()
    lines = [i.strip().decode("ISO-8859-1").split(";") for i in lines]
    fundos = pd.DataFrame(lines[1:], columns=lines[0])
    if "TP_FUNDO" in fundos.columns:
        fundos = fundos[fundos["TP_FUNDO"] == "FI"]
    if num_minimo_cotistas:
        fundos = [fundos["NR_COTST"] >= num_minimo_cotistas]
    if patriminio_liquido_minimo:
        fundos = [fundos["VL_PATRIM_LIQ"] >= patriminio_liquido_minimo]
    for col in ["VL_PATRIM_LIQ", "NR_COTST", "VL_QUOTA"]:
        fundos[col] = pd.to_numeric(fundos[col])
    print(f"Finalizado em {round((time.time()-start)/60,2)} minutos")
    return fundos


def get_classes() -> List[str]:
    return [
	        "Fundo de Renda Fixa",
	        "Fundo de Ações",
	        "Fundo Multimercado",
	        "Fundo Cambial",
	        "FMP-FGTS",
	        "FIDC",
	        "FIDC-NP",
	        "FIC FIDC",
	        "FICFIDC-NP",
	        "FIDCFIAGRO",
	        "FII",
	        "FII-FIAGRO",
	        "FIP",
	        "FIP EE",
	        "FIP Multi",
	        "FIC FIP",
	        "FIP CS",
	        "FIP IE",
	        "FIP-FIAGRO",
	        "FUNCINE",
	    	]


def get_fundsregistration(
    classe: Union[List[str], str, None] = None, 
    proxy: Union[Dict[str, str], None] = None) -> pd.DataFrame:
    classes_disponiveis = get_classes()
    start = time.time()
    url = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"
    if proxy:
        dados_cvm = requests.get(url, proxies=proxy, verify=False).text
        df = pd.read_csv(io.StringIO(dados_cvm), sep=";", encoding="ISO-8859-1")
    else:
        df = pd.read_csv(url, sep=";", encoding="ISO-8859-1")
    df_filtrado = df[df["SIT"] == "EM FUNCIONAMENTO NORMAL"]
    if classe:
        if not isinstance(classe, list):
            classe = [classe]
        check_classes = [x for x in classe if x not in classes_disponiveis]
        if check_classes:
            raise ValueError(f"Classe não encontrada {check_classes}")
            df_filtrado = df_filtrado[df_filtrado["CLASSE"].isin(classe)]
        print(f"Finalizado em {round((time.time()-start)/60,2)} minutos")
    return df_filtrado


user = os.getenv("userid").lower()  # getpass.getuser().lower()
pwd = getpass.getpass(prompt="Senha: ")
proxies = {
    "http": f"http://{user}:{pwd}@proxy.inf.bndes.net:8080",
    "https": f"https://{user}:{pwd}@proxy.inf.bndes.net:8080",
	}

informe_diario_fundos = get_brfunds(2022, 7, proxy=proxies)
cadastro_fundos = get_fundsregistration(classe="Fundo de Ações", proxy=proxies)
cadastro_fundos = get_fundsregistration()
cadastro_fundos = get_fundsregistration(classe=["Fundo de Ações","Fundo de Renda Fixa"])

informe_diario_fundos_historico = pd.DataFrame()
for ano in range(2018, 2023):
    for mes in range(1, 13):
        try:
            if ano == datetime.now().year and mes <= datetime.now().month:
                print(f"ano {ano} mes {mes}")
                informe_diario_fundos = get_brfunds(ano, mes, proxy=proxies)
                informe_diario_fundos = informe_diario_fundos.set_index(["DT_COMPTC"])
                informe_diario_fundos_historico = pd.concat([informe_diario_fundos_historico, informe_diario_fundos])
            elif ano < datetime.now().year:
                print(f"ano {ano} mes {mes}")
                informe_diario_fundos = get_brfunds(ano, mes, proxy=proxies)
                informe_diario_fundos = informe_diario_fundos.set_index(["DT_COMPTC"])
                informe_diario_fundos_historico = pd.concat([informe_diario_fundos_historico, informe_diario_fundos])
        except:
            continue
informe_diario_fundos_historico.index = pd.to_datetime(informe_diario_fundos_historico.index)
informe_diario_fundos_historico = informe_diario_fundos_historico.sort_index()
informe_diario_fundos_historico = informe_diario_fundos_historico.reset_index()

cotas = informe_diario_fundos_historico.pivot_table(index="DT_COMPTC", columns="CNPJ_FUNDO", values=["VL_QUOTA", "VL_PATRIM_LIQ"])
cotas = cotas.sort_index()

cotas_normalizadas = cotas["VL_QUOTA"] / cotas["VL_QUOTA"].iloc[0]
retorno = cotas_normalizadas.iloc[-1].sort_values(ascending=False).dropna() - 1


def get_fidc(ano: int, 
             mes: int, proxy: 
             Union[Dict[str, str], None] = None) -> pd.DataFrame:
    start = time.time()
    url = "http://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/inf_mensal_fidc_{:02d}{:02d}.zip".format(ano, mes)
    if proxy:
        dados_cvm = requests.get(url, proxies=proxy, verify=False)
    else:
        dados_cvm = requests.get(url)
    arquivo = "inf_mensal_fidc_tab_X_2_{:02d}{:02d}.csv".format(ano, mes)
    zf = zipfile.ZipFile(io.BytesIO(dados_cvm.content))
    zf = zf.open(arquivo)
    lines = zf.readlines()
    lines = [i.strip().decode("ISO-8859-1").split(";") for i in lines]
    end = time.time()
    print(f"Finalizado em {round((end-start)/60,2)} minutos")
    return pd.DataFrame(lines[1:], columns=lines[0])


def get_fip(ano: int, 
            proxy: Union[Dict[str, str], None] = None) -> pd.DataFrame:
    start = time.time()
    url = "http://dados.cvm.gov.br/dados/FIP/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fip_{:02d}.csv".format(ano)
    if proxy:
        dados_cvm = requests.get(url, proxies=proxy, verify=False)
    else:
        dados_cvm = requests.get(url)
    lines = [i.strip().split(";") for i in dados_cvm.text.split("\n")]
    end = time.time()
    print(f"Finalizado em {round((end-start)/60,2)} minutos")
    return pd.DataFrame(lines[1:], columns=lines[0])


fip = get_fip(2022)

informe_fidcs_all = pd.DataFrame()
for ano in [2020, 2021]:
    for mes in range(1, 13):
        print(f"Data {mes}/{ano}")
        informe_fidcs = get_fidc(ano, mes)
        if not informe_fidcs.empty:
            informe_fidcs_all = pd.concat([informe_fidcs_all, informe_fidcs])
