from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "SuperStoreOrders.csv"
OUTPUT_DIR = ROOT / "outputs"
TABLE_DIR = OUTPUT_DIR / "tables"
CHART_DIR = OUTPUT_DIR / "charts"


def money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.1%}"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["sales"] = pd.to_numeric(df["sales"].astype(str).str.replace(",", "", regex=False).str.strip())
    df["order_date"] = pd.to_datetime(df["order_date"], dayfirst=True, format="mixed")
    df["ship_date"] = pd.to_datetime(df["ship_date"], dayfirst=True, format="mixed")
    df["ship_days"] = (df["ship_date"] - df["order_date"]).dt.days
    df["profit_margin"] = df["profit"] / df["sales"]
    return df


def summarize(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "orders": df["order_id"].nunique(),
        "customers": df["customer_name"].nunique(),
        "sales": df["sales"].sum(),
        "profit": df["profit"].sum(),
        "profit_margin": df["profit"].sum() / df["sales"].sum(),
        "avg_discount": df["discount"].mean(),
        "loss_orders": int((df["profit"] < 0).sum()),
        "loss_order_share": (df["profit"] < 0).mean(),
    }


def grouped_performance(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    result = (
        df.groupby(cols, dropna=False, observed=False)
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            quantity=("quantity", "sum"),
            orders=("order_id", "nunique"),
            avg_discount=("discount", "mean"),
            avg_ship_days=("ship_days", "mean"),
        )
        .reset_index()
    )
    result["profit_margin"] = result["profit"] / result["sales"]
    return result.sort_values("profit", ascending=False)


def save_tables(df: pd.DataFrame) -> dict:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    tables = {
        "yearly_performance": grouped_performance(df, ["year"]).sort_values("year"),
        "market_performance": grouped_performance(df, ["market"]),
        "region_performance": grouped_performance(df, ["market", "region"]),
        "category_performance": grouped_performance(df, ["category"]),
        "subcategory_performance": grouped_performance(df, ["sub_category"]),
        "segment_performance": grouped_performance(df, ["segment"]),
        "country_losses": grouped_performance(df, ["country"]).sort_values("profit").head(15),
        "product_losses": grouped_performance(df, ["product_name", "category", "sub_category"]).sort_values("profit").head(15),
    }

    discount = df.copy()
    discount["discount_bucket"] = pd.cut(
        discount["discount"],
        bins=[-0.01, 0, 0.1, 0.2, 0.3, 0.5, 1.0],
        labels=["0%", "0-10%", "10-20%", "20-30%", "30-50%", "50%+"],
    )
    tables["discount_performance"] = grouped_performance(discount, ["discount_bucket"]).sort_values("discount_bucket")
    tables["discount_by_category"] = grouped_performance(discount, ["category", "discount_bucket"]).sort_values(
        ["category", "discount_bucket"]
    )
    tables["discount_by_market"] = grouped_performance(discount, ["market", "discount_bucket"]).sort_values(
        ["market", "discount_bucket"]
    )

    for name, table in tables.items():
        table.to_csv(TABLE_DIR / f"{name}.csv", index=False)

    return tables


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


def bar_chart(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    filename: str,
    color: tuple[int, int, int] = (45, 103, 180),
    money_axis: bool = True,
) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1200, 760
    margin_left, margin_right, margin_top, margin_bottom = 260, 80, 100, 70
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(34, bold=True)
    label_font = _font(20)
    small_font = _font(18)

    draw.text((margin_left, 35), title, fill=(20, 28, 38), font=title_font)

    values = data[value_col].astype(float).tolist()
    labels = data[label_col].astype(str).tolist()
    max_abs = max(abs(v) for v in values) or 1
    row_h = plot_h / len(values)
    zero_x = margin_left if min(values) >= 0 else margin_left + plot_w / 2
    scale = (plot_w if min(values) >= 0 else plot_w / 2) / max_abs

    draw.line((zero_x, margin_top - 10, zero_x, height - margin_bottom + 15), fill=(160, 170, 180), width=2)

    for i, (label, value) in enumerate(zip(labels, values)):
        y = margin_top + i * row_h + row_h * 0.18
        bar_h = row_h * 0.55
        x2 = zero_x + value * scale
        x0, x1 = sorted([zero_x, x2])
        fill = color if value >= 0 else (196, 67, 72)
        draw.rounded_rectangle((x0, y, x1, y + bar_h), radius=5, fill=fill)
        draw.text((20, y + 2), label[:28], fill=(45, 52, 61), font=label_font)
        value_text = money(value) if money_axis else percent(value)
        text_x = min(max(x1 + 10, margin_left + 5), width - margin_right - 150)
        if value < 0:
            text_x = max(x0 - 155, margin_left + 5)
        draw.text((text_x, y + 2), value_text, fill=(45, 52, 61), font=small_font)

    img.save(CHART_DIR / filename)


