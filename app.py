"""
app.py - Library Management System
Unified Campus Workspace (Zero Login)
Matches the custom web design pixel-for-pixel on both Localhost and Streamlit Community Cloud.
- When run directly (`python app.py`): Starts FastAPI modern web server on port 8501.
- When run via Streamlit (`streamlit run app.py`): Renders the exact UI from Screenshots natively in Streamlit.
"""

from __future__ import annotations

import io
import math
import sys
import textwrap
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

import database as db

# -----------------------------------------------------------------------------
# CLI Entry Point: If invoked directly via `python app.py`, launch FastAPI server
# -----------------------------------------------------------------------------
if __name__ == "__main__" and not (hasattr(st, "runtime") and st.runtime.exists()):
    import uvicorn
    print("\n" + "=" * 60)
    print(" [*] Launching Library Management System on http://localhost:8501")
    print("=" * 60 + "\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8501, reload=False)
    sys.exit(0)

# -----------------------------------------------------------------------------
# Streamlit Mode: Native Pixel-Perfect Matching of the Modern Web Design
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Library Management",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()
db.seed_sample_data()

# Helper to render clean HTML without leading markdown indentation
def render_html(html_code: str):
    st.markdown(textwrap.dedent(html_code).strip(), unsafe_allow_html=True)

# Load External CSS Stylesheet + Streamlit Integration Rules
css_path = Path(__file__).parent / "static" / "styles.css"
custom_css = ""
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        custom_css = f.read()

render_html(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

    {custom_css}

    /* Streamlit Chrome Overrides */
    #MainMenu, header, footer, [data-testid="stHeader"] {{
        display: none !important;
    }}

    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: #f8fafc !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        color: #0f172a !important;
    }}

    .main .block-container, [data-testid="block-container"] {{
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1240px !important;
    }}

    /* Top Sticky Brand Navigation Bar Card */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.brand-emblem-wrap) {{
        position: -webkit-sticky !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 999 !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 8px 18px !important;
        margin-bottom: 24px !important;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04) !important;
    }}

    /* Navigation Pills - No Radio Circles! */
    [data-testid="stPills"] {{
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 6px !important;
    }}

    [data-testid="stPills"] button {{
        border-radius: 8px !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        border: none !important;
        background: transparent !important;
        color: #475569 !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}

    [data-testid="stPills"] button:hover {{
        color: #0b132b !important;
        background: #f1f5f9 !important;
    }}

    [data-testid="stPills"] button[aria-selected="true"],
    [data-testid="stPills"] button[data-checked="true"] {{
        color: #0284c7 !important;
        background: #f0f9ff !important;
        font-weight: 600 !important;
        box-shadow: inset 0 -2px 0 #0ea5e9 !important;
    }}

    /* Buttons */
    .stButton > button {{
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}

    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.25) !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.45), 0 4px 12px rgba(2, 132, 199, 0.35) !important;
        border-color: #38bdf8 !important;
    }}

    .stButton > button[kind="secondary"] {{
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
    }}

    .stButton > button[kind="secondary"]:hover {{
        border-color: #0ea5e9 !important;
        color: #0284c7 !important;
        box-shadow: 0 0 12px rgba(14, 165, 233, 0.15) !important;
    }}

    /* Quick Action Pills */
    div[data-testid*="qa_"] button {{
        border-radius: 9999px !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        color: #475569 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 6px 14px !important;
    }}

    div[data-testid*="qa_"] button:hover {{
        background: #f0f9ff !important;
        border-color: #0ea5e9 !important;
        color: #0284c7 !important;
        box-shadow: 0 0 12px rgba(14, 165, 233, 0.16) !important;
        transform: translateY(-1px) !important;
    }}

    /* Form Fields & Dropdowns */
    label, [data-testid="stWidgetLabel"] {{
        color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }}

    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input {{
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 9px 14px !important;
    }}

    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stDateInput"] input:focus {{
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.2) !important;
        outline: none !important;
    }}

    div[data-baseweb="select"] {{
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }}

    /* Dialog Card */
    [data-testid="stDialog"] div[role="dialog"] {{
        border-radius: 16px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25) !important;
    }}

    /* Table Row Border */
    .table-row {{
        display: grid;
        grid-template-columns: 3fr 2fr 1.5fr 1.5fr 1.5fr 1.5fr;
        align-items: center;
        padding: 14px 18px;
        border-bottom: 1px solid #e2e8f0;
        background: #ffffff;
        font-size: 0.9rem;
    }}
    .table-row:hover {{
        background: #f8fafc;
    }}
    .table-head {{
        background: #f1f5f9;
        font-weight: 600;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        border-bottom: 2px solid #e2e8f0;
    }}
    </style>
    """
)

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Overview"
if "catalog_search" not in st.session_state:
    st.session_state["catalog_search"] = ""

# -----------------------------------------------------------------------------
# Modal Dialogs (Using Streamlit Native @st.dialog)
# -----------------------------------------------------------------------------

@st.dialog("Add New Book")
def modal_add_book():
    render_html("<p style='font-size:0.88rem; color:#64748b; margin-top:-8px; margin-bottom:16px;'>Enter the book details to add it to the campus catalogue.</p>")
    with st.form("modal_form_add_book", clear_on_submit=False):
        b_title = st.text_input("Book Title *", placeholder="e.g. Introduction to Algorithms")
        b_author = st.text_input("Author(s) *", placeholder="e.g. Thomas H. Cormen")
        c1, c2 = st.columns(2)
        with c1:
            b_category = st.text_input("Category / Subject *", placeholder="e.g. Computer Science")
        with c2:
            b_copies = st.number_input("Total Physical Copies *", min_value=1, max_value=500, value=3)
        b_isbn = st.text_input("ISBN (Optional)", placeholder="e.g. 978-0262033848 (leave blank if none)")
        st.caption("Leave blank if the book has no ISBN. Duplicate ISBNs will be prevented.")
        
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with btn_c2:
            submit = st.form_submit_button("Save Book", type="primary", use_container_width=True)
            
        if submit:
            if not b_title.strip() or not b_author.strip() or not b_category.strip():
                st.error("Please fill in all required fields (Title, Author, Category).")
            else:
                ok, msg = db.add_book(
                    title=b_title.strip(),
                    author=b_author.strip(),
                    isbn=b_isbn.strip() if b_isbn.strip() else None,
                    category=b_category.strip(),
                    total_copies=int(b_copies),
                )
                if ok:
                    st.toast(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(msg)
        elif cancel:
            st.rerun()


@st.dialog("Issue a Book")
def modal_issue_book():
    render_html("<p style='font-size:0.88rem; color:#64748b; margin-top:-8px; margin-bottom:16px;'>Assign an available book copy to a registered student.</p>")
    students = db.get_all_students()
    available_books = [b for b in db.get_all_books() if b["available_copies"] > 0]
    
    if not students:
        st.warning("No students registered. Please register a student first.")
        return
    if not available_books:
        st.warning("No books currently have copies available in stock.")
        return

    stu_dict = {f"{s['name']} ({s['student_id']})": s["id"] for s in students}
    book_dict = {f"{b['title']} — {b['available_copies']} available (by {b['author']})": b["id"] for b in available_books}

    with st.form("modal_form_issue_book", clear_on_submit=False):
        sel_student = st.selectbox("Select Student *", list(stu_dict.keys()))
        sel_book = st.selectbox("Select Available Book *", list(book_dict.keys()))
        
        ic1, ic2 = st.columns(2)
        with ic1:
            issue_date = st.date_input("Issue Date", value=date.today())
        with ic2:
            due_date = st.date_input("Due Date", value=date.today() + timedelta(days=14))
            
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with btn_c2:
            submit = st.form_submit_button("Confirm & Issue", type="primary", use_container_width=True)
            
        if submit:
            ok, msg = db.issue_book(
                book_id=book_dict[sel_book],
                student_pk=stu_dict[sel_student],
                issue_date=issue_date.isoformat(),
                due_date=due_date.isoformat(),
            )
            if ok:
                st.toast(f"✅ {msg}")
                st.rerun()
            else:
                st.error(msg)
        elif cancel:
            st.rerun()


@st.dialog("Register Student")
def modal_add_student():
    render_html("<p style='font-size:0.88rem; color:#64748b; margin-top:-8px; margin-bottom:16px;'>Register a new student account to enable book checkout.</p>")
    with st.form("modal_form_add_student", clear_on_submit=False):
        s_id = st.text_input("Student ID / Code *", placeholder="e.g. STU-2024-015")
        s_name = st.text_input("Full Name *", placeholder="e.g. Rahul Sharma")
        s_email = st.text_input("Email Address *", placeholder="e.g. rahul@college.edu")
        
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with btn_c2:
            submit = st.form_submit_button("Register Student", type="primary", use_container_width=True)
            
        if submit:
            if not s_id.strip() or not s_name.strip() or not s_email.strip():
                st.error("Please fill in all student details.")
            else:
                ok, msg = db.add_student(s_id.strip(), s_name.strip(), s_email.strip())
                if ok:
                    st.toast(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(msg)
        elif cancel:
            st.rerun()


@st.dialog("Borrowing History")
def modal_student_history(student: Dict[str, Any]):
    render_html(f"<h3 style='margin-top:-8px; color:#0b132b;'>{student['name']}</h3>")
    st.caption(f"Student ID: {student['student_id']} • Email: {student['email']}")
    loans = db.get_loans(student_id_filter=student["id"])
    if not loans:
        st.info("No borrowing history found for this student.")
    else:
        for l in loans:
            is_ret = l.get("status") == "RETURNED"
            bg_col = "#ecfdf5" if is_ret else "#f0f9ff"
            txt_col = "#059669" if is_ret else "#0284c7"
            render_html(
                f"""
                <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:12px 16px; margin-bottom:10px;">
                    <div style="font-weight:700; color:#0b132b;">{l['book_title']}</div>
                    <div style="font-size:0.82rem; color:#64748b;">Issued: {l['issue_date']} | Due: {l['due_date']}</div>
                    <div style="margin-top:6px;">
                        <span style="font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:9999px; background:{bg_col}; color:{txt_col};">
                            {l['status']}
                        </span>
                    </div>
                </div>
                """
            )


@st.dialog("Edit Book")
def modal_edit_book(book: Dict[str, Any]):
    render_html(f"<p style='font-size:0.88rem; color:#64748b; margin-top:-8px;'>Update details for ID: #{book['id']}</p>")
    with st.form(f"form_edit_book_{book['id']}"):
        new_title = st.text_input("Title", value=book["title"])
        new_author = st.text_input("Author", value=book["author"])
        c1, c2 = st.columns(2)
        with c1:
            new_cat = st.text_input("Category", value=book["category"])
        with c2:
            new_copies = st.number_input("Total Copies", min_value=1, value=book["total_copies"])
        new_isbn = st.text_input("ISBN", value=book["isbn"] or "")
        
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        with btn_c2:
            save = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
            
        if save:
            ok, msg = db.update_book(
                book_id=book["id"],
                title=new_title.strip(),
                author=new_author.strip(),
                isbn=new_isbn.strip() if new_isbn.strip() else None,
                category=new_cat.strip(),
                new_total_copies=int(new_copies),
            )
            if ok:
                st.toast(f"✅ {msg}")
                st.rerun()
            else:
                st.error(msg)
        elif cancel:
            st.rerun()


# -----------------------------------------------------------------------------
# Top Navigation Bar (Header) Matching Screenshot 1
# -----------------------------------------------------------------------------
with st.container(border=True):
    col_brand, col_nav, col_actions = st.columns([2.6, 5.2, 2.6], vertical_alignment="center")

    with col_brand:
        render_html(
            """
            <div class="brand-emblem-wrap" style="display:flex; align-items:center; gap:12px;">
                <div class="brand-emblem" style="width:38px; height:38px; background:linear-gradient(135deg, #0b132b 0%, #1e3a8a 100%); border-radius:8px; display:flex; align-items:center; justify-content:center; color:#38bdf8; flex-shrink:0;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                        <path d="M12 6v6"></path>
                        <path d="M9 9h6"></path>
                    </svg>
                </div>
                <div>
                    <div style="font-family:'Plus Jakarta Sans',sans-serif; font-weight:800; font-size:1.15rem; color:#0b132b; line-height:1.2;">Library Management</div>
                    <div style="font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#0284c7;">CAMPUS EDITION</div>
                </div>
            </div>
            """
        )

    with col_nav:
        pages = ["Overview", "Catalogue", "Circulation Desk", "Students", "Reports & Activity"]
        current = st.session_state.get("current_page", "Overview")
        if hasattr(st, "pills"):
            selected = st.pills("nav_pills", pages, default=current if current in pages else "Overview", label_visibility="collapsed")
            if selected and selected != st.session_state["current_page"]:
                st.session_state["current_page"] = selected
                st.rerun()
        else:
            n_cols = st.columns(5)
            for i, p in enumerate(pages):
                is_active = (p == current)
                if n_cols[i].button(p, key=f"nav_p_{i}", type="primary" if is_active else "secondary", use_container_width=True):
                    st.session_state["current_page"] = p
                    st.rerun()

    with col_actions:
        a1, a2 = st.columns([1, 1], vertical_alignment="center")
        with a1:
            if st.button("📋 Issue Book", key="btn_top_issue", use_container_width=True):
                modal_issue_book()
        with a2:
            if st.button("➕ Add Book", key="btn_top_add", type="primary", use_container_width=True):
                modal_add_book()


# -----------------------------------------------------------------------------
# PAGE 1: OVERVIEW (Screenshot 1)
# -----------------------------------------------------------------------------
if st.session_state["current_page"] == "Overview":
    stats = db.get_dashboard_stats()
    avail_rate = (
        round((stats["available_copies"] / stats["total_copies"]) * 100)
        if stats.get("total_copies", 0) > 0
        else 0
    )

    # Hero Badge & Title & Subtitle (No indentation)
    render_html(
        """
        <div style="text-align: center; padding: 20px 0 16px 0;">
            <div style="display:inline-flex; align-items:center; gap:8px; font-size:0.78rem; font-weight:700; color:#0284c7; background:#f0f9ff; padding:6px 16px; border-radius:9999px; margin-bottom:14px; border:1px solid #bae6fd;">
                <span style="width:6px; height:6px; border-radius:50%; background:#0284c7; display:inline-block;"></span>
                <span>Unified Library Management System • Demonstration Edition</span>
            </div>
            <h1 style="font-family:'Plus Jakarta Sans',sans-serif; font-size:2.8rem; font-weight:800; color:#0b132b; letter-spacing:-0.03em; margin:0 0 10px 0;">
                Your Library, <span style="background:linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Simplified.</span>
            </h1>
            <p style="font-size:1.05rem; color:#475569; max-width:680px; margin:0 auto 28px auto; line-height:1.6;">
                Intelligent book cataloguing, instant book checkout and returns, live inventory tracking, and full student borrowing histories in one frictionless interface.
            </p>
        </div>
        """
    )

    # Hero Search Bar (Screenshot 1)
    c_s1, c_s2, c_s3 = st.columns([1, 4.5, 1])
    with c_s2:
        with st.form("hero_search_form", clear_on_submit=False):
            s_in_col, s_btn_col = st.columns([3.8, 1.2], vertical_alignment="center")
            with s_in_col:
                hero_q = st.text_input("hero_q", placeholder="Search by title, author, category, or ISBN...", label_visibility="collapsed")
            with s_btn_col:
                hero_search_btn = st.form_submit_button("Search Books", type="primary", use_container_width=True)
            if hero_search_btn and hero_q.strip():
                st.session_state["catalog_search"] = hero_q.strip()
                st.session_state["current_page"] = "Catalogue"
                st.rerun()

    # Quick Action Shortcuts (Screenshot 1)
    qa1, qa2, qa3, qa4, qa5 = st.columns([1.2, 1.5, 1.5, 1.5, 1.5], vertical_alignment="center")
    with qa1:
        st.markdown("<div style='text-align:right; font-size:0.85rem; font-weight:600; color:#94a3b8; padding-top:6px;'>Quick Actions:</div>", unsafe_allow_html=True)
    with qa2:
        if st.button("📖 Browse Books", key="qa_browse", use_container_width=True):
            st.session_state["current_page"] = "Catalogue"
            st.rerun()
    with qa3:
        if st.button("➕ Add New Book", key="qa_add", use_container_width=True):
            modal_add_book()
    with qa4:
        if st.button("📋 Issue a Book", key="qa_issue", use_container_width=True):
            modal_issue_book()
    with qa5:
        if st.button("🔄 Return a Book", key="qa_return", use_container_width=True):
            st.session_state["current_page"] = "Circulation Desk"
            st.rerun()

    st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

    # Real-Time Metric Cards (Screenshot 1)
    overdue_count = stats.get("overdue_loans", 0)
    overdue_badge = (
        '<span style="font-size:0.78rem; font-weight:700; color:#dc2626; background:#fef2f2; padding:3px 10px; border-radius:9999px;">Action required: overdue books</span>'
        if overdue_count > 0
        else '<span style="font-size:0.78rem; color:#94a3b8;">All loans in good standing</span>'
    )

    render_html(
        f"""
        <div class="metrics-grid">
            <div class="metric-card glow-card">
                <div class="metric-icon-wrap icon-blue">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                    </svg>
                </div>
                <div class="metric-data">
                    <span class="metric-label">Total Titles</span>
                    <span class="metric-value">{stats['total_books']}</span>
                </div>
                <span class="metric-sub">{stats['total_copies']} total physical copies</span>
            </div>

            <div class="metric-card glow-card">
                <div class="metric-icon-wrap icon-green">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </div>
                <div class="metric-data">
                    <span class="metric-label">Available Copies</span>
                    <span class="metric-value">{stats['available_copies']}</span>
                </div>
                <span class="metric-sub">{avail_rate}% copies ready to issue</span>
            </div>

            <div class="metric-card glow-card">
                <div class="metric-icon-wrap icon-cyan">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                        <circle cx="8.5" cy="7" r="4"></circle>
                        <line x1="20" y1="8" x2="20" y2="14"></line>
                        <line x1="23" y1="11" x2="17" y2="11"></line>
                    </svg>
                </div>
                <div class="metric-data">
                    <span class="metric-label">Active Loans</span>
                    <span class="metric-value">{stats['borrowed_copies']}</span>
                </div>
                <span class="metric-sub">Across {stats['total_students']} students</span>
            </div>

            <div class="metric-card glow-card">
                <div class="metric-icon-wrap icon-red">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                </div>
                <div class="metric-data">
                    <span class="metric-label">Overdue Loans</span>
                    <span class="metric-value" style="color:{'#dc2626' if overdue_count > 0 else '#0b132b'};">{overdue_count}</span>
                </div>
                <div style="margin-top:4px;">{overdue_badge}</div>
            </div>
        </div>
        """
    )


# -----------------------------------------------------------------------------
# PAGE 2: CIRCULATION DESK (Screenshot 5)
# -----------------------------------------------------------------------------
elif st.session_state["current_page"] == "Circulation Desk":
    active_loans = db.get_active_loans()
    overdue_loans = [l for l in active_loans if l.get("is_overdue")]

    # Section Header
    sh_c1, sh_c2 = st.columns([4, 1.2], vertical_alignment="center")
    with sh_c1:
        render_html(
            """
            <div>
                <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#0284c7; margin-bottom:4px;">CIRCULATION MANAGEMENT</div>
                <h1 style="font-size:2.1rem; font-weight:800; color:#0b132b; margin:0 0 6px 0;">Circulation Desk</h1>
                <p style="font-size:0.95rem; color:#475569; margin:0;">Manage active loans, process fast book returns, and issue books to registered students.</p>
            </div>
            """
        )
    with sh_c2:
        if st.button("📋 Issue Book", key="btn_circ_hdr_issue", type="primary", use_container_width=True):
            modal_issue_book()

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    tab_active, tab_overdue, tab_issue_form, tab_history = st.tabs([
        f"Active Loans ({len(active_loans)})",
        f"Overdue Loans ({len(overdue_loans)})",
        "Issue New Book",
        "Complete Loan History",
    ])

    with tab_active:
        filter_col, ref_col = st.columns([4, 1], vertical_alignment="center")
        with filter_col:
            q_circ = st.text_input("filter_active_loans", placeholder="Search loans by book title or student...", label_visibility="collapsed")
        with ref_col:
            if st.button("🔄 Refresh", key="btn_refresh_circ", use_container_width=True):
                st.rerun()

        loans_to_show = active_loans
        if q_circ.strip():
            qw = q_circ.strip().lower()
            loans_to_show = [
                l for l in active_loans
                if qw in l["book_title"].lower() or qw in l["student_name"].lower() or qw in l["student_code"].lower()
            ]

        if not loans_to_show:
            render_html(
                """
                <div class="empty-state" style="padding:48px 20px; text-align:center; background:#ffffff; border:1px dashed #cbd5e1; border-radius:12px; margin-top:16px;">
                    <div style="font-size:1.15rem; font-weight:700; color:#0b132b; margin-bottom:6px;">No Active Borrowed Books</div>
                    <p style="font-size:0.9rem; color:#64748b; margin:0;">All issued books have been returned in full or match no active filter.</p>
                </div>
                """
            )
        else:
            render_html(
                """
                <div class="table-row table-head" style="margin-top:12px; border-radius:8px 8px 0 0;">
                    <div>BOOK DETAILS</div>
                    <div>BORROWER</div>
                    <div>ISSUE DATE</div>
                    <div>DUE DATE</div>
                    <div>STATUS</div>
                    <div style="text-align:right;">ACTION</div>
                </div>
                """
            )

            for l in loans_to_show:
                r1, r2, r3, r4, r5, r6 = st.columns([3, 2, 1.4, 1.4, 1.4, 1.4], vertical_alignment="center")
                with r1:
                    render_html(f"<div><strong style='color:#0b132b;'>{l['book_title']}</strong><br><span style='font-size:0.8rem; color:#64748b;'>by {l['book_author']}</span></div>")
                with r2:
                    render_html(f"<div><strong style='color:#0b132b;'>{l['student_name']}</strong><br><span style='font-size:0.75rem; font-family:monospace; background:#f1f5f9; padding:2px 6px; border-radius:4px; color:#475569;'>{l['student_code']}</span></div>")
                with r3:
                    render_html(f"<span style='font-size:0.88rem; color:#475569;'>{l['issue_date']}</span>")
                with r4:
                    render_html(f"<span style='font-size:0.88rem; font-weight:700; color:#0b132b;'>{l['due_date']}</span>")
                with r5:
                    if l.get("is_overdue"):
                        render_html(f"<span style='background:#fef2f2; color:#dc2626; font-size:0.75rem; font-weight:700; padding:4px 8px; border-radius:9999px;'>⚠️ Overdue ({l.get('days_overdue')}d)</span>")
                    else:
                        render_html("<span style='background:#f0f9ff; color:#0284c7; font-size:0.75rem; font-weight:700; padding:4px 8px; border-radius:9999px;'>Active</span>")
                with r6:
                    if st.button("Return Book", key=f"ret_btn_{l['id']}", use_container_width=True):
                        ok, msg = db.return_book(l["id"], date.today().isoformat())
                        if ok:
                            st.toast(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(msg)
                render_html("<hr style='margin:4px 0; border:none; border-top:1px solid #e2e8f0;'/>")

    with tab_overdue:
        if not overdue_loans:
            st.success("🎉 Excellent! There are currently no overdue loans in the library.")
        else:
            for l in overdue_loans:
                ro1, ro2, ro3, ro4 = st.columns([3, 2, 2, 1.5], vertical_alignment="center")
                with ro1:
                    render_html(f"<div><strong style='color:#0b132b;'>{l['book_title']}</strong><br><span style='font-size:0.8rem; color:#64748b;'>by {l['book_author']}</span></div>")
                with ro2:
                    render_html(f"<div><strong style='color:#0b132b;'>{l['student_name']}</strong> ({l['student_code']})<br><span style='font-size:0.8rem; color:#64748b;'>{l['student_email']}</span></div>")
                with ro3:
                    render_html(f"<span style='color:#dc2626; font-weight:700;'>Due: {l['due_date']} ({l.get('days_overdue')} days overdue)</span>")
                with ro4:
                    if st.button("Return Book", key=f"ret_overdue_{l['id']}", type="primary", use_container_width=True):
                        ok, msg = db.return_book(l["id"], date.today().isoformat())
                        if ok:
                            st.toast(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(msg)
                render_html("<hr style='margin:4px 0; border:none; border-top:1px solid #e2e8f0;'/>")

    with tab_issue_form:
        students = db.get_all_students()
        available_books = [b for b in db.get_all_books() if b["available_copies"] > 0]
        if not students:
            st.warning("Please register students first.")
        elif not available_books:
            st.warning("No books currently available in stock.")
        else:
            with st.form("form_tab_issue"):
                stu_dict = {f"{s['name']} ({s['student_id']})": s["id"] for s in students}
                book_dict = {f"{b['title']} ({b['available_copies']} available)": b["id"] for b in available_books}
                i1, i2 = st.columns(2)
                with i1:
                    sel_s = st.selectbox("Select Student *", list(stu_dict.keys()))
                    i_date = st.date_input("Issue Date", value=date.today())
                with i2:
                    sel_b = st.selectbox("Select Available Book *", list(book_dict.keys()))
                    d_date = st.date_input("Due Date", value=date.today() + timedelta(days=14))
                if st.form_submit_button("Confirm & Issue Book", type="primary"):
                    ok, msg = db.issue_book(book_dict[sel_b], stu_dict[sel_s], i_date.isoformat(), d_date.isoformat())
                    if ok:
                        st.toast(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(msg)

    with tab_history:
        all_loans = db.get_loans()
        if not all_loans:
            st.info("No loan records found.")
        else:
            df = pd.DataFrame(all_loans)
            cols = ["id", "book_title", "student_name", "student_code", "issue_date", "due_date", "return_date", "status"]
            df_display = df[cols].copy()
            df_display.columns = ["ID", "Book Title", "Student Name", "Student ID", "Issued", "Due", "Returned", "Status"]
            df_display["Returned"] = df_display["Returned"].fillna("—")
            st.dataframe(df_display, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# PAGE 3: STUDENTS DIRECTORY (Screenshot 4)
# -----------------------------------------------------------------------------
elif st.session_state["current_page"] == "Students":
    all_students = db.get_all_students()
    active_loans = db.get_active_loans()
    loan_counts: Dict[int, int] = {}
    for l in active_loans:
        sid = l.get("student_pk")
        if sid:
            loan_counts[sid] = loan_counts.get(sid, 0) + 1

    for s in all_students:
        s["active_loans_count"] = loan_counts.get(s["id"], 0)

    # Header Matching Screenshot 4
    sh_c1, sh_c2 = st.columns([4, 1.5], vertical_alignment="center")
    with sh_c1:
        render_html(
            """
            <div>
                <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#0284c7; margin-bottom:4px;">STUDENT DIRECTORY</div>
                <h1 style="font-size:2.1rem; font-weight:800; color:#0b132b; margin:0 0 6px 0;">Student Directory & Records</h1>
                <p style="font-size:0.95rem; color:#475569; margin:0;">View registered students, track their active borrowing counts, and inspect borrowing histories.</p>
            </div>
            """
        )
    with sh_c2:
        if st.button("➕ Register Student", key="btn_hdr_reg_stu", type="primary", use_container_width=True):
            modal_add_student()

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Search Bar & Counter Pill (Screenshot 4)
    s_col1, s_col2 = st.columns([3.5, 1], vertical_alignment="center")
    with s_col1:
        q_stu = st.text_input("search_stu", placeholder="Search by student name, ID code, or email...", label_visibility="collapsed")
    with s_col2:
        render_html(
            f"""
            <div style="text-align:right;">
                <span style="font-size:0.85rem; font-weight:600; color:#475569; background:#ffffff; border:1px solid #e2e8f0; padding:8px 16px; border-radius:9999px;">
                    {len(all_students)} registered students
                </span>
            </div>
            """
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    filtered_students = all_students
    if q_stu.strip():
        qw = q_stu.strip().lower()
        filtered_students = [
            s for s in all_students
            if qw in s["name"].lower() or qw in s["student_id"].lower() or qw in s["email"].lower()
        ]

    if not filtered_students:
        render_html(
            """
            <div class="empty-state" style="padding:48px 20px; text-align:center; background:#ffffff; border:1px dashed #cbd5e1; border-radius:12px;">
                <div style="font-size:1.15rem; font-weight:700; color:#0b132b; margin-bottom:6px;">No Students Found</div>
                <p style="font-size:0.9rem; color:#64748b; margin:0;">No students match the current search keyword.</p>
            </div>
            """
        )
    else:
        # 4-Column Student Cards Grid Matching Screenshot 4
        cols = st.columns(4)
        for idx, s in enumerate(filtered_students):
            with cols[idx % 4]:
                name_parts = s["name"].split()
                initials = (name_parts[0][0] + (name_parts[1][0] if len(name_parts) > 1 else "")).upper()
                render_html(
                    f"""
                    <div class="student-card glow-card" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:18px; margin-bottom:12px; box-shadow:0 1px 3px rgba(15,23,42,0.05); min-height:190px; display:flex; flex-direction:column;">
                        <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
                            <div style="width:40px; height:40px; border-radius:50%; background:linear-gradient(135deg, #0284c7 0%, #1e3a8a 100%); display:flex; align-items:center; justify-content:center; color:#ffffff; font-weight:700; font-size:1rem; flex-shrink:0;">
                                {initials}
                            </div>
                            <div style="overflow:hidden;">
                                <div style="font-size:1.02rem; font-weight:700; color:#0b132b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{s['name']}</div>
                                <div style="font-size:0.75rem; font-family:monospace; background:#f1f5f9; padding:2px 6px; border-radius:4px; color:#475569; display:inline-block; margin-top:2px;">{s['student_id']}</div>
                            </div>
                        </div>
                        <div style="font-size:0.82rem; color:#64748b; margin-bottom:14px; word-break:break-all; overflow:hidden; text-overflow:ellipsis;">{s['email']}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:6px 12px; font-size:0.8rem; margin-top:auto; margin-bottom:10px;">
                            <span style="color:#64748b; font-weight:500;">Active Loans</span>
                            <span style="font-weight:700; color:#0284c7;">{s['active_loans_count']} books</span>
                        </div>
                    </div>
                    """
                )
                if st.button("Borrowing History", key=f"btn_hist_{s['id']}", use_container_width=True):
                    modal_student_history(s)


# -----------------------------------------------------------------------------
# PAGE 4: REPORTS & ACTIVITY (Screenshot 3)
# -----------------------------------------------------------------------------
elif st.session_state["current_page"] == "Reports & Activity":
    rep_data = db.get_circulation_report()
    recent = db.get_recent_activity(8)

    # Header Matching Screenshot 3
    rh_c1, rh_c2 = st.columns([4, 1.5], vertical_alignment="center")
    with rh_c1:
        render_html(
            """
            <div>
                <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#0284c7; margin-bottom:4px;">ANALYTICS & AUDIT</div>
                <h1 style="font-size:2.1rem; font-weight:800; color:#0b132b; margin:0 0 6px 0;">Activity & Reports</h1>
                <p style="font-size:0.95rem; color:#475569; margin:0;">Export complete library logs and inspect real-time transaction activity.</p>
            </div>
            """
        )
    with rh_c2:
        if rep_data:
            df_rep = pd.DataFrame(rep_data)
            csv_buf = io.StringIO()
            df_rep.to_csv(csv_buf, index=False)
            st.download_button(
                label="📥 Export CSV Report",
                data=csv_buf.getvalue(),
                file_name=f"library_report_{date.today().isoformat()}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Two-Column Dashboard (Screenshot 3)
    dash_col1, dash_col2 = st.columns([1.6, 1], gap="large")

    with dash_col1:
        recent_items_html = ""
        if not recent:
            recent_items_html = "<p style='color:#64748b;'>No activity recorded yet.</p>"
        else:
            for r in recent:
                is_ret = r.get("status") == "RETURNED"
                dot_color = "#059669" if is_ret else "#0284c7"
                action_text = "returned" if is_ret else "borrowed"
                recent_items_html += f"""
                <div style="display:flex; align-items:flex-start; gap:12px; margin-bottom:16px; padding-left:14px; position:relative; border-left:2px solid #e2e8f0;">
                    <span style="position:absolute; left:-6px; top:4px; width:10px; height:10px; border-radius:50%; background:{dot_color};"></span>
                    <div>
                        <div style="font-size:0.9rem; color:#0f172a;">
                            <strong>{r['student_name']}</strong> {action_text} <em>'{r['book_title']}'</em>
                        </div>
                        <div style="font-size:0.78rem; color:#94a3b8; margin-top:2px;">
                            {r['created_at']} • Status: <span style="font-weight:600; color:{dot_color};">{r['status']}</span>
                        </div>
                    </div>
                </div>
                """

        render_html(
            f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:24px; box-shadow:0 1px 3px rgba(15,23,42,0.05);">
                <div style="display:flex; align-items:center; gap:8px; font-size:1.15rem; font-weight:700; color:#0b132b; margin-bottom:20px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                    </svg>
                    <span>Recent Circulation Activity</span>
                </div>
                {recent_items_html}
            </div>
            """
        )

    with dash_col2:
        render_html(
            """
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:24px; box-shadow:0 1px 3px rgba(15,23,42,0.05);">
                <div style="display:flex; align-items:center; gap:8px; font-size:1.15rem; font-weight:700; color:#0b132b; margin-bottom:20px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                    </svg>
                    <span>System Overview & Storage</span>
                </div>
                <div style="display:flex; flex-direction:column; gap:14px;">
                    <div style="display:flex; justify-content:space-between; font-size:0.88rem; padding-bottom:10px; border-bottom:1px solid #e2e8f0;">
                        <span style="color:#64748b;">Architecture:</span>
                        <span style="font-weight:600; color:#0b132b;">FastAPI + SQLite + Modern Web</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.88rem; padding-bottom:10px; border-bottom:1px solid #e2e8f0;">
                        <span style="color:#64748b;">Transactions:</span>
                        <span style="font-weight:600; color:#0b132b;">Atomic ACID with WAL Mode</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.88rem; padding-bottom:10px; border-bottom:1px solid #e2e8f0;">
                        <span style="color:#64748b;">Authentication:</span>
                        <span style="font-weight:600; color:#0b132b;">Unified Shared Access (Zero Login)</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.88rem; padding-bottom:10px; border-bottom:1px solid #e2e8f0;">
                        <span style="color:#64748b;">ISBN Policy:</span>
                        <span style="font-weight:600; color:#0b132b;">Optional (Unique when present)</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.88rem;">
                        <span style="color:#64748b;">Overdue Calculation:</span>
                        <span style="font-weight:600; color:#0b132b;">Dynamic, real-time date check</span>
                    </div>
                </div>
            </div>
            """
        )


