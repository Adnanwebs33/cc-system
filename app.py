import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from database import backup_database, get_connection, ensure_db

st.set_page_config(page_title="HBC Project Cost Control", page_icon="🏗️", layout="wide")

ensure_db()

# Sidebar nav
st.sidebar.title("HBC – Hazim Brothers for Construction")
st.sidebar.caption("Project Cost Control System")
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Add Transaction",
        "Transactions",
        "Excel Import",
        "Excel Export",
        "Budget vs Actual",
        "Suppliers",
        "GL Accounts",
        "Reports",
        "Settings",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Seef Lusail")
st.sidebar.markdown("Project Code: 26061")
st.sidebar.markdown("Description: Modification of Fit Out")


def currency_qar(value):
    if value is None or pd.isna(value):
        return "QAR 0.00"
    return f"QAR {float(value):,.2f}"


def render_dashboard():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM transactions WHERE is_deleted = 0",
        conn,
    )
    conn.close()

    if df.empty:
        st.info("No transactions yet. Add your first project cost entry.")
        return

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    total_cost = df["amount"].sum()
    this_month = df[df["transaction_date"].dt.to_period("M") == pd.Timestamp.now().to_period("M")]["amount"].sum()
    total_supplier_count = df["supplier"].dropna().nunique()
    top_category = df.groupby("expense_category")["amount"].sum().idxmax() if not df.empty else "N/A"
    top_supplier = df.groupby("supplier")["amount"].sum().idxmax() if not df.empty else "N/A"

    # Budget used placeholder
    budget = 1500000.00
    remaining = budget - total_cost
    budget_used_pct = (total_cost / budget * 100) if budget else 0

    cols = st.columns(6)
    metrics = [
        ("Total Project Cost", currency_qar(total_cost)),
        ("Cost This Month", currency_qar(this_month)),
        ("Number of Transactions", f"{len(df):,}"),
        ("Total Suppliers", f"{total_supplier_count}"),
        ("Highest Cost Category", top_category),
        ("Highest Cost Supplier", top_supplier),
        ("Budget Used %", f"{budget_used_pct:.1f}%"),
        ("Remaining Budget", currency_qar(remaining)),
    ]

    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    st.markdown("---")
    chart_col1, chart_col2 = st.columns(2)

    monthly = df.groupby(df["transaction_date"].dt.to_period("M").astype(str), as_index=False)["amount"].sum()
    if not monthly.empty:
        monthly.columns = ["Month", "Amount"]
        fig_month = px.bar(monthly, x="Month", y="Amount", title="Monthly Cost Trend")
        fig_month.update_layout(template="plotly_white")
        chart_col1.plotly_chart(fig_month, use_container_width=True)

    gl_data = df.groupby("gl_account_name", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    if not gl_data.empty:
        fig_gl = px.pie(gl_data, names="gl_account_name", values="amount", title="Cost by GL Account")
        chart_col2.plotly_chart(fig_gl, use_container_width=True)

    st.markdown("---")
    chart_col3, chart_col4 = st.columns(2)

    category_data = df.groupby("expense_category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    if not category_data.empty:
        fig_cat = px.bar(category_data, x="expense_category", y="amount", title="Cost by Expense Category")
        fig_cat.update_layout(xaxis_tickangle=-45, template="plotly_white")
        chart_col3.plotly_chart(fig_cat, use_container_width=True)

    supplier_data = df.groupby("supplier", as_index=False)["amount"].sum().sort_values("amount", ascending=False).head(10)
    if not supplier_data.empty:
        fig_sup = px.bar(supplier_data, x="supplier", y="amount", title="Top Suppliers")
        fig_sup.update_layout(xaxis_tickangle=-45, template="plotly_white")
        chart_col4.plotly_chart(fig_sup, use_container_width=True)

    st.markdown("---")
    recent = df.sort_values("transaction_date", ascending=False).head(10)
    st.subheader("Recent Transactions")
    st.dataframe(recent[["transaction_date", "supplier", "gl_account_name", "expense_category", "amount", "description"]].rename(columns={"transaction_date": "Date"}), use_container_width=True)


def render_add_transaction():
    st.subheader("Add Transaction")
    conn = get_connection()
    suppliers = pd.read_sql_query("SELECT supplier_name FROM suppliers WHERE is_active = 1 ORDER BY supplier_name", conn)
    gls = pd.read_sql_query("SELECT gl_code, gl_account_name, reporting_category FROM gl_accounts WHERE is_active = 1 ORDER BY gl_account_name", conn)
    conn.close()

    with st.form("add_transaction_form"):
        col1, col2 = st.columns(2)
        with col1:
            date_value = st.date_input("Date")
            project_name = st.text_input("Project", value="SEEF LUSAIL")
            project_code = st.text_input("Project Code", value="26061")
            supplier = st.selectbox("Supplier", ["Select supplier"] + suppliers["supplier_name"].tolist())
            invoice_number = st.text_input("Invoice Number")
            reference_number = st.text_input("Reference Number")
        with col2:
            gl_code = st.selectbox("GL Account", ["Select GL"] + gls["gl_code"].tolist())
            expense_category = st.text_input("Expense Category")
            description = st.text_input("Description")
            amount = st.number_input("Amount", min_value=0.01, step=0.01, format="%.2f")
            payment_method = st.selectbox("Payment Method", ["Petty Cash", "Bank Transfer", "Cheque", "Credit Purchase", "Cash", "Other"])
            source = st.selectbox("Source", ["Manual Entry", "Sage Import", "Excel Import", "Petty Cash", "Supplier Invoice", "Other"])
            remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("Save Transaction")
        if submitted:
            if supplier == "Select supplier" or not supplier:
                st.error("Please select a supplier.")
            elif gl_code == "Select GL" or not gl_code:
                st.error("Please select a GL account.")
            elif not description:
                st.error("Description is required.")
            else:
                selected_gl = gls[gls["gl_code"] == gl_code].iloc[0]
                if not expense_category:
                    expense_category = selected_gl["reporting_category"] or selected_gl["gl_account_name"]

                conn = get_connection()
                conn.execute(
                    "INSERT INTO transactions (transaction_date, project_code, project_name, supplier, invoice_number, reference_number, gl_code, gl_account_name, expense_category, description, debit, credit, amount, payment_method, source, remarks, created_by, created_at, edited_by, last_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, datetime('now'))",
                    (
                        date_value.isoformat(),
                        project_code,
                        project_name,
                        supplier,
                        invoice_number,
                        reference_number,
                        gl_code,
                        selected_gl["gl_account_name"],
                        expense_category,
                        description,
                        0.0,
                        0.0,
                        float(amount),
                        payment_method,
                        source,
                        remarks,
                        "Accountant",
                        "Accountant",
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Transaction successfully saved.")


def render_transactions():
    st.subheader("Transactions")
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM transactions WHERE is_deleted = 0 ORDER BY transaction_date DESC, id DESC",
        conn,
    )
    conn.close()

    if df.empty:
        st.info("No transactions available.")
        return

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    st.write(f"Filtered Transactions: {len(df)}")
    st.write(f"Filtered Total: {currency_qar(df['amount'].sum())}")
    st.dataframe(df[["transaction_date", "supplier", "gl_account_name", "expense_category", "amount", "description", "source"]], use_container_width=True)


def render_excel_import():
    st.subheader("Excel Import")
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])
    if uploaded_file is None:
        return

    try:
        df = pd.read_excel(uploaded_file)
        st.write("Preview of uploaded rows")
        st.dataframe(df.head(20), use_container_width=True)
        st.write(df.columns.tolist())

        if st.button("Confirm Import"):
            conn = get_connection()
            rows = 0
            valid_rows = 0
            for _, row in df.iterrows():
                rows += 1
                try:
                    description = str(row.get("Description", "")).strip()
                    gl_code = str(row.get("GL Code", row.get("Account", ""))).strip()
                    amount = pd.to_numeric(row.get("Amount", row.get("Debit", 0)), errors="coerce")
                    if not description or not gl_code or pd.isna(amount) or float(amount) <= 0:
                        continue
                    valid_rows += 1
                    conn.execute(
                        "INSERT INTO transactions (transaction_date, project_code, project_name, supplier, invoice_number, reference_number, gl_code, gl_account_name, expense_category, description, debit, credit, amount, payment_method, source, remarks, created_by, created_at, edited_by, last_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, datetime('now'))",
                        (
                            pd.Timestamp(row.get("Date", pd.Timestamp.now())).strftime("%Y-%m-%d"),
                            "26061",
                            "SEEF LUSAIL",
                            row.get("Supplier", ""),
                            row.get("Invoice Number", ""),
                            row.get("Reference", ""),
                            gl_code,
                            gl_code,
                            str(row.get("Expense Category", "Other")),
                            description,
                            float(amount),
                            0.0,
                            float(amount),
                            "Bank Transfer",
                            "Excel Import",
                            "Imported from Excel",
                            "Accountant",
                            "Accountant",
                        ),
                    )
                except Exception:
                    continue
            conn.commit()
            conn.close()
            st.success(f"Import complete. {valid_rows} valid rows added from {rows} detected rows.")
    except Exception as exc:
        st.error(f"Excel file could not be read: {exc}")


def render_excel_export():
    st.subheader("Excel Export")
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM transactions WHERE is_deleted = 0 ORDER BY transaction_date DESC", conn)
    conn.close()
    if df.empty:
        st.info("No data to export.")
        return
    export_file = "hbc_transaction_export.xlsx"
    df.to_excel(export_file, index=False)
    st.success(f"Export generated: {export_file}")
    with open(export_file, "rb") as file:
        st.download_button("Download Excel file", file.read(), file_name=export_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def render_budget():
    st.subheader("Budget vs Actual")
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM transactions WHERE is_deleted = 0", conn)
    conn.close()
    if df.empty:
        st.info("No budget analysis yet.")
        return
    budget_df = df.groupby("expense_category", as_index=False)["amount"].sum().rename(columns={"amount": "actual_amount"})
    budget_df["budget_amount"] = [100000.0 if x in ["Consumables", "Paint", "Steel", "Marble & Tiles"] else 50000.0 for x in budget_df["expense_category"]]
    budget_df["remaining_amount"] = budget_df["budget_amount"] - budget_df["actual_amount"]
    budget_df["variance"] = budget_df["actual_amount"] - budget_df["budget_amount"]
    budget_df["budget_used_pct"] = (budget_df["actual_amount"] / budget_df["budget_amount"] * 100).fillna(0)
    st.dataframe(budget_df, use_container_width=True)


def render_suppliers():
    st.subheader("Suppliers")
    conn = get_connection()
    suppliers = pd.read_sql_query("SELECT * FROM suppliers ORDER BY supplier_name", conn)
    conn.close()
    st.dataframe(suppliers, use_container_width=True)

    with st.form("supplier_form"):
        supplier_name = st.text_input("Supplier Name")
        contact_person = st.text_input("Contact Person")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
        supplier_category = st.text_input("Supplier Category")
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Supplier")
        if submitted and supplier_name:
            conn = get_connection()
            conn.execute(
                "INSERT OR IGNORE INTO suppliers (supplier_name, contact_person, phone, email, supplier_category, notes, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (supplier_name, contact_person, phone, email, supplier_category, notes),
            )
            conn.commit()
            conn.close()
            st.success("Supplier saved.")


def render_gl_accounts():
    st.subheader("GL Accounts")
    conn = get_connection()
    gls = pd.read_sql_query("SELECT * FROM gl_accounts ORDER BY gl_account_name", conn)
    conn.close()
    st.dataframe(gls, use_container_width=True)

    with st.form("gl_form"):
        gl_code = st.text_input("GL Code")
        gl_account_name = st.text_input("GL Account Name")
        reporting_category = st.text_input("Reporting Category")
        submitted = st.form_submit_button("Add GL Account")
        if submitted and gl_code and gl_account_name:
            conn = get_connection()
            conn.execute(
                "INSERT OR IGNORE INTO gl_accounts (gl_code, gl_account_name, reporting_category, is_active) VALUES (?, ?, ?, 1)",
                (gl_code, gl_account_name, reporting_category),
            )
            conn.commit()
            conn.close()
            st.success("GL account saved.")


def render_reports():
    st.subheader("Reports")
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM transactions WHERE is_deleted = 0", conn)
    conn.close()
    if df.empty:
        st.info("No data available for reports.")
        return
    st.dataframe(df[["transaction_date", "supplier", "gl_account_name", "amount", "description"]].sort_values("transaction_date", ascending=False), use_container_width=True)


def render_settings():
    st.subheader("Settings")
    st.write("HBC Project Cost Control System")
    if st.button("Create Database Backup"):
        path = backup_database()
        if path:
            st.success(f"Backup created: {path}")
        else:
            st.warning("No database found to back up.")


if page == "Dashboard":
    render_dashboard()
elif page == "Add Transaction":
    render_add_transaction()
elif page == "Transactions":
    render_transactions()
elif page == "Excel Import":
    render_excel_import()
elif page == "Excel Export":
    render_excel_export()
elif page == "Budget vs Actual":
    render_budget()
elif page == "Suppliers":
    render_suppliers()
elif page == "GL Accounts":
    render_gl_accounts()
elif page == "Reports":
    render_reports()
else:
    render_settings()
