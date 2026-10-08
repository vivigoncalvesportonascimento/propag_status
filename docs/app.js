/*
 * Painel Propag MG — versão web (HTML/CSS/JS puro, sem backend).
 * Reproduz a mesma lógica de dados de utils.py / app.py / pages/*.py
 * do painel Streamlit, lendo os mesmos CSVs em data/.
 *
 * Diferença deliberada em relação à versão Streamlit atual: a tabela da
 * página "Execução por Órgão" aqui já usa merge externo (outer) com as
 * duas colunas preenchidas com 0 quando faltam — corrigindo o bug
 * conhecido e ainda pendente na versão Streamlit (que usa merge "left"
 * e subestima o total liquidado em ~6,6%).
 */

const DATA_DIR = "../data/";

const COR = {
  planejado: "#2a78d6",
  executado: "#1baf7a",
  empenhado: "#2a78d6",
  liquidado: "#eb6834",
  previsto: "#2a78d6",
  arrecadado: "#1baf7a",
};

const CATEGORIAS = ["Investimentos Próprios", "FEF"];

// ---------------------------------------------------------------------
// Carregamento de dados
// ---------------------------------------------------------------------

function carregarCSV(nome) {
  return new Promise((resolve, reject) => {
    Papa.parse(DATA_DIR + nome, {
      download: true,
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (resultado) => resolve(resultado.data),
      error: reject,
    });
  });
}

async function carregarTudo() {
  const [execucao, restosPagar, receita, plano, valorAplicado] = await Promise.all([
    carregarCSV("execucao_propag.csv"),
    carregarCSV("restos_pagar_propag.csv"),
    carregarCSV("receita_propag.csv"),
    carregarCSV("plano_intervencoes.csv"),
    carregarCSV("valor_a_ser_aplicado.csv"),
  ]);
  return { execucao, restosPagar, receita, plano, valorAplicado };
}

// ---------------------------------------------------------------------
// Regras de negócio (espelham utils.py)
// ---------------------------------------------------------------------

function obterLimites(valorAplicado) {
  const limites = {};
  for (const row of valorAplicado) {
    if (typeof row.descricao === "string" && row.descricao.startsWith("Valor mínimo a ser aplicado")) {
      limites[row.tipo_recurso] = (limites[row.tipo_recurso] || 0) + row.valor;
    }
  }
  return limites;
}

// carregarValorLiquidado: combina execução (vlr_liquidado) + restos a
// pagar (vlr_despesa_liquidada_rpnp) numa lista única com campo `valor`.
function carregarValorLiquidado(execucao, restosPagar) {
  const combinado = [];
  for (const row of execucao) {
    combinado.push({
      ano: row.ano, mes_cod: row.mes_cod, uo_cod: row.uo_cod,
      uo_sigla_current: row.uo_sigla_current, uo_nome: row.uo_nome,
      acao_cod: row.acao_cod, acao_desc: row.acao_desc,
      area_tematica: row.area_tematica, categoria_propag: row.categoria_propag,
      origem: "execucao", valor: row.vlr_liquidado || 0,
    });
  }
  for (const row of restosPagar) {
    combinado.push({
      ano: row.ano, mes_cod: row.mes_cod, uo_cod: row.uo_cod,
      uo_sigla_current: row.uo_sigla_current, uo_nome: row.uo_nome,
      acao_cod: row.acao_cod, acao_desc: row.acao_desc,
      area_tematica: row.area_tematica, categoria_propag: row.categoria_propag,
      origem: "rpnp", valor: row.vlr_despesa_liquidada_rpnp || 0,
    });
  }
  return combinado;
}

function formatarReais(valor) {
  const num = (valor || 0);
  const texto = num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return "R$ " + texto;
}

// soma `valor` agrupando por uma ou mais chaves (retorna Map, chave = array.join("|||"))
function agruparSoma(linhas, chaves, campoValor) {
  const mapa = new Map();
  for (const linha of linhas) {
    const chave = chaves.map((c) => linha[c]).join("|||");
    mapa.set(chave, (mapa.get(chave) || 0) + (linha[campoValor] || 0));
  }
  return mapa;
}

function valoresUnicos(linhas, campo) {
  return [...new Set(linhas.map((l) => l[campo]).filter((v) => v !== null && v !== undefined && v !== ""))].sort();
}

