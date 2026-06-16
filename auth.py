import streamlit as st
import hashlib
import secrets
import string
from sheets import (
    get_user_by_email, create_user, email_exists,
    get_org_by_code, create_organization, org_code_exists
)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def generate_org_code(name: str) -> str:
    prefix = "".join(c for c in name.upper() if c.isalpha())[:4]
    suffix = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"{prefix}{suffix}"


def login(email: str, password: str) -> bool:
    user = get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user["password_hash"]):
        return False
    st.session_state["user"] = user
    st.session_state["logged_in"] = True
    return True


def logout():
    for key in ["user", "logged_in"]:
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def current_user() -> dict:
    return st.session_state.get("user", {})


def require_login():
    if not is_logged_in():
        st.warning("Please log in to continue.")
        st.stop()


def require_role(role: str):
    require_login()
    user = current_user()
    if user.get("role") != role:
        st.error(f"Access denied. This page is for {role}s only.")
        st.stop()


# ── UI Forms ──────────────────────────────────────────────────────────────────

def show_login_form():
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)
    if submitted:
        if not email or not password:
            st.error("Please fill in all fields.")
            return
        if login(email.strip(), password):
            st.success("Welcome back!")
            st.rerun()
        else:
            st.error("Invalid email or password.")


def show_register_org_form():
    st.subheader("Register Your Cooperative")
    with st.form("register_org_form"):
        org_name = st.text_input("Cooperative Name", placeholder="e.g. Ilorin Teachers Cooperative")
        admin_name = st.text_input("Your Full Name")
        email = st.text_input("Admin Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Register Cooperative", use_container_width=True)

    if submitted:
        if not all([org_name, admin_name, email, password, confirm]):
            st.error("Please fill in all fields.")
            return
        if password != confirm:
            st.error("Passwords do not match.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return
        if email_exists(email.strip()):
            st.error("An account with this email already exists.")
            return

        org_code = generate_org_code(org_name)
        while org_code_exists(org_code):
            org_code = generate_org_code(org_name)

        org_id = create_organization(org_name.strip(), email.strip(), org_code)
        create_user(org_id, email.strip(), hash_password(password), "admin", admin_name.strip())

        st.success(f"Cooperative registered successfully!")
        st.info(f"**Your Organization Code: `{org_code}`** — Share this with your members so they can join.")
        st.balloons()


def show_register_member_form():
    st.subheader("Join Your Cooperative")
    with st.form("register_member_form"):
        org_code = st.text_input("Organization Code", placeholder="e.g. ILORI1234")
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Join Cooperative", use_container_width=True)

    if submitted:
        if not all([org_code, full_name, email, password, confirm]):
            st.error("Please fill in all fields.")
            return
        if password != confirm:
            st.error("Passwords do not match.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return

        org = get_org_by_code(org_code.strip())
        if not org:
            st.error("Organization code not found. Ask your cooperative admin for the correct code.")
            return
        if email_exists(email.strip()):
            st.error("An account with this email already exists.")
            return

        create_user(org["org_id"], email.strip(), hash_password(password), "member", full_name.strip())
        st.success(f"You've joined **{org['name']}** successfully! You can now log in.")
