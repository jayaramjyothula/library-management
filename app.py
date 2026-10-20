"""
app.py - Library Management System
Unified shared interface (zero-login) for everyone.
- When run directly (`python app.py`): Starts the high-performance modern web server on port 8501.
- When run via Streamlit (`streamlit run app.py`): Renders the zero-login, shared interface.
"""

from __future__ import annotations

import io
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

import database as db

# -----------------------------------------------------------------------------
# If invoked directly via `python app.py`, launch the modern web server!
# -----------------------------------------------------------------------------
if __name__ == "__main__" and not (hasattr(st, "runtime") and st.runtime.exists()):
    import uvicorn
    print("\n" + "=" * 60)
    print(" [*] Launching Library Management System on http://localhost:8501")
    print("=" * 60 + "\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8501, reload=False)
    sys.exit(0)

# -----------------------------------------------------------------------------
# Streamlit Mode: Zero-Login Shared Interface
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Library Management",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()
db.seed_sample_data()

# Custom Modern CSS (Navy + Electric Blue Palette, High-Contrast Light Theme)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    /* Global Light Theme Root Variables */
    :root, .stApp {
        --primary-color: #0284c7 !important;
        --background-color: #f8fafc !important;
        --secondary-background-color: #ffffff !important;
        --text-color: #0f172a !important;
    }

    /* Base Page & App Canvas */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    #MainMenu, header, footer {
        visibility: hidden;
    }

    .main .block-container,
    [data-testid="block-container"] {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1200px !important;
    }

    /* Universal Typography & High Contrast Text */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6 {
        color: #0b132b !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
    }

    .stApp p, .stApp span, .stApp div, .stApp li,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] li {
        color: #0f172a !important;
    }

    /* Subtext and Captions */
    [data-testid="stCaptionContainer"],
    .stCaption,
    small,
    [data-testid="stMarkdownContainer"] small {
        color: #475569 !important;
        font-weight: 500 !important;
    }

    /* Top Brand Bar */
    .top-brand-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 24px;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
        margin-bottom: 24px;
    }

    .brand-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .brand-icon {
        width: 38px;
        height: 38px;
        background: linear-gradient(135deg, #0b132b 0%, #1e3a8a 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #38bdf8 !important;
        font-size: 1.2rem;
    }

    .brand-name {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 800;
        font-size: 1.2rem;
        color: #0b132b !important;
        letter-spacing: -0.02em;
    }

    .brand-tag {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #0284c7 !important;
    }

    /* Hero Section */
    .hero-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 16px;
        padding: 36px 32px;
        text-align: center;
        margin-bottom: 28px;
        position: relative;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
    }

    .hero-heading {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 2.4rem;
        font-weight: 800;
        color: #0b132b !important;
        letter-spacing: -0.03em;
        margin-bottom: 8px;
    }

    .gradient-cyan {
        background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-sub {
        font-size: 1.05rem;
        color: #475569 !important;
        max-width: 640px;
        margin: 0 auto 24px auto;
    }

    /* Metric Cards */
    [data-testid="stMetric"], .stMetric {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stMetric"]:hover, .stMetric:hover {
        border-color: rgba(14, 165, 233, 0.5) !important;
        box-shadow: 0 8px 24px -4px rgba(15, 23, 42, 0.08), 0 0 16px rgba(14, 165, 233, 0.15) !important;
        transform: translateY(-2px) !important;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] *,
    .stMetric label {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }

    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] *,
    .stMetric [data-testid="stMetricValue"] {
        color: #0b132b !important;
        font-weight: 800 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 2rem !important;
    }

    /* Navigation Tabs */
    [data-testid="stTabs"] [role="tablist"] {
        gap: 8px;
        border-bottom: 1px solid #e2e8f0 !important;
    }

    [data-testid="stTabs"] button,
    .stTabs [role="tab"] {
        color: #475569 !important;
        background: transparent !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 10px 18px !important;
        border-radius: 8px 8px 0 0 !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stTabs"] button:hover,
    .stTabs [role="tab"]:hover {
        color: #0284c7 !important;
        background: #f0f9ff !important;
    }

    [data-testid="stTabs"] button[aria-selected="true"],
    .stTabs [role="tab"][aria-selected="true"] {
        color: #0284c7 !important;
        border-bottom: 3px solid #0284c7 !important;
        font-weight: 700 !important;
    }

    /* Form Fields, Inputs & Labels */
    label,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] *,
    .stTextInput label,
    .stSelectbox label,
    .stNumberInput label,
    .stDateInput label {
        color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
    }

    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stDateInput"] input:focus {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.2) !important;
        outline: none !important;
    }

    /* Selectbox & Dropdowns */
    div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"]:focus-within {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.2) !important;
    }

    div[data-baseweb="select"] * {
        color: #0f172a !important;
    }

    div[data-baseweb="popover"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.1) !important;
    }

    div[data-baseweb="popover"] * {
        color: #0f172a !important;
        background-color: transparent !important;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary * {
        color: #0b132b !important;
        font-weight: 600 !important;
    }

    /* Radio buttons & Checkboxes */
    [data-testid="stRadio"] [role="radiogroup"] label *,
    [data-testid="stCheckbox"] label * {
        color: #1e293b !important;
        font-weight: 500 !important;
    }

    /* Dataframes & Tables */
    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
    }

    /* Alert Banners */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
    }

    [data-testid="stAlert"] * {
        color: #0f172a !important;
    }

    /* Buttons with Cyan Hover Glow */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.25) !important;
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.45), 0 4px 12px rgba(2, 132, 199, 0.35) !important;
        border-color: #38bdf8 !important;
    }

    .stButton > button[kind="secondary"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
    }

    .stButton > button[kind="secondary"]:hover {
        border-color: #0ea5e9 !important;
        color: #0284c7 !important;
        box-shadow: 0 0 12px rgba(14, 165, 233, 0.15) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Top Header Bar
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="top-brand-bar">
        <div class="brand-left">
            <div class="brand-icon">📖</div>
            <div>
                <div class="brand-name">Library Management</div>
                <div class="brand-tag">Unified Campus Workspace • Zero Login</div>
            </div>
        </div>
        <div style="font-size: 0.85rem; color: #64748b; font-weight: 500;">
            Active Database: <strong>library.db</strong>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Hero Banner & Metrics
# -----------------------------------------------------------------------------
stats = db.get_dashboard_stats()

st.markdown(
    """
    <div class="hero-card">
        <div style="display:inline-block; font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#0284c7; background:#f0f9ff; padding:4px 12px; border-radius:9999px; margin-bottom:12px; border:1px solid #bae6fd;">
            College Demonstration Edition
        </div>
        <h1 class="hero-heading">Your Library, <span class="gradient-cyan">Simplified.</span></h1>
        <p class="hero-sub">Explore the catalog, issue and return book copies instantly, and view student borrowing histories from one unified interface.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Books", stats.get("total_books", 0), help=f"{stats.get('total_copies', 0)} total copies")
m2.metric("Available Copies", stats.get("available_copies", 0), help="Copies ready to borrow")
m3.metric("Active Loans", stats.get("borrowed_copies", 0), help="Currently issued to students")
m4.metric("Overdue Loans", stats.get("overdue_loans", 0), delta=f"-{stats.get('overdue_loans', 0)}" if stats.get("overdue_loans", 0) > 0 else "0", delta_color="inverse")

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Main Navigation Tabs (Shared Single-Portal Interface)
# -----------------------------------------------------------------------------
tab_catalog, tab_circulation, tab_students, tab_reports = st.tabs(
    ["📚 Book Catalogue", "🔄 Circulation Desk", "👥 Student Records", "📊 Activity & Reports"]
)

# =============================================================================
# Tab 1: Book Catalogue
# =============================================================================
with tab_catalog:
    st.subheader("Book Catalogue")
    st.caption("Search, filter, add, edit, or delete books.")

    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_kw = st.text_input("Search Books", placeholder="Search by title, author, or ISBN...", label_visibility="collapsed")
    with f_col2:
        cats = ["All"] + db.get_distinct_categories()
        sel_cat = st.selectbox("Category", cats, label_visibility="collapsed")
    with f_col3:
        sel_avail = st.selectbox("Availability", ["All Statuses", "Available (In Stock)", "Checked Out"], label_visibility="collapsed")

    avail_only = (sel_avail == "Available (In Stock)")
    cat_param = None if sel_cat == "All" else sel_cat
    books = db.get_all_books(search_query=search_kw, category_filter=cat_param, available_only=avail_only)

    if sel_avail == "Checked Out":
        books = [b for b in books if b["available_copies"] == 0]

    # Add Book Accordion
    with st.expander("➕ Add New Book to Catalogue", expanded=False):
        with st.form("form_add_book", clear_on_submit=True):
            a_c1, a_c2 = st.columns(2)
            with a_c1:
                b_title = st.text_input("Title *")
                b_author = st.text_input("Author *")
            with a_c2:
                b_category = st.text_input("Category / Subject *")
                b_copies = st.number_input("Total Copies *", min_value=1, max_value=500, value=3)
            b_isbn = st.text_input("ISBN (Optional, leave empty if none)")
            
            submitted_add = st.form_submit_button("Save Book", type="primary")
            if submitted_add:
                ok, msg = db.add_book(
                    title=b_title.strip(),
                    author=b_author.strip(),
                    isbn=b_isbn.strip() if b_isbn else None,
                    category=b_category.strip(),
                    total_copies=int(b_copies),
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # Books Table Display
    if not books:
        st.info("No books found matching the current search criteria.")
    else:
        df_books = pd.DataFrame(books)
        display_df = df_books[["id", "title", "author", "category", "isbn", "available_copies", "total_copies"]].copy()
        display_df.columns = ["ID", "Title", "Author", "Category", "ISBN", "Available", "Total"]
        display_df["ISBN"] = display_df["ISBN"].fillna("-")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Edit & Delete Management Section
    st.markdown("---")
    st.write("##### Manage Existing Book Details")
    if books:
        book_options = {f"{b['id']} - {b['title']} (by {b['author']})": b for b in books}
        sel_book_label = st.selectbox("Select book to Edit or Delete:", list(book_options.keys()))
        target_b = book_options[sel_book_label]

        e_c1, e_c2 = st.columns([3, 1])
        with e_c1:
            with st.form("form_edit_book"):
                st.write(f"Editing: **{target_b['title']}** (ID: {target_b['id']})")
                e_t1, e_t2 = st.columns(2)
                with e_t1:
                    new_title = st.text_input("Title", value=target_b["title"])
                    new_author = st.text_input("Author", value=target_b["author"])
                with e_t2:
                    new_cat = st.text_input("Category", value=target_b["category"])
                    new_copies = st.number_input("Total Copies", min_value=1, value=target_b["total_copies"])
                new_isbn = st.text_input("ISBN (Optional)", value=target_b["isbn"] or "")

                if st.form_submit_button("Update Book Details", type="primary"):
                    ok, msg = db.update_book(
                        book_id=target_b["id"],
                        title=new_title.strip(),
                        author=new_author.strip(),
                        isbn=new_isbn.strip() if new_isbn else None,
                        category=new_cat.strip(),
                        new_total_copies=int(new_copies),
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with e_c2:
            st.write("Danger Zone")
            st.caption("Cannot delete books with active loans.")
            if st.button("Delete Book", type="secondary", key="btn_del_book"):
                ok, msg = db.delete_book(target_b["id"])
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


# =============================================================================
# Tab 2: Circulation Desk (Issue & Return)
# =============================================================================
with tab_circulation:
    st.subheader("Circulation Desk")
    st.caption("Issue books to students and process returns.")

    circ_action = st.radio("Action", ["Active Loans & Returns", "Issue a Book", "Loan History"], horizontal=True, label_visibility="collapsed")

    if circ_action == "Active Loans & Returns":
        active_loans = db.get_active_loans()
        if not active_loans:
            st.success("All borrowed books have been returned. No active loans!")
        else:
            search_loan = st.text_input("Filter Active Loans", placeholder="Search by student name or book title...")
            if search_loan:
                q = search_loan.lower()
                active_loans = [
                    l for l in active_loans
                    if q in l["book_title"].lower() or q in l["student_name"].lower() or q in l["student_code"].lower()
                ]

            for l in active_loans:
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    with c1:
                        st.write(f"**{l['book_title']}**")
                        st.caption(f"Author: {l['book_author']} | ISBN: {l['isbn'] or 'None'}")
                    with c2:
                        st.write(f"Borrower: **{l['student_name']}**")
                        st.caption(f"ID: {l['student_code']} | Email: {l['student_email']}")
                    with c3:
                        st.write(f"Due: **{l['due_date']}**")
                        if l.get("is_overdue"):
                            st.markdown(f"<span style='color:#dc2626; font-weight:700;'>⚠️ Overdue ({l.get('days_overdue')} days)</span>", unsafe_allow_html=True)
                        else:
                            st.caption("Issued: " + str(l.get("issue_date")))
                    with c4:
                        if st.button("Return", key=f"ret_{l['id']}", type="primary"):
                            ok, msg = db.return_book(l["id"], date.today().isoformat())
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e2e8f0;' />", unsafe_allow_html=True)

    elif circ_action == "Issue a Book":
        students = db.get_all_students()
        available_books = [b for b in db.get_all_books() if b["available_copies"] > 0]

        if not students:
            st.warning("No students registered. Please register a student first.")
        elif not available_books:
            st.warning("No books currently have copies available to borrow.")
        else:
            with st.form("form_issue_book"):
                stu_dict = {f"{s['name']} ({s['student_id']})": s["id"] for s in students}
                book_dict = {f"{b['title']} - {b['available_copies']} available": b["id"] for b in available_books}

                i_c1, i_c2 = st.columns(2)
                with i_c1:
                    sel_student_label = st.selectbox("Select Student *", list(stu_dict.keys()))
                    issue_d = st.date_input("Issue Date", value=date.today())
                with i_c2:
                    sel_book_label = st.selectbox("Select Available Book *", list(book_dict.keys()))
                    due_d = st.date_input("Due Date", value=date.today() + timedelta(days=14))

                if st.form_submit_button("Confirm & Issue Book", type="primary"):
                    ok, msg = db.issue_book(
                        book_id=book_dict[sel_book_label],
                        student_pk=stu_dict[sel_student_label],
                        issue_date=issue_d.isoformat(),
                        due_date=due_d.isoformat(),
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    elif circ_action == "Loan History":
        all_loans = db.get_loans()
        if not all_loans:
            st.info("No borrowing history records.")
        else:
            df_hist = pd.DataFrame(all_loans)
            cols = ["id", "book_title", "student_name", "student_code", "issue_date", "due_date", "return_date", "status"]
            st.dataframe(df_hist[cols], use_container_width=True, hide_index=True)


# =============================================================================
# Tab 3: Student Records
# =============================================================================
with tab_students:
    st.subheader("Student Directory")
    st.caption("Registered students and individual borrowing records.")

    s_c1, s_c2 = st.columns([3, 1])
    with s_c1:
        s_search = st.text_input("Search Students", placeholder="Search by name, student ID, or email...")
    with s_c2:
        st.write("")
        st.write("")
        # Add Student Toggle
        show_reg = st.checkbox("➕ Register New Student", value=False)

    if show_reg:
        with st.form("form_reg_student"):
            r_c1, r_c2, r_c3 = st.columns(3)
            with r_c1:
                r_id = st.text_input("Student ID / Roll No *", placeholder="e.g. STU-2024-010")
            with r_c2:
                r_name = st.text_input("Full Name *", placeholder="e.g. Rahul Sharma")
            with r_c3:
                r_email = st.text_input("Email Address *", placeholder="e.g. rahul@college.edu")

            if st.form_submit_button("Register Student", type="primary"):
                ok, msg = db.add_student(r_id.strip(), r_name.strip(), r_email.strip())
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    students_list = db.get_all_students(search_query=s_search)
    if not students_list:
        st.info("No students found.")
    else:
        df_stu = pd.DataFrame(students_list)
        st.dataframe(df_stu[["id", "student_id", "name", "email", "created_at"]], use_container_width=True, hide_index=True)


# =============================================================================
# Tab 4: Activity & Reports
# =============================================================================
with tab_reports:
    st.subheader("Activity & Reports")
    st.caption("Recent system activity and exportable circulation reports.")

    rep_data = db.get_circulation_report()
    if rep_data:
        df_rep = pd.DataFrame(rep_data)
        csv_buffer = io.StringIO()
        df_rep.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Export Circulation Report (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"library_report_{date.today().isoformat()}.csv",
            mime="text/csv",
            type="primary",
        )
    
    st.write("##### Recent Circulation Activity")
    recent = db.get_recent_activity(8)
    if not recent:
        st.caption("No recent activity recorded.")
    else:
        for r in recent:
            st.write(f"• **{r['student_name']}** ({r['student_code']}) — *{r['book_title']}* — Status: `{r['status']}` ({r['created_at']})")
