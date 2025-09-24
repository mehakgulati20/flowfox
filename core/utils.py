import io
import pandas as pd
from . import storage as S

DEFAULT_CATEGORIES = [
    ("Groceries", "expense"), ("Utilities", "expense"), ("Rent", "expense"),
    ("Restaurants", "expense"), ("Shopping", "expense"), ("Other Activities", "expense"),
    ("Salary", "income"), ("Emergency Fund", "savings")
]
DEFAULT_ACCOUNT = ("Chase Checking", "bank", 2000.0)

def ensure_seed_data():
    if S.load_categories().empty:
        for n,k in DEFAULT_CATEGORIES:
            S.add_category(n, k, is_default=1)
    if S.load_accounts().empty:
        n,t,b = DEFAULT_ACCOUNT
        S.add_account(n, t, b)

def export_all_tables():
    csvs = {}
    for name, loader in {
        "accounts": S.load_accounts, "categories": S.load_categories,
        "transactions": S.load_transactions, "budgets": S.load_budgets
    }.items():
        df = loader()
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        csvs[name] = buf.getvalue().encode("utf-8")
    return csvs

def import_transactions_csv(file) -> int:
    df = pd.read_csv(file)
    cols = {c.lower(): c for c in df.columns}
    req = {"date","account","category","type","amount"}
    if not req.issubset(set(cols.keys())):
        raise ValueError(f"CSV must include: {', '.join(sorted(req))}")
    accs = S.load_accounts()
    cats = S.load_categories()
    count = 0
    for _, r in df.iterrows():
        acc = str(r[cols["account"]]).strip()
        cat = str(r[cols["category"]]).strip()
        typ = str(r[cols["type"]]).strip()
        dt  = pd.to_datetime(r[cols["date"]]).date()
        amt = float(r[cols["amount"]])
        note = str(r.get(cols.get("note","note"), "") or "")

        # ensure account
        acc_row = accs[accs["name"] == acc]
        if acc_row.empty:
            S.add_account(acc, "bank", 0.0)
            accs = S.load_accounts()
            acc_row = accs[accs["name"] == acc]
        account_id = int(acc_row.iloc[0]["id"])

        # ensure category
        cat_row = cats[cats["name"] == cat]
        if cat_row.empty:
            S.add_category(cat, "expense", is_default=0)
            cats = S.load_categories()
            cat_row = cats[cats["name"] == cat]
        category_id = int(cat_row.iloc[0]["id"])

        S.add_transaction(account_id, category_id, amt, typ, dt, note)
        count += 1
    return count
