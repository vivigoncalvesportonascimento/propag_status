from etl.transformar import (
    normalizar_sigla,
    parse_numero_br,
    transformar_acao,
    transformar_area_tematica,
    transformar_uo,
)


def test_parse_numero_br():
    assert parse_numero_br(" 575.047.787 ") == 575047787.0
    assert parse_numero_br("1.821.457.378,60") == 1821457378.60
    assert parse_numero_br("0,00") == 0.0


def test_normalizar_sigla():
    assert normalizar_sigla("DER/MG") == normalizar_sigla("DER-MG") == "DERMG"


def test_transformar_uo_tem_colunas_esperadas():
    uo = transformar_uo()
    assert {"ano", "uo_cod", "uo_nome", "uo_sigla", "uo_sigla_current"}.issubset(uo.columns)


def test_transformar_area_tematica_decodifica_acentos():
    area = transformar_area_tematica()
    assert "Segurança Pública" in area["area_tematica"].unique()
