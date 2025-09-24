# pages/5_Reports.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from core import storage as S
from core.logic import get_month_bounds, monthly_cashflow

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
st.title("📊 Reports")

# ----------------------- Helpers -----------------------
def money(x: float) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"

def safe_to_datetime(s):
    return pd.to_datetime(s, errors="coerce")

# ----------------------- Data --------------------------
tx = S.load_transactions()
cats = S.load_categories()
acc = S.load_accounts()
budgets = S.load_budgets()

# Ensure types
if not tx.empty:
    tx["date"] = safe_to_datetime(tx["date"])

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    today = date.today()
    year = st.number_input("Year", 2000, 2100, today.year, step=1)
    month = st.number_input("Month", 1, 12, today.month, step=1)
    months_back = st.slider("Show last N months (trends)", 3, 24, 6)

start_dt, end_dt = get_month_bounds(year, month)
period_label = f"{year:04d}-{month:02d}"

# KPIs (all-time)
income = float(tx.loc[tx["type"] == "income", "amount"].sum()) if not tx.empty else 0.0
expenses = float(tx.loc[tx["type"] == "expense", "amount"].sum()) if not tx.empty else 0.0
starts = float(acc["starting_balance"].sum()) if not acc.empty else 0.0
net = income - expenses
savings_now = net + starts

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Income", money(income))
c2.metric("Total Expenses", money(expenses))
c3.metric("All-Time Net", money(net))
c4.metric("Current Savings", money(savings_now))

st.markdown("---")

# Tabs for a friendlier UX
tab_overview, tab_trends, tab_budgets, tab_data = st.tabs(
    ["Overview", "Trends", "Budgets", "Data"]
)

# =======================================================
# ===================== OVERVIEW ========================
# =======================================================
with tab_overview:
    st.subheader(f"Overview for {period_label}")

    # Filter this-month data
    tx_month = tx[(tx["date"] >= pd.to_datetime(start_dt)) & (tx["date"] <= pd.to_datetime(end_dt))] if not tx.empty else tx
    month_income = float(tx_month.loc[tx_month["type"] == "income", "amount"].sum()) if not tx_month.empty else 0.0
    month_expense = float(tx_month.loc[tx_month["type"] == "expense", "amount"].sum()) if not tx_month.empty else 0.0
    month_net = month_income - month_expense

    k1, k2, k3 = st.columns(3)
    k1.metric("This Month • Income", money(month_income))
    k2.metric("This Month • Expenses", money(month_expense))
    k3.metric("This Month • Net", money(month_net))

    # Category splits (pie/donut)
    left, right = st.columns(2)
    # Expenses by category
    if not tx_month.empty:
        exp_m = tx_month[tx_month["type"] == "expense"]
        if not exp_m.empty:
            exp_merge = exp_m.merge(
                cats[["id", "name"]].rename(columns={"id": "category_id", "name": "category"}),
                on="category_id", how="left"
            )
            exp_by_cat = exp_merge.groupby("category", dropna=False)["amount"].sum().reset_index().sort_values("amount", ascending=False)
            with left:
                st.caption("Expense Share by Category")
                fig_exp = px.pie(exp_by_cat, names="category", values="amount", hole=0.55)
                fig_exp.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig_exp, use_container_width=True)
        else:
            left.info("No expenses this month.")
        # Income by category
        inc_m = tx_month[tx_month["type"] == "income"]
        if not inc_m.empty:
            inc_merge = inc_m.merge(
                cats[["id", "name"]].rename(columns={"id": "category_id", "name": "category"}),
                on="category_id", how="left"
            )
            inc_by_cat = inc_merge.groupby("category", dropna=False)["amount"].sum().reset_index().sort_values("amount", ascending=False)
            with right:
                st.caption("Income Share by Category")
                fig_inc = px.pie(inc_by_cat, names="category", values="amount", hole=0.35)
                fig_inc.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig_inc, use_container_width=True)
        else:
            right.info("No income this month.")
    else:
        left.info("No transactions this month.")
        right.info("No transactions this month.")

    st.markdown("### Top Categories (This Month)")
    cols = st.columns(2)
    # Top 5 expense categories bar
    if not tx_month.empty and not exp_m.empty:
        top_exp = exp_by_cat.head(5).sort_values("amount")
        with cols[0]:
            fig = px.bar(top_exp, x="amount", y="category", orientation="h", title="Top 5 Expenses")
            fig.update_layout(yaxis_title="", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    else:
        cols[0].info("No expenses to show.")

    # Top 5 income categories bar
    if not tx_month.empty and not inc_m.empty:
        top_inc = inc_by_cat.head(5).sort_values("amount")
        with cols[1]:
            fig = px.bar(top_inc, x="amount", y="category", orientation="h", title="Top 5 Income")
            fig.update_layout(yaxis_title="", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    else:
        cols[1].info("No income to show.")

# =======================================================
# ====================== TRENDS =========================
# =======================================================
with tab_trends:
    st.subheader(f"Trends (last {months_back} months, ending {period_label})")

    cf = monthly_cashflow(reference_year=year, reference_month=month, months=months_back)
    if cf.empty:
        st.info("Add transactions to see trends.")
    else:
        # Line chart for income/expenses/net
        st.caption("Income, Expenses, and Net by Month")
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=cf["period"], y=cf["income"], mode="lines+markers", name="Income"))
        fig_line.add_trace(go.Scatter(x=cf["period"], y=cf["expenses"], mode="lines+markers", name="Expenses"))
        fig_line.add_trace(go.Scatter(x=cf["period"], y=cf["net"], mode="lines+markers", name="Net"))
        fig_line.update_layout(xaxis_title="", yaxis_title="Amount", hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)
