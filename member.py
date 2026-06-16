import streamlit as st
import pandas as pd
from auth import current_user, require_role
from sheets import (
    get_member_contributions, get_member_total_savings,
    get_member_loans, request_loan, get_loan_balance,
    get_org_by_id
)


def format_naira(amount) -> str:
    try:
        return f"₦{float(amount):,.2f}"
    except Exception:
        return f"₦{amount}"


def show_member_dashboard():
    require_role("member")
    user = current_user()
    org_id = user["org_id"]
    org = get_org_by_id(org_id)
    org_name = org["name"] if org else "Your Cooperative"

    st.title(f"👤 {user['name']}")
    st.caption(f"{org_name}")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["💰 Savings", "🏦 Loans", "📋 History"])

    with tab1:
        _show_savings(org_id, user)

    with tab2:
        _show_loans(org_id, user)

    with tab3:
        _show_history(org_id, user)


def _show_savings(org_id: str, user: dict):
    total = get_member_total_savings(org_id, user["user_id"])
    contributions_df = get_member_contributions(org_id, user["user_id"])

    st.metric("Total Savings", format_naira(total))

    if contributions_df.empty:
        st.info("No contributions recorded yet. Contact your cooperative admin.")
        return

    st.subheader("Contribution History")
    df = contributions_df[["date", "amount"]].rename(columns={"date": "Date", "amount": "Amount (₦)"})
    df = df.sort_values("Date", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Simple monthly chart
    if not contributions_df.empty:
        contributions_df["date"] = pd.to_datetime(contributions_df["date"], errors="coerce")
        contributions_df["amount"] = pd.to_numeric(contributions_df["amount"], errors="coerce")
        monthly = contributions_df.groupby(contributions_df["date"].dt.to_period("M"))["amount"].sum().reset_index()
        monthly["date"] = monthly["date"].astype(str)
        if len(monthly) > 1:
            st.subheader("Monthly Contributions")
            st.bar_chart(monthly.set_index("date")["amount"])


def _show_loans(org_id: str, user: dict):
    loans_df = get_member_loans(org_id, user["user_id"])

    # ── Active loans summary ──
    if not loans_df.empty:
        approved = loans_df[loans_df["status"] == "approved"]
        if not approved.empty:
            st.subheader("Active Loans")
            for _, loan in approved.iterrows():
                balance = get_loan_balance(loan["id"], loan["amount"])
                paid = float(loan["amount"]) - balance
                progress = paid / float(loan["amount"]) if float(loan["amount"]) > 0 else 0
                with st.expander(f"{format_naira(loan['amount'])} — {loan['purpose']}"):
                    st.write(f"**Loan Amount:** {format_naira(loan['amount'])}")
                    st.write(f"**Amount Paid:** {format_naira(paid)}")
                    st.write(f"**Outstanding Balance:** {format_naira(balance)}")
                    st.progress(min(progress, 1.0), text=f"{progress*100:.0f}% repaid")

    st.divider()

    # ── New loan request ──
    st.subheader("Request a Loan")
    pending_count = len(loans_df[loans_df["status"] == "pending"]) if not loans_df.empty else 0
    if pending_count > 0:
        st.warning("You already have a pending loan request. Wait for admin review before requesting another.")
    else:
        total_savings = get_member_total_savings(org_id, user["user_id"])
        st.caption(f"Your total savings: {format_naira(total_savings)}")

        with st.form("loan_request_form"):
            amount = st.number_input("Loan Amount (₦)", min_value=1000.0, step=500.0)
            purpose = st.text_area("Purpose / Reason", placeholder="e.g. School fees, Business stock, Medical emergency")
            submitted = st.form_submit_button("Submit Loan Request", use_container_width=True)

        if submitted:
            if not purpose.strip():
                st.error("Please describe the purpose of the loan.")
            else:
                request_loan(org_id, user["user_id"], user["name"], amount, purpose.strip())
                st.success("Loan request submitted. Your admin will review it shortly.")
                st.rerun()


def _show_history(org_id: str, user: dict):
    st.subheader("All Loan History")
    loans_df = get_member_loans(org_id, user["user_id"])

    if loans_df.empty:
        st.info("No loan history yet.")
        return

    display = []
    for _, loan in loans_df.iterrows():
        balance = get_loan_balance(loan["id"], loan["amount"])
        display.append({
            "Date": str(loan["requested_at"])[:10],
            "Amount (₦)": f"{float(loan['amount']):,.2f}",
            "Purpose": loan["purpose"],
            "Status": loan["status"].capitalize(),
            "Balance (₦)": f"{balance:,.2f}",
        })

    st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)
