from etl.transformar import (
    normalizar_sigla,
    parse_numero_br,
    transformar_acao,
    transformar_area_tematica,
    transformar_uo,
    transformar_execucao,
    transformar_plano_intervencoes,
    transformar_receita,
    transformar_restos_pagar,
    transformar_valor_a_ser_aplicado,
)


def test_parse_numero_br():
    assert parse_numero_br(" 575.047.787 ") == 575047787.0
    assert parse_numero_br("1.821.457.378,60") == 1821457378.60
    assert parse_numero_br("0,00") == 0.0
    assert parse_numero_br(" -   ") == 0.0


def test_normalizar_sigla():
    assert normalizar_sigla("DER/MG") == normalizar_sigla("DER-MG") == "DERMG"


def test_transformar_uo_tem_colunas_esperadas():
    uo = transformar_uo()
    assert {"ano", "uo_cod", "uo_nome", "uo_sigla", "uo_sigla_current"}.issubset(uo.columns)


def test_transformar_area_tematica_decodifica_acentos():
    area = transformar_area_tematica()
    assert "Segurança Pública" in area["area_tematica"].unique()


def test_execucao_sem_sobreposicao_fonte_e_ipu():
    uo, acao, area = transformar_uo(), transformar_acao(), transformar_area_tematica()
    execucao = transformar_execucao(uo, acao, area)
    sobreposicao = (execucao["fonte_cod"] == 89) & (execucao["ipu_cod"] == 0)
    assert not sobreposicao.any()


def test_execucao_sem_linhas_orfas_de_dimensao():
    uo, acao, area = transformar_uo(), transformar_acao(), transformar_area_tematica()
    execucao = transformar_execucao(uo, acao, area)
    assert execucao["uo_nome"].notna().all()
    assert execucao["area_tematica"].notna().all()


def test_restos_pagar_sem_sobreposicao_fonte_e_ipu():
    uo, acao, area = transformar_uo(), transformar_acao(), transformar_area_tematica()
    restos_pagar = transformar_restos_pagar(uo, acao, area)
    sobreposicao = (restos_pagar["fonte_cod"] == 89) & (restos_pagar["ipu_cod"] == 0)
    assert not sobreposicao.any()


def test_restos_pagar_sem_linhas_orfas_de_dimensao():
    uo, acao, area = transformar_uo(), transformar_acao(), transformar_area_tematica()
    restos_pagar = transformar_restos_pagar(uo, acao, area)
    assert restos_pagar["uo_nome"].notna().all()
    assert restos_pagar["area_tematica"].notna().all()


def test_valor_liquidado_total_positivo():
    uo, acao, area = transformar_uo(), transformar_acao(), transformar_area_tematica()
    execucao = transformar_execucao(uo, acao, area)
    restos_pagar = transformar_restos_pagar(uo, acao, area)
    total = execucao["vlr_liquidado"].sum() + restos_pagar["vlr_despesa_liquidada_rpnp"].sum()
    assert total > 0


def test_receita_so_tem_fonte_89():
    receita = transformar_receita()
    assert (receita["fonte_cod"] == 89).all()
    assert len(receita) == 10


def test_todas_uo_do_plano_existem_em_uo():
    uo = transformar_uo()
    plano = transformar_plano_intervencoes(uo)
    sem_match = plano.loc[plano["uo_cod"].isna(), "uo_sigla"].unique()
    assert plano["uo_cod"].notna().all(), f"uo_sigla sem correspondencia em uo.csv: {sem_match}"


def test_valor_a_ser_aplicado_bate_com_plano_v3():
    uo = transformar_uo()
    plano_v3 = transformar_plano_intervencoes(uo)
    plano_v3 = plano_v3[plano_v3["plano"] == "v3"]
    valor_aplicado = transformar_valor_a_ser_aplicado()
    limite_total = valor_aplicado.loc[
        valor_aplicado["descricao"].str.startswith("Valor mínimo a ser aplicado"), "valor"
    ].sum()
    # o plano v3 e o total dos dois limites (FEF + Investimentos Proprios) devem
    # bater dentro de um centavo de arredondamento por linha do plano
    assert abs(plano_v3["valor_previsto"].sum() - limite_total) < 1.0
