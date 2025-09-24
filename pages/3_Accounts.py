import streamlit as st
import pandas as pd
import plotly.express as px
from core import storage as S

st.set_page_config(page_title="Accounts", page_icon="🏦", layout="wide")
st.title("🏦 Accounts")

acc = S.load_accounts()
tx = S.load_transactions()

# metrics
if not acc.empty:
    income = tx[tx["type"]=="income"].groupby("account_id")["amount"].sum() if not tx.empty else pd.Series(dtype=float)
    expense = tx[tx["type"]=="expense"].groupby("account_id")["amount"].sum() if not tx.empty else pd.Series(dtype=float)

    acc["income_in"] = acc["id"].map(income).fillna(0.0)
    acc["expense_out"] = acc["id"].map(expense).fillna(0.0)
    acc["current_balance"] = acc["starting_balance"] + acc["income_in"] - acc["expense_out"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Accounts", f"{len(acc)}")
    c2.metric("Starting Balances", f"${acc['starting_balance'].sum():,.2f}")
    c3.metric("Current Total", f"${acc['current_balance'].sum():,.2f}")

    st.subheader("Balances by Account")
    fig = px.bar(acc.sort_values("current_balance", ascending=False), x="name", y="current_balance")
    fig.update_layout(xaxis_title="", yaxis_title="Current Balance")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Accounts Table")
    st.dataframe(acc[["id","name","type","starting_balance","income_in","expense_out","current_balance"]],
                 use_container_width=True)
else:
    st.info("No accounts yet. Add one below.")

st.markdown("---")
st.subheader("Add Account")
col1, col2, col3 = st.columns([2,1,1])
with col1: name = st.text_input("Account name")
with col2: acc_type = st.selectbox("Type", ["bank","wallet","card"])
with col3: starting_balance = st.number_input("Starting balance", min_value=0.0, step=1.0, value=0.0)
if st.button("Add"):
    if not name.strip(): st.error("Name is required.")
    else:
        S.add_account(name.strip(), acc_type, starting_balance)
        st.success("Account added. Refresh to see it.")

st.subheader("Rename / Update Balance")
colR1, colR2, colR3 = st.columns([2,2,1])
with colR1: old = st.selectbox("Existing account", acc["name"].tolist() if not acc.empty else [])
with colR2: new = st.text_input("New name (optional)")
with colR3: new_bal = st.number_input("New starting balance (optional)", min_value=0.0, step=1.0, value=0.0)
apply_bal = st.checkbox("Apply new starting balance")
if st.button("Update"):
    df = S.load_accounts()
    row = df[df["name"] == old]
    if row.empty:
        st.error("Account not found.")
    else:
        idx = row.index[0]
        if new.strip(): df.loc[idx, "name"] = new.strip()
        if apply_bal: df.loc[idx, "starting_balance"] = float(new_bal)
        S.save_accounts(df)
        st.success("Account updated. Refresh to see it.")
