import streamlit as st
import plotly.express as px

from utils import (
    COR_EMPENHADO,
    COR_EXECUTADO,
    COR_LIQUIDADO,
    COR_PLANEJADO,
    carregar_execucao,
    carregar_plano_intervencoes,
    carregar_valor_liquidado,
    formatar_reais,
    obter_limites,
)

st.set_page_config(page_title="Propag MG — Visão Geral", layout="wide")
st.title("Propag — Visão Geral 2026")

CATEGORIAS = ["Investimentos Próprios", "FEF"]

limites = obter_limites()
liquidado = carregar_valor_liquidado()
liquidado_por_categoria = liquidado.groupby("categoria_propag")["valor"].sum()


def render_cards(coluna, titulo: str, limite: float, valor_liquidado: float) -> None:
    saldo = limite - valor_liquidado
    percentual = (valor_liquidado / limite * 100) if limite else 0
    with coluna:
        st.subheader(titulo)
        st.metric("Limite 2026", formatar_reais(limite))
        st.metric("Liquidado", formatar_reais(valor_liquidado))
        st.metric("Saldo a liquidar", formatar_reais(saldo))
        st.metric("% cumprido", f"{percentual:.1f}%")


colunas_cards = st.columns(len(CATEGORIAS) + 1)
limite_total = sum(limites.values())
liquidado_total = liquidado_por_categoria.sum()
render_cards(colunas_cards[0], "Total Propag", limite_total, liquidado_total)
for coluna, categoria in zip(colunas_cards[1:], CATEGORIAS):
    render_cards(coluna, categoria, limites.get(categoria, 0), liquidado_por_categoria.get(categoria, 0))

st.divider()
st.subheader("Ritmo de execução mensal")
categoria_filtro = st.selectbox("Categoria", ["Todas"] + CATEGORIAS)
execucao = carregar_execucao()
if categoria_filtro != "Todas":
    execucao = execucao[execucao["categoria_propag"] == categoria_filtro]

mensal = execucao.groupby("mes_cod")[["vlr_empenhado", "vlr_liquidado"]].sum().reset_index()
mensal = mensal.rename(columns={"vlr_empenhado": "Empenhado", "vlr_liquidado": "Liquidado"})
mensal_longo = mensal.melt(id_vars="mes_cod", value_vars=["Empenhado", "Liquidado"], var_name="Etapa", value_name="Valor")

if mensal_longo.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    fig_mensal = px.bar(
        mensal_longo, x="mes_cod", y="Valor", color="Etapa", barmode="group",
        color_discrete_map={"Empenhado": COR_EMPENHADO, "Liquidado": COR_LIQUIDADO},
        labels={"mes_cod": "Mês", "Valor": "Valor (R$)"},
    )
    st.plotly_chart(fig_mensal, use_container_width=True)

st.divider()
st.subheader("Planejado (Plano v3) x Executado, por órgão e área temática")

plano = carregar_plano_intervencoes()
plano_v3 = plano[plano["plano"] == "v3"]
areas_disponiveis = sorted(plano_v3["area_tematica"].dropna().unique())
area_filtro = st.selectbox("Área temática", ["Todas"] + areas_disponiveis)

plano_agg = plano_v3.groupby(["uo_sigla_current", "area_tematica"])["valor_previsto"].sum().reset_index()
plano_agg = plano_agg.rename(columns={"valor_previsto": "Planejado"})

executado_agg = liquidado.groupby(["uo_sigla_current", "area_tematica"])["valor"].sum().reset_index()
executado_agg = executado_agg.rename(columns={"valor": "Executado"})

comparacao = plano_agg.merge(executado_agg, on=["uo_sigla_current", "area_tematica"], how="outer").fillna(0)
comparacao["rotulo"] = comparacao["uo_sigla_current"] + " — " + comparacao["area_tematica"]
comparacao["gap"] = comparacao["Planejado"] - comparacao["Executado"]

if area_filtro != "Todas":
    comparacao = comparacao[comparacao["area_tematica"] == area_filtro]
comparacao = comparacao.sort_values("gap", ascending=False)

comparacao_longa = comparacao.melt(id_vars="rotulo", value_vars=["Planejado", "Executado"], var_name="Tipo", value_name="Valor")

if comparacao.empty:
    st.info("Nenhum dado para os filtros selecionados.")
else:
    fig_comparacao = px.bar(
        comparacao_longa, x="Valor", y="rotulo", color="Tipo", barmode="group", orientation="h",
        color_discrete_map={"Planejado": COR_PLANEJADO, "Executado": COR_EXECUTADO},
        labels={"rotulo": "Órgão — Área temática", "Valor": "Valor (R$)"},
    )
    st.plotly_chart(fig_comparacao, use_container_width=True)
