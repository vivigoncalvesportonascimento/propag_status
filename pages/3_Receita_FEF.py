import plotly.express as px
import streamlit as st

from utils import COR_EXECUTADO, COR_PLANEJADO, carregar_receita, formatar_reais, obter_limites

st.set_page_config(page_title="Propag MG — Receita do FEF", layout="wide")
st.title("Receita do FEF (fonte 89)")

limites = obter_limites()
st.info(
    f"A lei permite arrecadar num exercício e aplicar no seguinte. O saldo do FEF recebido em "
    f"2025 e a aplicar em 2026 é {formatar_reais(limites.get('FEF', 0))} — esse é o limite mínimo "
    f"que a página Visão Geral acompanha para a categoria FEF."
)

receita = carregar_receita()
total_previsto = receita["vlr_previsto_atualizado"].sum()
total_arrecadado = receita["vlr_efetivado_ajustado"].sum()

col1, col2 = st.columns(2)
col1.metric("Previsto atualizado (2026)", formatar_reais(total_previsto))
col2.metric("Arrecadado até o momento", formatar_reais(total_arrecadado))

mensal = receita.groupby("mes_cod")[["vlr_previsto_atualizado", "vlr_efetivado_ajustado"]].sum().reset_index()
mensal = mensal.rename(columns={
    "vlr_previsto_atualizado": "Previsto atualizado", "vlr_efetivado_ajustado": "Arrecadado",
})
mensal_longo = mensal.melt(id_vars="mes_cod", value_vars=["Previsto atualizado", "Arrecadado"], var_name="Tipo", value_name="Valor")

if mensal_longo.empty:
    st.info("Nenhum dado disponível.")
else:
    fig = px.bar(
        mensal_longo, x="mes_cod", y="Valor", color="Tipo", barmode="group",
        color_discrete_map={"Previsto atualizado": COR_PLANEJADO, "Arrecadado": COR_EXECUTADO},
        labels={"mes_cod": "Mês", "Valor": "Valor (R$)"},
    )
    st.plotly_chart(fig, width="stretch")
