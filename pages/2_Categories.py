import streamlit as st
import pandas as pd
from core import storage as S

st.set_page_config(page_title="Categories", page_icon="🗂️", layout="wide")
st.title("🗂️ Categories")

cats = S.load_categories().sort_values(["kind","name"])
st.caption("Tip: Use **expense** for outflows, **income** for inflows, and **savings** for transfers to savings.")

# Quick overview
c1, c2, c3 = st.columns(3)
for label, kind, col in [("Expense Categories", "expense", c1), ("Income Categories", "income", c2), ("Savings Categories", "savings", c3)]:
    with col:
        subset = cats[cats["kind"]==kind]
        st.markdown(f"**{label}** ({len(subset)})")
        if subset.empty: st.info("None")
        else: st.write(", ".join(subset["name"].tolist()))

st.markdown("---")

# Add
st.subheader("Add Category")
colA, colB, colC = st.columns([2,1,1])
with colA: name = st.text_input("Name")
with colB: kind = st.selectbox("Kind", ["expense","income","savings"])
with colC:
    if st.button("Add"):
        if not name.strip(): st.error("Name is required.")
        else:
            S.add_category(name.strip(), kind, is_default=0)
            st.success("Category added. Refresh to see it.")

# Rename
st.subheader("Rename Category")
colR1, colR2 = st.columns([2,2])
with colR1: old = st.selectbox("Existing", cats["name"].tolist() if not cats.empty else [])
with colR2: new = st.text_input("New name")
if st.button("Rename"):
    if not old or not new.strip():
        st.error("Pick an existing category and type a new name.")
    else:
        df = S.load_categories()
        if (df["name"] == new.strip()).any():
            st.error("A category with that name already exists.")
        else:
            idx = df[df["name"] == old].index
            if len(idx):
                df.loc[idx[0], "name"] = new.strip()
                S.save_categories(df)
                st.success("Category renamed. Refresh to see it.")

# Delete
st.subheader("Delete Category")
to_del = st.selectbox("Select to delete", cats["name"].tolist() if not cats.empty else [])
if st.button("Delete"):
    result = S.delete_category_by_name(to_del) if to_del else "not-found"
    messages = {
        "not-found": "Category not found.",
        "default": "Cannot delete a default category.",
        "in-use": "Cannot delete: category is used by existing transactions.",
        "deleted": "Category deleted."
    }
    (st.success if result=="deleted" else st.error)(messages.get(result, f"Result: {result}"))
