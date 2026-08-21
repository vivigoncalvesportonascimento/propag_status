"""ETL: filtra e limpa as bases orçamentárias para o escopo do Propag
(fonte_cod == 89 ou ipu_cod == 0) e normaliza encoding/delimitador."""
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data-raw"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ANO_REFERENCIA = 2026


def parse_numero_br(valor) -> float:
    """Converte número no formato BR ('1.821.457.378,60') para float.
    Um traço isolado ('-') é uma convenção comum em tabelas financeiras
    brasileiras para valor zero/não aplicável e é tratado como 0.0."""
    texto = str(valor).strip()
    if texto in ("", "-"):
        return 0.0
    texto = texto.replace(".", "").replace(",", ".")
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


def transformar_plano_intervencoes(uo: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "propag_plano_intervencoes.csv", sep=";", encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df.rename(columns={"valor previsto": "valor_previsto"})
    df["valor_previsto"] = df["valor_previsto"].apply(parse_numero_br)
    df["uo_sigla_norm"] = df["uo_sigla"].apply(normalizar_sigla)

    uo_atual = uo[uo["ano"] == ANO_REFERENCIA].copy()
    uo_atual["uo_sigla_norm"] = uo_atual["uo_sigla_current"].apply(normalizar_sigla)
    df = df.merge(uo_atual[["uo_sigla_norm", "uo_cod", "uo_sigla_current"]], on="uo_sigla_norm", how="left")
    return df


def transformar_valor_a_ser_aplicado() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "propag_valor_a_ser_aplicado.csv", sep=";", encoding="latin-1")
    df["valor"] = df["valor"].apply(parse_numero_br)
    return df


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    uo = transformar_uo()
    acao = transformar_acao()
    area_tematica = transformar_area_tematica()
    uo.to_csv(DATA_DIR / "uo.csv", index=False)
    acao.to_csv(DATA_DIR / "acao.csv", index=False)
    area_tematica.to_csv(DATA_DIR / "area_tematica.csv", index=False)

    execucao = transformar_execucao(uo, acao, area_tematica)
    if execucao["uo_nome"].isna().any() or execucao["area_tematica"].isna().any():
        print("AVISO: execucao_propag tem linhas sem uo_nome ou area_tematica apos o merge")
    execucao.to_csv(DATA_DIR / "execucao_propag.csv", index=False)

    restos_pagar = transformar_restos_pagar(uo, acao, area_tematica)
    if restos_pagar["uo_nome"].isna().any() or restos_pagar["area_tematica"].isna().any():
        print("AVISO: restos_pagar_propag tem linhas sem uo_nome ou area_tematica apos o merge")
    restos_pagar.to_csv(DATA_DIR / "restos_pagar_propag.csv", index=False)

    receita = transformar_receita()
    receita.to_csv(DATA_DIR / "receita_propag.csv", index=False)

    plano = transformar_plano_intervencoes(uo)
    if plano["uo_cod"].isna().any():
        faltantes = plano.loc[plano["uo_cod"].isna(), "uo_sigla"].unique()
        print(f"AVISO: uo_sigla do plano sem correspondencia em uo.csv: {faltantes}")
    plano.to_csv(DATA_DIR / "plano_intervencoes.csv", index=False)

    valor_aplicado = transformar_valor_a_ser_aplicado()
    valor_aplicado.to_csv(DATA_DIR / "valor_a_ser_aplicado.csv", index=False)

    print(f"ETL concluido. Arquivos gravados em {DATA_DIR}")


if __name__ == "__main__":
    main()
