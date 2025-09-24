# pages/1_Transactions.py
import streamlit as st
import pandas as pd
from datetime import date
from core import storage as S
from core.logic import get_month_bounds

st.set_page_config(page_title="Transactions", page_icon="🧾", layout="wide")
st.title("🧾 Transactions")

# ---------- Data ----------
accounts = S.load_accounts()
categories = S.load_categories()

# ---------- Sidebar filters ----------
with st.sidebar:
    st.header("Filters")
    today = date.today()
    default_start = today.replace(day=1)
    start_end = st.date_input("Date range", (default_start, today))
    search = st.text_input("Search (note/category/account)")
    type_filter = st.multiselect("Type", ["income", "expense", "savings"],
                                 default=["income", "expense", "savings"])

# ---------- Quick Add ----------
st.subheader("Quick Add")
col1, col2, col3, col4 = st.columns([1,1,2,2])
with col1:
    q_date = st.date_input("Date", value=date.today(), key="qa_date")
with col2:
    q_type = st.selectbox("Type", ["expense", "income", "savings"], key="qa_type")
with col3:
    acc_name = st.selectbox("Account", accounts["name"].tolist() if not accounts.empty else [], key="qa_acc")
with col4:
    # show relevant categories by type
    cat_options = categories[categories["kind"] == q_type]["name"].tolist() if not categories.empty else []
    q_cat = st.selectbox("Category", cat_options, key="qa_cat")

col5, col6 = st.columns([1,3])
with col5:
    q_amount = st.number_input("Amount", min_value=0.0, step=1.0, value=0.0, key="qa_amt")
with col6:
    q_note = st.text_input("Note (optional)", key="qa_note")

if st.button("Add Transaction"):
    if accounts.empty or categories.empty:
        st.error("Please create at least one account and one category first.")
    elif q_amount <= 0:
        st.error("Amount must be greater than 0.")
    elif not acc_name or not q_cat:
        st.error("Please choose an account and category.")
    else:
        account_id = int(accounts.loc[accounts["name"] == acc_name, "id"].iloc[0])
        cat_id = int(categories.loc[categories["name"] == q_cat, "id"].iloc[0])
        S.add_transaction(account_id, cat_id, q_amount, q_type, q_date, q_note)
        st.success("Transaction added.")

st.markdown("---")

# ---------- Table / Edit ----------
st.subheader("Browse, Filter & Edit")

tx = S.load_transactions()
acc = S.load_accounts()[["id","name"]].rename(columns={"name":"account"})
cat = categories[["id","name","kind"]].rename(columns={"name":"category"})

if not tx.empty:
    tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
    # filter by date
    if isinstance(start_end, tuple) and len(start_end) == 2:
        s, e = pd.to_datetime(start_end[0]), pd.to_datetime(start_end[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        tx = tx[(tx["date"] >= s) & (tx["date"] <= e)]
    # type filter
    if type_filter:
        tx = tx[tx["type"].isin(type_filter)]
else:
    tx = pd.DataFrame(columns=["id","date","account_id","category_id","type","amount","note"])
    st.info("No transactions yet. Add one above.")

# join names
df = tx.merge(acc, left_on="account_id", right_on="id", how="left", suffixes=("","_acc")).drop(columns=["id_acc"], errors="ignore")
df = df.merge(cat[["id","category"]], left_on="category_id", right_on="id", how="left", suffixes=("","_cat")).drop(columns=["id_cat"], errors="ignore")
df = df.rename(columns={"id_x":"id"}).drop(columns=[c for c in ["id_y"] if c in df.columns])

# ensure required columns exist
keep = ["id","date","account","category","type","amount","note"]
for c in keep:
    if c not in df.columns:
        df[c] = None

# ---- DTYPE NORMALIZATION (fixes your error) ----
df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["type"] = df["type"].astype(str).fillna("")
df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
df["note"] = df["note"].astype(str).fillna("").replace({"nan": ""})
df["account"] = df["account"].astype(str).fillna("")
df["category"] = df["category"].astype(str).fillna("")
# -----------------------------------------------

df = df[keep].sort_values(["date","id"], ascending=[False, False])

# totals row
tot_income = df.loc[df["type"]=="income","amount"].sum() if not df.empty else 0.0
tot_exp = df.loc[df["type"]=="expense","amount"].sum() if not df.empty else 0.0
tot_net = tot_income - tot_exp
t1, t2, t3 = st.columns(3)
t1.metric("Filtered Income", f"${tot_income:,.2f}")
t2.metric("Filtered Expenses", f"${tot_exp:,.2f}")
t3.metric("Net", f"${tot_net:,.2f}")

edited = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True),
        "date": st.column_config.DateColumn("Date"),
        "type": st.column_config.SelectboxColumn("Type", options=["income","expense","savings"]),
        "amount": st.column_config.NumberColumn("Amount", step=1.0, format="%.2f"),
        "note": st.column_config.TextColumn("Note"),
    },
    key="txn_editor_table",
)

# Detect deletions/updates
orig_ids = set(pd.to_numeric(df["id"], errors="coerce").dropna().astype(int))
new_ids = set(pd.to_numeric(edited["id"], errors="coerce").dropna().astype(int))
deleted = orig_ids - new_ids
updated = edited[edited["id"].isin(orig_ids & new_ids)]

cA, cB = st.columns([1,1])
with cA:
    if st.button("💾 Save Changes"):
        master = S.load_transactions()
        # delete
        if not master.empty and deleted:
            master = master[~master["id"].isin(list(deleted))]
        # update mutable fields (date, type, amount, note)
        for _, r in updated.iterrows():
            mid = int(r["id"])
            mask = master["id"] == mid
            if mask.any():
                master.loc[mask, "date"] = pd.to_datetime(r["date"])
                master.loc[mask, "type"] = str(r["type"])
                master.loc[mask, "amount"] = float(r["amount"])
                master.loc[mask, "note"] = ("" if pd.isna(r.get("note")) else str(r.get("note")))
        S.save_transactions(master)
        st.success("Changes saved.")
with cB:
    @st.cache_data
    def to_csv(d: pd.DataFrame) -> bytes:
        return d.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export filtered CSV", data=to_csv(df),
                       file_name="transactions_filtered.csv", mime="text/csv")
