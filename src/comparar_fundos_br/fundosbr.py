# -*- coding: utf-8 -*-
"""
@author: Rafael
"""
import io
import time
import warnings
import zipfile
from datetime import datetime
from typing import List, Union, Dict, Optional
import polars as pl
import pandas as pd
import requests

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)

def get_classes() -> List[str]:
    '''Lista as classes disponíveis para filtro.'''
    return ['Renda Fixa', 'Ações', 'Multimercado', 'Cambial', 'Curto Prazo', 'Referenciado']

def pontua_cnpj(cnpj: str) -> str:
    '''Efetua a pontuação do CNPJ'''
    if len(cnpj) < 14:
        cnpj = cnpj.zfill(14)
    cnpj = cnpj.replace("-","").replace(".","").replace("/","")
    p1, p2, p3, p4, p5 = cnpj[:2], cnpj[2:5], cnpj[5:8], cnpj[8:12], cnpj[12:]
    return f"{p1}.{p2}.{p3}/{p4}-{p5}"

def _get_response(url: str, proxy: Optional[Dict[str, str]] = None):
    if proxy:
        resposta = requests.get(url, proxies=proxy, verify=False)
    else:
        resposta = requests.get(url)
    return resposta

def _ler_zip_files(resposta, arquivo: str) -> pl.dataframe.frame.DataFrame:
    if str(resposta) != "<Response [200]>" and str(resposta) != '<Response [407]>':
        raise ValueError("Não foi possível baixar os dados solicitados")
    elif str(resposta) == '<Response [407]>':
        raise ValueError("Necessário informar proxy correta. Response [407]")
    zf = zipfile.ZipFile(io.BytesIO(resposta.content))
    zf = zf.open(arquivo)
    lines = zf.readlines()
    lines = [i.strip().decode("ISO-8859-1").split(";") for i in lines]
    fundos = pl.DataFrame(lines[1:], schema=lines[0])
    return fundos

def get_cadastro_fundos(
    classe: Optional[Union[List[str], str]] = None, 
    proxy: Optional[Dict[str, str]] = None,
    output_format: str = 'pandas') -> Union[pd.DataFrame, pl.dataframe.frame.DataFrame]:
    '''Busca o cadastro dos fundos em funcionamento normal, dos tipos de classe FIF e FIDC cuja classificação seja não nula
    e busca sua respectiva classe.'''
    classes_disponiveis = get_classes()
    start = time.time()
    url1 = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi_hist.zip"
    resposta1 = _get_response(url1, proxy=proxy)
    url2 = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"
    resposta2 = _get_response(url2, proxy=proxy)
    resposta3 = _get_response(url2, proxy=proxy)

    arquivo1, arquivo2, arquivo3 = "cad_fi_hist_classe.csv", "registro_classe.csv", "registro_fundo.csv"
    classes_dos_fundos = _ler_zip_files(resposta1, arquivo1)
    classes_dos_fundos = classes_dos_fundos.filter(pl.col('DT_FIM_CLASSE')!='') #classes atuais

    nome_dos_fundos = _ler_zip_files(resposta2, arquivo2)
    nome_dos_fundos = nome_dos_fundos.with_columns(pl.col(["CNPJ_Classe"]).map_elements(pontua_cnpj))

    fundos_filtrado = classes_dos_fundos.join(nome_dos_fundos, right_on='CNPJ_Classe', left_on='CNPJ_FUNDO', how='outer')
    fundos_filtrado = fundos_filtrado.with_columns(
                                        pl.when(pl.col('CNPJ_FUNDO').is_null())
                                          .then(pl.col('CNPJ_Classe'))
                                          .otherwise(pl.col('CNPJ_FUNDO'))
                                          .alias('CNPJ')
                                            )
    fundos_filtrado = fundos_filtrado.drop('CNPJ_FUNDO').rename({'CNPJ': 'CNPJ_FUNDO'})
    mais_info_dos_fundos = _ler_zip_files(resposta3, arquivo3)
    mais_info_dos_fundos = mais_info_dos_fundos.select(['CNPJ_Fundo', 'Tipo_Fundo', 'Denominacao_Social', 'Situacao', 'Data_Adaptacao_RCVM175'])
    mais_info_dos_fundos = mais_info_dos_fundos.rename({'CNPJ_Fundo': 'CNPJ_FUNDO'})
    mais_info_dos_fundos = mais_info_dos_fundos.with_columns(pl.col(["CNPJ_FUNDO"]).map_elements(pontua_cnpj))
    fundos_filtrado = fundos_filtrado.join(mais_info_dos_fundos, on=['CNPJ_FUNDO', 'Denominacao_Social', 'Situacao'], how='right')
    fundos_filtrado = fundos_filtrado.filter( (pl.col('Situacao')=="Em Funcionamento Normal") &
                                              (pl.col('Tipo_Fundo').is_in(['FIDC', 'FI', 'FIF']) )).drop(['CNPJ_Classe',
                                                                                                        'DT_INI_CLASSE',
                                                                                                        'DT_FIM_CLASSE',
                                                                                                        'ID_Registro_Fundo',
                                                                                                        'ID_Registro_Classe'])
    if classe:
        if not isinstance(classe, list):
            classe = [classe]
        check_classes = [x for x in classe if x not in classes_disponiveis]
        if check_classes:
            raise ValueError(f"Classe não encontrada {check_classes}")
        fundos_filtrado = fundos_filtrado.filter((pl.col('CLASSE').is_in(classe)) | (pl.col('CLASSE').is_null()) |
                                                 (pl.col('CLASSE')==''))
    if output_format.lower() == 'pandas':
        fundos_filtrado = fundos_filtrado.to_pandas()
    print(f"Cadastro finalizado em {round((time.time()-start)/60,2)} minutos")
    return fundos_filtrado

