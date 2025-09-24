from datetime import date
import calendar
import pandas as pd
from . import storage as S

def get_month_bounds(year: int, month: int):
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return start, end

def _between(df: pd.DataFrame, col: str, start: date, end: date):
    if df.empty: return df
    if df[col].dtype != "datetime64[ns]":
        df[col] = pd.to_datetime(df[col])
    return df[(df[col] >= pd.to_datetime(start)) & (df[col] <= pd.to_datetime(end))]

def totals_for_period(start_dt: date, end_dt: date):
    tx = S.load_transactions()
    txp = _between(tx, "date", start_dt, end_dt)
    income = txp.loc[txp["type"] == "income", "amount"].sum()
    expenses = txp.loc[txp["type"] == "expense", "amount"].sum()
    return float(income), float(expenses), float(income - expenses)

def current_savings():
    tx = S.load_transactions()
    inc = tx.loc[tx["type"] == "income", "amount"].sum()
    exp = tx.loc[tx["type"] == "expense", "amount"].sum()
    starts = S.load_accounts()["starting_balance"].sum()
    return float(inc - exp + starts)

def expenses_by_category(start_dt: date, end_dt: date) -> pd.DataFrame:
    tx = S.load_transactions()
    cats = S.load_categories()
    txp = _between(tx, "date", start_dt, end_dt)
    exp = txp[txp["type"] == "expense"]
    if exp.empty:
        return pd.DataFrame(columns=["category","amount"])
    merged = exp.merge(cats[["id","name"]], left_on="category_id", right_on="id", how="left")
    out = merged.groupby("name", dropna=False)["amount"].sum().reset_index().rename(columns={"name":"category"})
    out = out.sort_values(["amount","category"], ascending=[False, True])
    return out

def monthly_cashflow(reference_year: int, reference_month: int, months: int = 6) -> pd.DataFrame:
    periods = []
    y, m = reference_year, reference_month
    for _ in range(months-1, -1, -1):
        periods.append((y, m, f"{y:04d}-{m:02d}"))
        # move back one month
        m -= 1
        if m == 0: m, y = 12, y - 1

    rows = []
    for yy, mm, label in reversed(periods):
        s, e = get_month_bounds(yy, mm)
        inc, exp, net = totals_for_period(s, e)
        rows.append({"period": label, "income": inc, "expenses": exp, "net": net})
    return pd.DataFrame(rows)