def line_chart(data: pd.DataFrame, title: str, filename: str) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1200, 720
    margin_left, margin_right, margin_top, margin_bottom = 110, 80, 100, 120
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(34, bold=True)
    label_font = _font(20)
    small_font = _font(18)

    draw.text((margin_left, 35), title, fill=(20, 28, 38), font=title_font)
    draw.line((margin_left, height - margin_bottom, width - margin_right, height - margin_bottom), fill=(160, 170, 180), width=2)
    draw.line((margin_left, margin_top, margin_left, height - margin_bottom), fill=(160, 170, 180), width=2)

    years = data["year"].astype(str).tolist()
    sales = data["sales"].astype(float).tolist()
    profit = data["profit"].astype(float).tolist()
    max_value = max(sales) * 1.1

    def points(values: list[float]) -> list[tuple[float, float]]:
        result = []
        for i, value in enumerate(values):
            x = margin_left + i * plot_w / (len(values) - 1)
            y = height - margin_bottom - value / max_value * plot_h
            result.append((x, y))
        return result

    sales_points = points(sales)
    profit_points = points(profit)
    draw.line(sales_points, fill=(45, 103, 180), width=5)
    draw.line(profit_points, fill=(35, 140, 95), width=5)

    for i, year in enumerate(years):
        x = margin_left + i * plot_w / (len(years) - 1)
        draw.text((x - 22, height - margin_bottom + 22), year, fill=(45, 52, 61), font=label_font)

    for point, value in zip(sales_points, sales):
        draw.ellipse((point[0] - 7, point[1] - 7, point[0] + 7, point[1] + 7), fill=(45, 103, 180))
        draw.text((point[0] - 55, point[1] - 34), money(value), fill=(45, 103, 180), font=small_font)

    for point, value in zip(profit_points, profit):
        draw.ellipse((point[0] - 7, point[1] - 7, point[0] + 7, point[1] + 7), fill=(35, 140, 95))
        draw.text((point[0] - 48, point[1] - 34), money(value), fill=(35, 140, 95), font=small_font)

    legend_y = height - 58
    draw.rectangle((margin_left, legend_y, margin_left + 24, legend_y + 24), fill=(45, 103, 180))
    draw.text((margin_left + 34, legend_y - 2), "Sales", fill=(45, 52, 61), font=label_font)
    draw.rectangle((margin_left + 160, legend_y, margin_left + 184, legend_y + 24), fill=(35, 140, 95))
    draw.text((margin_left + 194, legend_y - 2), "Profit", fill=(45, 52, 61), font=label_font)

    img.save(CHART_DIR / filename)


def _margin_color(value: float) -> tuple[int, int, int]:
    if pd.isna(value):
        return (238, 240, 243)
    value = max(min(value, 0.30), -0.60)
    if value >= 0:
        intensity = value / 0.30
        r = int(232 - 150 * intensity)
        g = int(246 - 74 * intensity)
        b = int(238 - 108 * intensity)
        return (r, g, b)
    intensity = abs(value) / 0.60
    r = int(250 - 54 * intensity)
    g = int(230 - 163 * intensity)
    b = int(230 - 158 * intensity)
    return (r, g, b)


