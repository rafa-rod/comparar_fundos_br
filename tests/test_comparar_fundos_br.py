# -*- coding: utf-8 -*-

import matplotlib

matplotlib.use("Agg")  # sem janela: CI e terminal

import io
import sys
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import comparar_fundos_br as cfb
from comparar_fundos_br import (
    DadosFinanceiros,
    calcula_rentabilidade_periodo,
    calcula_retorno_janelas_moveis,
    calcula_risco_retorno_fundos,
    get_classes,
    plotar_evolucao,
    plotar_heatmap_rentabilidade,
    pontua_cnpj,
    qto_supera_benchmark,
    remove_outliers,
    supera_benchmark,
)

FUNDOS = [
    "03.916.081/0001-62 // FUNDO ALFA",
    "06.916.384/0001-73 // FUNDO BETA",
    "11.111.111/0001-11 // FUNDO GAMA",
]


def _cotas(seed=0, inicio="2021-01-04", fim="2023-12-29"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(inicio, fim)
    retornos = rng.normal(0.0004, 0.01, (len(idx), len(FUNDOS)))
    return pd.DataFrame(100 * np.exp(np.cumsum(retornos, axis=0)), index=idx, columns=FUNDOS)


class _FakeResponse:
    def __init__(self, payload=None, content=b"", status_code=200):
        self._payload = payload
        self.content = content
        self.status_code = status_code

    def json(self):
        return self._payload


@pytest.fixture
def fake_sgs(monkeypatch):
    """Simula a API SGS do Banco Central: série com taxa constante por dia útil."""

    def fake_get(url, *args, **kwargs):
        serie = int(url.split("bcdata.sgs.")[1].split("/")[0])
        inicio = pd.to_datetime(url.split("dataInicial=")[1].split("&")[0], dayfirst=True)
        fim = pd.to_datetime(url.split("dataFinal=")[1].split("&")[0], dayfirst=True)
        valor = "0.05" if serie == 12 else "5.0000"
        return _FakeResponse(
            [{"data": d.strftime("%d/%m/%Y"), "valor": valor} for d in pd.bdate_range(inicio, fim)]
        )

    monkeypatch.setattr(cfb.benchmarks.requests, "get", fake_get)
    monkeypatch.setattr(cfb.benchmarks.time, "sleep", lambda s: None)


INFORME_DIARIO = """TP_FUNDO_CLASSE;CNPJ_FUNDO_CLASSE;ID_SUBCLASSE;DT_COMPTC;VL_TOTAL;VL_QUOTA;VL_PATRIM_LIQ;CAPTC_DIA;RESG_DIA;NR_COTST
CLASSES - FIF;03.916.081/0001-62;;2024-01-02;1000000.00;1.500000;990000.00;0.00;0.00;150
CLASSES - FIF;03.916.081/0001-62;;2024-01-03;1001000.00;1.501000;991000.00;0.00;0.00;151
CLASSES - FIF;06.916.384/0001-73;;2024-01-02;500000.00;2.000000;480000.00;0.00;0.00;5
CLASSES - FIF;06.916.384/0001-73;;2024-01-03;500100.00;2.001000;480100.00;0.00;0.00;5
FII;11.111.111/0001-11;;2024-01-02;100.00;1.000000;100.00;0.00;0.00;1000
"""


@pytest.fixture
def fake_cvm(monkeypatch):
    """Simula o zip do informe diário da CVM (jan/2024)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("inf_diario_fi_202401.csv", INFORME_DIARIO.encode("ISO-8859-1"))
    modulo = sys.modules["comparar_fundos_br.fundosbr"]
    monkeypatch.setattr(
        modulo, "_get_response", lambda url, proxy=None: _FakeResponse(content=buffer.getvalue())
    )


class TestClass:
    def setup_method(self):
        """Setup configurations executed before each test"""
        self.cotas = _cotas()

    def teardown_method(self):
        plt.close("all")

    # ==================== PACOTE ====================
    def test_version_matches_package_metadata(self):
        from importlib.metadata import version

        assert cfb.__version__ == version("comparar_fundos_br")

    # ==================== UTILITÁRIOS ====================
    def test_get_classes(self):
        assert "Ações" in get_classes()

    @pytest.mark.parametrize(
        "entrada", ["03916081000162", "3916081000162", "03.916.081/0001-62"]
    )
    def test_pontua_cnpj(self, entrada):
        assert pontua_cnpj(entrada) == "03.916.081/0001-62"

    # ==================== COMPARADOR ====================
    def test_calcula_risco_retorno_fundos(self):
        risco_retorno, diaria, normalizadas, acumulada, por_ano = calcula_risco_retorno_fundos(self.cotas)
        assert list(risco_retorno.columns) == ["volatilidade", "rentabilidade"]
        assert risco_retorno["rentabilidade"].is_monotonic_decreasing
        assert (normalizadas.iloc[0] == 1).all()
        assert list(por_ano.columns) == ["2021", "2022", "2023"]

        fundo = FUNDOS[0]
        T = len(self.cotas)
        esperado = (self.cotas[fundo].iloc[-1] / self.cotas[fundo].iloc[0]) ** (252 / T) - 1
        assert risco_retorno.loc[fundo, "rentabilidade"] == pytest.approx(esperado)
        vol = self.cotas[fundo].pct_change().std() * np.sqrt(252)
        assert risco_retorno.loc[fundo, "volatilidade"] == pytest.approx(vol)
        assert acumulada[fundo].iloc[-1] == pytest.approx(normalizadas[fundo].iloc[-1] - 1)

    def test_calcula_retorno_janelas_moveis(self):
        bench = self.cotas[[FUNDOS[1]]].rename(columns={FUNDOS[1]: "CDI"})
        janela = calcula_retorno_janelas_moveis(self.cotas[[FUNDOS[0]]], 21, bench)
        assert len(janela) == len(self.cotas) - 21
        esperado = self.cotas[FUNDOS[0]].iloc[21] / self.cotas[FUNDOS[0]].iloc[0] - 1
        assert janela[FUNDOS[0]].iloc[0] == pytest.approx(esperado)

    def test_calcula_rentabilidade_periodo(self):
        mensal = calcula_rentabilidade_periodo(self.cotas, "M")
        assert len(mensal) == 36
        jan = self.cotas.loc["2021-01", FUNDOS[0]]
        assert mensal[FUNDOS[0]].iloc[0] == pytest.approx(jan.iloc[-1] / jan.iloc[0] - 1)
        semestral = calcula_rentabilidade_periodo(self.cotas, "sem")
        assert semestral.dropna().index.month.isin([6, 12]).all()

    def test_supera_benchmark(self):
        fundo, bench = self.cotas[[FUNDOS[0]]], self.cotas[[FUNDOS[0]]] * 0.99
        bench.columns = ["CDI"]
        resultado = supera_benchmark(fundo * 1.0, bench, HP=21, limit=0.0)
        assert resultado.shape[0] == 1

        qto = qto_supera_benchmark(self.cotas[FUNDOS[:2]], self.cotas[[FUNDOS[2]]].set_axis(["CDI"], axis=1),
                                   HP=21, corte_bench=-1e9)
        assert {"% do CDI, em média"} <= set(qto.columns)
        assert len(qto) == 2

    def test_remove_outliers(self):
        retornos = self.cotas[[FUNDOS[0]]].pct_change().dropna()
        filtrado = remove_outliers(retornos, q=0.05)
        assert 0 < len(filtrado.dropna()) < len(retornos)

    def test_graficos(self):
        por_cnpj = plotar_evolucao(self.cotas, ["03.916.081/0001-62", "06.916.384/0001-73"])
        assert por_cnpj.shape[1] == 2
        por_nome = plotar_evolucao(self.cotas, ["ALFA", "BETA", "GAMA"])
        assert por_nome.shape[1] == 3
        plotar_heatmap_rentabilidade(self.cotas[[FUNDOS[0]]], "M")

    # ==================== FUNDOS CVM (SEM REDE) ====================
    def test_fundosbr(self, fake_cvm):
        informe = cfb.fundosbr(2024, 1)  # conversão polars -> pandas exige pyarrow
        assert isinstance(informe, pd.DataFrame)
        assert informe.index.name == "DT_COMPTC"
        assert set(informe["CNPJ_FUNDO"]) == {"03.916.081/0001-62", "06.916.384/0001-73"}  # FII fora
        assert informe["VL_QUOTA"].dtype == np.float32

        filtrado = cfb.fundosbr([2024], range(1, 2), num_minimo_cotistas=10, output_format="polars")
        assert filtrado["CNPJ_FUNDO"].unique().to_list() == ["03.916.081/0001-62"]
        por_cnpj = cfb.fundosbr(2024, 1, cnpj="06916384000173")
        assert set(por_cnpj["CNPJ_FUNDO"]) == {"06.916.384/0001-73"}

    # ==================== BENCHMARKS (SEM REDE) ====================
    def test_cdi_bacen(self, fake_sgs):
        cdi = DadosFinanceiros().cdi("2024-01-01", "2024-03-31", metodo_cdi="bacen")
        assert list(cdi.columns) == ["CDI", "Retorno CDI", "Retorno Acumulado CDI"]
        assert np.allclose(cdi["Retorno CDI"], 0.0005)
        n = len(cdi)
        assert cdi["Retorno Acumulado CDI"].iloc[-1] == pytest.approx(1.0005**n - 1)

    def test_cdi_metodo_invalido(self):
        with pytest.raises(ValueError):
            DadosFinanceiros().cdi("2024-01-01", "2024-03-31", metodo_cdi="outro")

    def test_ptax(self, fake_sgs):
        ptax = DadosFinanceiros().benchmarks("2024-01-01", "2024-01-31", benchmark="PTAX")
        assert list(ptax.columns) == ["PTAX", "Retorno PTAX", "Retorno Acumulado PTAX"]
        assert ptax["PTAX"].iloc[0] == pytest.approx(5.0)


# ==================== INTEGRAÇÃO (REDE) ====================
@pytest.mark.network
def test_fundos_cvm():
    informe = cfb.fundosbr(anos=range(2024, 2025), meses=range(1, 2))
    assert isinstance(informe, pd.DataFrame) and not informe.empty


@pytest.mark.network
def test_fidc_fip():
    assert not cfb.get_fidc(2024).empty
    assert not cfb.get_fip(2024).empty


@pytest.mark.network
def test_benchmarks_reais():
    dados = DadosFinanceiros()
    bmk = dados.benchmarks("2024-01-01", "2024-07-01", benchmark=["CDI", "IBOV", "imab"])
    assert {"CDI", "IBOV", "IMAB"} <= set(bmk.columns)
    acoes = dados.stocks(["PETR4", "VALE3"], "2024-01-01", "2024-07-01")
    assert not acoes.empty
