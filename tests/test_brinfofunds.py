import getpass
import os
import sys

import numpy as np
import pandas as pd
import pytest

import matplotlib.pyplot as plt
import seaborn as sns; sns.set()

path = "../comparar_fundos_br/"
sys.path.append(path)

from comparar_fundos_br import *

class TestClass():

      def __init__(self):
            user = os.getenv("userid").lower()
            senha = ""
            self.proxy = {
                        "http": f"http://{user}:{senha}@proxy.inf.bndes.net:8080",
                        "https": f"https://{user}:{senha}@proxy.inf.bndes.net:8080",
                        }
            self.test_getfunds()
            self.test_benchmarks()
            self.comparador()

      def test_getfunds(self):
            self.informe_diario_fundos = get_brfunds(anos=range(2021,2022), #somente 2021
                                                     meses = range(1,3),  #somente Jan e Fev
                                                     classe="Fundo de Ações", 
                                                     num_minimo_cotistas=10, 
                                                     patriminio_liquido_minimo=1_000_000, 
                                                     proxy=self.proxy
                                                     )
            assert isinstance(self.informe_diario_fundos, pd.core.frame.DataFrame)
            with pytest.raises(Exception) as error1:
                informe_diario_fundos = get_brfunds(2022, 7, classe=["Fundo ABC"], proxy=self.proxy)
            with pytest.raises(Exception) as error2:
                informe_diario_fundos = get_brfunds(2022, 7, proxy={"teste":"teste"})
            with pytest.raises(Exception) as error3:
                informe_diario_fundos = get_brfunds(2022, 7, proxy=None)

            assert str(error1.value) == "Classe não encontrada ['Fundo ABC']"
            assert str(error2.value) == "Verifique se a proxy está correta. ParserError: Error tokenizing data"
            assert str(error3.value) == "Informar proxy. HTTPError: authenticationrequired"

            fidc = get_fidc(2022, 6, proxy=self.proxy)
            assert isinstance(fidc, pd.core.frame.DataFrame)
            fip = get_fip(2022, proxy=self.proxy)
            assert isinstance(fip, pd.core.frame.DataFrame)

            with pytest.raises(Exception) as error5:
                fidc = get_fidc(2022, 7, proxy={"teste":"teste"})
            with pytest.raises(Exception) as error6:
                fip = get_fip(2022, proxy={"teste":"teste"})
            with pytest.raises(Exception) as error7:
                fidc = get_fidc(2022, 7, proxy=self.proxy)

            assert str(error5.value) == "Necessário informar proxy correta. Response [407]"
            assert str(error6.value) == "Necessário informar proxy correta. Response [407]"
            assert str(error7.value) == "Não há dados para esta data. Response [404]"

      def test_benchmarks(self):
            cdi, cdi_acumulado = get_benchmark("2022-01-01", "2022-07-01", proxy=self.proxy)
            assert isinstance(cdi, pd.core.frame.DataFrame)
            assert isinstance(cdi_acumulado, pd.core.frame.DataFrame)
            ibov, indice_ibov_acumulado = get_benchmark("2022-01-01", "2022-07-01", benchmark="ibov", proxy=self.proxy)
            assert isinstance(ibov, pd.core.frame.DataFrame)
            stocks = get_stocks(["PETR4, VALE3"],"2022-01-01", "2022-07-01", proxy=self.proxy)
            assert isinstance(stocks, pd.core.frame.DataFrame)
            stocks1 = get_stocks("PETR4","2022-01-01", "2022-07-01", proxy=self.proxy)
            assert isinstance(stocks1, pd.core.frame.DataFrame)
            with pytest.raises(Exception) as error8:
                cdi, cdi_acumulado = get_benchmark("2022-01-01", "2022-07-01", benchmark="selic", proxy=self.proxy)
            assert str(error8.value) == "Benchmark não encontrado."

      def comparador(self):
            (
                risco_retorno,
                cotas_normalizadas,
                rentabilidade_media_anualizada,
                rentabilidade_acumulada_por_ano,
                rentabilidade_fundos_total,
            ) = calcula_rentabilidade_fundos(self.informe_diario_fundos)
            assert isinstance(risco_retorno, pd.core.frame.DataFrame)
            melhores_fundos, piores_fundos = melhores_e_piores_fundos(rentabilidade_fundos_total, num=10)
            assert isinstance(melhores_fundos, pd.core.frame.DataFrame)
            assert isinstance(piores_fundos, pd.core.frame.DataFrame)
            fundos_maior_risco, fundos_menor_risco = melhores_e_piores_fundos(risco_retorno[["volatilidade"]], num=10)
            assert isinstance(fundos_maior_risco, pd.core.frame.DataFrame)
            assert isinstance(fundos_menor_risco, pd.core.frame.DataFrame)

            _ = plotar_evolucao(
                        cotas_normalizadas,
                        lista_fundos=["03.916.081/0001-62","06.916.384/0001-73"],
                        figsize=(15, 5),
                        color="darkblue",
                        alpha=0.8
            )
            plt.title("Evolução dos Fundos")
            plt.show()

            df4 = risco_retorno[
                (risco_retorno["volatilidade"] <= 40)
                & (risco_retorno["rentabilidade"] >= 0)
                & (risco_retorno["rentabilidade"] <= 100)
                ]

            plotar_comparacao_risco_retorno(
                                            df4,
                                            (21, 18), #(risco, retorno) da minha carteira
                                            (19, 15), #(risco, retorno) do benchmark
                                            nome_carteira="Minha Carteira",
                                            nome_benchmark="Benchmark",
                                            figsize=(15, 5),
                                            posicao_texto_carteira=(30, 25),
                                            posicao_texto_benchmark=(31, -25),
                                            )
            plt.title("Risco x Retorno - Fundos de Ações")
            plt.ylim(-10, 140)
            plt.xlim(-3, 60)
            plt.show()


TestClass()