// ---------------------------------------------------------------------
// Estado global (dados brutos, calculado uma vez após carregar)
// ---------------------------------------------------------------------

let DADOS = null;
let LIQUIDADO = null;

// ---------------------------------------------------------------------
// Visão Geral
// ---------------------------------------------------------------------

function renderCardsVisaoGeral() {
  const limites = obterLimites(DADOS.valorAplicado);
  const liquidadoPorCategoria = agruparSoma(LIQUIDADO, ["categoria_propag"], "valor");

  const limiteTotal = Object.values(limites).reduce((a, b) => a + b, 0);
  const liquidadoTotal = [...liquidadoPorCategoria.values()].reduce((a, b) => a + b, 0);

  const grupos = [
    { titulo: "Total Propag", limite: limiteTotal, liquidado: liquidadoTotal },
    ...CATEGORIAS.map((c) => ({
      titulo: c,
      limite: limites[c] || 0,
      liquidado: liquidadoPorCategoria.get(c) || 0,
    })),
  ];

  const container = document.getElementById("cards-visao-geral");
  container.innerHTML = grupos.map((g) => {
    const saldo = g.limite - g.liquidado;
    const pct = g.limite ? (g.liquidado / g.limite) * 100 : 0;
    return `
      <div class="card">
        <div class="card-title">${g.titulo}</div>
        <div class="metric"><span class="metric-label">Limite 2026</span><span class="metric-value">${formatarReais(g.limite)}</span></div>
        <div class="metric"><span class="metric-label">Liquidado</span><span class="metric-value">${formatarReais(g.liquidado)}</span></div>
        <div class="metric"><span class="metric-label">Saldo a liquidar</span><span class="metric-value">${formatarReais(saldo)}</span></div>
        <div class="metric"><span class="metric-label">% cumprido</span><span class="metric-value good">${pct.toFixed(1)}%</span></div>
      </div>`;
  }).join("");
}

function renderChartMensal(categoriaFiltro) {
  let base = DADOS.execucao;
  if (categoriaFiltro && categoriaFiltro !== "Todas") {
    base = base.filter((r) => r.categoria_propag === categoriaFiltro);
  }
  const empenhadoPorMes = agruparSoma(base, ["mes_cod"], "vlr_empenhado");
  const liquidadoPorMes = agruparSoma(base, ["mes_cod"], "vlr_liquidado");
  const meses = [...new Set([...empenhadoPorMes.keys(), ...liquidadoPorMes.keys()])]
    .map(Number).sort((a, b) => a - b);

  if (meses.length === 0) {
    Plotly.purge("chart-mensal");
    document.getElementById("chart-mensal").innerHTML = '<p class="hint">Nenhum dado para os filtros selecionados.</p>';
    return;
  }

  const traces = [
    { x: meses, y: meses.map((m) => empenhadoPorMes.get(String(m)) || 0), name: "Empenhado", type: "bar", marker: { color: COR.empenhado } },
    { x: meses, y: meses.map((m) => liquidadoPorMes.get(String(m)) || 0), name: "Liquidado", type: "bar", marker: { color: COR.liquidado } },
  ];
  Plotly.newPlot("chart-mensal", traces, layoutBase({
    barmode: "group",
    xaxis: { title: "Mês", tickmode: "linear" },
    yaxis: { title: "Valor (R$)" },
  }), plotlyConfig());
}

function renderChartComparacao(areaFiltro) {
  const planoV3 = DADOS.plano.filter((r) => r.plano === "v3");
  const planejadoMapa = agruparSoma(planoV3, ["uo_sigla_current", "area_tematica"], "valor_previsto");
  const executadoMapa = agruparSoma(LIQUIDADO, ["uo_sigla_current", "area_tematica"], "valor");

  const chaves = new Set([...planejadoMapa.keys(), ...executadoMapa.keys()]);
  let linhas = [...chaves].map((chave) => {
    const [uo, area] = chave.split("|||");
    return {
      uo, area,
      rotulo: `${uo} — ${area}`,
      planejado: planejadoMapa.get(chave) || 0,
      executado: executadoMapa.get(chave) || 0,
    };
  });
  linhas.forEach((l) => (l.gap = l.planejado - l.executado));

  if (areaFiltro && areaFiltro !== "Todas") {
    linhas = linhas.filter((l) => l.area === areaFiltro);
  }
  linhas.sort((a, b) => b.gap - a.gap);

  if (linhas.length === 0) {
    Plotly.purge("chart-comparacao");
    document.getElementById("chart-comparacao").innerHTML = '<p class="hint">Nenhum dado para os filtros selecionados.</p>';
    return;
  }

  const rotulos = linhas.map((l) => l.rotulo);
  const traces = [
    { y: rotulos, x: linhas.map((l) => l.planejado), name: "Planejado", type: "bar", orientation: "h", marker: { color: COR.planejado } },
    { y: rotulos, x: linhas.map((l) => l.executado), name: "Executado", type: "bar", orientation: "h", marker: { color: COR.executado } },
  ];
  Plotly.newPlot("chart-comparacao", traces, layoutBase({
    barmode: "group",
    xaxis: { title: "Valor (R$)" },
    yaxis: { title: "Órgão — Área temática", categoryorder: "total ascending", automargin: true },
    margin: { l: 220 },
  }), plotlyConfig());
}

