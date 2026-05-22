import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "SuperStoreOrders.csv"
DASHBOARD_DIR = ROOT / "dashboard"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["sales"] = pd.to_numeric(df["sales"].astype(str).str.replace(",", "", regex=False).str.strip())
    df["order_date"] = pd.to_datetime(df["order_date"], dayfirst=True, format="mixed")
    df["year"] = df["order_date"].dt.year
    df["discount_bucket"] = pd.cut(
        df["discount"],
        bins=[-0.01, 0, 0.1, 0.2, 0.3, 0.5, 1.0],
        labels=["0%", "0-10%", "10-20%", "20-30%", "30-50%", "50%+"],
    ).astype(str)
    return df


def grouped(df: pd.DataFrame, cols: list[str]) -> list[dict]:
    df = df.copy()
    df["loss_rows"] = df["profit"] < 0
    table = (
        df.groupby(cols, dropna=False, observed=False)
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            quantity=("quantity", "sum"),
            rows=("order_id", "size"),
            loss_rows=("loss_rows", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
    )
    table["profit_margin"] = table["profit"] / table["sales"]
    return json.loads(table.to_json(orient="records"))


def options(df: pd.DataFrame, col: str) -> list:
    return sorted(df[col].dropna().unique().tolist())


def main() -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()

    data = {
        "meta": {
            "title": "SuperStore Sales Dashboard",
            "period": f"{df['year'].min()}-{df['year'].max()}",
            "rows": int(len(df)),
        },
        "filters": {
            "years": options(df, "year"),
            "markets": options(df, "market"),
            "categories": options(df, "category"),
        },
        "records": grouped(df, ["year", "market", "category", "discount_bucket", "country"]),
        "topProducts": grouped(df, ["year", "market", "category", "product_name", "sub_category"]),
    }

    output = DASHBOARD_DIR / "data.js"
    output.write_text(
        "window.SUPERSTORE_DASHBOARD_DATA = "
        + json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )
    print(f"Dashboard data written to {output}")
    print(f"Records: {len(data['records']):,}")
    print(f"Product records: {len(data['topProducts']):,}")


if __name__ == "__main__":
    main()
