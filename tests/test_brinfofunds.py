import getpass
import os
import sys

import numpy as np
import pandas as pd
import pytest

path = "../comparebrfunds/"
sys.path.append(path)

from comparebrfunds import *

class TestClass():

      def __init__(self):
            #user = os.getenv("userid").lower()
            #senha = ""
            self.proxy = None#{
                        #"http": f"http://{user}:{senha}@proxy.inf.bndes.net:8080",
                        #"https": f"https://{user}:{senha}@proxy.inf.bndes.net:8080",
                        #}
            self.test_getfunds()
            self.test_benchmarks()
            self.comparador()

      def test_getfunds(self):
            self.informe_diario_fundos = get_brfunds(2022, 7, proxy=self.proxy)
            assert isinstance(self.informe_diario_fundos, pd.core.frame.DataFrame)
            cadastro_fundos = get_fundsregistration(classe="Fundo de Ações", proxy=self.proxy)
            assert isinstance(cadastro_fundos, pd.core.frame.DataFrame)
            cadastro_fundos = get_fundsregistration(proxy=self.proxy)
            assert isinstance(cadastro_fundos, pd.core.frame.DataFrame)
            cadastro_fundos = get_fundsregistration(classe=["Fundo de Ações","Fundo de Renda Fixa"], proxy=self.proxy)
            assert isinstance(cadastro_fundos, pd.core.frame.DataFrame)

            with pytest.raises(Exception) as error1:
                cadastro_fundos = get_fundsregistration(classe=["Fundo ABC"], proxy=self.proxy)
            with pytest.raises(Exception) as error2:
                cadastro_fundos = get_fundsregistration(proxy={"teste":"teste"})
            with pytest.raises(Exception) as error3:
                cadastro_fundos = get_brfunds(2022, 7, proxy={"teste":"teste"})
            with pytest.raises(Exception) as error4:
                cadastro_fundos = get_fundsregistration(proxy=None)

            assert str(error1.value) == "Classe não encontrada ['Fundo ABC']"
            assert str(error2.value) == "Verifique se a proxy está correta. ParserError: Error tokenizing data"
            assert str(error3.value) == "Necessário informar proxy correta. Response [407]"
            assert str(error4.value) == "Informar proxy. HTTPError: authenticationrequired"

            fidc = get_fidc(2022, 6, proxy=self.proxy)
            assert isinstance(fidc, pd.core.frame.DataFrame)
            fip = get_fip(2022, proxy=self.proxy)
            assert isinstance(fip, pd.core.frame.DataFrame)

            with pytest.raises(Exception) as error5:
                fidc = get_fidc(2022, 7, proxy={"teste":"teste"})
            with pytest.raises(Exception) as error6:
                fip = get_fip(2022, 7, proxy={"teste":"teste"})
            with pytest.raises(Exception) as error7:
                fidc = get_fidc(2022, 7, proxy=self.proxy)

            assert str(error5.value) == "Necessário informar proxy correta. Response [407]"
            assert str(error6.value) == "Necessário informar proxy correta. Response [407]"
            assert str(error7.value) == "Não há dados para esta data. Response [404]"

      def test_benchmarks(self):
            cdi, cdi_acumulado = get_cdi("2022-01-01", "2022-07-01", proxy=self.proxy)
            assert isinstance(cdi, pd.core.frame.DataFrame)
            assert isinstance(cdi_acumulado, pd.core.frame.DataFrame)
            ibov = get_ibovespa("2022-01-01", "2022-07-01", proxy=self.proxy)
            assert isinstance(ibov, pd.core.frame.DataFrame)
            stocks = get_stocks(["PETR4, VALE3"],"2022-01-01", "2022-07-01", proxy=self.proxy)
            assert isinstance(stocks, pd.core.frame.DataFrame)
            stocks1 = get_stocks("PETR4","2022-01-01", "2022-07-01", proxy=self.proxy)
            assert isinstance(stocks1, pd.core.frame.DataFrame)

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

TestClass()