function popularFiltroAreaComparacao() {
  const areas = valoresUnicos(DADOS.plano.filter((r) => r.plano === "v3"), "area_tematica");
  const select = document.getElementById("filtro-area-comparacao");
  select.innerHTML = '<option value="Todas">Todas</option>' + areas.map((a) => `<option value="${a}">${a}</option>`).join("");
}

function initVisaoGeral() {
  renderCardsVisaoGeral();
  popularFiltroAreaComparacao();
  renderChartMensal("Todas");
  renderChartComparacao("Todas");

  document.getElementById("filtro-categoria-mensal").addEventListener("change", (e) => renderChartMensal(e.target.value));
  document.getElementById("filtro-area-comparacao").addEventListener("change", (e) => renderChartComparacao(e.target.value));
}

// ---------------------------------------------------------------------
// Execução por Órgão/Ação
// ---------------------------------------------------------------------

function selecionados(selectEl) {
  return [...selectEl.selectedOptions].map((o) => o.value);
}

function popularFiltrosExecucao() {
  const uoSel = document.getElementById("filtro-uo-exec");
  const areaSel = document.getElementById("filtro-area-exec");
  const catSel = document.getElementById("filtro-categoria-exec");

  uoSel.innerHTML = valoresUnicos(DADOS.execucao, "uo_nome").map((v) => `<option value="${v}">${v}</option>`).join("");
  areaSel.innerHTML = valoresUnicos(DADOS.execucao, "area_tematica").map((v) => `<option value="${v}">${v}</option>`).join("");
  catSel.innerHTML = valoresUnicos(DADOS.execucao, "categoria_propag").map((v) => `<option value="${v}">${v}</option>`).join("");

  [uoSel, areaSel, catSel].forEach((el) => el.addEventListener("change", renderExecucao));
}

function filtrar(linhas, { uo, area, categoria }) {
  return linhas.filter((l) =>
    (uo.length === 0 || uo.includes(l.uo_nome)) &&
    (area.length === 0 || area.includes(l.area_tematica)) &&
    (categoria.length === 0 || categoria.includes(l.categoria_propag))
  );
}

