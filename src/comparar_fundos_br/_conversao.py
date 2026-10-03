# -*- coding: utf-8 -*-
"""Conversão de Polars para pandas sem depender do pyarrow."""

import pandas as pd
import polars as pl


def _para_pandas(df: pl.DataFrame) -> pd.DataFrame:
    """Equivalente a `df.to_pandas()`, coluna a coluna via NumPy.

    O `to_pandas` do Polars exige o pyarrow, que não tem wheels para algumas
    plataformas (ex.: macOS 11 Intel) e pesa dezenas de MB. Datas, números e
    textos convertem direto; inteiros com nulos viram float, como no pyarrow.
    """
    return pd.DataFrame({coluna: df[coluna].to_numpy() for coluna in df.columns})
