import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from core.logic import (
    get_month_bounds,
    totals_for_period,
    current_savings,
    expenses_by_category,
    monthly_cashflow,
)
from core.utils import ensure_seed_data
from core import storage as S

st.set_page_config(page_title="FlowFox – Personal Finance Studio", page_icon="🦊", layout="wide")
ensure_seed_data()

# --------- light styling for "cards" ---------
st.markdown("""
<style>
.kpi-card {
  padding: 16px; border-radius: 16px; border: 1px solid #e7e7e7;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.kpi-label { font-size: 0.85rem; color: #666; margin-bottom: 4px; }
.kpi-value { font-size: 1.4rem; font-weight: 700; }
.section { padding: 10px 14px; border-radius: 14px; border: 1px solid #eee; background: #fff; }
.quick-links a { text-decoration: none; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.title("🦊 FlowFox – Personal Finance Studio")
st.caption("Track income, expenses, budgets, and savings — simply and beautifully.")

# --------- Filters ---------
with st.sidebar:
    st.header("Filters")
    today = date.today()
    year = st.number_input("Year", 2000, 2100, today.year, step=1)
    month = st.number_input("Month", 1, 12, today.month, step=1)

start_dt, end_dt = get_month_bounds(year, month)

# --------- KPIs ---------
income_sum, expense_sum, net_sum = totals_for_period(start_dt, end_dt)
savings = current_savings()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="kpi-card"><div class="kpi-label">This Month Income</div>'
                f'<div class="kpi-value">${income_sum:,.2f}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="kpi-card"><div class="kpi-label">This Month Expenses</div>'
                f'<div class="kpi-value">${expense_sum:,.2f}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="kpi-card"><div class="kpi-label">Net</div>'
                f'<div class="kpi-value">${net_sum:,.2f}</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="kpi-card"><div class="kpi-label">Current Savings</div>'
                f'<div class="kpi-value">${savings:,.2f}</div></div>', unsafe_allow_html=True)

st.markdown(" ")

# --------- Quick links ---------
ql1, ql2, ql3, ql4 = st.columns(4)
with ql1: st.markdown('<div class="section quick-links">➕ <a href="/1_Transactions" target="_self">Add Transaction</a></div>', unsafe_allow_html=True)
with ql2: st.markdown('<div class="section quick-links">🏦 <a href="/3_Accounts" target="_self">Manage Accounts</a></div>', unsafe_allow_html=True)
with ql3: st.markdown('<div class="section quick-links">🗂️ <a href="/2_Categories" target="_self">Edit Categories</a></div>', unsafe_allow_html=True)
with ql4: st.markdown('<div class="section quick-links">📊 <a href="/5_Reports" target="_self">Open Reports</a></div>', unsafe_allow_html=True)

st.markdown(" ")

# --------- This-month breakdown (donut + bar) ---------
tx = S.load_transactions()
cats = S.load_categories()

left, right = st.columns([1, 1])
if not tx.empty:
    tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
    tx_m = tx[(tx["date"] >= pd.to_datetime(start_dt)) & (tx["date"] <= pd.to_datetime(end_dt))]
    exp_m = tx_m[tx_m["type"] == "expense"]
    inc_m = tx_m[tx_m["type"] == "income"]

    if not exp_m.empty:
        em = exp_m.merge(cats[["id", "name"]].rename(columns={"id": "category_id", "name": "category"}), on="category_id", how="left")
        exp_by_cat = em.groupby("category", dropna=False)["amount"].sum().reset_index().sort_values("amount", ascending=False)
        with left:
            st.subheader("This Month • Expense Mix")
            fig = px.pie(exp_by_cat, names="category", values="amount", hole=0.55)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
    else:
        left.info("No expenses this month yet.")

    if not inc_m.empty:
        im = inc_m.merge(cats[["id", "name"]].rename(columns={"id": "category_id", "name": "category"}), on="category_id", how="left")
        inc_by_cat = im.groupby("category", dropna=False)["amount"].sum().reset_index().sort_values("amount", ascending=False)
        with right:
            st.subheader("This Month • Income by Category")
            fig2 = px.bar(inc_by_cat, x="category", y="amount")
            fig2.update_layout(xaxis_title="", yaxis_title="Amount")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        right.info("No income this month yet.")
else:
    left.info("Add your first transaction to see insights.")
    right.info("Add your first transaction to see insights.")

st.markdown(" ")
st.subheader("Trends (Last 6 Months)")
cf = monthly_cashflow(reference_year=year, reference_month=month, months=6)
if cf.empty:
    st.info("Add transactions to view trends.")
else:
    figl = px.line(cf, x="period", y=["income", "expenses", "net"])
    figl.update_layout(xaxis_title="", yaxis_title="Amount", legend_title="")
    st.plotly_chart(figl, use_container_width=True)

st.caption("Tip: Use the sidebar filters to change the month view. Use the **pages** on the left to manage data.")
