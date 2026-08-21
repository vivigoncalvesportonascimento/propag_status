# Painel Propag MG — Design (v1)

Data: 2026-08-21
Status: aprovado para geração do plano de implementação

## Contexto e objetivo

O Estado de Minas Gerais aderiu ao Propag (Programa de Pleno Pagamento de
Dívidas dos Estados), que exige a aplicação de um valor mínimo anual de
investimentos com dois marcadores orçamentários:

- **FEF** — `fonte_cod = 89`
- **Investimentos Próprios (IPU 0)** — `ipu_cod = 0`

Este projeto cria um painel em Streamlit, publicado no Streamlit Community
Cloud, para acompanhar o cumprimento dessas obrigações em 2026 — tanto para
consumo da alta gestão (cards resumo) quanto das equipes/órgãos executores
(detalhamento operacional). O repositório é público (dados de execução
orçamentária são informação de transparência).

A comprovação do cumprimento se dá no estágio de **liquidação**. Como há
despesas plurianuais, o valor liquidado total para fins de comprovação soma:

- `vlr_liquidado` da base `execucao` (liquidado no exercício corrente)
- `vlr_despesa_liquidada_rpnp` da base `restos_pagar` (liquidado de restos a
  pagar não processados, isto é, empenhados em exercício anterior e
  liquidados agora)

Confirmado nos dados: nenhuma linha de `execucao` ou `restos_pagar` tem
`fonte_cod == 89` e `ipu_cod == 0` simultaneamente — as duas categorias do
Propag são mutuamente exclusivas nos dados de 2026.

## Fora de escopo (v1)

- Bases `credito.csv.gz`, `cota.csv.gz` — página de Crédito/Alterações
  Orçamentárias fica para uma iteração futura.
- Dimensões `elemento_item.csv`, `fonte_recurso.csv` — não usadas pelas
  páginas desta versão.
- Cruzamento de valor executado por intervenção do plano de aplicação — os
  dados atuais não permitem esse nível de granularidade (só existe
  planejado por intervenção e executado por UO/ação).
- Testes automatizados do Streamlit em si (overhead alto, baixo retorno
  para um painel de leitura).

## Estrutura do repositório

```
data-raw/          (já existe — dados brutos, não é alterado)
data/              (novo — saída do ETL, CSV em UTF-8)
etl/
  __init__.py
  transformar.py    (script único: `python -m etl.transformar`)
app.py              (Visão Geral — página inicial nativa do Streamlit)
pages/
  1_Execucao_por_Orgao.py
  2_Plano_de_Intervencoes.py
  3_Receita_FEF.py
utils.py            (carregamento com cache, formatação R$, combinação de valor liquidado)
tests/
  test_etl.py        (pytest — validações do ETL)
```

Um script único em `etl/transformar.py` (não um pacote com um módulo por
tabela): a lógica por tabela é pequena (ler, corrigir encoding/delimitador,
filtrar, salvar) — um arquivo com uma função por tabela já é organização
suficiente para 7 tabelas de entrada.

## Formato de dados transformados

CSV em UTF-8, separador vírgula, decimal ponto — legível no GitHub/Excel,
alinhado com a proposta de transparência do repositório público. Os volumes
são pequenos o bastante (a base de execução filtrada cai de ~718 mil para
~4.800 linhas) para não pesar no repositório nem justificar Parquet.

## Pipeline de transformação (ETL)

Todas as tabelas de origem têm inconsistências de encoding (UTF-8 vs
Latin-1) e delimitador (`,` vs `;`) que o ETL normaliza na saída.

| Origem | Saída | Regra |
|---|---|---|
| `receita.csv.gz` | `data/receita_propag.csv` | filtro `fonte_cod == 89` |
| `execucao.csv.gz` | `data/execucao_propag.csv` | filtro `fonte_cod == 89 OR ipu_cod == 0`; junta com `area_tematica` (ano+uo_cod+acao_cod) e `uo`/`acao` (ano+código); descarta colunas operacionais não usadas no painel (CNPJ do credor, processo/contrato/obra); mantém `vlr_empenhado`, `vlr_liquidado`, `vlr_pago_orcamentario` |
| `restos_pagar.csv.gz` | `data/restos_pagar_propag.csv` | mesmo filtro fonte/ipu e mesmas junções; mantém `vlr_despesa_liquidada_rpnp` como métrica principal |
| `propag_plano_intervencoes.csv` | `data/plano_intervencoes.csv` | corrige encoding e delimitador; parseia valor previsto do formato BR ("575.047.787") para float |
| `propag_valor_a_ser_aplicado.csv` | `data/valor_a_ser_aplicado.csv` | corrige encoding e decimal BR |
| `uo.csv`, `acao.csv`, `area_tematica.csv` | cópias em `data/` | só normalização de encoding/delimitador, sem filtro (dimensão mantém todos os anos, é preciso respeitar ano+código na hora de usar) |

