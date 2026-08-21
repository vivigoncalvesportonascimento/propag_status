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
