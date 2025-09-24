import streamlit as st
from core.utils import export_all_tables, import_transactions_csv
from core import storage as S

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings")

st.subheader("Backup / Export")
csvs = export_all_tables()
for name, csv_bytes in csvs.items():
    st.download_button(f"Download {name}.csv", data=csv_bytes, file_name=f"{name}.csv", mime="text/csv")

st.divider()
st.subheader("Import Transactions (CSV)")
st.caption("Columns required: date, account, category, type (income|expense|savings), amount, note (optional)")
upload = st.file_uploader("Upload CSV", type=["csv"])
if upload:
    try:
        count = import_transactions_csv(upload)
        st.success(f"Imported {count} transactions.")
    except Exception as e:
        st.error(f"Import failed: {e}")

st.divider()
st.subheader("Danger Zone")
if st.button("Delete ALL data (irreversible)"):
    # wipe CSVs
    for loader, saver in [(S.load_transactions, S.save_transactions),
                          (S.load_budgets, S.save_budgets),
                          (S.load_accounts, S.save_accounts),
                          (S.load_categories, S.save_categories)]:
        df = loader()
        df = df.iloc[0:0]  # empty but keep columns
        saver(df)
    st.success("All data deleted. Reload the app to re-seed defaults.")
