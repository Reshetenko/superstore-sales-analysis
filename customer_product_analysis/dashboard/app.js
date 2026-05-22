const data = window.CUSTOMER_PRODUCT_DASHBOARD_DATA;
const customers = data.customers;
const products = data.products;
const segments = data.segments;
const pareto = data.pareto;

const segmentFilter = document.getElementById("segmentFilter");
const abcFilter = document.getElementById("abcFilter");

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const integer = new Intl.NumberFormat("en-US", {
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

function filteredCustomers() {
  return customers.filter((row) => {
    const segmentOk = segmentFilter.value === "All" || row.segment === segmentFilter.value;
    const abcOk = abcFilter.value === "All" || row.abc_class === abcFilter.value;
    return segmentOk && abcOk;
  });
}

function totals(rows) {
  const result = rows.reduce(
    (acc, row) => {
      acc.sales += row.sales || 0;
      acc.profit += row.profit || 0;
      acc.orders += row.orders || 0;
      return acc;
    },
    { sales: 0, profit: 0, orders: 0 }
  );
  result.margin = result.sales ? result.profit / result.sales : 0;
  return result;
}

function svgWrap(width, height, content) {
  return `<svg viewBox="0 0 ${width} ${height}" role="img">${content}</svg>`;
}

function text(x, y, label, cls = "", anchor = "start") {
  return `<text x="${x}" y="${y}" text-anchor="${anchor}" class="${cls}">${label}</text>`;
}

function paretoChart(el) {
  const width = 1080;
  const height = 390;
  const left = 70;
  const right = 35;
  const top = 28;
  const bottom = 58;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const step = Math.max(Math.floor(pareto.length / 150), 1);
  const points = pareto
    .filter((_, index) => index % step === 0)
    .map((row) => {
      const x = left + row.customer_rank_share * plotW;
      const y = top + plotH - row.cumulative_profit_share * plotH;
      return `${x},${y}`;
    })
    .join(" ");

  const y80 = top + plotH - 0.8 * plotH;
  const y95 = top + plotH - 0.95 * plotH;
  el.innerHTML = svgWrap(
    width,
    height,
    `
      <line x1="${left}" y1="${top + plotH}" x2="${width - right}" y2="${top + plotH}" stroke="var(--line)" />
      <line x1="${left}" y1="${top}" x2="${left}" y2="${top + plotH}" stroke="var(--line)" />
      <line x1="${left}" y1="${y80}" x2="${width - right}" y2="${y80}" stroke="var(--orange)" />
      <line x1="${left}" y1="${y95}" x2="${width - right}" y2="${y95}" stroke="var(--orange)" />
      <polyline points="${points}" fill="none" stroke="var(--blue)" stroke-width="5" />
      ${text(width - right - 92, y80 - 8, "80% profit", "chart-label")}
      ${text(width - right - 92, y95 - 8, "95% profit", "chart-label")}
      ${text(left, height - 24, "0%", "axis-label", "middle")}
      ${text(left + plotW * 0.25, height - 24, "25%", "axis-label", "middle")}
      ${text(left + plotW * 0.5, height - 24, "50%", "axis-label", "middle")}
      ${text(left + plotW * 0.75, height - 24, "75%", "axis-label", "middle")}
      ${text(left + plotW, height - 24, "100%", "axis-label", "middle")}
      ${text(18, top + plotH, "0%", "axis-label")}
      ${text(10, top + plotH * 0.5, "50%", "axis-label")}
      ${text(0, top + 5, "100%", "axis-label")}
      ${text(left + 350, height - 4, "Share of profitable customers", "chart-label")}
    `
  );
}

function barChart(el, rows, key, labelKey, formatter = money, color = "var(--green)") {
  const width = 680;
  const rowH = 42;
  const left = 185;
  const right = 92;
  const height = Math.max(230, rows.length * rowH + 28);
  const maxAbs = Math.max(...rows.map((row) => Math.abs(row[key])), 1);
  const hasNegative = rows.some((row) => row[key] < 0);
  const zero = hasNegative ? left + (width - left - right) / 2 : left;
  const scale = (hasNegative ? (width - left - right) / 2 : width - left - right) / maxAbs;

  const bars = rows
    .map((row, index) => {
      const y = 18 + index * rowH;
      const value = row[key];
      const x2 = zero + value * scale;
      const x = Math.min(zero, x2);
      const w = Math.max(Math.abs(x2 - zero), 1);
      const fill = value < 0 ? "var(--red)" : color;
      const labelX = value < 0 ? x - 8 : x + w + 8;
      const anchor = value < 0 ? "end" : "start";
      return `
        ${text(8, y + 20, String(row[labelKey]).slice(0, 25), "axis-label")}
        <rect x="${x}" y="${y}" width="${w}" height="24" rx="4" fill="${fill}" />
        ${text(labelX, y + 18, formatter(value), "chart-label", anchor)}
      `;
    })
    .join("");

  el.innerHTML = svgWrap(
    width,
    height,
    `<line x1="${zero}" y1="10" x2="${zero}" y2="${height - 8}" stroke="var(--line)" />${bars}`
  );
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
  const filtered = filteredCustomers();
  const total = totals(filtered);
  document.getElementById("customersKpi").textContent = integer.format(filtered.length);
  document.getElementById("productsKpi").textContent = integer.format(data.meta.products);
  document.getElementById("salesKpi").textContent = money(total.sales);
  document.getElementById("profitKpi").textContent = money(total.profit);
  document.getElementById("profitKpi").className = total.profit < 0 ? "negative" : "positive";
  document.getElementById("marginKpi").textContent = pct(total.margin);

  paretoChart(document.getElementById("paretoChart"));
  barChart(
    document.getElementById("segmentChart"),
    segments.sort((a, b) => b.profit - a.profit),
    "profit",
    "segment"
  );

  const abcRows = ["A", "B", "C", "Loss"]
    .map((name) => data.abcSummary.find((row) => row.abc_class === name))
    .filter(Boolean);
  table(document.getElementById("abcTable"), abcRows, [
    { key: "abc_class", label: "Class" },
    { key: "customers", label: "Customers", numeric: true, format: integer.format },
    { key: "sales", label: "Sales", numeric: true, format: money },
    { key: "profit", label: "Profit", numeric: true, format: money },
  ]);

  const tableColumns = [
    { key: "customer_name", label: "Customer" },
    { key: "segment", label: "Segment" },
    { key: "sales", label: "Sales", numeric: true, format: money },
    { key: "profit", label: "Profit", numeric: true, format: money },
    { key: "profit_margin", label: "Margin", numeric: true, format: pct },
  ];

  table(
    document.getElementById("topCustomers"),
    [...filtered].sort((a, b) => b.profit - a.profit).slice(0, 8),
    tableColumns
  );
  table(
    document.getElementById("bottomCustomers"),
    [...filtered].sort((a, b) => a.profit - b.profit).slice(0, 8),
    tableColumns
  );

  const productColumns = [
    { key: "product_name", label: "Product" },
    { key: "sub_category", label: "Sub-category" },
    { key: "sales", label: "Sales", numeric: true, format: money },
    { key: "profit", label: "Profit", numeric: true, format: money },
    { key: "profit_margin", label: "Margin", numeric: true, format: pct },
  ];
  table(
    document.getElementById("topProducts"),
    [...products].sort((a, b) => b.profit - a.profit).slice(0, 8),
    productColumns
  );
  table(
    document.getElementById("bottomProducts"),
    [...products].sort((a, b) => a.profit - b.profit).slice(0, 8),
    productColumns
  );
}

function init() {
  const segments = [...new Set(customers.map((row) => row.segment))].sort();
  fillSelect(segmentFilter, segments, "All segments");
  fillSelect(abcFilter, ["A", "B", "C", "Loss"], "All classes");
  segmentFilter.addEventListener("change", update);
  abcFilter.addEventListener("change", update);
  document.getElementById("resetFilters").addEventListener("click", () => {
    segmentFilter.value = "All";
    abcFilter.value = "All";
    update();
  });
  update();
}

init();
