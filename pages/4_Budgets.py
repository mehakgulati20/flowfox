import streamlit as st
import pandas as pd
from datetime import date
from core import storage as S
from core.logic import get_month_bounds

st.set_page_config(page_title="Budgets", page_icon="🎯", layout="wide")
st.title("🎯 Budgets")

cats = S.load_categories()
exp_cats = cats[cats["kind"]=="expense"].sort_values("name")

with st.form("add_budget"):
    st.subheader("Set Monthly Budget")
    c1, c2, c3 = st.columns(3)
    with c1: cat_name = st.selectbox("Category", exp_cats["name"].tolist() if not exp_cats.empty else [])
    with c2: period = st.text_input("Period (YYYY-MM)", value=date.today().strftime("%Y-%m"))
    with c3: amount = st.number_input("Amount", min_value=0.0, step=10.0, value=0.0)
    if st.form_submit_button("Save Budget"):
        if not cat_name: st.error("Pick a category.")
        else:
            cat_id = int(exp_cats.loc[exp_cats["name"]==cat_name,"id"].iloc[0])
            S.upsert_budget(cat_id, period, amount)
            st.success("Budget saved.")

st.markdown("---")
st.subheader("Budget vs Actual (Selected Month)")

with st.sidebar:
    st.header("Filters")
    today = date.today()
    year = st.number_input("Year", 2000, 2100, today.year, step=1, key="bud_year")
    month = st.number_input("Month", 1, 12, today.month, step=1, key="bud_month")

s, e = get_month_bounds(year, month)
period = f"{year:04d}-{month:02d}"

tx = S.load_transactions()
if not tx.empty:
    tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
tx_m = tx[(tx["date"] >= pd.to_datetime(s)) & (tx["date"] <= pd.to_datetime(e))] if not tx.empty else tx
spent = tx_m[tx_m["type"]=="expense"].groupby("category_id")["amount"].sum().reset_index().rename(columns={"category_id":"id","amount":"spent"}) if not tx_m.empty else pd.DataFrame(columns=["id","spent"])

bud = S.load_budgets()
bud_m = bud[bud["period"] == period][["category_id","amount"]].rename(columns={"category_id":"id","amount":"budget"}) if not bud.empty else pd.DataFrame(columns=["id","budget"])

df = exp_cats[["id","name"]].copy().rename(columns={"name":"category"})
df = df.merge(bud_m, on="id", how="left").merge(spent, on="id", how="left")
df["budget"] = df["budget"].fillna(0.0)
df["spent"] = df["spent"].fillna(0.0)
df["utilization"] = (df["spent"] / df["budget"]).replace([float("inf")], 0.0).fillna(0.0)

# Nice table
view = df[["category","budget","spent","utilization"]].copy()
view["budget"] = view["budget"].map(lambda x: f"${x:,.2f}")
view["spent"] = view["spent"].map(lambda x: f"${x:,.2f}")
view["utilization"] = (df["utilization"] * 100).round(1).astype(str) + "%"

st.dataframe(view, use_container_width=True)

# Progress bars (friendly visual)
st.subheader("Progress")
if df.empty:
    st.info("No expense categories or budgets yet.")
else:
    for _, row in df.sort_values("category").iterrows():
        pct = float(row["utilization"])
        label = f'{row["category"]}: {pct*100:.1f}%  — spent ${row["spent"]:,.2f} of ${row["budget"]:,.2f}'
        st.write(label)
        st.progress(min(1.0, pct))
