from pathlib import Path
import json

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "SuperStoreOrders.csv"
OUTPUT_DIR = ROOT / "customer_product_analysis"
TABLE_DIR = OUTPUT_DIR / "tables"
CHART_DIR = OUTPUT_DIR / "charts"
DASHBOARD_DIR = OUTPUT_DIR / "dashboard"


def money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.1%}"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["sales"] = pd.to_numeric(df["sales"].astype(str).str.replace(",", "", regex=False).str.strip())
    df["order_date"] = pd.to_datetime(df["order_date"], dayfirst=True, format="mixed")
    df["profit_margin"] = df["profit"] / df["sales"]
    return df


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def grouped(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    table = (
        df.groupby(cols, dropna=False, observed=False)
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            quantity=("quantity", "sum"),
            rows=("order_id", "size"),
            orders=("order_id", "nunique"),
            avg_discount=("discount", "mean"),
        )
        .reset_index()
    )
    table["profit_margin"] = table["profit"] / table["sales"]
    return table


def add_abc(table: pd.DataFrame, value_col: str = "profit") -> pd.DataFrame:
    result = table.sort_values(value_col, ascending=False).copy()
    positive_total = result.loc[result[value_col] > 0, value_col].sum()
    result["cumulative_profit"] = result[value_col].clip(lower=0).cumsum()
    result["cumulative_profit_share"] = result["cumulative_profit"] / positive_total
    result["abc_class"] = pd.cut(
        result["cumulative_profit_share"],
        bins=[-0.01, 0.8, 0.95, 1.01],
        labels=["A", "B", "C"],
    ).astype(str)
    result.loc[result[value_col] <= 0, "abc_class"] = "Loss"
    return result


def customer_table(df: pd.DataFrame) -> pd.DataFrame:
    table = (
        df.groupby("customer_name", dropna=False)
        .agg(
            segment=("segment", lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0]),
            markets=("market", "nunique"),
            countries=("country", "nunique"),
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            quantity=("quantity", "sum"),
            rows=("order_id", "size"),
            orders=("order_id", "nunique"),
            avg_discount=("discount", "mean"),
        )
        .reset_index()
    )
    table["profit_margin"] = table["profit"] / table["sales"]
    return table


def bar_chart(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    filename: str,
    color: tuple[int, int, int] = (45, 103, 180),
) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1300, 780
    margin_left, margin_right, margin_top, margin_bottom = 330, 90, 95, 60
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(34, bold=True)
    label_font = _font(19)
    small_font = _font(17)

    draw.text((margin_left, 34), title, fill=(20, 28, 38), font=title_font)
    values = data[value_col].astype(float).tolist()
    labels = data[label_col].astype(str).tolist()
    max_abs = max(abs(v) for v in values) or 1
    row_h = plot_h / len(values)
    zero_x = margin_left if min(values) >= 0 else margin_left + plot_w / 2
    scale = (plot_w if min(values) >= 0 else plot_w / 2) / max_abs
    draw.line((zero_x, margin_top - 8, zero_x, height - margin_bottom + 10), fill=(164, 174, 186), width=2)

    for i, (label, value) in enumerate(zip(labels, values)):
        y = margin_top + i * row_h + row_h * 0.18
        bar_h = row_h * 0.55
        x2 = zero_x + value * scale
        x0, x1 = sorted([zero_x, x2])
        fill = color if value >= 0 else (196, 67, 72)
        draw.rounded_rectangle((x0, y, x1, y + bar_h), radius=5, fill=fill)
        draw.text((20, y + 2), label[:38], fill=(45, 52, 61), font=label_font)
        value_text = money(value)
        text_x = min(max(x1 + 10, margin_left + 5), width - margin_right - 145)
        if value < 0:
            text_x = max(x0 - 145, margin_left + 5)
        draw.text((text_x, y + 2), value_text, fill=(45, 52, 61), font=small_font)

    img.save(CHART_DIR / filename)


