import plotly.express as px
import streamlit as st

from utils import carregar_plano_intervencoes, formatar_reais

st.set_page_config(page_title="Propag MG — Plano de Intervenções", layout="wide")
st.title("Plano de Intervenções")
st.info(
    "EPT entra como uma linha única consolidada (tem plano de aplicação próprio, à parte). "
    "Ainda não há valor executado por intervenção — apenas o valor planejado."
)

plano = carregar_plano_intervencoes()

col1, col2, col3 = st.columns(3)
versao_filtro = col1.selectbox("Versão do plano", sorted(plano["plano"].unique(), reverse=True))
area_filtro = col2.multiselect("Área temática", sorted(plano["area_tematica"].dropna().unique()))
uo_filtro = col3.multiselect("Órgão (UO)", sorted(plano["uo_sigla"].dropna().unique()))

filtrado = plano[plano["plano"] == versao_filtro]
if area_filtro:
    filtrado = filtrado[filtrado["area_tematica"].isin(area_filtro)]
if uo_filtro:
    filtrado = filtrado[filtrado["uo_sigla"].isin(uo_filtro)]

if filtrado.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    tabela = filtrado[["area_tematica", "uo_sigla", "intervencao", "valor_previsto"]].rename(columns={
        "area_tematica": "Área temática", "uo_sigla": "Órgão",
        "intervencao": "Intervenção", "valor_previsto": "Valor previsto",
    }).sort_values("Valor previsto", ascending=False)
    st.dataframe(tabela.style.format({"Valor previsto": formatar_reais}), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Valor previsto por área temática")
        por_area = filtrado.groupby("area_tematica")["valor_previsto"].sum().reset_index().sort_values("valor_previsto", ascending=False)
        fig_area = px.bar(
            por_area, x="area_tematica", y="valor_previsto",
            color_discrete_sequence=["#2a78d6"],
            labels={"area_tematica": "Área temática", "valor_previsto": "Valor previsto (R$)"},
        )
        st.plotly_chart(fig_area, use_container_width=True)
    with col_b:
        st.subheader("Valor previsto por órgão")
        por_uo = filtrado.groupby("uo_sigla")["valor_previsto"].sum().reset_index().sort_values("valor_previsto", ascending=False)
        fig_uo = px.bar(
            por_uo, x="uo_sigla", y="valor_previsto",
            color_discrete_sequence=["#eb6834"],
            labels={"uo_sigla": "Órgão", "valor_previsto": "Valor previsto (R$)"},
        )
        st.plotly_chart(fig_uo, use_container_width=True)
