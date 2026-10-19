"""
server.py - Production-Grade REST API & Web Server for Library Management System
Backs the modern website with zero login screens and a shared interface for everyone.
"""

from __future__ import annotations

import csv
import io
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database as db

# Ensure database tables exist and migrations are safe
db.init_db()
db.seed_sample_data()

app = FastAPI(
    title="Library Management System",
    description="REST API powering the modern, zero-login Library Management web interface.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)


# -----------------------------------------------------------------------------
# Request & Response Models
# -----------------------------------------------------------------------------

class BookCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=150)
    isbn: Optional[str] = Field(None, max_length=30)
    category: str = Field(..., min_length=1, max_length=80)
    total_copies: int = Field(..., ge=1, le=1000)


class BookUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=150)
    isbn: Optional[str] = Field(None, max_length=30)
    category: str = Field(..., min_length=1, max_length=80)
    total_copies: int = Field(..., ge=1, le=1000)


class StudentCreateRequest(BaseModel):
    student_id: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=150)


class IssueLoanRequest(BaseModel):
    book_id: int
    student_id: int
    issue_date: Optional[str] = None
    due_date: Optional[str] = None


class ReturnLoanRequest(BaseModel):
    loan_id: int
    return_date: Optional[str] = None


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/stats")
def get_stats() -> Dict[str, Any]:
    """Retrieve real-time library metrics."""
    return db.get_dashboard_stats()


@app.get("/api/books")
def list_books(
    q: Optional[str] = Query(None, description="Search term for title, author, or ISBN"),
    category: Optional[str] = Query(None, description="Category filter"),
    available_only: bool = Query(False, description="Filter for books with available copies > 0"),
) -> List[Dict[str, Any]]:
    """Retrieve books matching search and category criteria."""
    cat_filter = None if (category == "All" or category == "" or category is None) else category
    return db.get_all_books(search_query=q, category_filter=cat_filter, available_only=available_only)


@app.get("/api/books/{book_id}")
def get_book(book_id: int) -> Dict[str, Any]:
    """Get single book details."""
    book = db.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.post("/api/books")
def create_book(req: BookCreateRequest) -> Dict[str, Any]:
    """Add a new book to the library catalogue."""
    ok, msg = db.add_book(
        title=req.title.strip(),
        author=req.author.strip(),
        isbn=req.isbn.strip() if req.isbn else None,
        category=req.category.strip(),
        total_copies=req.total_copies,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.put("/api/books/{book_id}")
def update_book(book_id: int, req: BookUpdateRequest) -> Dict[str, Any]:
    """Update details of an existing book."""
    ok, msg = db.update_book(
        book_id=book_id,
        title=req.title.strip(),
        author=req.author.strip(),
        isbn=req.isbn.strip() if req.isbn else None,
        category=req.category.strip(),
        new_total_copies=req.total_copies,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.delete("/api/books/{book_id}")
def delete_book(book_id: int) -> Dict[str, Any]:
    """Delete a book if it has no active loans."""
    ok, msg = db.delete_book(book_id=book_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.get("/api/categories")
def list_categories() -> List[str]:
    """Get all unique categories currently in the catalog."""
    return db.get_distinct_categories()


@app.get("/api/students")
def list_students(
    q: Optional[str] = Query(None, description="Search term for student ID, name, or email")
) -> List[Dict[str, Any]]:
    """Get all registered students."""
    students = db.get_all_students(search_query=q)
    # Augment with active loan count for each student
    loans = db.get_active_loans()
    loan_counts: Dict[int, int] = {}
    for l in loans:
        s_id = l.get("student_pk")
        if s_id:
            loan_counts[s_id] = loan_counts.get(s_id, 0) + 1

    for s in students:
        s["active_loans_count"] = loan_counts.get(s["id"], 0)
    return students


@app.post("/api/students")
def create_student(req: StudentCreateRequest) -> Dict[str, Any]:
    """Register a new student."""
    ok, msg = db.add_student(
        student_id=req.student_id.strip(),
        name=req.name.strip(),
        email=req.email.strip(),
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.get("/api/students/{student_id}/history")
def student_history(student_id: int) -> List[Dict[str, Any]]:
    """Retrieve full borrowing history for a specific student."""
    return db.get_loans(student_id_filter=student_id)


@app.get("/api/loans")
def list_loans(
    status: Optional[str] = Query(None, description="Loan status (ISSUED, RETURNED, etc.)"),
    q: Optional[str] = Query(None, description="Search term for book title, student name or code"),
    overdue_only: bool = Query(False, description="Filter for overdue loans only"),
) -> List[Dict[str, Any]]:
    """Retrieve loans with flexible filtering."""
    st = None if (status == "All" or status == "" or status is None) else status
    return db.get_loans(status_filter=st, overdue_only=overdue_only, search_query=q)


@app.get("/api/loans/active")
def list_active_loans(
    q: Optional[str] = Query(None, description="Search term for book title or student"),
) -> List[Dict[str, Any]]:
    """Retrieve currently active (ISSUED) loans."""
    return db.get_active_loans(search_query=q)


@app.get("/api/loans/overdue")
def list_overdue_loans(
    q: Optional[str] = Query(None, description="Search term for book title or student"),
) -> List[Dict[str, Any]]:
    """Retrieve active loans whose due date has passed."""
    return db.get_overdue_loans(search_query=q)


@app.post("/api/loans/issue")
def issue_loan(req: IssueLoanRequest) -> Dict[str, Any]:
    """Issue a book copy to a student."""
    issue_d = req.issue_date or date.today().isoformat()
    if not req.due_date:
        d_iss = datetime.strptime(issue_d, "%Y-%m-%d").date()
        due_d = (d_iss + timedelta(days=14)).isoformat()
    else:
        due_d = req.due_date

    ok, msg = db.issue_book(
        book_id=req.book_id,
        student_pk=req.student_id,
        issue_date=issue_d,
        due_date=due_d,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.post("/api/loans/return")
def return_loan(req: ReturnLoanRequest) -> Dict[str, Any]:
    """Return a currently issued book copy."""
    ret_d = req.return_date or date.today().isoformat()
    ok, msg = db.return_book(loan_id=req.loan_id, return_date=ret_d)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.get("/api/activity")
def list_activity(limit: int = 8) -> List[Dict[str, Any]]:
    """Get recent circulation events."""
    return db.get_recent_activity(limit=limit)


@app.get("/api/reports/export")
def export_circulation_report() -> StreamingResponse:
    """Download the full circulation audit report as a CSV file."""
    report_data = db.get_circulation_report()
    output = io.StringIO()
    if report_data:
        writer = csv.DictWriter(output, fieldnames=list(report_data[0].keys()))
        writer.writeheader()
        writer.writerows(report_data)
    else:
        writer = csv.writer(output)
        writer.writerow(["loan_id", "book_title", "book_author", "isbn", "category", "student_name", "student_code", "student_email", "issue_date", "due_date", "return_date", "status"])

    output.seek(0)
    filename = f"library_circulation_report_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# -----------------------------------------------------------------------------
# Static Frontend Serving
# -----------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index() -> FileResponse:
    """Serve the single-page application entry point."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(str(index_file))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8501, reload=False)
