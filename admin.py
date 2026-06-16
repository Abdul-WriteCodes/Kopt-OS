import streamlit as st
import pandas as pd
from auth import current_user, require_role
from sheets import (
    get_org_members, get_org_contributions, get_org_loans,
    record_contribution, review_loan, record_repayment,
    get_loan_balance, get_org_by_id, get_loan_repayments
)


def format_naira(amount) -> str:
    try:
        return f"₦{float(amount):,.2f}"
    except Exception:
        return f"₦{amount}"


def show_admin_dashboard():
    require_role("admin")
    user = current_user()
    org_id = user["org_id"]
    org = get_org_by_id(org_id)
    org_name = org["name"] if org else "Your Cooperative"
    org_code = org["org_code"] if org else ""

    st.title(f"🏛️ {org_name}")
    st.caption(f"Organization Code: **{org_code}** · Admin: {user['name']}")
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "👥 Members", "💰 Contributions", "🏦 Loans"])

    with tab1:
        _show_overview(org_id)

    with tab2:
        _show_members(org_id)

    with tab3:
        _show_contributions(org_id, user)

    with tab4:
        _show_loans(org_id, user)


def _show_overview(org_id: str):
    members_df = get_org_members(org_id)
    contributions_df = get_org_contributions(org_id)
    loans_df = get_org_loans(org_id)

    total_members = len(members_df)
    total_savings = pd.to_numeric(contributions_df["amount"], errors="coerce").sum() if not contributions_df.empty else 0
    pending_loans = len(loans_df[loans_df["status"] == "pending"]) if not loans_df.empty else 0
    approved_loans_amount = 0
    if not loans_df.empty:
        approved = loans_df[loans_df["status"] == "approved"]
        approved_loans_amount = pd.to_numeric(approved["amount"], errors="coerce").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Members", total_members)
    c2.metric("Total Savings", format_naira(total_savings))
    c3.metric("Pending Loans", pending_loans)
    c4.metric("Loans Disbursed", format_naira(approved_loans_amount))

    if not contributions_df.empty:
        st.subheader("Recent Contributions")
        recent = contributions_df.sort_values("date", ascending=False).head(5)
        st.dataframe(
            recent[["date", "member_name", "amount"]].rename(columns={
                "date": "Date", "member_name": "Member", "amount": "Amount (₦)"
            }),
            use_container_width=True, hide_index=True
        )


def _show_members(org_id: str):
    st.subheader("Members")
    members_df = get_org_members(org_id)

    if members_df.empty:
        st.info("No members yet. Share the organization code with your members so they can sign up.")
        return

    contributions_df = get_org_contributions(org_id)

    display_rows = []
    for _, m in members_df.iterrows():
        member_contribs = contributions_df[contributions_df["member_id"] == m["user_id"]] if not contributions_df.empty else pd.DataFrame()
        total = pd.to_numeric(member_contribs["amount"], errors="coerce").sum() if not member_contribs.empty else 0
        display_rows.append({
            "Name": m["name"],
            "Email": m["email"],
            "Total Savings (₦)": f"{float(total):,.2f}",
            "Joined": m.get("created_at", "")[:10],
        })

    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)


def _show_contributions(org_id: str, user: dict):
    st.subheader("Record Contribution")

    members_df = get_org_members(org_id)
    if members_df.empty:
        st.info("No members yet to record contributions for.")
    else:
        member_options = {f"{r['name']} ({r['email']})": r["user_id"] for _, r in members_df.iterrows()}
        member_name_map = {r["user_id"]: r["name"] for _, r in members_df.iterrows()}

        with st.form("contribution_form"):
            selected = st.selectbox("Select Member", list(member_options.keys()))
            amount = st.number_input("Amount (₦)", min_value=1.0, step=100.0)
            submitted = st.form_submit_button("Record Contribution", use_container_width=True)

        if submitted:
            member_id = member_options[selected]
            member_name = member_name_map[member_id]
            record_contribution(org_id, member_id, member_name, amount, user["name"])
            st.success(f"Contribution of {format_naira(amount)} recorded for {member_name}.")
            st.rerun()

    st.divider()
    st.subheader("All Contributions")
    contributions_df = get_org_contributions(org_id)
    if contributions_df.empty:
        st.info("No contributions recorded yet.")
    else:
        df = contributions_df[["date", "member_name", "amount", "recorded_by"]].rename(columns={
            "date": "Date", "member_name": "Member", "amount": "Amount (₦)", "recorded_by": "Recorded By"
        })
        st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)


def _show_loans(org_id: str, user: dict):
    loans_df = get_org_loans(org_id)

    # ── Pending approvals ──
    st.subheader("Pending Loan Requests")
    if loans_df.empty or loans_df[loans_df["status"] == "pending"].empty:
        st.info("No pending loan requests.")
    else:
        pending = loans_df[loans_df["status"] == "pending"]
        for _, loan in pending.iterrows():
            with st.expander(f"{loan['member_name']} — {format_naira(loan['amount'])} · {loan['requested_at'][:10]}"):
                st.write(f"**Purpose:** {loan['purpose']}")
                st.write(f"**Amount:** {format_naira(loan['amount'])}")
                c1, c2 = st.columns(2)
                if c1.button("✅ Approve", key=f"approve_{loan['id']}"):
                    review_loan(loan["id"], "approved", user["name"])
                    st.success("Loan approved.")
                    st.rerun()
                if c2.button("❌ Reject", key=f"reject_{loan['id']}"):
                    review_loan(loan["id"], "rejected", user["name"])
                    st.warning("Loan rejected.")
                    st.rerun()

    st.divider()

    # ── Repayment recording ──
    st.subheader("Record Repayment")
    if not loans_df.empty:
        approved_loans = loans_df[loans_df["status"] == "approved"]
        if not approved_loans.empty:
            loan_options = {
                f"{r['member_name']} — {format_naira(r['amount'])} (ID: {r['id']})": r
                for _, r in approved_loans.iterrows()
            }
            with st.form("repayment_form"):
                selected_label = st.selectbox("Select Loan", list(loan_options.keys()))
                repay_amount = st.number_input("Repayment Amount (₦)", min_value=1.0, step=100.0)
                submitted = st.form_submit_button("Record Repayment", use_container_width=True)

            if submitted:
                loan = loan_options[selected_label]
                balance = get_loan_balance(loan["id"], loan["amount"])
                if repay_amount > balance:
                    st.error(f"Repayment exceeds outstanding balance of {format_naira(balance)}.")
                else:
                    record_repayment(loan["id"], org_id, loan["member_id"], repay_amount)
                    st.success(f"Repayment of {format_naira(repay_amount)} recorded.")
                    st.rerun()
        else:
            st.info("No approved loans to record repayments against.")
    else:
        st.info("No loans yet.")

    st.divider()

    # ── All loans ──
    st.subheader("All Loans")
    if loans_df.empty:
        st.info("No loans yet.")
    else:
        display = []
        for _, loan in loans_df.iterrows():
            balance = get_loan_balance(loan["id"], loan["amount"])
            display.append({
                "Member": loan["member_name"],
                "Amount (₦)": f"{float(loan['amount']):,.2f}",
                "Purpose": loan["purpose"],
                "Status": loan["status"].capitalize(),
                "Balance (₦)": f"{balance:,.2f}",
                "Requested": str(loan["requested_at"])[:10],
            })
        st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)