function renderExecucao() {
  const filtros = {
    uo: selecionados(document.getElementById("filtro-uo-exec")),
    area: selecionados(document.getElementById("filtro-area-exec")),
    categoria: selecionados(document.getElementById("filtro-categoria-exec")),
  };

  const execFiltrada = filtrar(DADOS.execucao, filtros);
  const liquidadoFiltrado = filtrar(LIQUIDADO, filtros);

  const empenhadoMapa = agruparSoma(execFiltrada, ["uo_nome", "acao_desc"], "vlr_empenhado");
  const liquidadoMapa = agruparSoma(liquidadoFiltrado, ["uo_nome", "acao_desc"], "valor");

  // merge externo (outer) com as duas colunas preenchidas com 0 quando faltam
  const chaves = new Set([...empenhadoMapa.keys(), ...liquidadoMapa.keys()]);
  let tabela = [...chaves].map((chave) => {
    const [uo, acao] = chave.split("|||");
    const empenhado = empenhadoMapa.get(chave) || 0;
    const liquidado = liquidadoMapa.get(chave) || 0;
    return { uo, acao, empenhado, liquidado, saldo: empenhado - liquidado };
  });
  tabela.sort((a, b) => b.liquidado - a.liquidado);

  const corpo = document.querySelector("#tabela-execucao tbody");
  const vazio = document.getElementById("vazio-execucao");
  if (tabela.length === 0) {
    corpo.innerHTML = "";
    vazio.style.display = "block";
  } else {
    vazio.style.display = "none";
    corpo.innerHTML = tabela.map((l) => `
      <tr>
        <td>${l.uo}</td><td>${l.acao}</td>
        <td class="num">${formatarReais(l.empenhado)}</td>
        <td class="num">${formatarReais(l.liquidado)}</td>
        <td class="num">${formatarReais(l.saldo)}</td>
      </tr>`).join("");
  }

  // ranking por UO (usa o mesmo total liquidado combinado, agrupado só por órgão)
  const rankingMapa = agruparSoma(liquidadoFiltrado, ["uo_nome"], "valor");
  let ranking = [...rankingMapa.entries()].map(([uo, valor]) => ({ uo, valor }));
  ranking.sort((a, b) => b.valor - a.valor);

  if (ranking.length === 0) {
    Plotly.purge("chart-ranking");
    document.getElementById("chart-ranking").innerHTML = '<p class="hint">Nenhum dado para os filtros selecionados.</p>';
    return;
  }

  Plotly.newPlot("chart-ranking", [{
    y: ranking.map((r) => r.uo),
    x: ranking.map((r) => r.valor),
    type: "bar", orientation: "h",
    marker: { color: COR.liquidado },
  }], layoutBase({
    xaxis: { title: "Valor liquidado (R$)" },
    yaxis: { title: "Órgão", categoryorder: "total ascending", automargin: true },
    margin: { l: 260 },
  }), plotlyConfig());
}

function initExecucao() {
  popularFiltrosExecucao();
  renderExecucao();
}

// ---------------------------------------------------------------------
// Plano de Intervenções
// ---------------------------------------------------------------------

function popularFiltrosPlano() {
  const versoes = valoresUnicos(DADOS.plano, "plano").sort().reverse(); // v3, v2, v1
  const versaoSel = document.getElementById("filtro-versao-plano");
  versaoSel.innerHTML = versoes.map((v) => `<option value="${v}">${v}</option>`).join("");

  const areaSel = document.getElementById("filtro-area-plano");
  const uoSel = document.getElementById("filtro-uo-plano");
  areaSel.innerHTML = valoresUnicos(DADOS.plano, "area_tematica").map((v) => `<option value="${v}">${v}</option>`).join("");
  uoSel.innerHTML = valoresUnicos(DADOS.plano, "uo_sigla_current").map((v) => `<option value="${v}">${v}</option>`).join("");

  [versaoSel, areaSel, uoSel].forEach((el) => el.addEventListener("change", renderPlano));
}

function renderPlano() {
  const versao = document.getElementById("filtro-versao-plano").value;
  const areas = selecionados(document.getElementById("filtro-area-plano"));
  const uos = selecionados(document.getElementById("filtro-uo-plano"));

  let filtrado = DADOS.plano.filter((r) => r.plano === versao);
  if (areas.length) filtrado = filtrado.filter((r) => areas.includes(r.area_tematica));
  if (uos.length) filtrado = filtrado.filter((r) => uos.includes(r.uo_sigla_current));
  filtrado = [...filtrado].sort((a, b) => b.valor_previsto - a.valor_previsto);

  const corpo = document.querySelector("#tabela-plano tbody");
  const vazio = document.getElementById("vazio-plano");
  if (filtrado.length === 0) {
    corpo.innerHTML = "";
    vazio.style.display = "block";
    Plotly.purge("chart-plano-area");
    Plotly.purge("chart-plano-uo");
    return;
  }
  vazio.style.display = "none";
  corpo.innerHTML = filtrado.map((l) => `
    <tr>
      <td>${l.area_tematica}</td><td>${l.uo_sigla_current}</td><td>${l.intervencao}</td>
      <td class="num">${formatarReais(l.valor_previsto)}</td>
    </tr>`).join("");

  const porArea = [...agruparSoma(filtrado, ["area_tematica"], "valor_previsto").entries()]
    .sort((a, b) => b[1] - a[1]);
  Plotly.newPlot("chart-plano-area", [{
    x: porArea.map((e) => e[0]), y: porArea.map((e) => e[1]),
    type: "bar", marker: { color: COR.planejado },
  }], layoutBase({ xaxis: { title: "Área temática" }, yaxis: { title: "Valor previsto (R$)" } }), plotlyConfig());

  const porUo = [...agruparSoma(filtrado, ["uo_sigla_current"], "valor_previsto").entries()]
    .sort((a, b) => b[1] - a[1]);
  Plotly.newPlot("chart-plano-uo", [{
    x: porUo.map((e) => e[0]), y: porUo.map((e) => e[1]),
    type: "bar", marker: { color: COR.planejado },
  }], layoutBase({ xaxis: { title: "Órgão" }, yaxis: { title: "Valor previsto (R$)" } }), plotlyConfig());
}

