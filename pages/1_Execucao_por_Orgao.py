import plotly.express as px
import streamlit as st

from utils import carregar_execucao, formatar_reais

st.set_page_config(page_title="Propag MG — Execução por Órgão", layout="wide")
st.title("Execução por Órgão e Ação")

execucao = carregar_execucao()

col1, col2, col3 = st.columns(3)
uo_filtro = col1.multiselect("Órgão (UO)", sorted(execucao["uo_nome"].dropna().unique()))
area_filtro = col2.multiselect("Área temática", sorted(execucao["area_tematica"].dropna().unique()))
categoria_filtro = col3.multiselect("Categoria Propag", sorted(execucao["categoria_propag"].dropna().unique()))

filtrado = execucao.copy()
if uo_filtro:
    filtrado = filtrado[filtrado["uo_nome"].isin(uo_filtro)]
if area_filtro:
    filtrado = filtrado[filtrado["area_tematica"].isin(area_filtro)]
if categoria_filtro:
    filtrado = filtrado[filtrado["categoria_propag"].isin(categoria_filtro)]

if filtrado.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    tabela = filtrado.groupby(["uo_nome", "acao_desc"])[["vlr_empenhado", "vlr_liquidado"]].sum().reset_index()
    tabela["saldo"] = tabela["vlr_empenhado"] - tabela["vlr_liquidado"]
    tabela = tabela.rename(columns={
        "uo_nome": "Órgão", "acao_desc": "Ação",
        "vlr_empenhado": "Empenhado", "vlr_liquidado": "Liquidado", "saldo": "Saldo",
    }).sort_values("Liquidado", ascending=False)
    st.dataframe(
        tabela.style.format({"Empenhado": formatar_reais, "Liquidado": formatar_reais, "Saldo": formatar_reais}),
        use_container_width=True,
    )

    st.subheader("Ranking de órgãos por valor liquidado")
    ranking = filtrado.groupby("uo_nome")["vlr_liquidado"].sum().reset_index().sort_values("vlr_liquidado", ascending=False)
    fig = px.bar(
        ranking, x="vlr_liquidado", y="uo_nome", orientation="h",
        color_discrete_sequence=["#2a78d6"],
        labels={"vlr_liquidado": "Valor liquidado (R$)", "uo_nome": "Órgão"},
    )
    st.plotly_chart(fig, use_container_width=True)