def mesclar_bases(cadastro_fundos: pl.dataframe.frame.DataFrame, informe_diario_fundos: pl.dataframe.frame.DataFrame,
                  output_format: str = 'pandas') -> pl.dataframe.frame.DataFrame:
    '''Função para obter dados adicionais dos Fundos que estão em seu cadastro.
    Basta informar o dataframe do cadastro com o dataframe do informe diario para obter as informações.'''
    if isinstance(cadastro_fundos, pd.DataFrame):
        cadastro_fundos = pl.from_pandas(cadastro_fundos)
    if isinstance(informe_diario_fundos, pd.DataFrame):
        if 'DT_COMPTC' not in informe_diario_fundos.columns:
            informe_diario_fundos = informe_diario_fundos.reset_index()
        informe_diario_fundos = pl.from_pandas(informe_diario_fundos)
    dados_completos_filtrados = informe_diario_fundos.join(cadastro_fundos, on=['CNPJ_FUNDO'], how="inner")
    dados_completos_filtrados = dados_completos_filtrados.with_columns(((pl.col('CNPJ_FUNDO')) + ' // ' + (pl.col('Denominacao_Social'))).alias('CNPJ - Nome'))
    if output_format.lower() == 'pandas':
        return dados_completos_filtrados.to_pandas().set_index('DT_COMPTC').sort_index()
    else:
        return dados_completos_filtrados.sort('DT_COMPTC')

def _ler_dados_diarios(ano: int, mes: int, proxy: Optional[Dict[str, str]] = None,
                       cnpj: Optional[str] = None,
                       num_minimo_cotistas: Optional[int] = None, 
                       patriminio_liquido_minimo: Optional[int] = None) -> pl.dataframe.frame.DataFrame:
    arquivo = "inf_diario_fi_{:02d}{:02d}.csv".format(ano, mes) if ano> 2004 else "inf_diario_fi_{:02d}.csv".format(ano)
    url = "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{:02d}{:02d}.zip".format(ano, mes) if ano>= 2021 else \
           "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/HIST/inf_diario_fi_{:02d}.zip".format(ano)
    resposta = _get_response(url, proxy=proxy)
    fundos = _ler_zip_files(resposta, arquivo)
    cols1 = [x for x in fundos.columns if "TP_FUNDO" in x]
    if cols1 and int(ano)>=2004:
        fundos = fundos.rename({cols1[0]: 'TP_FUNDO'})
        fundos = fundos.filter(pl.col("TP_FUNDO").is_in(['FI','FIF','CLASSES - FIF']))
    cols2 = [x for x in fundos.columns if "CNPJ_FUNDO" in x][0]
    fundos = fundos.rename({cols2: 'CNPJ_FUNDO'})
    fundos = fundos.with_columns(pl.col("NR_COTST").cast(pl.Int32, strict=False))
    fundos = fundos.with_columns(pl.col("VL_PATRIM_LIQ").cast(pl.Float64, strict=False))
    fundos = fundos.with_columns(pl.col("VL_TOTAL").cast(pl.Float64, strict=False))
    fundos = fundos.with_columns(pl.col("CAPTC_DIA").cast(pl.Float64, strict=False))
    fundos = fundos.with_columns(pl.col("RESG_DIA").cast(pl.Float64, strict=False))
    fundos = fundos.with_columns(pl.col("VL_QUOTA").cast(pl.Float32, strict=False))
    fundos = fundos.with_columns(pl.col("DT_COMPTC").str.to_datetime("%Y-%m-%d"))
    if num_minimo_cotistas:
        fundos = fundos.filter(pl.col("NR_COTST") >= num_minimo_cotistas)
    if patriminio_liquido_minimo:
        fundos = fundos.filter(pl.col("VL_PATRIM_LIQ") >= patriminio_liquido_minimo)
    if cnpj:
        if isinstance(cnpj, str): cnpj = [cnpj]
        lista_cnpj = [pontua_cnpj(x) for x in cnpj]
        fundos = fundos.filter(pl.col("CNPJ_FUNDO").is_in(lista_cnpj))
    return fundos.select(['DT_COMPTC', 'CNPJ_FUNDO', 'NR_COTST', 'VL_PATRIM_LIQ', 'VL_QUOTA',
                          'VL_TOTAL', 'CAPTC_DIA', 'RESG_DIA']).unique().sort('DT_COMPTC')

