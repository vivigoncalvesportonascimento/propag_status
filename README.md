# Propag Status

Painel em Streamlit para acompanhar o cumprimento das obrigações do Propag
(Programa de Pleno Pagamento de Dívidas dos Estados) pelo Estado de Minas
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
