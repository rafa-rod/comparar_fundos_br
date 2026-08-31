"""
@author: Rafael
"""

import io
import time
import warnings
import zipfile
from datetime import datetime

import pandas as pd
import polars as pl
import requests
from tqdm import tqdm

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)


def get_classes() -> list[str]:
    """Lista as classes disponíveis para filtro."""
    return ["Renda Fixa", "Ações", "Multimercado", "Cambial", "Curto Prazo", "Referenciado"]


def pontua_cnpj(cnpj: str) -> str:
    """Efetua a pontuação do CNPJ"""
    if len(cnpj) < 14:
        cnpj = cnpj.zfill(14)
    cnpj = cnpj.replace("-", "").replace(".", "").replace("/", "")
    p1, p2, p3, p4, p5 = cnpj[:2], cnpj[2:5], cnpj[5:8], cnpj[8:12], cnpj[12:]
    return f"{p1}.{p2}.{p3}/{p4}-{p5}"


def _get_response(url: str, proxy: dict[str, str] | None = None):
    if proxy:
        resposta = requests.get(url, proxies=proxy, verify=False)
    else:
        resposta = requests.get(url)
    return resposta


def _ler_zip_files(resposta, arquivo: str) -> pl.DataFrame:
    """
    Lê arquivos CSV dentro de um ZIP baixado da CVM.

    Args:
        resposta: Objeto Response do requests
        arquivo: Nome do arquivo dentro do ZIP

    Returns:
        Polars DataFrame com os dados

    Raises:
        ValueError: Se a resposta não for 200
        FileNotFoundError: Se o arquivo não existir dentro do ZIP
    """
    # Verifica o status code
    if resposta.status_code == 200:
        # Sucesso - processa o arquivo
        try:
            zf = zipfile.ZipFile(io.BytesIO(resposta.content))

            # Verifica se o arquivo existe dentro do ZIP
            if arquivo not in zf.namelist():
                raise FileNotFoundError(f"Arquivo {arquivo} não encontrado no ZIP")

            with zf.open(arquivo) as f:
                lines = f.readlines()
                lines = [i.strip().decode("ISO-8859-1").split(";") for i in lines]

                if not lines:
                    raise ValueError(f"Arquivo {arquivo} está vazio")

                fundos = pl.DataFrame(lines[1:], schema=lines[0])
                return fundos

        except zipfile.BadZipFile:
            raise ValueError("Arquivo ZIP corrompido ou inválido")

    elif resposta.status_code == 407:
        raise ValueError("Necessário informar proxy correta. Response [407]")

    elif resposta.status_code == 404:
        raise FileNotFoundError("Arquivo não encontrado na CVM (404)")

    elif resposta.status_code == 403:
        raise PermissionError("Acesso negado ao recurso (403)")

    elif resposta.status_code in [500, 502, 503, 504]:
        raise ConnectionError(f"Erro no servidor da CVM: {resposta.status_code}")

    else:
        raise ValueError(f"Erro inesperado ao baixar dados: {resposta.status_code}")


