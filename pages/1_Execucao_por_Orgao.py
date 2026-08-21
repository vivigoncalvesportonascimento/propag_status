import plotly.express as px
import streamlit as st

from utils import COR_LIQUIDADO, carregar_execucao, carregar_valor_liquidado, formatar_reais

st.set_page_config(page_title="Propag MG — Execução por Órgão", layout="wide")
st.title("Execução por Órgão e Ação")

execucao = carregar_execucao()
liquidado = carregar_valor_liquidado()

col1, col2, col3 = st.columns(3)
uo_filtro = col1.multiselect("Órgão (UO)", sorted(execucao["uo_nome"].dropna().unique()))
area_filtro = col2.multiselect("Área temática", sorted(execucao["area_tematica"].dropna().unique()))
categoria_filtro = col3.multiselect("Categoria Propag", sorted(execucao["categoria_propag"].dropna().unique()))

filtrado = execucao.copy()
liquidado_filtrado = liquidado.copy()
if uo_filtro:
    filtrado = filtrado[filtrado["uo_nome"].isin(uo_filtro)]
    liquidado_filtrado = liquidado_filtrado[liquidado_filtrado["uo_nome"].isin(uo_filtro)]
if area_filtro:
    filtrado = filtrado[filtrado["area_tematica"].isin(area_filtro)]
    liquidado_filtrado = liquidado_filtrado[liquidado_filtrado["area_tematica"].isin(area_filtro)]
if categoria_filtro:
    filtrado = filtrado[filtrado["categoria_propag"].isin(categoria_filtro)]
    liquidado_filtrado = liquidado_filtrado[liquidado_filtrado["categoria_propag"].isin(categoria_filtro)]

if filtrado.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    empenhado_agg = filtrado.groupby(["uo_nome", "acao_desc"])["vlr_empenhado"].sum().reset_index()
    liquidado_agg = liquidado_filtrado.groupby(["uo_nome", "acao_desc"])["valor"].sum().reset_index()
    liquidado_agg = liquidado_agg.rename(columns={"valor": "vlr_liquidado"})

    tabela = empenhado_agg.merge(liquidado_agg, on=["uo_nome", "acao_desc"], how="left")
    tabela["vlr_liquidado"] = tabela["vlr_liquidado"].fillna(0)
    tabela["saldo"] = tabela["vlr_empenhado"] - tabela["vlr_liquidado"]
    tabela = tabela.rename(columns={
        "uo_nome": "Órgão", "acao_desc": "Ação",
        "vlr_empenhado": "Empenhado", "vlr_liquidado": "Liquidado", "saldo": "Saldo",
    }).sort_values("Liquidado", ascending=False)
    st.dataframe(
        tabela.style.format({"Empenhado": formatar_reais, "Liquidado": formatar_reais, "Saldo": formatar_reais}),
        width="stretch",
    )

    st.subheader("Ranking de órgãos por valor liquidado")
    ranking = liquidado_filtrado.groupby("uo_nome")["valor"].sum().reset_index().sort_values("valor", ascending=False)
    fig = px.bar(
        ranking, x="valor", y="uo_nome", orientation="h",
        color_discrete_sequence=[COR_LIQUIDADO],
        labels={"valor": "Valor liquidado (R$)", "uo_nome": "Órgão"},
    )
    fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig, width="stretch")
