"""
@author: Rafael
"""

import time
import warnings
from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd
import polars as pl
import requests
import seaborn as sns
import tesouro_direto_br as tesouro_direto
import yfinance as yf

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", lambda x: "%.6f" % x)
pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 1000)

sns.set_theme()


class DadosFinanceiros:
    """Cliente para captura de dados financeiros (renda fixa, câmbio e renda variável).

    Centraliza a configuração de proxy: passe-a uma vez no construtor e ela é
    reaplicada automaticamente em todas as chamadas (BACEN, ANBIMA, Yahoo Finance).

    Exemplo:
        dados = DadosFinanceiros(proxy={"https": "http://meuproxy:8080"})
        cdi = dados.cdi("2024-01-01", "2024-12-31")
        acoes = dados.stocks(["PETR4", "VALE3"], "2024-01-01", "2024-12-31")
        bmk = dados.benchmarks("2024-01-01", "2024-12-31", benchmark=["CDI", "IBOV"])
    """

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
    BASE_ANBIMA = "https://s3-data-prd-use1-precos.s3.us-east-1.amazonaws.com/arquivos/indices-historico/{arquivo}"

    def __init__(self, proxy: dict[str, str] | None = None):
        self.proxy = proxy
        if proxy:
            yf.set_config(proxy=proxy)

    # ------------------------------------------------------------------
    # Consulta genérica ao SGS/BACEN (fonte comum de CDI e PTAX)
    # ------------------------------------------------------------------

    def _consulta_sgs_bacen(
        self,
        codigo_serie: int,
        data_inicio: str,
        data_fim: str,
        timeout: int = 30,
    ) -> pd.DataFrame:
        """Consulta genérica ao Sistema Gerenciador de Séries Temporais (SGS) do Banco
        Central, usado como fonte tanto do CDI (série 12) quanto do câmbio PTAX
        (séries 1/10813). Faz requisições em janelas de até 10 anos — limite prático
        da API para séries diárias — e trata erros de rede/resposta vazia por janela
        sem interromper a consulta inteira.

        Retorna um DataFrame com colunas ['data', 'valor'], sem index e sem conversão
        de tipo além de datetime/float — a interpretação do valor (ex: dividir por 100
        no caso do CDI) fica a cargo de quem chama.
        """
        if isinstance(data_inicio, str):
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        else:
            inicio = data_inicio
        if isinstance(data_fim, str):
            fim = datetime.strptime(data_fim, "%Y-%m-%d")
        else:
            fim = data_fim

        todos_dados = []
        data_atual = inicio
        while data_atual <= fim:
            data_limite = min(data_atual + timedelta(days=365 * 10 - 1), fim)
            inicio_str = data_atual.strftime("%d/%m/%Y")
            fim_str = data_limite.strftime("%d/%m/%Y")

            url = (
                f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados"
                f"?formato=json&dataInicial={inicio_str}&dataFinal={fim_str}"
            )
            try:
                if self.proxy:
                    response = requests.get(url, proxies=self.proxy, timeout=timeout, verify=False)
                else:
                    response = requests.get(url, timeout=timeout)
                dados = response.json()
                if dados and isinstance(dados, list):
                    todos_dados.extend(dados)
                    print(f"Baixados dados de {inicio_str} a {fim_str}: {len(dados)} registros")
                else:
                    print(f"Resposta vazia/sem dados para {inicio_str} a {fim_str}: {dados!r}")
                time.sleep(0.5)
            except Exception as e:
                print(f"Erro ao baixar dados para o periodo {inicio_str} a {fim_str}: {e}")

            data_atual = data_limite + timedelta(days=1)

        if not todos_dados:
            return pd.DataFrame(columns=["data", "valor"])

        df = pd.DataFrame(todos_dados)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = df["valor"].astype(float)
        return df.sort_values("data").reset_index(drop=True)

    # ------------------------------------------------------------------
    # CDI
    # ------------------------------------------------------------------

    def cdi(self, inicio: str, fim: str, metodo_cdi: str = "bacen") -> pd.DataFrame:
        """Função que provê o retorno do CDI usada como referência especialmente para Renda Fixa.
        Esta função usa os métodos: tesouro, anbima ou bacen para extrair a rentabilidade.
        Tesouro = usa-se o rendimento diário dos titulos Tesouro Selic de vencimentos mais longos;
        Anbima = usa-se o índice IMA-S que usa rendimentos de Tesouro Selic;
        BACEN = usa-se a série diária do CDI (via SGS, mesma fonte usada em `cambio_ptax`).
        As datas devem ser no formato string '2025-01-02', ou seja, 'ANO-MES-DIA'.
        A saída gera o retorno diário e o acumulado.
        Os valores resultantes são próximos, mas não iguais. Divergem em função da metodologia."""
        if metodo_cdi.lower() == "tesouro":
            titulos_ofertados = tesouro_direto.busca_tesouro_direto(
                tipo="taxa", proxies=self.proxy, agrupar=True
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
            bruto = self._consulta_sgs_bacen(codigo_serie=12, data_inicio=inicio, data_fim=fim)
            cdi = bruto.set_index("data")
            cdi = cdi[(cdi.index >= inicio) & (cdi.index <= fim)] / 100
            cdi.columns = ["CDI"]
            cdi["Retorno CDI"] = cdi["CDI"]
            cdi["Retorno Acumulado CDI"] = (1 + cdi["Retorno CDI"]).cumprod() - 1
        else:
            raise ValueError("Método não permitido")
        return cdi

    # ------------------------------------------------------------------
    # Índices ANBIMA
    # ------------------------------------------------------------------

    def indices_anbima(self, data_inicio: str, data_fim: str, benchmark: str = "imas") -> pd.DataFrame:
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
        chave = benchmark.lower().strip()
        if chave not in self.ARQUIVOS_ANBIMA:
            raise ValueError(f"Benchmark não encontrado: {chave}")

        url = self.BASE_ANBIMA.format(arquivo=self.ARQUIVOS_ANBIMA[chave])
        response = requests.get(url, proxies=self.proxy, stream=True)
        response.raise_for_status()
        file_object = BytesIO(response.content)

        indice = pl.read_excel(file_object, engine="calamine", columns=[1, 2])
        indice = indice.filter(
            (pl.col("Data de Referência") >= pd.to_datetime(data_inicio))
            & (pl.col("Data de Referência") <= pd.to_datetime(data_fim))
        )
        indice = indice.rename({"Número Índice": benchmark.upper()})
        return indice.to_pandas().set_index("Data de Referência")

    # ------------------------------------------------------------------
    # Câmbio PTAX
    # ------------------------------------------------------------------

    def cambio_ptax(self, data_inicio: str, data_fim: str, compra: bool = False) -> pd.DataFrame:
        """
        Usa dados do Sistema de Gestao de Series do Banco Central:
        https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries
        para obter os dados do dólar oficial (PTAX, fonte Sisbacen PTAX800), via a mesma
        consulta genérica ao SGS usada em `cdi(metodo_cdi="bacen")`.

        Se desejar valores de venda, colocar compra = False e para compra, compra = True.
        """
        codigo_serie = 10813 if compra else 1
        bruto = self._consulta_sgs_bacen(codigo_serie=codigo_serie, data_inicio=data_inicio, data_fim=data_fim)

        if bruto.empty:
            return pd.DataFrame(columns=["Cambio", "Retorno Cambio", "Retorno Acumulado Cambio"])

        df = bruto.set_index("data")
        df.columns = ["Cambio"]
        df["Retorno Cambio"] = df["Cambio"].pct_change()
        df["Retorno Acumulado Cambio"] = (1 + df["Retorno Cambio"]).cumprod() - 1
        return df

    # ------------------------------------------------------------------
    # Ações / índices listados
    # ------------------------------------------------------------------

    def stocks(self, acoes: list[str] | str, data_inicio: str, data_fim: str) -> pd.DataFrame:
        """Função para capturar dados de Ações ou Índices Listados."""
        df1 = pd.DataFrame()
        if isinstance(acoes, list):
            for st in acoes:
                if not st.endswith(".SA"):
                    st = st + ".SA"
                if self.proxy:
                    df = yf.download(st, start=data_inicio, end=data_fim, auto_adjust=True)["Close"]
                else:
                    df = yf.download(st, start=data_inicio, end=data_fim, auto_adjust=True)["Close"]
                df1 = pd.concat([df, df1], axis=1)
        else:
            if not acoes.endswith(".SA"):
                acoes = acoes + ".SA"
            if self.proxy:
                df1 = yf.download(acoes, start=data_inicio, end=data_fim, auto_adjust=True)["Close"]
            else:
                df1 = yf.download(acoes, start=data_inicio, end=data_fim, auto_adjust=True)["Close"]
        df1.index = pd.to_datetime(df1.index)
        for cols in df1.columns:
            df1[f"Retorno {cols}"] = df1[cols].pct_change()
            df1[f"Retorno Acumulado {cols}"] = (1 + df1[f"Retorno {cols}"]).cumprod() - 1
        return df1

    # ------------------------------------------------------------------
    # Benchmarks (dispatcher)
    # ------------------------------------------------------------------

    def _benchmark_unico(
        self, data_inicio: str, data_fim: str, benchmark: str, metodo_cdi: str, compra: bool
    ) -> pd.DataFrame:
        """Resolve um único benchmark (uso interno de `benchmarks`)."""
        nome = benchmark.upper()

        if nome == "CDI":
            return self.cdi(data_inicio, data_fim, metodo_cdi)

        if nome == "IBOV":
            df_benchmark = yf.download("^BVSP", start=data_inicio, end=data_fim, interval="1d", auto_adjust=True)[
                "Close"
            ]
            df_benchmark.columns = ["IBOV"]
        elif nome == "DIVO11":
            df_benchmark = yf.download("DIVO11.SA", start=data_inicio, end=data_fim, interval="1d", auto_adjust=True)[
                "Close"
            ]
            df_benchmark.columns = ["DIVO11"]
        elif nome == "SP500":
            df_benchmark = yf.download("^GSPC", start=data_inicio, end=data_fim, interval="1d", auto_adjust=True)[
                "Close"
            ]
            df_benchmark.columns = ["SP500"]
        elif nome == "USD":
            df_benchmark = yf.download("BRL=X", start=data_inicio, end=data_fim, interval="1d", auto_adjust=True)[
                "Close"
            ]
            df_benchmark.columns = ["USD"]
        elif nome == "PTAX":
            df_benchmark = self.cambio_ptax(data_inicio, data_fim, compra=compra)
            df_benchmark.columns = ["PTAX", "Retorno PTAX", "Retorno Acumulado PTAX"]
            return df_benchmark
        else:
            df_benchmark = self.indices_anbima(data_inicio, data_fim, benchmark)

        df_benchmark[f"Retorno {nome}"] = df_benchmark[nome].pct_change()
        df_benchmark[f"Retorno Acumulado {nome}"] = (1 + df_benchmark[f"Retorno {nome}"]).cumprod() - 1
        return df_benchmark

    def benchmarks(
        self,
        data_inicio: str,
        data_fim: str,
        benchmark: list[str] | str = "CDI",
        metodo_cdi: str = "bacen",
        compra: bool = False,
    ) -> pd.DataFrame:
        """Função que provê o retorno de referências de mercado, aceitando um único benchmark
        ou uma lista deles (nesse caso, concatenados lado a lado por data, igual `stocks`).

        Implementa:
        -CDI (usa `metodo_cdi`: bacen/tesouro/anbima — ver `cdi` para detalhes);
        -PTAX (câmbio oficial BCB; usa `compra` — ver `cambio_ptax` para detalhes);
        -IBOV, DIVO11, SP500, USD (cotações via Yahoo Finance);
        -Índices ANBIMA: imas, imab, imab5, imab5+, imab5p2, irfm, irfmp2, ihfa,
         ida-di, ida-ipca, ida-geral (ver `indices_anbima` para detalhes).

        As datas devem ser no formato string '2025-01-02', ou seja, 'ANO-MES-DIA'.
        A saída gera o retorno diário e o acumulado para cada benchmark."""
        if isinstance(benchmark, list):
            resultado = pd.DataFrame()
            for bm in benchmark:
                df_bm = self._benchmark_unico(data_inicio, data_fim, bm, metodo_cdi, compra)
                resultado = pd.concat([resultado, df_bm], axis=1)
            return resultado

        return self._benchmark_unico(data_inicio, data_fim, benchmark, metodo_cdi, compra)
