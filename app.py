import streamlit as st
from auth import (
    is_logged_in, current_user, logout,
    show_login_form, show_register_org_form, show_register_member_form
)
from admin import show_admin_dashboard
from member import show_member_dashboard

st.set_page_config(
    page_title="Cooperative OS",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal global styles ─────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    .stMetric { background: #fff; padding: 1rem; border-radius: 8px; border: 1px solid #e9ecef; }
</style>
""", unsafe_allow_html=True)


def show_sidebar():
    with st.sidebar:
        st.image("https://via.placeholder.com/200x60?text=Cooperative+OS", use_container_width=True)
        st.divider()

        if is_logged_in():
            user = current_user()
            st.write(f"**{user.get('name', 'User')}**")
            role = str(user.get("role", "")).strip()
            st.caption(f"Role: {role.capitalize() if role else 'Unknown'}")
            st.divider()
            if st.button("🚪 Logout", use_container_width=True):
                logout()
                st.rerun()
        else:
            st.info("Login or register to get started.")


def show_landing():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# 🏛️ Cooperative OS")
        st.markdown("### The digital operating system for cooperative societies")
        st.markdown("Manage members, savings, loans, and financial records — all in one place.")
        st.divider()

        tab1, tab2, tab3 = st.tabs(["🔐 Login", "🏛️ Register Cooperative", "👤 Join as Member"])

        with tab1:
            show_login_form()

        with tab2:
            show_register_org_form()

        with tab3:
            show_register_member_form()


def main():
    show_sidebar()

    if not is_logged_in():
        show_landing()
        return

    user = current_user()
    role = str(user.get("role", "")).strip().lower()

    if role == "admin":
        show_admin_dashboard()
    elif role == "member":
        show_member_dashboard()
    else:
        st.error(f"Could not determine your role (got: '{role}'). This usually means the users sheet has a blank role column.")
        st.info("Check your Google Sheet → users tab → confirm the 'role' column has 'admin' or 'member' for this user.")
        if st.button("Logout"):
            logout()
            st.rerun()


if __name__ == "__main__":
    main()