def pareto_chart(customer_abc: pd.DataFrame) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    positive = customer_abc[customer_abc["profit"] > 0].copy()
    positive["customer_rank_share"] = range(1, len(positive) + 1)
    positive["customer_rank_share"] = positive["customer_rank_share"] / len(positive)
    width, height = 1200, 720
    left, right, top, bottom = 100, 70, 95, 80
    plot_w = width - left - right
    plot_h = height - top - bottom
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(34, bold=True)
    label_font = _font(18)
    draw.text((left, 35), "Customer Profit Pareto Curve", fill=(20, 28, 38), font=title_font)
    draw.line((left, height - bottom, width - right, height - bottom), fill=(164, 174, 186), width=2)
    draw.line((left, top, left, height - bottom), fill=(164, 174, 186), width=2)

    step = max(len(positive) // 160, 1)
    sample = positive.iloc[::step]
    points = []
    for _, row in sample.iterrows():
        x = left + row["customer_rank_share"] * plot_w
        y = height - bottom - row["cumulative_profit_share"] * plot_h
        points.append((x, y))
    draw.line(points, fill=(45, 103, 180), width=5)

    for threshold, label in [(0.8, "80% profit"), (0.95, "95% profit")]:
        y = height - bottom - threshold * plot_h
        draw.line((left, y, width - right, y), fill=(217, 137, 52), width=2)
        draw.text((width - right - 105, y - 22), label, fill=(93, 109, 126), font=label_font)
    for share, label in [(0, "0%"), (0.25, "25%"), (0.5, "50%"), (0.75, "75%"), (1, "100%")]:
        x = left + share * plot_w
        draw.text((x - 16, height - bottom + 25), label, fill=(93, 109, 126), font=label_font)
        y = height - bottom - share * plot_h
        draw.text((left - 60, y - 10), label, fill=(93, 109, 126), font=label_font)

    draw.text((left + 360, height - 30), "Share of profitable customers", fill=(45, 52, 61), font=label_font)
    img.save(CHART_DIR / "customer_profit_pareto.png")


def save_outputs(df: pd.DataFrame) -> dict:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    customer = customer_table(df).sort_values("profit", ascending=False)
    customer_abc = add_abc(customer)
    product = grouped(df, ["product_name", "category", "sub_category"]).sort_values("profit", ascending=False)
    segment = grouped(df, ["segment"]).sort_values("profit", ascending=False)

    tables = {
        "customer_profitability": customer_abc,
        "top_customers": customer.sort_values("profit", ascending=False).head(20),
        "bottom_customers": customer.sort_values("profit").head(20),
        "product_profitability": product,
        "top_products": product.sort_values("profit", ascending=False).head(20),
        "bottom_products": product.sort_values("profit").head(20),
        "segment_profitability": segment,
        "abc_summary": customer_abc.groupby("abc_class", dropna=False)
        .agg(customers=("customer_name", "count"), sales=("sales", "sum"), profit=("profit", "sum"))
        .reset_index()
        .sort_values("abc_class"),
    }

    for name, table in tables.items():
        table.to_csv(TABLE_DIR / f"{name}.csv", index=False)

    bar_chart(tables["top_customers"].head(10), "customer_name", "profit", "Top 10 Customers by Profit", "top_customers_profit.png", (35, 140, 95))
    bar_chart(tables["bottom_customers"].head(10), "customer_name", "profit", "Bottom 10 Customers by Profit", "bottom_customers_profit.png")
    bar_chart(tables["top_products"].head(10), "product_name", "profit", "Top 10 Products by Profit", "top_products_profit.png", (35, 140, 95))
    bar_chart(tables["bottom_products"].head(10), "product_name", "profit", "Bottom 10 Products by Profit", "bottom_products_profit.png")
    pareto_chart(customer_abc)

    return tables


def to_records(table: pd.DataFrame) -> list[dict]:
    return json.loads(table.to_json(orient="records"))


def save_dashboard_data(tables: dict) -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    customer = tables["customer_profitability"].copy()
    product = tables["product_profitability"].copy()
    segment = tables["segment_profitability"].copy()
    positive = customer[customer["profit"] > 0].copy()
    positive["customer_rank_share"] = range(1, len(positive) + 1)
    positive["customer_rank_share"] = positive["customer_rank_share"] / len(positive)

    data = {
        "meta": {
            "customers": int(customer["customer_name"].nunique()),
            "products": int(product["product_name"].nunique()),
            "lossCustomers": int((customer["profit"] < 0).sum()),
            "customersFor80PctProfit": int((positive["cumulative_profit_share"] <= 0.8).sum()),
        },
        "customers": to_records(customer),
        "products": to_records(product),
        "segments": to_records(segment),
        "abcSummary": to_records(tables["abc_summary"]),
        "pareto": to_records(positive[["customer_name", "customer_rank_share", "cumulative_profit_share", "profit"]]),
    }

    (DASHBOARD_DIR / "data.js").write_text(
        "window.CUSTOMER_PRODUCT_DASHBOARD_DATA = "
        + json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )


def main() -> None:
    df = load_data()
    tables = save_outputs(df)
    save_dashboard_data(tables)
    customer_abc = tables["customer_profitability"]
    profitable = customer_abc[customer_abc["profit"] > 0]
    customers_for_80 = int((profitable["cumulative_profit_share"] <= 0.8).sum())
    print("Customer and product profitability analysis complete")
    print(f"Customers analyzed: {customer_abc['customer_name'].nunique():,}")
    print(f"Products analyzed: {tables['product_profitability']['product_name'].nunique():,}")
    print(f"Customers needed for 80% of positive profit: {customers_for_80:,}")
    print(f"Output folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