def get_cadastro_fundos(
    classe: list[str] | str | None = None, proxy: dict[str, str] | None = None, output_format: str = "pandas"
) -> pd.DataFrame | pl.dataframe.frame.DataFrame:
    """Busca o cadastro dos fundos em funcionamento normal, dos tipos de classe FIF e FIDC cuja classificação seja não nula
    e busca sua respectiva classe."""
    classes_disponiveis = get_classes()
    start = time.time()
    url1 = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi_hist.zip"
    resposta1 = _get_response(url1, proxy=proxy)
    url2 = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"
    resposta2 = _get_response(url2, proxy=proxy)
    resposta3 = _get_response(url2, proxy=proxy)

    arquivo1, arquivo2, arquivo3 = "cad_fi_hist_classe.csv", "registro_classe.csv", "registro_fundo.csv"
    classes_dos_fundos = _ler_zip_files(resposta1, arquivo1)
    classes_dos_fundos = classes_dos_fundos.filter(pl.col("DT_FIM_CLASSE") != "")  # classes atuais

    nome_dos_fundos = _ler_zip_files(resposta2, arquivo2)
    nome_dos_fundos = nome_dos_fundos.with_columns(pl.col(["CNPJ_Classe"]).map_elements(pontua_cnpj))

    fundos_filtrado = classes_dos_fundos.join(
        nome_dos_fundos, right_on="CNPJ_Classe", left_on="CNPJ_FUNDO", how="outer"
    )
    fundos_filtrado = fundos_filtrado.with_columns(
        pl.when(pl.col("CNPJ_FUNDO").is_null())
        .then(pl.col("CNPJ_Classe"))
        .otherwise(pl.col("CNPJ_FUNDO"))
        .alias("CNPJ")
    )
    fundos_filtrado = fundos_filtrado.drop("CNPJ_FUNDO").rename({"CNPJ": "CNPJ_FUNDO"})
    mais_info_dos_fundos = _ler_zip_files(resposta3, arquivo3)
    mais_info_dos_fundos = mais_info_dos_fundos.select(
        ["CNPJ_Fundo", "Tipo_Fundo", "Denominacao_Social", "Situacao", "Data_Adaptacao_RCVM175"]
    )
    mais_info_dos_fundos = mais_info_dos_fundos.rename({"CNPJ_Fundo": "CNPJ_FUNDO"})
    mais_info_dos_fundos = mais_info_dos_fundos.with_columns(pl.col(["CNPJ_FUNDO"]).map_elements(pontua_cnpj))
    fundos_filtrado = fundos_filtrado.join(
        mais_info_dos_fundos, on=["CNPJ_FUNDO", "Denominacao_Social", "Situacao"], how="right"
    )
    fundos_filtrado = fundos_filtrado.filter(
        (pl.col("Situacao") == "Em Funcionamento Normal") & (pl.col("Tipo_Fundo").is_in(["FIDC", "FI", "FIF"]))
    ).drop(["CNPJ_Classe", "DT_REG", "DT_INI_CLASSE", "DT_FIM_CLASSE", "ID_Registro_Fundo", "ID_Registro_Classe"])
    if classe:
        if not isinstance(classe, list):
            classe = [classe]
        check_classes = [x for x in classe if x not in classes_disponiveis]
        if check_classes:
            raise ValueError(f"Classe não encontrada {check_classes}")
        fundos_filtrado = fundos_filtrado.filter(
            (pl.col("CLASSE").is_in(classe)) | (pl.col("CLASSE").is_null()) | (pl.col("CLASSE") == "")
        )
    fundos_filtrado = fundos_filtrado.with_columns(pl.col("Denominacao_Social").str.to_uppercase())
    if output_format.lower() == "pandas":
        fundos_filtrado = fundos_filtrado.to_pandas()
    print(f"Cadastro finalizado em {round((time.time() - start) / 60, 2)} minutos")
    return fundos_filtrado


def mesclar_bases(
    cadastro_fundos: pl.dataframe.frame.DataFrame,
    informe_diario_fundos: pl.dataframe.frame.DataFrame,
    output_format: str = "pandas",
) -> pl.dataframe.frame.DataFrame:
    """Função para obter dados adicionais dos Fundos que estão em seu cadastro.
    Basta informar o dataframe do cadastro com o dataframe do informe diario para obter as informações."""
    if isinstance(cadastro_fundos, pd.DataFrame):
        cadastro_fundos = pl.from_pandas(cadastro_fundos)
    if isinstance(informe_diario_fundos, pd.DataFrame):
        if "DT_COMPTC" not in informe_diario_fundos.columns:
            informe_diario_fundos = informe_diario_fundos.reset_index()
        informe_diario_fundos = pl.from_pandas(informe_diario_fundos)
    dados_completos_filtrados = informe_diario_fundos.join(cadastro_fundos, on=["CNPJ_FUNDO"], how="inner")
    dados_completos_filtrados = dados_completos_filtrados.with_columns(
        ((pl.col("CNPJ_FUNDO")) + " // " + (pl.col("Denominacao_Social"))).alias("CNPJ - Nome")
    )
    if output_format.lower() == "pandas":
        return dados_completos_filtrados.to_pandas().set_index("DT_COMPTC").sort_index()
    else:
        return dados_completos_filtrados.sort("DT_COMPTC")


