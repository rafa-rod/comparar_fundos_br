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
        try:
            dados_cvm = requests.get(url, proxies=proxy, verify=False).text
            df = pd.read_csv(io.StringIO(dados_cvm), sep=";", encoding="ISO-8859-1")
        except:
            raise ValueError("Verifique se a proxy está correta. ParserError: Error tokenizing data")
    else:
        try:
            df = pd.read_csv(url, sep=";", encoding="ISO-8859-1")
        except:
            raise ValueError("Informar proxy. HTTPError: authenticationrequired")
    df_filtrado = df[df["SIT"] == "EM FUNCIONAMENTO NORMAL"]
    if classe:
        if not isinstance(classe, list):
            classe = [classe]
        check_classes = [x for x in classe if x not in classes_disponiveis]
        if check_classes:
            raise ValueError(f"Classe não encontrada {check_classes}")
        df_filtrado = df_filtrado[df_filtrado["CLASSE"].isin(classe)]
        print(f"Cadastro finalizado em {round((time.time()-start)/60,2)} minutos")
    return df_filtrado

def _mesclar_bases(cadastro_fundos: pd.DataFrame, informe_diario_fundos: pd.DataFrame) -> pd.DataFrame:
    cadastro_fundos_filtrado = cadastro_fundos[['CNPJ_FUNDO', 'CLASSE', 'DENOM_SOCIAL']]
    dados_completos_filtrados = informe_diario_fundos.merge(cadastro_fundos_filtrado, on=['CNPJ_FUNDO'], how="inner")
    dados_completos_filtrados["CNPJ - Nome"] = dados_completos_filtrados["CNPJ_FUNDO"] + " // " + dados_completos_filtrados["DENOM_SOCIAL"]
    dados_completos_filtrados = dados_completos_filtrados[["CNPJ - Nome", 'DT_COMPTC', 'CLASSE', 'VL_QUOTA', "NR_COTST", "VL_PATRIM_LIQ"]]
    return dados_completos_filtrados

def _get_response(url: str, proxy: Union[Dict[str, str], None] = None) -> pd.DataFrame:
    if proxy:
        dados_cvm = requests.get(url, proxies=proxy, verify=False)
    else:
        dados_cvm = requests.get(url)
    return dados_cvm

def _ler_dados_diarios(ano: int, mes: int, cadastro_fundos: pd.DataFrame, proxy: Union[Dict[str, str], None] = None, num_minimo_cotistas: Union[int, None] = None, patriminio_liquido_minimo: Union[int, None] = None) -> pd.DataFrame:
    arquivo = "inf_diario_fi_{:02d}{:02d}.csv".format(ano, mes)
    url = "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{:02d}{:02d}.zip".format(ano, mes)
    dados_cvm = _get_response(url, proxy=proxy)
    if str(dados_cvm) != "<Response [200]>":
        url = "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/HIST/inf_diario_fi_{:02d}.zip".format(ano)
        dados_cvm = _get_response(url, proxy=proxy)
    if str(dados_cvm) == '<Response [407]>':
        raise ValueError("Necessário informar proxy correta. Response [407]")
    zf = zipfile.ZipFile(io.BytesIO(dados_cvm.content))
    zf = zf.open(arquivo)
    lines = zf.readlines()
    lines = [i.strip().decode("ISO-8859-1").split(";") for i in lines]
    fundos = pd.DataFrame(lines[1:], columns=lines[0])
    if "TP_FUNDO" in fundos.columns:
        fundos = fundos[fundos["TP_FUNDO"] == "FI"]
    for col in ["VL_PATRIM_LIQ", "NR_COTST", "VL_QUOTA"]:
        fundos[col] = pd.to_numeric(fundos[col])
    if num_minimo_cotistas:
        fundos = fundos[fundos["NR_COTST"] >= num_minimo_cotistas]
    if patriminio_liquido_minimo:
        fundos = fundos[fundos["VL_PATRIM_LIQ"] >= patriminio_liquido_minimo]

    informe_diario_fundos_filtrado = _mesclar_bases(cadastro_fundos, fundos)
    informe_diario_fundos_filtrado = informe_diario_fundos_filtrado.set_index(["DT_COMPTC"])
    informe_diario_fundos_filtrado.index = pd.to_datetime(informe_diario_fundos_filtrado.index)
    return informe_diario_fundos_filtrado
     

def get_brfunds(
			    anos: Union[List[int], int],
			    meses: Union[List[int], int],
                classe: Union[List[str], str, None] = None,
			    num_minimo_cotistas: Union[int, None] = None,
			    patriminio_liquido_minimo: Union[int, None] = None,
			    proxy: Union[Dict[str, str], None] = None,
				) -> pd.DataFrame:
    start = time.time()
    if isinstance(anos, int): anos = [anos]
    else: anos = list(anos)
    if isinstance(meses, int): meses = [meses]
    else: anos = list(anos)
    cadastro_fundos = get_fundsregistration(classe=classe, proxy=proxy)
    
    informe_diario_fundos_historico = pd.DataFrame()
    for ano in anos:
        for mes in meses:
            if ano == datetime.now().year and mes <= datetime.now().month:
                informe_diario_fundos_filtrado = _ler_dados_diarios(ano, mes, cadastro_fundos, proxy, num_minimo_cotistas, patriminio_liquido_minimo)
                informe_diario_fundos_historico = pd.concat([informe_diario_fundos_historico, informe_diario_fundos_filtrado])
            elif ano < datetime.now().year:
                informe_diario_fundos_filtrado = _ler_dados_diarios(ano, mes, cadastro_fundos, proxy, num_minimo_cotistas, patriminio_liquido_minimo)
                informe_diario_fundos_historico = pd.concat([informe_diario_fundos_historico, informe_diario_fundos_filtrado])
        
    print(f"Dados diários finalizados em {round((time.time()-start)/60,2)} minutos")
    return informe_diario_fundos_historico.sort_index()

def get_fidc(ano: int, 
             mes: int, proxy: 
             Union[Dict[str, str], None] = None) -> pd.DataFrame:
    start = time.time()
    url = "http://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/inf_mensal_fidc_{:02d}{:02d}.zip".format(ano, mes)
    if proxy:
        dados_cvm = requests.get(url, proxies=proxy, verify=False)
    else:
        dados_cvm = requests.get(url)
    if str(dados_cvm) == '<Response [404]>':
        raise ValueError("Não há dados para esta data. Response [404]")
    elif str(dados_cvm) == '<Response [407]>':
        raise ValueError("Necessário informar proxy correta. Response [407]")
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
    if str(dados_cvm) == '<Response [404]>':
        raise ValueError("Não há dados para esta data. Response [404]")
    elif str(dados_cvm) == '<Response [407]>':    
        raise ValueError("Necessário informar proxy correta. Response [407]")
    lines = [i.strip().split(";") for i in dados_cvm.text.split("\n")]
    end = time.time()
    print(f"Finalizado em {round((end-start)/60,2)} minutos")
    return pd.DataFrame(lines[1:], columns=lines[0])
