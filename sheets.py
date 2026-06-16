import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_TABS = ["organizations", "users", "contributions", "loans", "repayments"]

HEADERS = {
    "organizations": ["org_id", "name", "org_code", "admin_email", "created_at"],
    "users": ["user_id", "org_id", "email", "password_hash", "role", "name", "created_at"],
    "contributions": ["id", "org_id", "member_id", "member_name", "amount", "date", "recorded_by"],
    "loans": ["id", "org_id", "member_id", "member_name", "amount", "purpose", "status", "requested_at", "reviewed_at", "reviewed_by"],
    "repayments": ["id", "loan_id", "org_id", "member_id", "amount", "date"],
}


@st.cache_resource
def get_client():
    try:
        # Try secrets first (for Streamlit Cloud)
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    except Exception:
        # Fall back to local file
        creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource
def get_spreadsheet():
    client = get_client()
    sheet_id = st.secrets.get("SHEET_ID") or os.environ.get("SHEET_ID")
    if not sheet_id:
        raise ValueError("SHEET_ID not set in secrets or environment variables.")
    return client.open_by_key(sheet_id)


def get_sheet(tab_name: str):
    ss = get_spreadsheet()
    try:
        ws = ss.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=tab_name, rows=1000, cols=20)
        ws.append_row(HEADERS[tab_name])
    return ws


def read_sheet(tab_name: str) -> pd.DataFrame:
    ws = get_sheet(tab_name)
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=HEADERS[tab_name])
    return pd.DataFrame(records)


def append_row(tab_name: str, row: dict):
    ws = get_sheet(tab_name)
    ordered = [row.get(h, "") for h in HEADERS[tab_name]]
    ws.append_row(ordered, value_input_option="USER_ENTERED")


def update_cell_by_id(tab_name: str, id_col: str, id_val: str, update: dict):
    ws = get_sheet(tab_name)
    records = ws.get_all_records()
    headers = ws.row_values(1)
    for i, record in enumerate(records):
        if str(record.get(id_col)) == str(id_val):
            row_num = i + 2  # +1 for header, +1 for 1-indexing
            for col_name, value in update.items():
                if col_name in headers:
                    col_num = headers.index(col_name) + 1
                    ws.update_cell(row_num, col_num, value)
            return True
    return False


# ── Organization helpers ──────────────────────────────────────────────────────

def org_code_exists(code: str) -> bool:
    df = read_sheet("organizations")
    if df.empty:
        return False
    return code.upper() in df["org_code"].str.upper().values


def get_org_by_code(code: str):
    df = read_sheet("organizations")
    if df.empty:
        return None
    match = df[df["org_code"].str.upper() == code.upper()]
    return match.iloc[0].to_dict() if not match.empty else None


def get_org_by_id(org_id: str):
    df = read_sheet("organizations")
    if df.empty:
        return None
    match = df[df["org_id"] == org_id]
    return match.iloc[0].to_dict() if not match.empty else None


def create_organization(name: str, admin_email: str, org_code: str) -> str:
    org_id = str(uuid.uuid4())[:8].upper()
    append_row("organizations", {
        "org_id": org_id,
        "name": name,
        "org_code": org_code,
        "admin_email": admin_email,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    return org_id


# ── User helpers ──────────────────────────────────────────────────────────────

def email_exists(email: str) -> bool:
    df = read_sheet("users")
    if df.empty:
        return False
    return email.lower() in df["email"].str.lower().values


def get_user_by_email(email: str):
    df = read_sheet("users")
    if df.empty:
        return None
    match = df[df["email"].str.lower() == email.lower()]
    return match.iloc[0].to_dict() if not match.empty else None


def create_user(org_id: str, email: str, password_hash: str, role: str, name: str) -> str:
    user_id = str(uuid.uuid4())[:8].upper()
    append_row("users", {
        "user_id": user_id,
        "org_id": org_id,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "name": name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    return user_id


def get_org_members(org_id: str) -> pd.DataFrame:
    df = read_sheet("users")
    if df.empty:
        return pd.DataFrame(columns=HEADERS["users"])
    return df[(df["org_id"] == org_id) & (df["role"] == "member")]


# ── Contribution helpers ──────────────────────────────────────────────────────

def record_contribution(org_id: str, member_id: str, member_name: str, amount: float, recorded_by: str):
    append_row("contributions", {
        "id": str(uuid.uuid4())[:8].upper(),
        "org_id": org_id,
        "member_id": member_id,
        "member_name": member_name,
        "amount": amount,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "recorded_by": recorded_by,
    })


def get_member_contributions(org_id: str, member_id: str) -> pd.DataFrame:
    df = read_sheet("contributions")
    if df.empty:
        return df
    return df[(df["org_id"] == org_id) & (df["member_id"] == member_id)]


def get_org_contributions(org_id: str) -> pd.DataFrame:
    df = read_sheet("contributions")
    if df.empty:
        return df
    return df[df["org_id"] == org_id]


def get_member_total_savings(org_id: str, member_id: str) -> float:
    df = get_member_contributions(org_id, member_id)
    if df.empty:
        return 0.0
    return pd.to_numeric(df["amount"], errors="coerce").sum()


# ── Loan helpers ──────────────────────────────────────────────────────────────

def request_loan(org_id: str, member_id: str, member_name: str, amount: float, purpose: str):
    append_row("loans", {
        "id": str(uuid.uuid4())[:8].upper(),
        "org_id": org_id,
        "member_id": member_id,
        "member_name": member_name,
        "amount": amount,
        "purpose": purpose,
        "status": "pending",
        "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reviewed_at": "",
        "reviewed_by": "",
    })


def get_org_loans(org_id: str) -> pd.DataFrame:
    df = read_sheet("loans")
    if df.empty:
        return df
    return df[df["org_id"] == org_id]


def get_member_loans(org_id: str, member_id: str) -> pd.DataFrame:
    df = read_sheet("loans")
    if df.empty:
        return df
    return df[(df["org_id"] == org_id) & (df["member_id"] == member_id)]


def review_loan(loan_id: str, status: str, reviewed_by: str):
    update_cell_by_id("loans", "id", loan_id, {
        "status": status,
        "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reviewed_by": reviewed_by,
    })


def record_repayment(loan_id: str, org_id: str, member_id: str, amount: float):
    append_row("repayments", {
        "id": str(uuid.uuid4())[:8].upper(),
        "loan_id": loan_id,
        "org_id": org_id,
        "member_id": member_id,
        "amount": amount,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })


def get_loan_repayments(loan_id: str) -> pd.DataFrame:
    df = read_sheet("repayments")
    if df.empty:
        return df
    return df[df["loan_id"] == loan_id]


def get_loan_balance(loan_id: str, loan_amount: float) -> float:
    df = get_loan_repayments(loan_id)
    if df.empty:
        return float(loan_amount)
    paid = pd.to_numeric(df["amount"], errors="coerce").sum()
    return max(0.0, float(loan_amount) - paid)