def _ler_dados_diarios(
    ano: int,
    mes: int,
    proxy: dict[str, str] | None = None,
    cnpj: str | None = None,
    num_minimo_cotistas: int | None = None,
    patriminio_liquido_minimo: int | None = None,
) -> pl.dataframe.frame.DataFrame:
    arquivo = f"inf_diario_fi_{ano:02d}{mes:02d}.csv" if ano > 2004 else f"inf_diario_fi_{ano:02d}.csv"
    url = (
        f"http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{ano:02d}{mes:02d}.zip"
        if ano >= 2021
        else f"http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/HIST/inf_diario_fi_{ano:02d}.zip"
    )
    resposta = _get_response(url, proxy=proxy)
    fundos = _ler_zip_files(resposta, arquivo)
    cols1 = [x for x in fundos.columns if "TP_FUNDO" in x]
    if cols1 and int(ano) >= 2004:
        fundos = fundos.rename({cols1[0]: "TP_FUNDO"})
        fundos = fundos.filter(pl.col("TP_FUNDO").is_in(["FI", "FIF", "CLASSES - FIF"]))
    cols2 = [x for x in fundos.columns if "CNPJ_FUNDO" in x][0]
    fundos = fundos.rename({cols2: "CNPJ_FUNDO"})
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
        if isinstance(cnpj, str):
            cnpj = [cnpj]
        lista_cnpj = [pontua_cnpj(x) for x in cnpj]
        fundos = fundos.filter(pl.col("CNPJ_FUNDO").is_in(lista_cnpj))
    return (
        fundos.select(
            ["DT_COMPTC", "CNPJ_FUNDO", "NR_COTST", "VL_PATRIM_LIQ", "VL_QUOTA", "VL_TOTAL", "CAPTC_DIA", "RESG_DIA"]
        )
        .unique()
        .sort("DT_COMPTC")
    )


def fundosbr(
    anos: list[int] | int,
    meses: list[int] | int,
    cnpj: str | None = None,
    num_minimo_cotistas: int | None = None,
    patriminio_liquido_minimo: int | None = None,
    proxy: dict[str, str] | None = None,
    output_format: str = "pandas",
) -> pd.DataFrame | pl.dataframe.frame.DataFrame:
    start = time.time()
    if isinstance(anos, int):
        anos = [anos]
    else:
        anos = list(anos)
    if isinstance(meses, int):
        meses = [meses]
    else:
        anos = list(anos)
    informe_diario_fundos_historico = pl.DataFrame()
    for ano in anos:
        for mes in meses:
            if ano == datetime.now().year and mes <= datetime.now().month or ano < datetime.now().year:
                informe_diario_fundos_filtrado = _ler_dados_diarios(
                    ano, mes, proxy, cnpj, num_minimo_cotistas, patriminio_liquido_minimo
                )
                informe_diario_fundos_historico = pl.concat(
                    [informe_diario_fundos_historico, informe_diario_fundos_filtrado]
                )
    print(f"Dados diários finalizados em {round((time.time() - start) / 60, 2)} minutos")
    if output_format.lower() == "pandas":
        return informe_diario_fundos_historico.to_pandas().set_index("DT_COMPTC").sort_index()
    else:
        return informe_diario_fundos_historico.sort("DT_COMPTC")


def get_fip(ano: int, proxy: dict[str, str] | None = None) -> pd.DataFrame:
    """
    Captura dados de Fundos de Participaçõem em Investimentos (FIP) da CVM conforme ano apontado.
    Após 2023, os dados de FIP passaram a ser quadrimestrais.
    """
    start = time.time()
    url = (
        f"http://dados.cvm.gov.br/dados/FIP/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fip_{ano:02d}.csv"
        if ano <= 2023
        else f"http://dados.cvm.gov.br/dados/FIP/DOC/INF_QUADRIMESTRAL/DADOS/inf_quadrimestral_fip_{ano:02d}.csv"
    )
    try:
        resposta = _get_response(url, proxy=proxy)

        if resposta.status_code == 200:
            lines = [i.strip().split(";") for i in resposta.text.split("\n")]
            end = time.time()
            print(f"Finalizado em {round((end - start) / 60, 2)} minutos")
            return pd.DataFrame(lines[1:], columns=lines[0])
        elif resposta.status_code == 404:
            raise ValueError(f"Não há dados disponíveis para o ano {ano}. Arquivo não encontrado (404)")

        elif resposta.status_code == 403:
            raise PermissionError(f"Acesso negado ao recurso para o ano {ano}. Verifique suas permissões (403)")

        elif resposta.status_code == 500:
            raise ConnectionError(f"Erro interno no servidor da CVM para o ano {ano}. Tente novamente mais tarde (500)")

        elif resposta.status_code == 503:
            raise ConnectionError(f"Serviço da CVM indisponível para o ano {ano}. Tente novamente mais tarde (503)")

        else:
            raise ValueError(f"Erro inesperado ao acessar dados do ano {ano}: Status {resposta.status_code}")

    except requests.exceptions.Timeout:
        raise TimeoutError(f"Tempo limite excedido ao baixar dados do ano {ano}. Verifique sua conexão com a internet.")

    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Erro de conexão ao baixar dados do ano {ano}. Verifique sua conexão com a internet.")

    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Erro na requisição para o ano {ano}: {e!s}")


