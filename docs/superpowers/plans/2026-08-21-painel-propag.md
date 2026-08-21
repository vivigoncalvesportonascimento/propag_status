# Painel Propag MG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the v1 Streamlit dashboard that monitors Minas Gerais's Propag compliance in 2026, backed by a committed ETL pipeline that filters the raw budget bases to Propag scope.

**Architecture:** A single `etl/transformar.py` script reads `data-raw/`, applies the Propag filter (`fonte_cod == 89 OR ipu_cod == 0`), fixes encoding/delimiter inconsistencies, joins in dimension attributes, and writes clean UTF-8 CSVs to `data/`. A native multi-page Streamlit app (`app.py` + `pages/`) reads only from `data/` through cached loaders in `utils.py`, never touching `data-raw/` directly.

**Tech Stack:** Python 3.13, Streamlit, pandas, Plotly (new), pytest (new, dev-only), Poetry.

**Spec:** [docs/superpowers/specs/2026-08-21-painel-propag-design.md](../specs/2026-08-21-painel-propag-design.md)

## Global Constraints

- Propag filter on every fact table except receita: `fonte_cod == 89 OR ipu_cod == 0`. Receita uses `fonte_cod == 89` only.
- Derived column `categoria_propag` = `"FEF"` if `fonte_cod == 89` else `"Investimentos Próprios"` — these exact strings must match `tipo_recurso` in `propag_valor_a_ser_aplicado.csv` (verified: no row has `fonte_cod == 89 AND ipu_cod == 0` at the same time, so the two categories never overlap).
- All files in `data/` are UTF-8, comma-separated, dot-decimal — no exceptions.
- `credito.csv.gz`, `cota.csv.gz`, `elemento_item.csv`, `fonte_recurso.csv` are out of scope for v1 — do not transform or reference them.
- `requires-python = ">=3.13"` (already set in `pyproject.toml`) — do not lower it.
- The app only reads from `data/`, never from `data-raw/` — this is what keeps the published Streamlit Cloud app fast and the data lineage auditable.

---

### Task 1: ETL foundations — helpers and dimension tables

**Files:**
- Create: `etl/__init__.py`
- Create: `etl/transformar.py`
- Create: `tests/__init__.py`
- Create: `tests/test_etl.py`
- Modify: `pyproject.toml` (add `pytest` as dev dependency)

**Interfaces:**
- Produces (in `etl/transformar.py`):
  - `RAW_DIR: Path` — `data-raw/` resolved relative to this file
  - `DATA_DIR: Path` — `data/` resolved relative to this file
  - `ANO_REFERENCIA: int = 2026`
  - `parse_numero_br(valor) -> float` — turns `" 575.047.787 "` / `"1.821.457.378,60"` into a float
  - `normalizar_sigla(sigla: str) -> str` — uppercase, strips `/`, `-`, and spaces (so `"DER/MG"` and `"DER-MG"` compare equal)
  - `categoria_propag(fonte_cod) -> str` — `"FEF"` if `fonte_cod == 89` else `"Investimentos Próprios"`
  - `filtrar_propag(df: pd.DataFrame) -> pd.DataFrame` — filters `fonte_cod == 89 OR ipu_cod == 0` and adds `categoria_propag` column
  - `transformar_uo() -> pd.DataFrame`
  - `transformar_acao() -> pd.DataFrame`
  - `transformar_area_tematica() -> pd.DataFrame`

Run `poetry add --group dev pytest` first (needed for `tests/test_etl.py` in this and later tasks).

- [ ] **Step 1: Add pytest dev dependency**

Run: `poetry add --group dev pytest`
Expected: `pyproject.toml` gains a `[tool.poetry.group.dev.dependencies]` section with `pytest`, and `poetry.lock` is updated.

- [ ] **Step 2: Create `etl/__init__.py` (empty) and `tests/__init__.py` (empty)**

- [ ] **Step 3: Write `etl/transformar.py` with helpers and dimension transforms**

```python
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
```