Nova coluna derivada em toda tabela de fato filtrada:
`categoria_propag` = `"FEF"` se `fonte_cod == 89`, senão
`"Investimentos Próprios (IPU 0)"`.

## Regra de negócio central: valor liquidado total

Fica em `utils.py` (não no ETL, pois é uma regra de leitura usada por
várias páginas, não uma limpeza de dados):

`carregar_valor_liquidado()` lê `execucao_propag.csv` +
`restos_pagar_propag.csv`, empilha `vlr_liquidado` e
`vlr_despesa_liquidada_rpnp` numa coluna comum `valor`, com uma coluna
`origem` (`execucao`/`rpnp`), preservando `ano`, `mes_cod`, `uo_cod`,
`acao_cod`, `categoria_propag`, `area_tematica`. Toda soma de "valor
aplicado" no painel usa essa função. Cache via `st.cache_data`.

## Páginas e visuais

### Visão Geral (`app.py`)

- 3 colunas (Total / FEF / Investimentos Próprios), cada uma com 4
  `st.metric`: Limite 2026, Liquidado, Saldo a liquidar, % cumprido. Limite
  vem de `valor_a_ser_aplicado.csv`.
- Gráfico de ritmo mensal: empenhado x liquidado ao longo de 2026, com
  seletor de categoria.
- Gráfico central da página: planejado (plano v3) x executado, por UO +
  área temática — barras pareadas horizontais, ordenadas pelo maior gap
  entre planejado e executado, com filtro de área temática. Planejado vem
  de `plano_intervencoes.csv` agregado por UO+área temática (sem detalhar
  intervenção); executado vem de `carregar_valor_liquidado()` agregado no
  mesmo nível (UO mapeada de `uo_cod` para `uo_sigla` via `uo.csv`).

### Execução por Órgão/Ação (`pages/1_Execucao_por_Orgao.py`)

- Filtros: UO, área temática, categoria (FEF/IPU0), ação.
- Tabela detalhada (empenhado, liquidado, saldo) por UO+ação.
- Ranking de UOs por valor liquidado.

### Plano de Intervenções (`pages/2_Plano_de_Intervencoes.py`)

- Filtros: versão do plano (padrão v3, com opção de comparar v1/v2/v3),
  área temática, UO.
- Tabela com intervenção, UO, área temática, valor previsto + gráfico de
  valor previsto por área temática e por UO.
- Nota fixa explicando que EPT entra como linha única consolidada (tem
  plano próprio à parte) e que não há valor executado por intervenção
  ainda.

### Receita do FEF (`pages/3_Receita_FEF.py`)

- Gráfico mensal: previsto atualizado x arrecadado (2026).
- Card: total arrecadado até o momento x previsto atualizado.
- Nota sobre a regra de carência (arrecadado em 2025 é aplicado em 2026),
  puxando o valor mínimo de `valor_a_ser_aplicado.csv`.

## Validação e tratamento de erros

- ETL: aviso (não falha) se o merge com dimensões deixar `uo_nome` ou
  `area_tematica` nulo — indica código sem descritivo naquele ano.
  `assert` de que nenhuma linha tem `fonte_cod == 89 AND ipu_cod == 0`
  simultaneamente, para detectar cedo se esse padrão mudar em dados
  futuros.
- App: filtro do usuário sem resultado mostra `st.info(...)` em vez de
  gráfico quebrado.
- Cache via `st.cache_data` — dados só mudam quando o ETL roda de novo e
  o CSV é commitado.

## Testes

- `tests/test_etl.py` (pytest): sem sobreposição fonte89/ipu0; soma do
  valor liquidado é positiva; toda UO referenciada em
  `plano_intervencoes.csv` existe em `uo.csv`.
- Validação manual: rodar `streamlit run app.py` localmente e conferir os
  totais contra o PDF de prestação de contas do 1º semestre de 2026 já
  presente em `prestacao_contas/`.

## Dependências novas

Nenhuma além das já presentes (`streamlit`, `pandas`). Gráficos usam
`st.bar_chart`/`st.line_chart` ou Plotly via `st.plotly_chart` — decisão de
biblioteca de gráfico fica para a fase de implementação, seguindo a skill
de dataviz.
