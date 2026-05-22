const dashboardData = window.SUPERSTORE_DASHBOARD_DATA;
const records = dashboardData.records;
const topProducts = dashboardData.topProducts;

const filters = {
  year: document.getElementById("yearFilter"),
  market: document.getElementById("marketFilter"),
  category: document.getElementById("categoryFilter"),
};

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const number = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

function money(value) {
  return currency.format(value || 0);
}

function pct(value) {
  if (!Number.isFinite(value)) return "0.0%";
  return `${(value * 100).toFixed(1)}%`;
}

function fillSelect(select, values, allLabel) {
  select.innerHTML = "";
  const all = document.createElement("option");
  all.value = "All";
  all.textContent = allLabel;
  select.appendChild(all);

  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

function selectedFilters() {
  return {
    year: filters.year.value,
    market: filters.market.value,
    category: filters.category.value,
  };
}

function matches(row, state) {
  return (
    (state.year === "All" || String(row.year) === state.year) &&
    (state.market === "All" || row.market === state.market) &&
    (state.category === "All" || row.category === state.category)
  );
}

function aggregate(rows, key) {
  const map = new Map();
  rows.forEach((row) => {
    const name = row[key];
    if (!map.has(name)) {
      map.set(name, { name, sales: 0, profit: 0, orders: 0, rows: 0, quantity: 0 });
    }
    const item = map.get(name);
    item.sales += row.sales || 0;
    item.profit += row.profit || 0;
    item.orders += row.orders || 0;
    item.rows += row.rows || 0;
    item.quantity += row.quantity || 0;
  });
  return Array.from(map.values()).map((item) => ({
    ...item,
    margin: item.sales ? item.profit / item.sales : 0,
  }));
}

function total(rows) {
  const totals = rows.reduce(
    (acc, row) => {
      acc.sales += row.sales || 0;
      acc.profit += row.profit || 0;
      acc.orders += row.orders || 0;
      acc.rows += row.rows || 0;
      acc.lossRows += row.loss_rows || 0;
      return acc;
    },
    { sales: 0, profit: 0, orders: 0, rows: 0, lossRows: 0 }
  );
  totals.margin = totals.sales ? totals.profit / totals.sales : 0;
  totals.lossShare = totals.rows ? totals.lossRows / totals.rows : 0;
  return totals;
}

function svgWrap(width, height, content) {
  return `<svg viewBox="0 0 ${width} ${height}" role="img">${content}</svg>`;
}

function text(x, y, label, cls = "", anchor = "start") {
  return `<text x="${x}" y="${y}" text-anchor="${anchor}" class="${cls}">${label}</text>`;
}

function lineChart(el, rows) {
  const data = aggregate(rows, "year").sort((a, b) => Number(a.name) - Number(b.name));
  const width = 1080;
  const height = 360;
  const left = 72;
  const right = 30;
  const top = 24;
  const bottom = 58;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const maxSales = Math.max(...data.map((d) => d.sales), 1) * 1.12;
  const x = (i) => left + (i * plotW) / Math.max(data.length - 1, 1);
  const y = (value) => top + plotH - (value / maxSales) * plotH;
  const path = (field) => data.map((d, i) => `${i ? "L" : "M"} ${x(i)} ${y(d[field])}`).join(" ");

  const circles = data
    .map((d, i) => {
      const xi = x(i);
      return [
        `<circle cx="${xi}" cy="${y(d.sales)}" r="5" fill="var(--blue)"></circle>`,
        `<circle cx="${xi}" cy="${y(d.profit)}" r="5" fill="var(--green)"></circle>`,
        text(xi, height - 24, d.name, "axis-label", "middle"),
      ].join("");
    })
    .join("");

  el.innerHTML = svgWrap(
    width,
    height,
    `
      <line x1="${left}" y1="${top + plotH}" x2="${width - right}" y2="${top + plotH}" stroke="var(--line)" />
      <path d="${path("sales")}" fill="none" stroke="var(--blue)" stroke-width="4" />
      <path d="${path("profit")}" fill="none" stroke="var(--green)" stroke-width="4" />
      ${circles}
      <rect x="${left}" y="8" width="14" height="14" fill="var(--blue)" />
      ${text(left + 22, 20, "Sales", "chart-label")}
      <rect x="${left + 100}" y="8" width="14" height="14" fill="var(--green)" />
      ${text(left + 122, 20, "Profit", "chart-label")}
    `
  );
}

function barChart(el, data, valueKey, labelFormat, color = "var(--blue)") {
  const width = 680;
  const rowH = 42;
  const left = 150;
  const right = 90;
  const height = Math.max(250, data.length * rowH + 30);
  const maxAbs = Math.max(...data.map((d) => Math.abs(d[valueKey])), 1);
  const zero = data.some((d) => d[valueKey] < 0) ? left + (width - left - right) / 2 : left;
  const scale = (data.some((d) => d[valueKey] < 0) ? (width - left - right) / 2 : width - left - right) / maxAbs;

  const bars = data
    .map((d, i) => {
      const y = 18 + i * rowH;
      const value = d[valueKey];
      const x2 = zero + value * scale;
      const x = Math.min(zero, x2);
      const w = Math.max(Math.abs(x2 - zero), 1);
      const fill = value < 0 ? "var(--red)" : color;
      const labelX = value < 0 ? x - 8 : x + w + 8;
      const anchor = value < 0 ? "end" : "start";
      return `
        ${text(8, y + 22, String(d.name).slice(0, 22), "axis-label")}
        <rect x="${x}" y="${y}" width="${w}" height="24" rx="4" fill="${fill}" />
        ${text(labelX, y + 18, labelFormat(value), "chart-label", anchor)}
      `;
    })
    .join("");

  el.innerHTML = svgWrap(
    width,
    height,
    `<line x1="${zero}" y1="10" x2="${zero}" y2="${height - 10}" stroke="var(--line)" />${bars}`
  );
}

function heatBarChart(el, data) {
  const ordered = ["0%", "0-10%", "10-20%", "20-30%", "30-50%", "50%+"];
  const rows = ordered.map((bucket) => data.find((d) => d.name === bucket) || { name: bucket, margin: 0, sales: 0 });
  barChart(el, rows, "margin", pct, "var(--orange)");
}

function table(el, rows, columns) {
  const head = columns.map((col) => `<th class="${col.numeric ? "num" : ""}">${col.label}</th>`).join("");
  const body = rows
    .map((row) => {
      const cells = columns
        .map((col) => {
          const raw = row[col.key];
          const value = col.format ? col.format(raw, row) : raw;
          const cls = [col.numeric ? "num" : "", raw < 0 ? "negative" : raw > 0 && col.color ? "positive" : ""]
            .filter(Boolean)
            .join(" ");
          return `<td class="${cls}">${value}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  el.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function update() {
  const state = selectedFilters();
  const filtered = records.filter((row) => matches(row, state));
  const totals = total(filtered);

  document.getElementById("salesKpi").textContent = money(totals.sales);
  document.getElementById("profitKpi").textContent = money(totals.profit);
  document.getElementById("profitKpi").className = totals.profit < 0 ? "negative" : "positive";
  document.getElementById("marginKpi").textContent = pct(totals.margin);
  document.getElementById("ordersKpi").textContent = number.format(totals.rows);
  document.getElementById("lossRowsKpi").textContent = pct(totals.lossShare);

  lineChart(document.getElementById("trendChart"), filtered);
  barChart(
    document.getElementById("marketChart"),
    aggregate(filtered, "market").sort((a, b) => b.profit - a.profit),
    "profit",
    money,
    "var(--green)"
  );
  barChart(
    document.getElementById("categoryChart"),
    aggregate(filtered, "category").sort((a, b) => b.margin - a.margin),
    "margin",
    pct,
    "var(--blue)"
  );
  heatBarChart(document.getElementById("discountChart"), aggregate(filtered, "discount_bucket"));

  table(
    document.getElementById("countryTable"),
    aggregate(filtered, "country")
      .filter((row) => row.profit < 0)
      .sort((a, b) => a.profit - b.profit)
      .slice(0, 8),
    [
      { key: "name", label: "Country" },
      { key: "sales", label: "Sales", numeric: true, format: money },
      { key: "profit", label: "Profit", numeric: true, format: money },
      { key: "margin", label: "Margin", numeric: true, format: pct },
    ]
  );

  const productRows = topProducts
    .filter((row) => matches(row, state))
    .map((row) => ({ ...row, margin: row.sales ? row.profit / row.sales : 0, name: row.product_name }))
    .sort((a, b) => a.profit - b.profit)
    .slice(0, 8);

  table(document.getElementById("productTable"), productRows, [
    { key: "name", label: "Product" },
    { key: "sub_category", label: "Sub-category" },
    { key: "sales", label: "Sales", numeric: true, format: money },
    { key: "profit", label: "Profit", numeric: true, format: money },
  ]);
}

function init() {
  document.getElementById("periodBadge").textContent = dashboardData.meta.period;
  fillSelect(filters.year, dashboardData.filters.years, "All years");
  fillSelect(filters.market, dashboardData.filters.markets, "All markets");
  fillSelect(filters.category, dashboardData.filters.categories, "All categories");

  Object.values(filters).forEach((select) => select.addEventListener("change", update));
  document.getElementById("resetFilters").addEventListener("click", () => {
    Object.values(filters).forEach((select) => {
      select.value = "All";
    });
    update();
  });

  update();
}

init();