# -----------------------------------------------------------------------------
# PAGE 5: CATALOGUE (Book Inventory & Management)
# -----------------------------------------------------------------------------
elif st.session_state["current_page"] == "Catalogue":
    cat_h1, cat_h2 = st.columns([4, 1.2], vertical_alignment="center")
    with cat_h1:
        render_html(
            """
            <div>
                <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#0284c7; margin-bottom:4px;">BOOK CATALOGUE</div>
                <h1 style="font-size:2.1rem; font-weight:800; color:#0b132b; margin:0 0 6px 0;">Book Catalogue & Inventory</h1>
                <p style="font-size:0.95rem; color:#475569; margin:0;">Search, inspect copy availability, filter categories, or add new titles.</p>
            </div>
            """
        )
    with cat_h2:
        if st.button("➕ Add Book", key="btn_cat_add", type="primary", use_container_width=True):
            modal_add_book()

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Search & Filter Row
    f1, f2, f3 = st.columns([2.5, 1.2, 1.2])
    with f1:
        cat_q = st.text_input("cat_search", value=st.session_state["catalog_search"], placeholder="Search by title, author, or ISBN...", label_visibility="collapsed")
    with f2:
        cats = ["All Categories"] + db.get_distinct_categories()
        sel_cat = st.selectbox("cat_filter", cats, label_visibility="collapsed")
    with f3:
        sel_avail = st.selectbox("avail_filter", ["All Statuses", "Available (In Stock)", "Checked Out"], label_visibility="collapsed")

    cat_param = None if sel_cat == "All Categories" else sel_cat
    avail_only = (sel_avail == "Available (In Stock)")
    books = db.get_all_books(search_query=cat_q, category_filter=cat_param, available_only=avail_only)
    if sel_avail == "Checked Out":
        books = [b for b in books if b["available_copies"] == 0]

    render_html(f"<p style='font-size:0.85rem; color:#64748b; margin-top:8px;'>Showing <strong>{len(books)}</strong> titles</p>")

    if not books:
        render_html(
            """
            <div class="empty-state" style="padding:48px 20px; text-align:center; background:#ffffff; border:1px dashed #cbd5e1; border-radius:12px;">
                <div style="font-size:1.15rem; font-weight:700; color:#0b132b; margin-bottom:6px;">No Books Found</div>
                <p style="font-size:0.9rem; color:#64748b; margin:0;">Try adjusting your search criteria or category filter.</p>
            </div>
            """
        )
    else:
        # 3-Column Book Cards Grid
        b_cols = st.columns(3)
        for idx, b in enumerate(books):
            with b_cols[idx % 3]:
                avail = b["available_copies"]
                total = b["total_copies"]
                pct = round((avail / total) * 100) if total > 0 else 0
                render_html(
                    f"""
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:20px; margin-bottom:14px; box-shadow:0 1px 3px rgba(15,23,42,0.05); min-height:220px; display:flex; flex-direction:column;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                            <span style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#0284c7; background:#f0f9ff; padding:3px 10px; border-radius:9999px;">
                                {b['category']}
                            </span>
                            <span style="font-size:0.75rem; color:#94a3b8; font-family:monospace;">#{b['id']}</span>
                        </div>
                        <h3 style="font-size:1.08rem; font-weight:700; color:#0b132b; margin:0 0 4px 0; line-height:1.3;">{b['title']}</h3>
                        <p style="font-size:0.85rem; color:#64748b; margin:0 0 14px 0;">by {b['author']}</p>
                        
                        <div style="margin-top:auto; margin-bottom:12px;">
                            <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:600; color:#475569; margin-bottom:6px;">
                                <span>Copies Available</span>
                                <span>{avail} / {total}</span>
                            </div>
                            <div style="width:100%; height:6px; background:#f1f5f9; border-radius:9999px; overflow:hidden;">
                                <div style="width:{pct}%; height:100%; background:#0ea5e9; border-radius:9999px;"></div>
                            </div>
                        </div>
                    </div>
                    """
                )
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("✏️ Edit", key=f"edit_b_{b['id']}", use_container_width=True):
                        modal_edit_book(b)
                with bc2:
                    if st.button("🗑️ Delete", key=f"del_b_{b['id']}", use_container_width=True):
                        ok, msg = db.delete_book(b["id"])
                        if ok:
                            st.toast(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(msg)