def fundosbr(
            anos: Union[List[int], int],
            meses: Union[List[int], int],
            cnpj: Optional[str] = None,
            num_minimo_cotistas: Optional[int] = None,
            patriminio_liquido_minimo: Optional[int] = None,
            proxy: Optional[Dict[str, str]] = None,
            output_format: str = 'pandas'
				) -> Union[pd.DataFrame, pl.dataframe.frame.DataFrame]:
    start = time.time()
    if isinstance(anos, int): anos = [anos]
    else: anos = list(anos)
    if isinstance(meses, int): meses = [meses]
    else: anos = list(anos)
    informe_diario_fundos_historico = pl.DataFrame()
    for ano in anos:
        for mes in meses:
            if ano == datetime.now().year and mes <= datetime.now().month:
                informe_diario_fundos_filtrado = _ler_dados_diarios(ano, mes, proxy, cnpj, num_minimo_cotistas, patriminio_liquido_minimo)
                informe_diario_fundos_historico = pl.concat([informe_diario_fundos_historico, informe_diario_fundos_filtrado])
            elif ano < datetime.now().year:
                informe_diario_fundos_filtrado = _ler_dados_diarios(ano, mes, proxy, cnpj, num_minimo_cotistas, patriminio_liquido_minimo)
                informe_diario_fundos_historico = pl.concat([informe_diario_fundos_historico, informe_diario_fundos_filtrado])
    print(f"Dados diários finalizados em {round((time.time()-start)/60,2)} minutos")
    if output_format.lower() == 'pandas':
        return informe_diario_fundos_historico.to_pandas().set_index('DT_COMPTC').sort_index()
    else:
        return informe_diario_fundos_historico.sort('DT_COMPTC')

def get_fip(ano: int, 
            proxy: Union[Dict[str, str], None] = None) -> pd.DataFrame:
    start = time.time()
    url = "http://dados.cvm.gov.br/dados/FIP/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fip_{:02d}.csv".format(ano)
    if proxy:
        try:
            dados_cvm = requests.get(url, proxies=proxy, verify=False)
        except AttributeError:
            raise ValueError("Necessário informar proxy correta.")
    else:
        dados_cvm = requests.get(url)
    if str(dados_cvm) == '<Response [404]>':
        raise ValueError("Não há dados para esta data. Response [404]")
    lines = [i.strip().split(";") for i in dados_cvm.text.split("\n")]
    end = time.time()
    print(f"Finalizado em {round((end-start)/60,2)} minutos")
    return pd.DataFrame(lines[1:], columns=lines[0])

def get_fidc(ano: int, 
             mes: int, proxy: 
             Union[Dict[str, str], None] = None) -> pd.DataFrame:
    start = time.time()
    url = "http://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/inf_mensal_fidc_{:02d}{:02d}.zip".format(ano, mes)
    if proxy:
        try:
            dados_cvm = requests.get(url, proxies=proxy, verify=False)
        except AttributeError:
            raise ValueError("Necessário informar proxy correta.")
    else:
        dados_cvm = requests.get(url)
    if str(dados_cvm) == '<Response [404]>':
        raise ValueError("Não há dados para esta data. Response [404]")
    arquivo = "inf_mensal_fidc_tab_X_2_{:02d}{:02d}.csv".format(ano, mes)
    zf = zipfile.ZipFile(io.BytesIO(dados_cvm.content))
    zf = zf.open(arquivo)
    lines = zf.readlines()
    lines = [i.strip().decode("ISO-8859-1").split(";") for i in lines]
    end = time.time()
    print(f"Finalizado em {round((end-start)/60,2)} minutos")
    return pd.DataFrame(lines[1:], columns=lines[0])