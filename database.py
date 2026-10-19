"""
database.py - Database access layer for Campus Library Management System
Upgraded with:
- Safe, backward-compatible automatic migrations
- Secure PBKDF2 password hashing & role-based authentication (Admin & Student)
- Optional ISBN support with conditional uniqueness enforcement
- Student account lifecycle (active/deactivated) & borrowing history
- Student borrowing request workflow (REQUESTED, ISSUED, RETURNED, REJECTED)
- Configurable automatic reminders, deduplication, and notification queue
- Real-time dashboard analytics and circulation reporting
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import smtplib
import sqlite3
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = Path(__file__).parent / "library.db"


def get_connection(db_file: Optional[Path] = None) -> sqlite3.Connection:
    """
    Establish and return a SQLite database connection with row factory
    and foreign key constraints enabled.
    """
    target_db = db_file or DB_PATH
    conn = sqlite3.connect(target_db, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


# ============================================================================
# Password Security & Hashing (PBKDF2 with SHA-256)
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a cryptographically secure random salt."""
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    """Verify a plain-text password against a stored PBKDF2 salt$hash string."""
    if not stored_hash or "$" not in stored_hash or not password:
        return False
    try:
        salt, hash_val = stored_hash.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000)
        return secrets.compare_digest(dk.hex(), hash_val)
    except Exception:
        return False


# ============================================================================
# Database Initialization & Safe Migrations
# ============================================================================

def init_db(db_file: Optional[Path] = None) -> None:
    """
    Initialize tables and safely migrate existing databases to the latest schema
    without deleting or corrupting any existing data.
    """
    conn = get_connection(db_file)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        with conn:
            # 1. Settings Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            # Default settings
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reminder_days_before', '2');")
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('approval_required', '1');")

            # 2. Admins Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'ADMIN',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Seed default admin if table is empty
            admin_count = conn.execute("SELECT COUNT(*) AS c FROM admins").fetchone()["c"]
            if admin_count == 0:
                conn.execute(
                    """
                    INSERT INTO admins (username, name, email, password_hash, role)
                    VALUES (?, ?, ?, ?, 'ADMIN')
                    """,
                    ("admin", "Library Administrator", "admin@library.local", hash_password("AdminPassword123!")),
                )

            # 3. Students Table (with migration for password_hash & is_active)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            student_cols = [c[1] for c in conn.execute("PRAGMA table_info(students)").fetchall()]
            if "password_hash" not in student_cols:
                conn.execute("ALTER TABLE students ADD COLUMN password_hash TEXT;")
            if "is_active" not in student_cols:
                conn.execute("ALTER TABLE students ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1;")

            # For any student records without password, set default Student123!
            default_stu_hash = hash_password("Student123!")
            conn.execute("UPDATE students SET password_hash = ? WHERE password_hash IS NULL OR password_hash = '';", (default_stu_hash,))

            # 4. Books Table (Migrate isbn to OPTIONAL if previously NOT NULL)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    isbn TEXT,
                    category TEXT NOT NULL,
                    total_copies INTEGER NOT NULL CHECK(total_copies >= 0),
                    available_copies INTEGER NOT NULL CHECK(available_copies >= 0 AND available_copies <= total_copies),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            book_info = conn.execute("PRAGMA table_info(books)").fetchall()
            isbn_notnull = any(c[1] == "isbn" and c[3] == 1 for c in book_info)
            if isbn_notnull:
                # Migrate books table to make isbn optional
                conn.execute(
                    """
                    CREATE TABLE books_migration (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        isbn TEXT,
                        category TEXT NOT NULL,
                        total_copies INTEGER NOT NULL CHECK(total_copies >= 0),
                        available_copies INTEGER NOT NULL CHECK(available_copies >= 0 AND available_copies <= total_copies),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                conn.execute(
                    """
                    INSERT INTO books_migration (id, title, author, isbn, category, total_copies, available_copies, created_at)
                    SELECT id, title, author, isbn, category, total_copies, available_copies, created_at FROM books;
                    """
                )
                conn.execute("DROP TABLE books;")
                conn.execute("ALTER TABLE books_migration RENAME TO books;")

            # Conditional Unique Index for ISBN: Only enforces uniqueness when ISBN is provided
            conn.execute("DROP INDEX IF EXISTS idx_books_isbn;")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_books_isbn_unique ON books(isbn) WHERE isbn IS NOT NULL AND isbn != '';")

            # 5. Loans Table (Supporting REQUESTED, ISSUED, RETURNED, REJECTED)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    issue_date TEXT,
                    due_date TEXT,
                    return_date TEXT,
                    request_date TEXT,
                    status TEXT NOT NULL CHECK(status IN ('REQUESTED', 'ISSUED', 'RETURNED', 'REJECTED')),
                    reminder_due_time TEXT,
                    notification_status TEXT DEFAULT 'NONE',
                    last_attempt_time TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT,
                    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE RESTRICT
                );
                """
            )

            loan_cols = [c[1] for c in conn.execute("PRAGMA table_info(loans)").fetchall()]
            if "request_date" not in loan_cols:
                conn.execute("ALTER TABLE loans ADD COLUMN request_date TEXT;")
            if "reminder_due_time" not in loan_cols:
                conn.execute("ALTER TABLE loans ADD COLUMN reminder_due_time TEXT;")
            if "notification_status" not in loan_cols:
                conn.execute("ALTER TABLE loans ADD COLUMN notification_status TEXT DEFAULT 'NONE';")
            if "last_attempt_time" not in loan_cols:
                conn.execute("ALTER TABLE loans ADD COLUMN last_attempt_time TEXT;")

            # 6. Notifications Table (Reminder Queue & Delivery History)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loan_id INTEGER,
                    student_id INTEGER NOT NULL,
                    reminder_type TEXT NOT NULL, -- 'DUE_SOON', 'OVERDUE', 'APPROVAL', 'RETURN_CONFIRM', 'MANUAL'
                    recipient_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL, -- 'QUEUED', 'SENT', 'FAILED', 'SIMULATED'
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE SET NULL,
                    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
                );
                """
            )

            # Common Indices for Fast Search & Filtering
            conn.execute("CREATE INDEX IF NOT EXISTS idx_students_id ON students(student_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_loans_book_id ON loans(book_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_loans_student_id ON loans(student_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_loan ON notifications(loan_id);")
        conn.execute("PRAGMA foreign_keys = ON;")
    finally:
        conn.close()


# ============================================================================
# Validation & Configuration Helpers
# ============================================================================

def is_valid_email(email: str) -> bool:
    """Validate email using regex."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email.strip()))


