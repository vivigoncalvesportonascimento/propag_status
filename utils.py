"""Carregamento com cache e formatacao compartilhados pelas paginas do painel."""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"

COR_PLANEJADO = "#2a78d6"
COR_EXECUTADO = "#1baf7a"
COR_EMPENHADO = "#2a78d6"
COR_LIQUIDADO = "#eb6834"


@st.cache_data
def carregar_uo() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "uo.csv")


@st.cache_data
def carregar_execucao() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "execucao_propag.csv")


@st.cache_data
def carregar_restos_pagar() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "restos_pagar_propag.csv")


@st.cache_data
def carregar_receita() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "receita_propag.csv")


@st.cache_data
def carregar_plano_intervencoes() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "plano_intervencoes.csv")


@st.cache_data
def carregar_valor_a_ser_aplicado() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "valor_a_ser_aplicado.csv")


@st.cache_data
def carregar_valor_liquidado() -> pd.DataFrame:
    """Combina execucao (vlr_liquidado) e restos a pagar (vlr_despesa_liquidada_rpnp)
    numa unica coluna 'valor', com uma coluna 'origem' indicando a base de origem."""
    colunas = ["ano", "mes_cod", "uo_cod", "uo_sigla_current", "uo_nome", "acao_cod",
               "acao_desc", "area_tematica", "categoria_propag", "origem", "valor"]

    execucao = carregar_execucao().rename(columns={"vlr_liquidado": "valor"}).copy()
    execucao["origem"] = "execucao"

    restos_pagar = carregar_restos_pagar().rename(columns={"vlr_despesa_liquidada_rpnp": "valor"}).copy()
    restos_pagar["origem"] = "rpnp"

    return pd.concat([execucao[colunas], restos_pagar[colunas]], ignore_index=True)


def formatar_reais(valor: float) -> str:
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def obter_limites() -> dict[str, float]:
    df = carregar_valor_a_ser_aplicado()
    limites = df[df["descricao"].str.startswith("Valor mínimo a ser aplicado")]
    return dict(zip(limites["tipo_recurso"], limites["valor"]))