function initPlano() {
  popularFiltrosPlano();
  renderPlano();
}

// ---------------------------------------------------------------------
// Receita do FEF
// ---------------------------------------------------------------------

function initReceita() {
  const limites = obterLimites(DADOS.valorAplicado);
  const totalPrevisto = DADOS.receita.reduce((s, r) => s + (r.vlr_previsto_atualizado || 0), 0);
  const totalArrecadado = DADOS.receita.reduce((s, r) => s + (r.vlr_efetivado_ajustado || 0), 0);

  document.getElementById("banner-fef").textContent =
    `A lei permite arrecadar num exercício e aplicar no seguinte. O saldo do FEF recebido em 2025 e a aplicar ` +
    `em 2026 é ${formatarReais(limites["FEF"] || 0)} — esse é o limite mínimo que a Visão Geral acompanha para a categoria FEF.`;

  document.getElementById("cards-receita").innerHTML = `
    <div class="card">
      <div class="card-title">Previsto atualizado (2026)</div>
      <div class="metric"><span class="metric-value">${formatarReais(totalPrevisto)}</span></div>
    </div>
    <div class="card">
      <div class="card-title">Arrecadado até o momento</div>
      <div class="metric"><span class="metric-value">${formatarReais(totalArrecadado)}</span></div>
    </div>`;

  const previstoPorMes = agruparSoma(DADOS.receita, ["mes_cod"], "vlr_previsto_atualizado");
  const arrecadadoPorMes = agruparSoma(DADOS.receita, ["mes_cod"], "vlr_efetivado_ajustado");
  const meses = [...new Set([...previstoPorMes.keys(), ...arrecadadoPorMes.keys()])].map(Number).sort((a, b) => a - b);

  if (meses.length === 0) {
    document.getElementById("chart-receita").innerHTML = '<p class="hint">Nenhum dado disponível.</p>';
    return;
  }

  Plotly.newPlot("chart-receita", [
    { x: meses, y: meses.map((m) => previstoPorMes.get(String(m)) || 0), name: "Previsto atualizado", type: "bar", marker: { color: COR.previsto } },
    { x: meses, y: meses.map((m) => arrecadadoPorMes.get(String(m)) || 0), name: "Arrecadado", type: "bar", marker: { color: COR.arrecadado } },
  ], layoutBase({ barmode: "group", xaxis: { title: "Mês", tickmode: "linear" }, yaxis: { title: "Valor (R$)" } }), plotlyConfig());
}

// ---------------------------------------------------------------------
// Plotly helpers
// ---------------------------------------------------------------------

function layoutBase(extra) {
  return Object.assign({
    font: { family: "-apple-system, Segoe UI, system-ui, Roboto, sans-serif", size: 12, color: "#14171a" },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 60, r: 20, t: 10, b: 44 },
    legend: { orientation: "h", y: -0.18 },
  }, extra);
}

function plotlyConfig() {
  return { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] };
}

// ---------------------------------------------------------------------
// Navegação por abas
// ---------------------------------------------------------------------

function initTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".page").forEach((p) => p.classList.add("hidden"));
      btn.classList.add("active");
      document.getElementById("page-" + btn.dataset.tab).classList.remove("hidden");
      window.dispatchEvent(new Event("resize")); // força o Plotly a recalcular largura
    });
  });
}

// ---------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------

(async function main() {
  initTabs();
  try {
    DADOS = await carregarTudo();
    LIQUIDADO = carregarValorLiquidado(DADOS.execucao, DADOS.restosPagar);

    document.getElementById("loading").style.display = "none";

    initVisaoGeral();
    initExecucao();
    initPlano();
    initReceita();
  } catch (erro) {
    document.getElementById("loading").textContent =
      "Erro ao carregar os dados de data/. Veja o console (F12) para detalhes.";
    console.error(erro);
  }
})();