def get_setting(key: str, default_val: str = "", db_file: Optional[Path] = None) -> str:
    """Retrieve system configuration value."""
    conn = get_connection(db_file)
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default_val
    finally:
        conn.close()


def set_setting(key: str, value: str, db_file: Optional[Path] = None) -> None:
    """Persist system configuration value."""
    conn = get_connection(db_file)
    try:
        with conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);", (key, str(value)))
    finally:
        conn.close()


# ============================================================================
# Authentication (Admin & Student Roles)
# ============================================================================

def authenticate_admin(username: str, password: str, db_file: Optional[Path] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Authenticate an administrator with username/email and password."""
    username = username.strip()
    if not username or not password:
        return False, None, "Username and password are required."

    conn = get_connection(db_file)
    try:
        row = conn.execute(
            "SELECT id, username, name, email, password_hash, role FROM admins WHERE username = ? OR email = ?",
            (username, username),
        ).fetchone()

        if not row:
            return False, None, "Invalid admin credentials."

        if not verify_password(password, row["password_hash"]):
            return False, None, "Invalid admin credentials."

        user_dict = {
            "id": row["id"],
            "username": row["username"],
            "name": row["name"],
            "email": row["email"],
            "role": "ADMIN",
        }
        return True, user_dict, f"Welcome back, {row['name']}!"
    finally:
        conn.close()


def authenticate_student(identifier: str, password: str, db_file: Optional[Path] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Authenticate a student with Student ID / Roll No or Email and password."""
    identifier = identifier.strip().upper()
    if not identifier or not password:
        return False, None, "Student ID/Email and password are required."

    conn = get_connection(db_file)
    try:
        row = conn.execute(
            "SELECT id, student_id, name, email, password_hash, is_active FROM students WHERE UPPER(student_id) = ? OR UPPER(email) = ?",
            (identifier, identifier),
        ).fetchone()

        if not row:
            return False, None, "No student account found with this ID or Email."

        if row["is_active"] == 0:
            return False, None, "This student account is currently deactivated. Please contact the library administration."

        if not verify_password(password, row["password_hash"]):
            return False, None, "Incorrect password."

        student_dict = {
            "id": row["id"],
            "student_id": row["student_id"],
            "name": row["name"],
            "email": row["email"],
            "role": "STUDENT",
        }
        return True, student_dict, f"Welcome, {row['name']}!"
    finally:
        conn.close()


def create_admin(username: str, name: str, email: str, password: str, db_file: Optional[Path] = None) -> Tuple[bool, str]:
    """Create a new administrator account."""
    username = username.strip()
    name = name.strip()
    email = email.strip()

    if not username or not name or not email or not password:
        return False, "All fields are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    conn = get_connection(db_file)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO admins (username, name, email, password_hash, role)
                VALUES (?, ?, ?, ?, 'ADMIN')
                """,
                (username, name, email, hash_password(password)),
            )
        return True, f"Admin account '{username}' created successfully."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' is already taken."
    finally:
        conn.close()


def change_password(user_id: int, role: str, old_password: str, new_password: str, db_file: Optional[Path] = None) -> Tuple[bool, str]:
    """Update password for an admin or student account."""
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."

    table = "admins" if role == "ADMIN" else "students"
    conn = get_connection(db_file)
    try:
        with conn:
            row = conn.execute(f"SELECT password_hash FROM {table} WHERE id = ?", (user_id,)).fetchone()
            if not row or not verify_password(old_password, row["password_hash"]):
                return False, "Incorrect current password."

            conn.execute(
                f"UPDATE {table} SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), user_id),
            )
        return True, "Password updated successfully."
    finally:
        conn.close()


# ============================================================================
# Book Management (Optional ISBN & Copy Limits)
# ============================================================================

def add_book(
    title: str,
    author: str,
    isbn: Optional[str],
    category: str,
    total_copies: int,
    db_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Add a new book to catalog.
    - Title, author, category, total_copies are REQUIRED.
    - ISBN is OPTIONAL.
    - Duplicate ISBN check ONLY fires when an ISBN is provided.
    """
    title = title.strip()
    author = author.strip()
    category = category.strip()
    clean_isbn = isbn.strip().upper() if isbn and isbn.strip() else None

    if not title:
        return False, "Title cannot be empty."
    if not author:
        return False, "Author cannot be empty."
    if not category:
        return False, "Category cannot be empty."
    if total_copies < 1:
        return False, "Total copies must be at least 1."

    conn = get_connection(db_file)
    try:
        with conn:
            # Check duplicate ISBN only when provided
            if clean_isbn:
                existing = conn.execute("SELECT id FROM books WHERE isbn = ?", (clean_isbn,)).fetchone()
                if existing:
                    return False, f"A book with ISBN '{clean_isbn}' already exists in the catalog."

            conn.execute(
                """
                INSERT INTO books (title, author, isbn, category, total_copies, available_copies)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, author, clean_isbn, category, total_copies, total_copies),
            )
        return True, f"Book '{title}' added successfully."
    except Exception as e:
        return False, f"Error adding book: {e}"
    finally:
        conn.close()


def get_all_books(
    search_query: Optional[str] = None,
    category_filter: Optional[Any] = None,
    available_only: bool = False,
    db_file: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Fetch books with optional search, category, or availability filters."""
    if isinstance(category_filter, (Path, str)) and (isinstance(category_filter, Path) or category_filter.endswith(".db") or "/" in str(category_filter) or "\\" in str(category_filter)):
        db_file = Path(category_filter)
        category_filter = None

    conn = get_connection(db_file)
    try:
        query = "SELECT id, title, author, isbn, category, total_copies, available_copies, created_at FROM books WHERE 1=1"
        params: List[Any] = []

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query += " AND (title LIKE ? OR author LIKE ? OR (isbn IS NOT NULL AND isbn LIKE ?) OR category LIKE ?)"
            params.extend([term, term, term, term])

        if category_filter and category_filter != "All":
            query += " AND category = ?"
            params.append(category_filter)

        if available_only:
            query += " AND available_copies > 0"

        query += " ORDER BY title COLLATE NOCASE ASC"

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_book_by_id(book_id: int, db_file: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve book by ID."""
    conn = get_connection(db_file)
    try:
        row = conn.execute(
            "SELECT id, title, author, isbn, category, total_copies, available_copies FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_available_books(db_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve books with available copies for issue."""
    return get_all_books(available_only=True, db_file=db_file)


def update_book(
    book_id: int,
    title: str,
    author: str,
    isbn: Optional[str],
    category: str,
    new_total_copies: int,
    db_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Update book details.
    - ISBN is optional; duplicate checked only if provided.
    - Cannot reduce total copies below active loans.
    """
    title = title.strip()
    author = author.strip()
    category = category.strip()
    clean_isbn = isbn.strip().upper() if isbn and isbn.strip() else None

    if not title:
        return False, "Title cannot be empty."
    if not author:
        return False, "Author cannot be empty."
    if not category:
        return False, "Category cannot be empty."
    if new_total_copies < 1:
        return False, "Total copies must be at least 1."

    conn = get_connection(db_file)
    try:
        with conn:
            # Check book exists
            book = conn.execute("SELECT total_copies, available_copies FROM books WHERE id = ?", (book_id,)).fetchone()
            if not book:
                return False, "Book not found."

            old_total = book["total_copies"]
            old_available = book["available_copies"]
            currently_borrowed = old_total - old_available

            if new_total_copies < currently_borrowed:
                return (
                    False,
                    f"Cannot reduce total copies to {new_total_copies}. "
                    f"There are currently {currently_borrowed} copies actively borrowed by students.",
                )

            # Check duplicate ISBN if supplied
            if clean_isbn:
                dup = conn.execute("SELECT id FROM books WHERE isbn = ? AND id != ?", (clean_isbn, book_id)).fetchone()
                if dup:
                    return False, f"A book with ISBN '{clean_isbn}' already exists for another catalog entry."

            new_available_copies = new_total_copies - currently_borrowed

            conn.execute(
                """
                UPDATE books
                SET title = ?, author = ?, isbn = ?, category = ?, total_copies = ?, available_copies = ?
                WHERE id = ?
                """,
                (title, author, clean_isbn, category, new_total_copies, new_available_copies, book_id),
            )
        return True, f"Book '{title}' updated successfully."
    except Exception as e:
        return False, f"Error updating book: {e}"
    finally:
        conn.close()


def delete_book(book_id: int, db_file: Optional[Path] = None) -> Tuple[bool, str]:
    """Delete book only if no active loans or pending requests exist."""
    conn = get_connection(db_file)
    try:
        with conn:
            active_count = conn.execute(
                "SELECT COUNT(*) AS c FROM loans WHERE book_id = ? AND status IN ('ISSUED', 'REQUESTED')",
                (book_id,),
            ).fetchone()["c"]

            if active_count > 0:
                return (
                    False,
                    f"Cannot delete this book. There are currently {active_count} active loan(s) or pending request(s).",
                )

            # Clean past returned/rejected loans
            conn.execute("DELETE FROM loans WHERE book_id = ?", (book_id,))
            cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            if cursor.rowcount == 0:
                return False, "Book not found."

        return True, "Book deleted successfully."
    except Exception as e:
        return False, f"Error deleting book: {e}"
    finally:
        conn.close()


def get_distinct_categories(db_file: Optional[Path] = None) -> List[str]:
    """Retrieve distinct subject categories."""
    conn = get_connection(db_file)
    try:
        rows = conn.execute("SELECT DISTINCT category FROM books ORDER BY category ASC").fetchall()
        return [r["category"] for r in rows if r["category"]]
    finally:
        conn.close()


# ============================================================================
# Student Management (Registration, Status Toggle, History)
# ============================================================================

def add_student(
    student_id: str,
    name: str,
    email: str,
    password: Optional[Any] = None,
    db_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Register student with unique ID, verified email, and hashed password."""
    # Backward compatibility: if 4th positional argument was db_file
    if isinstance(password, Path) or (isinstance(password, str) and (password.endswith(".db") or "/" in password or "\\" in password)):
        db_file = Path(password)
        password = None

    student_id = student_id.strip().upper()
    name = name.strip()
    email = email.strip()
    pwd = password.strip() if isinstance(password, str) and password.strip() else "Student123!"

    if not student_id:
        return False, "Student ID cannot be empty."
    if not name:
        return False, "Student name cannot be empty."
    if not email:
        return False, "Email cannot be empty."
    if not is_valid_email(email):
        return False, f"'{email}' is not a valid email address."

    conn = get_connection(db_file)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO students (student_id, name, email, password_hash, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (student_id, name, email, hash_password(pwd)),
            )
        return True, f"Student '{name}' ({student_id}) registered successfully. Default password: {pwd}"
    except sqlite3.IntegrityError:
        return False, f"A student with ID '{student_id}' is already registered."
    except Exception as e:
        return False, f"Error registering student: {e}"
    finally:
        conn.close()


def update_student(
    student_pk: int,
    name: str,
    email: str,
    new_password: Optional[str] = None,
    db_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Update student name, email, or reset password."""
    name = name.strip()
    email = email.strip()

    if not name or not email:
        return False, "Name and Email are required."
    if not is_valid_email(email):
        return False, f"'{email}' is not a valid email address."

    conn = get_connection(db_file)
    try:
        with conn:
            if new_password and new_password.strip():
                conn.execute(
                    "UPDATE students SET name = ?, email = ?, password_hash = ? WHERE id = ?",
                    (name, email, hash_password(new_password.strip()), student_pk),
                )
            else:
                conn.execute(
                    "UPDATE students SET name = ?, email = ? WHERE id = ?",
                    (name, email, student_pk),
                )
        return True, "Student record updated successfully."
    except Exception as e:
        return False, f"Error updating student: {e}"
    finally:
        conn.close()


def toggle_student_status(student_pk: int, is_active: int, db_file: Optional[Path] = None) -> Tuple[bool, str]:
    """Activate or deactivate a student account."""
    conn = get_connection(db_file)
    try:
        with conn:
            conn.execute("UPDATE students SET is_active = ? WHERE id = ?", (is_active, student_pk))
        status_word = "activated" if is_active == 1 else "deactivated"
        return True, f"Student account {status_word} successfully."
    except Exception as e:
        return False, f"Error updating status: {e}"
    finally:
        conn.close()


def get_all_students(
    search_query: Optional[str] = None,
    active_only: Any = False,
    db_file: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Fetch students with optional search filter."""
    if isinstance(active_only, (Path, str)) and (isinstance(active_only, Path) or active_only.endswith(".db") or "/" in str(active_only) or "\\" in str(active_only)):
        db_file = Path(active_only)
        active_only = False

    conn = get_connection(db_file)
    try:
        query = "SELECT id, student_id, name, email, is_active, created_at FROM students WHERE 1=1"
        params: List[Any] = []

        if active_only is True:
            query += " AND is_active = 1"

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query += " AND (student_id LIKE ? OR name LIKE ? OR email LIKE ?)"
            params.extend([term, term, term])

        query += " ORDER BY name COLLATE NOCASE ASC"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_student_by_id(student_pk: int, db_file: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve single student by primary key."""
    conn = get_connection(db_file)
    try:
        row = conn.execute("SELECT id, student_id, name, email, is_active FROM students WHERE id = ?", (student_pk,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ============================================================================
# Circulation & Borrowing Workflow (Request, Issue, Return, Reject)
# ============================================================================

def request_book(
    book_id: int,
    student_pk: int,
    db_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Submit a book checkout request by a student.
    Enforces:
    - Student is active
    - Book exists and has available copies > 0
    - Student does not already have an active loan or pending request for this book
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection(db_file)
    try:
        with conn:
            # Check student active
            student = conn.execute("SELECT id, name, is_active FROM students WHERE id = ?", (student_pk,)).fetchone()
            if not student:
                return False, "Student not found."
            if student["is_active"] != 1:
                return False, "Your student account is deactivated. Please contact the librarian."

            # Check book availability
            book = conn.execute("SELECT id, title, available_copies FROM books WHERE id = ?", (book_id,)).fetchone()
            if not book:
                return False, "Book not found."
            if book["available_copies"] <= 0:
                return False, f"All copies of '{book['title']}' are currently borrowed."

            # Check duplicate active loan or pending request
            existing = conn.execute(
                """
                SELECT id, status FROM loans
                WHERE book_id = ? AND student_id = ? AND status IN ('REQUESTED', 'ISSUED')
                """,
                (book_id, student_pk),
            ).fetchone()
            if existing:
                if existing["status"] == "REQUESTED":
                    return False, f"You already have a pending borrowing request for '{book['title']}'."
                else:
                    return False, f"You already have an active loan for '{book['title']}'."

            # Create loan in REQUESTED status
            conn.execute(
                """
                INSERT INTO loans (book_id, student_id, request_date, status, notification_status)
                VALUES (?, ?, ?, 'REQUESTED', 'PENDING')
                """,
                (book_id, student_pk, now_str),
            )
        return True, f"Borrowing request for '{book['title']}' submitted successfully! Awaiting librarian approval."
    except Exception as e:
        return False, f"Error submitting request: {e}"
    finally:
        conn.close()


def approve_request(
    loan_id: int,
    due_days: int = 14,
    db_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Approve a student borrowing request and issue the book atomically."""
    today = date.today()
    issue_date = today.isoformat()
    due_date = (today + timedelta(days=due_days)).isoformat()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection(db_file)
    try:
        with conn:
            loan = conn.execute(
                """
                SELECT l.id, l.book_id, l.student_id, l.status,
                       b.title, b.available_copies,
                       s.name AS student_name, s.email AS student_email
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN students s ON l.student_id = s.id
                WHERE l.id = ?
                """,
                (loan_id,),
            ).fetchone()

            if not loan:
                return False, "Loan request not found."
            if loan["status"] != "REQUESTED":
                return False, f"Cannot approve request: Loan status is '{loan['status']}'."
            if loan["available_copies"] <= 0:
                return False, f"No copies available for '{loan['title']}'."

            # Decrement inventory
            conn.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ? AND available_copies > 0", (loan["book_id"],))

            # Update loan record
            conn.execute(
                """
                UPDATE loans
                SET issue_date = ?, due_date = ?, status = 'ISSUED', notification_status = 'NONE'
                WHERE id = ? AND status = 'REQUESTED'
                """,
                (issue_date, due_date, loan_id),
            )

            # Queue approval notification
            conn.execute(
                """
                INSERT INTO notifications (loan_id, student_id, reminder_type, recipient_email, subject, message, status)
                VALUES (?, ?, 'APPROVAL', ?, ?, ?, 'QUEUED')
                """,
                (
                    loan_id,
                    loan["student_id"],
                    loan["student_email"],
                    f"Library Request Approved: {loan['title']}",
                    f"Hello {loan['student_name']},\n\nYour request for '{loan['title']}' has been approved. Due Date: {due_date}.\nPlease collect your book from the circulation desk.",
                ),
            )
        return True, f"Request approved. '{loan['title']}' issued to {loan['student_name']} (Due: {due_date})."
    except Exception as e:
        return False, f"Error approving request: {e}"
    finally:
        conn.close()


def reject_request(loan_id: int, reason: Optional[str] = None, db_file: Optional[Path] = None) -> Tuple[bool, str]:
    """Reject a borrowing request."""
    conn = get_connection(db_file)
    try:
        with conn:
            loan = conn.execute(
                """
                SELECT l.id, l.student_id, b.title, s.name AS student_name, s.email AS student_email
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN students s ON l.student_id = s.id
                WHERE l.id = ? AND l.status = 'REQUESTED'
                """,
                (loan_id,),
            ).fetchone()

            if not loan:
                return False, "Pending request not found."

            conn.execute("UPDATE loans SET status = 'REJECTED' WHERE id = ? AND status = 'REQUESTED'", (loan_id,))

            msg_text = f"Hello {loan['student_name']},\n\nYour request for '{loan['title']}' could not be approved at this time."
            if reason:
                msg_text += f"\nReason: {reason}"

            conn.execute(
                """
                INSERT INTO notifications (loan_id, student_id, reminder_type, recipient_email, subject, message, status)
                VALUES (?, ?, 'REJECTED', ?, ?, ?, 'QUEUED')
                """,
                (loan_id, loan["student_id"], loan["student_email"], f"Library Request Declined: {loan['title']}", msg_text),
            )
        return True, f"Request for '{loan['title']}' was rejected."
    except Exception as e:
        return False, f"Error rejecting request: {e}"
    finally:
        conn.close()


def issue_book(
    book_id: int,
    student_pk: int,
    issue_date: str,
    due_date: str,
    db_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Issue a book directly (Admin direct checkout)."""
    try:
        d_issue = datetime.strptime(issue_date, "%Y-%m-%d").date()
        d_due = datetime.strptime(due_date, "%Y-%m-%d").date()
        if d_due < d_issue:
            return False, "Due date cannot be earlier than issue date."
    except ValueError:
        return False, "Invalid date format. Expected YYYY-MM-DD."

    conn = get_connection(db_file)
    try:
        with conn:
            student = conn.execute("SELECT id, name, student_id, is_active FROM students WHERE id = ?", (student_pk,)).fetchone()
            if not student:
                return False, "Selected student does not exist."
            if student["is_active"] != 1:
                return False, f"Student '{student['name']}' is deactivated and cannot borrow books."

            book = conn.execute("SELECT id, title, available_copies FROM books WHERE id = ?", (book_id,)).fetchone()
            if not book:
                return False, "Selected book does not exist."
            if book["available_copies"] <= 0:
                return False, f"No available copies for '{book['title']}'. All copies are currently issued."

            # Check duplicate active loan
            existing = conn.execute(
                "SELECT id FROM loans WHERE book_id = ? AND student_id = ? AND status = 'ISSUED'",
                (book_id, student_pk),
            ).fetchone()
            if existing:
                return False, f"Student '{student['name']}' already has an active loan for '{book['title']}'."

            # Decrement availability
            upd = conn.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ? AND available_copies > 0", (book_id,))
            if upd.rowcount == 0:
                return False, "Failed to reserve copy."

            conn.execute(
                """
                INSERT INTO loans (book_id, student_id, issue_date, due_date, status)
                VALUES (?, ?, ?, ?, 'ISSUED')
                """,
                (book_id, student_pk, issue_date, due_date),
            )
        return True, f"'{book['title']}' issued to {student['name']} ({student['student_id']}) successfully."
    except Exception as e:
        return False, f"Transaction error: {e}"
    finally:
        conn.close()


def return_book(
    loan_id: int,
    return_date: str,
    db_file: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Process book return atomically, updating loan and inventory."""
    try:
        d_return = datetime.strptime(return_date, "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid return date format. Expected YYYY-MM-DD."

    conn = get_connection(db_file)
    try:
        with conn:
            loan = conn.execute(
                """
                SELECT l.id, l.book_id, l.student_id, l.issue_date, l.status,
                       b.title, b.available_copies, b.total_copies,
                       s.name AS student_name, s.student_id AS student_code, s.email AS student_email
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN students s ON l.student_id = s.id
                WHERE l.id = ?
                """,
                (loan_id,),
            ).fetchone()

            if not loan:
                return False, "Loan record not found."
            if loan["status"] != "ISSUED":
                return False, f"This loan is already marked as {loan['status']} and cannot be returned again."

            if loan["issue_date"]:
                d_issue = datetime.strptime(loan["issue_date"][:10], "%Y-%m-%d").date()
                if d_return < d_issue:
                    return False, f"Return date cannot be earlier than issue date ({loan['issue_date']})."

            # Update loan to RETURNED
            conn.execute(
                """
                UPDATE loans
                SET return_date = ?, status = 'RETURNED'
                WHERE id = ? AND status = 'ISSUED'
                """,
                (return_date, loan_id),
            )

            # Restore available copies
            conn.execute(
                "UPDATE books SET available_copies = MIN(total_copies, available_copies + 1) WHERE id = ?",
                (loan["book_id"],),
            )

            # Queue return confirmation notification
            conn.execute(
                """
                INSERT INTO notifications (loan_id, student_id, reminder_type, recipient_email, subject, message, status)
                VALUES (?, ?, 'RETURN_CONFIRM', ?, ?, ?, 'QUEUED')
                """,
                (
                    loan_id,
                    loan["student_id"],
                    loan["student_email"],
                    f"Return Receipt: {loan['title']}",
                    f"Hello {loan['student_name']},\n\nThis confirms that '{loan['title']}' was received and returned on {return_date}. Thank you!",
                ),
            )

        return True, f"'{loan['title']}' returned successfully by {loan['student_name']}."
    except Exception as e:
        return False, f"Error returning book: {e}"
    finally:
        conn.close()


# ============================================================================
# Loans & Overdue Tracking
# ============================================================================

def get_loans(
    status_filter: Optional[str] = None,
    student_id_filter: Optional[int] = None,
    overdue_only: bool = False,
    search_query: Optional[str] = None,
    db_file: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch borrowing records with calculated overdue status.
    - If student_id_filter is supplied, ONLY returns records for that student (server-side authorization).
    - Returned books are NEVER marked as overdue.
    """
    today = date.today()
    today_str = today.isoformat()

    conn = get_connection(db_file)
    try:
        query = """
            SELECT l.id, l.book_id, l.student_id AS student_pk,
                   l.issue_date, l.due_date, l.return_date, l.request_date, l.status, l.created_at,
                   b.title AS book_title, b.author AS book_author, b.isbn,
                   s.name AS student_name, s.student_id AS student_code, s.email AS student_email
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN students s ON l.student_id = s.id
            WHERE 1=1
        """
        params: List[Any] = []

        if student_id_filter is not None:
            query += " AND l.student_id = ?"
            params.append(student_id_filter)

        if status_filter and status_filter != "All":
            query += " AND l.status = ?"
            params.append(status_filter)

        if overdue_only:
            query += " AND l.status = 'ISSUED' AND l.due_date < ?"
            params.append(today_str)

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query += " AND (b.title LIKE ? OR (b.isbn IS NOT NULL AND b.isbn LIKE ?) OR s.name LIKE ? OR s.student_id LIKE ?)"
            params.extend([term, term, term, term])

        query += " ORDER BY l.id DESC"
        cursor = conn.execute(query, params)
        raw_loans = cursor.fetchall()

        results: List[Dict[str, Any]] = []
        for row in raw_loans:
            item = dict(row)
            is_overdue = False
            days_overdue = 0

            # Dynamic Overdue Calculation
            if item["status"] == "ISSUED" and item.get("due_date"):
                try:
                    due = datetime.strptime(item["due_date"][:10], "%Y-%m-%d").date()
                    if due < today:
                        is_overdue = True
                        days_overdue = (today - due).days
                except ValueError:
                    pass

            item["is_overdue"] = is_overdue
            item["days_overdue"] = days_overdue
            results.append(item)

        return results
    finally:
        conn.close()


def get_active_loans(search_query: Optional[str] = None, student_id_filter: Optional[int] = None, db_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve only currently ISSUED loans."""
    return get_loans(status_filter="ISSUED", student_id_filter=student_id_filter, search_query=search_query, db_file=db_file)


def get_overdue_loans(search_query: Optional[str] = None, student_id_filter: Optional[int] = None, db_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve active loans past due date."""
    return get_loans(status_filter=None, student_id_filter=student_id_filter, overdue_only=True, search_query=search_query, db_file=db_file)


def get_pending_requests(db_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve all pending student checkout requests."""
    return get_loans(status_filter="REQUESTED", db_file=db_file)


# ============================================================================
# Automatic Reminders & Notification Engine
# ============================================================================

def send_email_via_smtp(to_email: str, subject: str, message_body: str) -> Tuple[bool, str]:
    """
    Send an email notification using SMTP configuration from environment or Streamlit secrets.
    Never hardcodes passwords. If credentials are not present, returns False with a helpful reason.
    """
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user or "library@campus.edu")

    if not smtp_host or not smtp_user or not smtp_pass:
        return False, "SMTP configuration not found in environment (SMTP_HOST, SMTP_USER, SMTP_PASSWORD)."

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message_body, "plain"))

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10.0)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [to_email], msg.as_string())
        server.quit()
        return True, "Email sent successfully."
    except Exception as e:
        return False, f"SMTP delivery failure: {e}"


def check_and_send_reminders(db_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Evaluates all active loans:
    1. Identifies loans due within reminder_days_before days (e.g. 2 days)
    2. Identifies loans overdue (due_date < today)
    3. Prevents duplicate reminders for the same event
    4. Queues or sends notifications and logs history
    """
    today = date.today()
    days_before = int(get_setting("reminder_days_before", "2", db_file=db_file))
    due_threshold = today + timedelta(days=days_before)

    conn = get_connection(db_file)
    summary = {
        "active_loans_scanned": 0,
        "due_soon_reminders": 0,
        "overdue_reminders": 0,
        "duplicates_skipped": 0,
        "delivery_mode": "SIMULATED / QUEUED (Set SMTP env vars to enable real delivery)",
        "details": [],
    }

    try:
        with conn:
            # Query all active loans
            loans = conn.execute(
                """
                SELECT l.id, l.book_id, l.student_id, l.issue_date, l.due_date,
                       b.title AS book_title,
                       s.name AS student_name, s.email AS student_email, s.student_id AS student_code
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN students s ON l.student_id = s.id
                WHERE l.status = 'ISSUED' AND l.due_date IS NOT NULL
                """
            ).fetchall()

            summary["active_loans_scanned"] = len(loans)

            for l in loans:
                loan_id = l["id"]
                due_d = datetime.strptime(l["due_date"][:10], "%Y-%m-%d").date()

                # CASE 1: OVERDUE
                if due_d < today:
                    days_od = (today - due_d).days
                    # Deduplication: Check if OVERDUE reminder was sent in the last 2 days
                    recent_od = conn.execute(
                        """
                        SELECT id FROM notifications
                        WHERE loan_id = ? AND reminder_type = 'OVERDUE'
                        AND date(sent_at) >= date('now', '-2 days')
                        """,
                        (loan_id,),
                    ).fetchone()

                    if recent_od:
                        summary["duplicates_skipped"] += 1
                        continue

                    subject = f"URGENT: Library Book Overdue - '{l['book_title']}'"
                    msg_body = (
                        f"Dear {l['student_name']},\n\n"
                        f"This is an urgent notice that '{l['book_title']}' was due on {l['due_date']} and is now {days_od} day(s) overdue.\n"
                        f"Please return it immediately to the library circulation desk.\n\n"
                        f"Library Circulation Desk"
                    )

                    sent_ok, reason = send_email_via_smtp(l["student_email"], subject, msg_body)
                    status_flag = "SENT" if sent_ok else "QUEUED"

                    conn.execute(
                        """
                        INSERT INTO notifications (loan_id, student_id, reminder_type, recipient_email, subject, message, status, error_message)
                        VALUES (?, ?, 'OVERDUE', ?, ?, ?, ?, ?)
                        """,
                        (loan_id, l["student_id"], l["student_email"], subject, msg_body, status_flag, None if sent_ok else reason),
                    )
                    summary["overdue_reminders"] += 1
                    summary["details"].append(f"Overdue reminder for '{l['book_title']}' ({l['student_name']}) -> {status_flag}")

                # CASE 2: DUE SOON (e.g. due in 0 to reminder_days_before days)
                elif today <= due_d <= due_threshold:
                    days_left = (due_d - today).days
                    # Deduplication: Check if DUE_SOON reminder was already sent for this loan
                    already_sent = conn.execute(
                        "SELECT id FROM notifications WHERE loan_id = ? AND reminder_type = 'DUE_SOON'",
                        (loan_id,),
                    ).fetchone()

                    if already_sent:
                        summary["duplicates_skipped"] += 1
                        continue

                    subject = f"Friendly Reminder: '{l['book_title']}' due in {days_left} day(s)"
                    msg_body = (
                        f"Dear {l['student_name']},\n\n"
                        f"This is a friendly reminder that '{l['book_title']}' is scheduled for return on {l['due_date']} ({days_left} day(s) remaining).\n"
                        f"You may return it at the circulation desk.\n\n"
                        f"Library Circulation Desk"
                    )

                    sent_ok, reason = send_email_via_smtp(l["student_email"], subject, msg_body)
                    status_flag = "SENT" if sent_ok else "QUEUED"

                    conn.execute(
                        """
                        INSERT INTO notifications (loan_id, student_id, reminder_type, recipient_email, subject, message, status, error_message)
                        VALUES (?, ?, 'DUE_SOON', ?, ?, ?, ?, ?)
                        """,
                        (loan_id, l["student_id"], l["student_email"], subject, msg_body, status_flag, None if sent_ok else reason),
                    )
                    summary["due_soon_reminders"] += 1
                    summary["details"].append(f"Upcoming due reminder for '{l['book_title']}' ({l['student_name']}) -> {status_flag}")

        return summary
    finally:
        conn.close()


def send_manual_reminder(loan_id: int, db_file: Optional[Path] = None) -> Tuple[bool, str]:
    """Manually trigger a reminder for a specific active loan."""
    conn = get_connection(db_file)
    try:
        with conn:
            loan = conn.execute(
                """
                SELECT l.id, l.student_id, l.due_date,
                       b.title AS book_title,
                       s.name AS student_name, s.email AS student_email
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN students s ON l.student_id = s.id
                WHERE l.id = ? AND l.status = 'ISSUED'
                """,
                (loan_id,),
            ).fetchone()

            if not loan:
                return False, "Active loan not found."

            subject = f"Library Notice: '{loan['book_title']}' Return Reminder"
            msg_body = (
                f"Dear {loan['student_name']},\n\n"
                f"This is an official library reminder regarding your loan of '{loan['book_title']}'. "
                f"Due Date: {loan['due_date']}.\nPlease ensure the book is returned on time."
            )

            sent_ok, reason = send_email_via_smtp(loan["student_email"], subject, msg_body)
            status_flag = "SENT" if sent_ok else "QUEUED"

            conn.execute(
                """
                INSERT INTO notifications (loan_id, student_id, reminder_type, recipient_email, subject, message, status, error_message)
                VALUES (?, ?, 'MANUAL', ?, ?, ?, ?, ?)
                """,
                (loan_id, loan["student_id"], loan["student_email"], subject, msg_body, status_flag, None if sent_ok else reason),
            )

        return True, f"Reminder logged ({status_flag}). {reason if not sent_ok else 'Delivered via SMTP.'}"
    except Exception as e:
        return False, f"Failed to send manual reminder: {e}"
    finally:
        conn.close()


def get_notifications(student_id_filter: Optional[int] = None, limit: int = 50, db_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve notification log records."""
    conn = get_connection(db_file)
    try:
        query = """
            SELECT n.id, n.loan_id, n.student_id, n.reminder_type, n.recipient_email,
                   n.subject, n.message, n.status, n.sent_at, n.error_message,
                   s.name AS student_name, s.student_id AS student_code
            FROM notifications n
            JOIN students s ON n.student_id = s.id
            WHERE 1=1
        """
        params: List[Any] = []
        if student_id_filter is not None:
            query += " AND n.student_id = ?"
            params.append(student_id_filter)

        query += " ORDER BY n.id DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


# ============================================================================
# Dashboard Statistics & Reports
# ============================================================================

def get_dashboard_stats(db_file: Optional[Path] = None) -> Dict[str, int]:
    """Retrieve accurate real-time dashboard counts."""
    today_str = date.today().isoformat()
    conn = get_connection(db_file)
    try:
        total_books = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()["c"]
        copies_row = conn.execute("SELECT COALESCE(SUM(total_copies), 0) AS tc, COALESCE(SUM(available_copies), 0) AS ac FROM books").fetchone()
        borrowed = conn.execute("SELECT COUNT(*) AS c FROM loans WHERE status = 'ISSUED'").fetchone()["c"]
        pending_req = conn.execute("SELECT COUNT(*) AS c FROM loans WHERE status = 'REQUESTED'").fetchone()["c"]
        total_students = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
        active_students = conn.execute("SELECT COUNT(*) AS c FROM students WHERE is_active = 1").fetchone()["c"]
        overdue = conn.execute("SELECT COUNT(*) AS c FROM loans WHERE status = 'ISSUED' AND due_date < ?", (today_str,)).fetchone()["c"]

        return {
            "total_books": total_books,
            "total_copies": copies_row["tc"],
            "available_copies": copies_row["ac"],
            "borrowed_copies": borrowed,
            "pending_requests": pending_req,
            "total_students": total_students,
            "active_students": active_students,
            "overdue_loans": overdue,
        }
    finally:
        conn.close()


def get_recent_activity(limit: int = 8, db_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve recent circulation activity feed."""
    conn = get_connection(db_file)
    try:
        cursor = conn.execute(
            """
            SELECT l.id, l.issue_date, l.due_date, l.return_date, l.request_date, l.status, l.created_at,
                   b.title AS book_title,
                   s.name AS student_name, s.student_id AS student_code
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN students s ON l.student_id = s.id
            ORDER BY l.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_circulation_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[str] = None,
    db_file: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve comprehensive borrowing records for export."""
    conn = get_connection(db_file)
    try:
        query = """
            SELECT l.id AS loan_id,
                   b.title AS book_title, b.author AS book_author, b.isbn, b.category,
                   s.name AS student_name, s.student_id AS student_code, s.email AS student_email,
                   l.request_date, l.issue_date, l.due_date, l.return_date, l.status
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN students s ON l.student_id = s.id
            WHERE 1=1
        """
        params: List[Any] = []

        if status_filter and status_filter != "All":
            query += " AND l.status = ?"
            params.append(status_filter)

        if start_date:
            query += " AND (l.issue_date >= ? OR l.request_date >= ?)"
            params.extend([start_date, start_date])

        if end_date:
            query += " AND (l.issue_date <= ? OR l.request_date <= ?)"
            params.extend([end_date, end_date])

        query += " ORDER BY l.id DESC"
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


# ============================================================================
# Starter Demo Data & Safe Reset
# ============================================================================

def seed_sample_data(db_file: Optional[Path] = None) -> Tuple[bool, str]:
    """Populates realistic demo catalog, students, and circulation records if database is empty."""
    init_db(db_file)
    conn = get_connection(db_file)
    try:
        c = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()["c"]
        if c > 0:
            return False, "Database already contains books. Seed skipped to preserve existing data."
    finally:
        conn.close()

    sample_books = [
        ("Introduction to Algorithms (4th Ed.)", "Thomas H. Cormen et al.", "978-0262046305", "Computer Science", 4),
        ("Clean Architecture: A Craftsman's Guide", "Robert C. Martin", "978-0134494166", "Software Engineering", 3),
        ("Operating System Concepts (10th Ed.)", "Abraham Silberschatz et al.", "978-1119800361", "Computer Science", 3),
        ("Artificial Intelligence: A Modern Approach", "Stuart Russell, Peter Norvig", "978-0134610993", "Artificial Intelligence", 2),
        ("Database System Concepts (7th Ed.)", "Silberschatz, Korth, Sudarshan", "978-0078022159", "Databases", 3),
        ("Discrete Mathematics & Its Applications", "Kenneth H. Rosen", "978-1259676512", "Mathematics", 3),
        ("Design Patterns in Python", "Gang of Four Authors", None, "Software Engineering", 2),  # No ISBN example
    ]

    for title, author, isbn, cat, copies in sample_books:
        add_book(title, author, isbn, cat, copies, db_file=db_file)

    sample_students = [
        ("STU-2024-001", "Aarav Sharma", "aarav.sharma@college.edu", "Student123!"),
        ("STU-2024-002", "Priya Patel", "priya.patel@college.edu", "Student123!"),
        ("STU-2024-003", "Rohan Mehta", "rohan.mehta@college.edu", "Student123!"),
        ("STU-2024-004", "Ananya Verma", "ananya.verma@college.edu", "Student123!"),
    ]

    for sid, name, email, pwd in sample_students:
        add_student(sid, name, email, password=pwd, db_file=db_file)

    books = get_all_books(db_file=db_file)
    students = get_all_students(db_file=db_file)

    if len(books) >= 3 and len(students) >= 3:
        today = date.today()
        # 1. Normal active loan
        issue_book(
            books[0]["id"],
            students[0]["id"],
            (today - timedelta(days=3)).isoformat(),
            (today + timedelta(days=11)).isoformat(),
            db_file=db_file,
        )

        # 2. Overdue loan
        issue_book(
            books[1]["id"],
            students[1]["id"],
            (today - timedelta(days=20)).isoformat(),
            (today - timedelta(days=6)).isoformat(),
            db_file=db_file,
        )

        # 3. Returned loan
        issue_book(
            books[2]["id"],
            students[2]["id"],
            (today - timedelta(days=30)).isoformat(),
            (today - timedelta(days=16)).isoformat(),
            db_file=db_file,
        )
        active_loans = get_active_loans(db_file=db_file)
        for l in active_loans:
            if l["book_id"] == books[2]["id"]:
                return_book(l["id"], (today - timedelta(days=12)).isoformat(), db_file=db_file)
                break

    return True, "Sample library records (books, students, and circulation data) added successfully!"


def reset_db(db_file: Optional[Path] = None) -> Tuple[bool, str]:
    """Wipes library circulation records and reinitializes fresh tables."""
    conn = get_connection(db_file)
    try:
        with conn:
            conn.execute("DELETE FROM notifications;")
            conn.execute("DELETE FROM loans;")
            conn.execute("DELETE FROM books;")
            conn.execute("DELETE FROM students;")
        return True, "All catalog, student, and loan records cleared."
    except Exception as e:
        return False, f"Failed to reset: {e}"
    finally:
        conn.close()
