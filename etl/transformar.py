"""ETL: filtra e limpa as bases orçamentárias para o escopo do Propag
(fonte_cod == 89 ou ipu_cod == 0) e normaliza encoding/delimitador."""
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data-raw"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ANO_REFERENCIA = 2026


def parse_numero_br(valor) -> float:
    """Converte número no formato BR ('1.821.457.378,60') para float."""
    texto = str(valor).strip().replace(".", "").replace(",", ".")
    return float(texto)


def normalizar_sigla(sigla: str) -> str:
    """Normaliza sigla de UO para comparação (remove '/', '-', espaços, uppercase)."""
    return str(sigla).upper().replace("/", "").replace("-", "").replace(" ", "")


def categoria_propag(fonte_cod) -> str:
    return "FEF" if fonte_cod == 89 else "Investimentos Próprios"


def filtrar_propag(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra linhas do escopo Propag e adiciona a coluna categoria_propag."""
    filtrado = df[(df["fonte_cod"] == 89) | (df["ipu_cod"] == 0)].copy()
    filtrado["categoria_propag"] = filtrado["fonte_cod"].apply(categoria_propag)
    return filtrado


def transformar_uo() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "uo.csv")


def transformar_acao() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "acao.csv")


def transformar_area_tematica() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "area_tematica.csv", sep=";", encoding="latin-1")


def _juntar_dimensoes(df: pd.DataFrame, uo: pd.DataFrame, acao: pd.DataFrame, area_tematica: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(uo[["ano", "uo_cod", "uo_nome", "uo_sigla", "uo_sigla_current"]], on=["ano", "uo_cod"], how="left")
    df = df.merge(acao[["ano", "acao_cod", "acao_desc"]], on=["ano", "acao_cod"], how="left")
    df = df.merge(area_tematica[["ano", "uo_cod", "acao_cod", "area_tematica"]], on=["ano", "uo_cod", "acao_cod"], how="left")
    return df


def transformar_execucao(uo: pd.DataFrame, acao: pd.DataFrame, area_tematica: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "execucao.csv.gz", compression="gzip")
    df = filtrar_propag(df)
    colunas = ["ano", "mes_cod", "uo_cod", "acao_cod", "fonte_cod", "ipu_cod",
               "categoria_propag", "vlr_empenhado", "vlr_liquidado", "vlr_pago_orcamentario"]
    df = df[colunas]
    return _juntar_dimensoes(df, uo, acao, area_tematica)


def transformar_restos_pagar(uo: pd.DataFrame, acao: pd.DataFrame, area_tematica: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "restos_pagar.csv.gz", compression="gzip")
    df = filtrar_propag(df)
    colunas = ["ano", "ano_rp", "mes_cod", "uo_cod", "acao_cod", "fonte_cod", "ipu_cod",
               "categoria_propag", "vlr_despesa_liquidada_rpnp"]
    df = df[colunas]
    return _juntar_dimensoes(df, uo, acao, area_tematica)


def transformar_receita() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "receita.csv.gz", compression="gzip")
    return df[df["fonte_cod"] == 89].copy()