def heatmap_chart(
    data: pd.DataFrame,
    row_col: str,
    col_col: str,
    value_col: str,
    title: str,
    filename: str,
    row_order: list[str] | None = None,
) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    pivot = data.pivot(index=row_col, columns=col_col, values=value_col)
    if row_order:
        pivot = pivot.reindex(row_order)

    rows = [str(v) for v in pivot.index.tolist()]
    cols = [str(v) for v in pivot.columns.tolist()]
    width, height = 1300, 760
    margin_left, margin_top = 220, 150
    cell_w = (width - margin_left - 70) / len(cols)
    cell_h = (height - margin_top - 90) / len(rows)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(34, bold=True)
    label_font = _font(20)
    small_font = _font(17)

    draw.text((margin_left, 35), title, fill=(20, 28, 38), font=title_font)
    draw.text((margin_left, 84), "Cell values show profit margin. Green is profitable; red is loss-making.", fill=(93, 109, 126), font=small_font)

    for j, col in enumerate(cols):
        x = margin_left + j * cell_w
        draw.text((x + 8, margin_top - 34), col, fill=(45, 52, 61), font=small_font)

    for i, row in enumerate(rows):
        y = margin_top + i * cell_h
        draw.text((20, y + cell_h * 0.32), row[:24], fill=(45, 52, 61), font=label_font)
        for j, col in enumerate(cols):
            x = margin_left + j * cell_w
            value = pivot.iloc[i, j]
            fill = _margin_color(value)
            draw.rectangle((x, y, x + cell_w - 4, y + cell_h - 4), fill=fill, outline=(255, 255, 255), width=2)
            text = "n/a" if pd.isna(value) else percent(float(value))
            draw.text((x + 12, y + cell_h * 0.32), text, fill=(20, 28, 38), font=small_font)

    img.save(CHART_DIR / filename)


def save_charts(tables: dict) -> None:
    yearly = tables["yearly_performance"]
    line_chart(yearly, "Sales and Profit Trend, 2011-2014", "sales_profit_trend.png")

    market = tables["market_performance"].sort_values("profit", ascending=True)
    bar_chart(market, "market", "profit", "Profit by Market", "profit_by_market.png", color=(35, 140, 95))

    category = tables["category_performance"].sort_values("profit_margin", ascending=True)
    bar_chart(
        category,
        "category",
        "profit_margin",
        "Profit Margin by Category",
        "margin_by_category.png",
        color=(122, 90, 168),
        money_axis=False,
    )

    discount = tables["discount_performance"].sort_values("profit_margin", ascending=True)
    bar_chart(
        discount,
        "discount_bucket",
        "profit_margin",
        "Profit Margin by Discount Bucket",
        "margin_by_discount.png",
        color=(219, 137, 52),
        money_axis=False,
    )

    heatmap_chart(
        tables["discount_by_category"],
        "category",
        "discount_bucket",
        "profit_margin",
        "Discount Impact by Category",
        "discount_impact_by_category.png",
        row_order=["Furniture", "Office Supplies", "Technology"],
    )

    market_order = (
        tables["market_performance"]
        .sort_values("profit", ascending=False)["market"]
        .astype(str)
        .tolist()
    )
    heatmap_chart(
        tables["discount_by_market"],
        "market",
        "discount_bucket",
        "profit_margin",
        "Discount Impact by Market",
        "discount_impact_by_market.png",
        row_order=market_order,
    )


def main() -> None:
    df = load_data()
    summary = summarize(df)
    tables = save_tables(df)
    save_charts(tables)

    summary_rows = [
        ("Rows", f"{summary['rows']:,}"),
        ("Orders", f"{summary['orders']:,}"),
        ("Customers", f"{summary['customers']:,}"),
        ("Sales", money(summary["sales"])),
        ("Profit", money(summary["profit"])),
        ("Profit margin", percent(summary["profit_margin"])),
        ("Average discount", percent(summary["avg_discount"])),
        ("Loss-making rows", f"{summary['loss_orders']:,}"),
        ("Loss-making row share", percent(summary["loss_order_share"])),
    ]
    pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(TABLE_DIR / "summary_metrics.csv", index=False)

    print("SuperStore analysis complete")
    for metric, value in summary_rows:
        print(f"{metric}: {value}")


if __name__ == "__main__":
    main()