- [ ] **Step 4: Write the failing tests for the helpers**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `poetry run pytest tests/test_etl.py -v`
Expected: 4 passed (the dimension-loading tests already pass since they just read files; this task has no separate "make it fail first" step because there's no behavior to stub — the functions are simple reads/parses).

- [ ] **Step 6: Commit**

```bash
git add etl/__init__.py etl/transformar.py tests/__init__.py tests/test_etl.py pyproject.toml poetry.lock
git commit -m "Adiciona helpers do ETL e transformação das dimensões (uo, acao, area_tematica)"
```

---

### Task 2: ETL — fact tables (execução, restos a pagar, receita)

**Files:**
- Modify: `etl/transformar.py`
- Modify: `tests/test_etl.py`

**Interfaces:**
- Consumes: `RAW_DIR`, `filtrar_propag`, `transformar_uo`, `transformar_acao`, `transformar_area_tematica` (Task 1)
- Produces:
  - `transformar_execucao(uo: pd.DataFrame, acao: pd.DataFrame, area_tematica: pd.DataFrame) -> pd.DataFrame` — columns: `ano, mes_cod, uo_cod, uo_nome, uo_sigla, uo_sigla_current, acao_cod, acao_desc, area_tematica, fonte_cod, ipu_cod, categoria_propag, vlr_empenhado, vlr_liquidado, vlr_pago_orcamentario`
  - `transformar_restos_pagar(uo, acao, area_tematica) -> pd.DataFrame` — columns: `ano, ano_rp, mes_cod, uo_cod, uo_nome, uo_sigla, uo_sigla_current, acao_cod, acao_desc, area_tematica, fonte_cod, ipu_cod, categoria_propag, vlr_despesa_liquidada_rpnp`
  - `transformar_receita() -> pd.DataFrame` — same columns as `data-raw/receita.csv.gz`, filtered to `fonte_cod == 89`

- [ ] **Step 1: Append the fact-table transforms to `etl/transformar.py`**

```python
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
```

- [ ] **Step 2: Add tests**

```python
from etl.transformar import transformar_execucao, transformar_receita, transformar_restos_pagar


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
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `poetry run pytest tests/test_etl.py -v`
Expected: 9 passed. `test_execucao_sem_linhas_orfas_de_dimensao` is the one worth double-checking manually — it passes today (verified: 0 unmatched rows in both execução and restos_pagar) precisely because `area_tematica.csv` and the dimension tables only carry 2026 data, matching the fact tables' single exercise year. If a future data refresh adds another year, this test is what will catch a broken join early.

- [ ] **Step 4: Commit**

```bash
git add etl/transformar.py tests/test_etl.py
git commit -m "Adiciona transformação das tabelas fato (execucao, restos_pagar, receita)"
```

---

### Task 3: ETL — plano de intervenções, valor a ser aplicado, main(), and generate data/

**Files:**
- Modify: `etl/transformar.py`
- Modify: `tests/test_etl.py`
- Create: `data/` (generated output — commit the CSVs)

**Interfaces:**
- Consumes: everything from Tasks 1-2, plus `normalizar_sigla`, `parse_numero_br`, `ANO_REFERENCIA`
- Produces:
  - `transformar_plano_intervencoes(uo: pd.DataFrame) -> pd.DataFrame` — columns: `plano, area_tematica, uo_sigla, uo_sigla_norm, intervencao, valor_previsto, uo_cod, uo_sigla_current`
  - `transformar_valor_a_ser_aplicado() -> pd.DataFrame` — columns: `ano, tipo_recurso, descricao, valor`
  - `main() -> None` — runs every transform and writes all CSVs to `DATA_DIR`

This task has a real, known gotcha: `propag_plano_intervencoes.csv` uses `uo_sigla == "DER/MG"` while `uo.csv`'s `uo_sigla_current` for 2026 uses `"DER-MG"`. `normalizar_sigla` (Task 1) exists specifically to bridge this — join on the normalized column, not the raw one.

- [ ] **Step 1: Append the remaining transforms and `main()` to `etl/transformar.py`**

```python
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
```

- [ ] **Step 2: Add tests**

```python
from etl.transformar import transformar_plano_intervencoes, transformar_valor_a_ser_aplicado


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
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `poetry run pytest tests/test_etl.py -v`
Expected: 11 passed. `test_valor_a_ser_aplicado_bate_com_plano_v3` is a real cross-check (verified manually: plano v3 sums to R$ 1.874.421.994,00, the two limits sum to R$ 1.874.421.994,32 — 32 cents of rounding drift across 112 rows, well under the 1.0 tolerance).

- [ ] **Step 4: Run the ETL and inspect the output**

Run: `poetry run python -m etl.transformar`
Expected: prints `ETL concluido. Arquivos gravados em ...data`, no `AVISO:` lines (all joins are clean — verified during design). `data/` now has 8 CSVs: `uo.csv`, `acao.csv`, `area_tematica.csv`, `execucao_propag.csv` (4,810 rows), `restos_pagar_propag.csv` (387 rows), `receita_propag.csv` (10 rows), `plano_intervencoes.csv` (112 rows), `valor_a_ser_aplicado.csv` (6 rows).

- [ ] **Step 5: Commit the ETL code and the generated data**

```bash
git add etl/transformar.py tests/test_etl.py data/
git commit -m "Adiciona transformacao do plano de intervencoes e valor a ser aplicado; gera data/"
```

---

### Task 4: `utils.py` — cached loaders, currency formatting, colors

**Files:**
- Create: `utils.py`

**Interfaces:**
- Consumes: CSVs in `data/` produced by Task 3 (`uo.csv`, `execucao_propag.csv`, `restos_pagar_propag.csv`, `receita_propag.csv`, `plano_intervencoes.csv`, `valor_a_ser_aplicado.csv`)
- Produces:
  - `carregar_uo() -> pd.DataFrame`
  - `carregar_execucao() -> pd.DataFrame`
  - `carregar_restos_pagar() -> pd.DataFrame`
  - `carregar_receita() -> pd.DataFrame`
  - `carregar_plano_intervencoes() -> pd.DataFrame`
  - `carregar_valor_a_ser_aplicado() -> pd.DataFrame`
  - `carregar_valor_liquidado() -> pd.DataFrame` — columns: `ano, mes_cod, uo_cod, uo_sigla_current, uo_nome, acao_cod, acao_desc, area_tematica, categoria_propag, origem, valor`
  - `formatar_reais(valor: float) -> str` — e.g. `1234567.8 -> "R$ 1.234.567,80"`
  - `obter_limites() -> dict[str, float]` — e.g. `{"FEF": 52964615.72, "Investimentos Próprios": 1821457378.60}`
  - `CORES_CATEGORIA: dict[str, str]`, `COR_PLANEJADO: str`, `COR_EXECUTADO: str`, `COR_EMPENHADO: str`, `COR_LIQUIDADO: str` — hex colors from the dataviz skill's validated categorical palette (slots 1/2/3: blue `#2a78d6`, orange `#eb6834`, aqua `#1baf7a`)

- [ ] **Step 1: Write `utils.py`**

```python
"""Carregamento com cache e formatacao compartilhados pelas paginas do painel."""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"

CORES_CATEGORIA = {
    "FEF": "#2a78d6",
    "Investimentos Próprios": "#eb6834",
}
COR_PLANEJADO = "#2a78d6"
COR_EXECUTADO = "#1baf7a"
COR_EMPENHADO = "#2a78d6"
COR_LIQUIDADO = "#eb6834"


@st.cache_data
def carregar_uo() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "uo.csv")


@st.cache_data
def carregar_execucao() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "execucao_propag.csv")


@st.cache_data
def carregar_restos_pagar() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "restos_pagar_propag.csv")


@st.cache_data
def carregar_receita() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "receita_propag.csv")


@st.cache_data
def carregar_plano_intervencoes() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "plano_intervencoes.csv")


@st.cache_data
def carregar_valor_a_ser_aplicado() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "valor_a_ser_aplicado.csv")


@st.cache_data
def carregar_valor_liquidado() -> pd.DataFrame:
    """Combina execucao (vlr_liquidado) e restos a pagar (vlr_despesa_liquidada_rpnp)
    numa unica coluna 'valor', com uma coluna 'origem' indicando a base de origem."""
    colunas = ["ano", "mes_cod", "uo_cod", "uo_sigla_current", "uo_nome", "acao_cod",
               "acao_desc", "area_tematica", "categoria_propag", "origem", "valor"]

    execucao = carregar_execucao().rename(columns={"vlr_liquidado": "valor"}).copy()
    execucao["origem"] = "execucao"

    restos_pagar = carregar_restos_pagar().rename(columns={"vlr_despesa_liquidada_rpnp": "valor"}).copy()
    restos_pagar["origem"] = "rpnp"

    return pd.concat([execucao[colunas], restos_pagar[colunas]], ignore_index=True)


def formatar_reais(valor: float) -> str:
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def obter_limites() -> dict[str, float]:
    df = carregar_valor_a_ser_aplicado()
    limites = df[df["descricao"].str.startswith("Valor mínimo a ser aplicado")]
    return dict(zip(limites["tipo_recurso"], limites["valor"]))
```

- [ ] **Step 2: Verify manually (no pytest — `st.cache_data` needs a Streamlit run context for the decorator's full behavior, and this is a thin enough module that a REPL check is sufficient)**

Run:
```bash
poetry run python -c "
import utils
print(utils.formatar_reais(1234567.8))
print(utils.obter_limites())
"
```
Expected:
```
R$ 1.234.567,80
{'Investimentos Próprios': 1821457378.6, 'FEF': 52964615.72}
```

- [ ] **Step 3: Commit**

```bash
git add utils.py
git commit -m "Adiciona utils.py com carregamento cacheado e formatacao de valores"
```

---

### Task 5: `app.py` — Visão Geral

**Files:**
- Create: `app.py`
- Modify: `pyproject.toml` (add `plotly` dependency)

**Interfaces:**
- Consumes (from `utils.py`, Task 4): `CORES_CATEGORIA`, `COR_EMPENHADO`, `COR_EXECUTADO`, `COR_LIQUIDADO`, `COR_PLANEJADO`, `carregar_execucao`, `carregar_plano_intervencoes`, `carregar_valor_liquidado`, `formatar_reais`, `obter_limites`

- [ ] **Step 1: Add the plotly dependency**

Run: `poetry add plotly`
Expected: `pyproject.toml` gains `plotly` under `[project] dependencies`, `poetry.lock` updated.

- [ ] **Step 2: Write `app.py`**

```python
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
```

- [ ] **Step 3: Run the app and verify against known values**

Run: `poetry run streamlit run app.py`

Expected (values verified by hand against the raw data during design):
- Card "Total Propag": Limite `R$ 1.874.421.994,32`, Liquidado ≈ `R$ 874.926.628,42` (18.694.356,25 + 856.232.272,17), % cumprido ≈ `46,7%`
- Card "FEF": Limite `R$ 52.964.615,72`, Liquidado `R$ 18.694.356,25`, % cumprido ≈ `35,3%`
- Card "Investimentos Próprios": Limite `R$ 1.821.457.378,60`, Liquidado `R$ 856.232.272,17`, % cumprido ≈ `47,0%`
- Monthly chart: month 8 (August, the current partial month) shows an "Investimentos Próprios" empenhado bar around `R$ 133,2 milhões` and liquidado around `R$ 41,9 milhões`
- Planned x Executed chart: top row by planned value should be `DER-MG — Transportes` around `R$ 842 milhões` planejado

If any of these are off by more than rounding, stop and check the ETL output before moving on — the Visão Geral page is the one place all the upstream logic converges, so a mismatch here usually means an earlier task's join or filter is wrong.

- [ ] **Step 4: Commit**

```bash
git add app.py pyproject.toml poetry.lock
git commit -m "Adiciona pagina Visao Geral do painel Propag"
```

---

### Task 6: Execução por Órgão/Ação page

**Files:**
- Create: `pages/1_Execucao_por_Orgao.py`

**Interfaces:**
- Consumes (from `utils.py`): `carregar_execucao`, `formatar_reais`

- [ ] **Step 1: Write `pages/1_Execucao_por_Orgao.py`**

```python
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
```

- [ ] **Step 2: Run the app and verify**

Run: `poetry run streamlit run app.py`, then open the "Execucao por Orgao" page from the sidebar.
Expected: with no filters, the table has rows for every UO+ação combination in the 4,810-row filtered execution set; the ranking chart's top bar is the UO with the largest `vlr_liquidado` total (based on the earlier aggregate check, this should be a UO under "Investimentos Próprios" given that category dominates liquidado). Selecting a single UO in the filter narrows both the table and the chart to that UO only.

- [ ] **Step 3: Commit**

```bash
git add pages/1_Execucao_por_Orgao.py
git commit -m "Adiciona pagina de Execucao por Orgao/Acao"
```

---

### Task 7: Plano de Intervenções page

**Files:**
- Create: `pages/2_Plano_de_Intervencoes.py`

**Interfaces:**
- Consumes (from `utils.py`): `carregar_plano_intervencoes`, `formatar_reais`

- [ ] **Step 1: Write `pages/2_Plano_de_Intervencoes.py`**

```python
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
```

- [ ] **Step 2: Run the app and verify**

Run: `poetry run streamlit run app.py`, open the "Plano de Intervencoes" page.
Expected: version selector defaults to `v3` (112 rows total across all UOs before filtering); "Valor previsto por área temática" chart's largest bar is Transportes at ≈ `R$ 869,5 milhões` (DER/MG + SEINFRA + FUNTRANS combined); "Valor previsto por órgão" chart's largest bar is `DER/MG` alone at ≈ `R$ 842 milhões` (all of it under Transportes).

- [ ] **Step 3: Commit**

```bash
git add pages/2_Plano_de_Intervencoes.py
git commit -m "Adiciona pagina de Plano de Intervencoes"
```

---

### Task 8: Receita do FEF page

**Files:**
- Create: `pages/3_Receita_FEF.py`

**Interfaces:**
- Consumes (from `utils.py`): `carregar_receita`, `formatar_reais`, `obter_limites`

- [ ] **Step 1: Write `pages/3_Receita_FEF.py`**

```python
import plotly.express as px
import streamlit as st

from utils import carregar_receita, formatar_reais, obter_limites

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
        color_discrete_map={"Previsto atualizado": "#2a78d6", "Arrecadado": "#1baf7a"},
        labels={"mes_cod": "Mês", "Valor": "Valor (R$)"},
    )
    st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: Run the app and verify**

Run: `poetry run streamlit run app.py`, open the "Receita FEF" page.
Expected: "Previsto atualizado" card ≈ `R$ 628.772.000`, "Arrecadado até o momento" card ≈ `R$ 38.227.860`. Monthly chart's largest "Arrecadado" bar is month 1 (January) at ≈ `R$ 34.683.178`.

- [ ] **Step 3: Commit**

```bash
git add pages/3_Receita_FEF.py
git commit -m "Adiciona pagina de Receita do FEF"
```

---

### Task 9: README and final walkthrough

**Files:**
- Modify: `README.md`

**Interfaces:** none (documentation + manual verification only)

- [ ] **Step 1: Rewrite `README.md`**

```markdown
# Propag Status

Painel em Streamlit para acompanhar o cumprimento das obrigações do Propag
(Programa de Acompanamento e Transparência Fiscal) pelo Estado de Minas
Gerais em 2026.

## Estrutura

- `data-raw/` — bases orçamentárias brutas (não editar diretamente)
- `data/` — bases filtradas para o escopo do Propag (`fonte_cod == 89` ou
  `ipu_cod == 0`), geradas por `etl/transformar.py`
- `etl/transformar.py` — script de transformação (`data-raw/` → `data/`)
- `app.py` — página inicial do painel (Visão Geral)
- `pages/` — demais páginas do painel
- `utils.py` — carregamento com cache e formatação compartilhados
- `tests/` — testes do ETL (`pytest`)

## Rodando localmente

```bash
poetry install
poetry run python -m etl.transformar   # gera/atualiza data/ a partir de data-raw/
poetry run streamlit run app.py
```

## Testes

```bash
poetry run pytest
```

## Deploy

Publicado no Streamlit Community Cloud, apontando para `app.py` como
arquivo principal. O Streamlit Cloud detecta `poetry.lock` automaticamente
e instala as dependências via Poetry — não é necessário `requirements.txt`.
```

- [ ] **Step 2: Full manual walkthrough against the 1S/2026 prestação de contas**

Open `prestacao_contas/propag_prestacao_contas_1S_2026.pdf` side by side with the running app (`poetry run streamlit run app.py`) and compare the FEF and Investimentos Próprios liquidado totals reported there against the Visão Geral cards. Numbers won't match exactly (the PDF covers through June 30, the dashboard reflects data through the current data-raw snapshot), but they should be in the same order of magnitude and tell the same story (Investimentos Próprios far ahead of FEF in absolute terms). Note any large discrepancy — it would point to a filter or join bug, not an expected timing difference.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Documenta estrutura do projeto e instrucoes de uso no README"
```

## Self-Review Notes

- **Spec coverage:** every `data-raw` → `data` mapping in the spec has a task (Tasks 1-3); every v1 page in the spec has a task (Tasks 5, 6, 7, 8); validation/error-handling items from the spec (dimension-join nulls, fonte/ipu overlap, empty-filter UI state) are implemented in Tasks 2-3 (ETL asserts/warnings) and Tasks 5-8 (`st.info` on empty filter results); the pytest checks from the spec's Testing section are implemented across Tasks 1-3.
- **Known real numbers used for verification** (computed from the current `data-raw/` snapshot, not placeholders): FEF empenhado R$ 21.185.846,12, FEF liquidado R$ 18.694.356,25, Investimentos Próprios empenhado R$ 1.271.279.242,74, Investimentos Próprios liquidado (execução) R$ 734.291.089,24 + RPNP R$ 121.941.182,93 = R$ 856.232.272,17, plano v3 total R$ 1.874.421.994,00 (matches the sum of both limits within 32 centavos), receita fonte 89 previsto atualizado R$ 628.772.000 / arrecadado R$ 38.227.860. If a future `data-raw/` refresh changes these, the verification steps' expected values will need updating too — they're tied to today's snapshot, not the schema.
- **Known data quirk baked into the plan:** `propag_plano_intervencoes.csv` uses `"DER/MG"` while `uo.csv`'s 2026 `uo_sigla_current` uses `"DER-MG"` — this is why `normalizar_sigla` exists and why Task 3's join goes through the normalized column instead of a direct string match.