def get_fidc(
    ano: int, tabela: str = "X", subtabela: int = 3, proxy: dict[str, str] | None = None, use_polars: bool = False
) -> pd.DataFrame | pl.DataFrame:
    """
    Busca dados de Fundos de Investimento em Direitos Creditórios (FIDC) da CVM.

    Args:
        ano: Ano dos dados
        tabela: Tabela a ser consultada (I, II, III, IV, V, VI, VII, VIII, IX, X)
        subtabela: Subtabela (padrão 3 para rentabilidade mensal)
        proxy: Configuração de proxy (opcional)
        use_polars: Se True, retorna Polars DataFrame, senão Pandas

    Returns:
        DataFrame com os dados concatenados de todos os meses

    Exemplo:
        df = get_fidc(2024, tabela="X", subtabela=3)
    """
    start = time.time()

    # Validação do ano
    if ano < 2000 or ano > 2100:
        raise ValueError(f"Ano inválido: {ano}")

    # Validação da tabela
    tabelas_validas = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    if tabela.upper() not in tabelas_validas:
        raise ValueError(f"Tabela inválida. Use uma de: {tabelas_validas}")

    # Define a URL base
    if ano <= 2024:
        url = f"https://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/HIST/inf_mensal_fidc_{ano:02d}.zip"
    else:
        # Para anos mais recentes, pode ser necessário baixar mês a mês
        url = f"http://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/inf_mensal_fidc_{ano:02d}"

    try:
        # Baixa o arquivo ZIP
        resposta = _get_response(url, proxy=proxy)

        if resposta.status_code != 200:
            # Se falhou, tenta o formato alternativo para anos recentes
            if ano > 2024:
                return _baixar_fidc_mensal(ano, tabela, subtabela, proxy, use_polars)
            else:
                raise ValueError(f"Erro ao baixar dados do ano {ano}: Status {resposta.status_code}")

        # Processa cada mês
        resultados = []
        meses = list(range(1, 13))

        print(f" Processando {len(meses)} meses...")
        for mes in tqdm(meses, desc="Processando meses"):
            try:
                if tabela.upper() == "X":
                    arquivo = f"inf_mensal_fidc_tab_{tabela}_{subtabela}_{ano:02d}{mes:02d}.csv"
                else:
                    arquivo = f"inf_mensal_fidc_tab_{tabela}_{ano:02d}{mes:02d}.csv"

                df_mes = _ler_zip_files(resposta, arquivo)
                resultados.append(df_mes)

            except FileNotFoundError as e:
                print(f" Mês {mes:02d}/{ano}: {e}")
                continue
            except Exception as e:
                print(f" Erro no mês {mes:02d}/{ano}: {e}")
                continue

        if not resultados:
            raise ValueError(f"Nenhum dado encontrado para o ano {ano}")

        # Concatena todos os meses
        df_final = pl.concat(resultados)

        end = time.time()
        print(f" Finalizado em {round((end - start) / 60, 2)} minutos")
        print(f" Total de registros: {len(df_final)}")

        # Retorna no formato solicitado
        if use_polars:
            return df_final
        else:
            return df_final.to_pandas()

    except requests.exceptions.Timeout:
        raise TimeoutError(f" Timeout ao baixar dados de FIDC {ano}")
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f" Erro de conexão para FIDC {ano}")
    except Exception as e:
        raise Exception(f" Erro ao processar FIDC {ano}: {e!s}")


def _baixar_fidc_mensal(
    ano: int, tabela: str, subtabela: int, proxy: dict[str, str] | None = None, use_polars: bool = True
) -> pl.DataFrame:
    """
    Função auxiliar para baixar dados mensais individualmente (anos > 2024).
    """
    resultados = []
    url_base = f"http://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/inf_mensal_fidc_{ano:02d}"

    for mes in tqdm(range(1, 13), desc="Baixando meses"):
        try:
            url = f"{url_base}{mes:02d}.zip"
            resposta = _get_response(url, proxy=proxy)

            if resposta.status_code != 200:
                print(f" Mês {mes:02d} não disponível (status {resposta.status_code})")
                continue

            if tabela.upper() == "X":
                arquivo = f"inf_mensal_fidc_tab_{tabela}_{subtabela}_{ano:02d}{mes:02d}.csv"
            else:
                arquivo = f"inf_mensal_fidc_tab_{tabela}_{ano:02d}{mes:02d}.csv"

            df_mes = _ler_zip_files(resposta, arquivo)
            resultados.append(df_mes)

        except Exception as e:
            print(f" Erro no mês {mes:02d}: {e}")
            continue

    if not resultados:
        raise ValueError(f"Nenhum dado encontrado para o ano {ano}")

    df_final = pl.concat(resultados)

    if use_polars:
        return df_final
    else:
        return df_final.to_pandas()
