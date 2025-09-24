import os, io, calendar
from datetime import datetime, date
import pandas as pd

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "accounts": os.path.join(DATA_DIR, "accounts.csv"),
    "categories": os.path.join(DATA_DIR, "categories.csv"),
    "transactions": os.path.join(DATA_DIR, "transactions.csv"),
    "budgets": os.path.join(DATA_DIR, "budgets.csv"),
}

SCHEMAS = {
    "accounts": ["id", "name", "type", "starting_balance", "created_at"],
    "categories": ["id", "name", "kind", "is_default", "created_at"],
    "transactions": ["id", "account_id", "category_id", "amount", "type", "date", "note", "created_at"],
    "budgets": ["id", "category_id", "period", "amount"],
}

def _ensure_file(kind: str):
    path = FILES[kind]
    if not os.path.exists(path):
        pd.DataFrame(columns=SCHEMAS[kind]).to_csv(path, index=False)

def _read(kind: str, parse_dates=False) -> pd.DataFrame:
    _ensure_file(kind)
    if kind == "transactions" and parse_dates:
        return pd.read_csv(FILES[kind], parse_dates=["date"])
    return pd.read_csv(FILES[kind])

def _write_atomic(df: pd.DataFrame, path: str):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)

def _write(kind: str, df: pd.DataFrame):
    cols = SCHEMAS[kind]
    # add any missing columns
    for c in cols:
        if c not in df.columns:
            df[c] = "" if c not in ("starting_balance","amount","is_default","account_id","category_id","id") else 0
    df = df[cols]
    _write_atomic(df, FILES[kind])

def _next_id(df: pd.DataFrame) -> int:
    if df.empty: return 1
    return int(df["id"].max()) + 1

# Public API
def load_accounts() -> pd.DataFrame:
    df = _read("accounts")
    if "starting_balance" in df.columns:
        df["starting_balance"] = pd.to_numeric(df["starting_balance"], errors="coerce").fillna(0.0)
    return df

def load_categories() -> pd.DataFrame:
    df = _read("categories")
    if "is_default" in df.columns:
        df["is_default"] = pd.to_numeric(df["is_default"], errors="coerce").fillna(0).astype(int)
    return df

def load_transactions() -> pd.DataFrame:
    df = _read("transactions", parse_dates=True)
    numeric_cols = ["amount","account_id","category_id","id"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "type" in df.columns:
        df["type"] = df["type"].astype(str)
    return df

def load_budgets() -> pd.DataFrame:
    df = _read("budgets")
    for c in ["id","category_id"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df

def save_accounts(df: pd.DataFrame): _write("accounts", df)
def save_categories(df: pd.DataFrame): _write("categories", df)
def save_transactions(df: pd.DataFrame): _write("transactions", df)
def save_budgets(df: pd.DataFrame): _write("budgets", df)

def add_account(name: str, type_: str, starting_balance: float = 0.0):
    acc = load_accounts()
    if (acc["name"] == name).any(): return  # dedupe by name
    new_id = _next_id(acc)
    now = datetime.utcnow().isoformat()
    row = {"id": new_id, "name": name, "type": type_, "starting_balance": float(starting_balance), "created_at": now}
    acc = pd.concat([acc, pd.DataFrame([row])], ignore_index=True)
    save_accounts(acc)

def add_category(name: str, kind: str, is_default: int = 0):
    cats = load_categories()
    if (cats["name"] == name).any(): return
    new_id = _next_id(cats)
    now = datetime.utcnow().isoformat()
    row = {"id": new_id, "name": name, "kind": kind, "is_default": int(is_default), "created_at": now}
    cats = pd.concat([cats, pd.DataFrame([row])], ignore_index=True)
    save_categories(cats)

def add_transaction(account_id: int, category_id: int, amount: float, type_: str, date_: date, note: str = ""):
    tx = load_transactions()
    new_id = _next_id(tx)
    now = datetime.utcnow().isoformat()
    row = {
        "id": new_id, "account_id": int(account_id), "category_id": int(category_id),
        "amount": float(amount), "type": type_, "date": pd.to_datetime(date_), "note": note, "created_at": now
    }
    tx = pd.concat([tx, pd.DataFrame([row])], ignore_index=True)
    save_transactions(tx)

def upsert_budget(category_id: int, period: str, amount: float):
    b = load_budgets()
    # ensure uniqueness on (category_id, period)
    mask = (b["category_id"] == int(category_id)) & (b["period"] == period)
    if mask.any():
        b.loc[mask, "amount"] = float(amount)
    else:
        new_id = _next_id(b)
        row = {"id": new_id, "category_id": int(category_id), "period": period, "amount": float(amount)}
        b = pd.concat([b, pd.DataFrame([row])], ignore_index=True)
    save_budgets(b)

def delete_category_by_name(name: str) -> str:
    cats = load_categories()
    match = cats[cats["name"] == name]
    if match.empty: return "not-found"
    if int(match.iloc[0]["is_default"]) == 1: return "default"
    # guard if used in transactions
    tx = load_transactions()
    if (tx["category_id"] == int(match.iloc[0]["id"])).any(): return "in-use"
    cats = cats[cats["name"] != name]
    save_categories(cats)
    return "deleted"
