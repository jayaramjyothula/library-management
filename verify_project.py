"""
verify_project.py - Comprehensive verification script for Library Management System.
Tests:
- Database initialization and idempotency
- Book management (CRUD, validations, constraints, safe delete)
- Student management (registration, duplicate prevention, email format)
- Issue book (stock decrement, date validation, duplicate active loan guard)
- Return book (stock increment, double return prevention)
- Overdue tracking (dynamic calculation, isolation of returned books)
- Dashboard statistics accuracy
"""

import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
import database as db


def run_checks():
    temp_dir = tempfile.mkdtemp()
    test_db = Path(temp_dir) / "test_library.db"
    print(f"[*] Running verification on isolated database: {test_db}")

    # =========================================================================
    # Step 1: Database Initialization
    # =========================================================================
    print("\n--- 1. Testing Database Initialization ---")
    db.init_db(test_db)
    conn = db.get_connection(test_db)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]
    print(f"[+] Tables created: {sorted(tables)}")
    assert all(t in tables for t in ["books", "loans", "students"]), f"Required tables missing: {tables}"

    # Verify idempotence
    db.init_db(test_db)
    print("[+] Idempotency check passed (init_db can run multiple times safely)")

    # Verify Foreign Keys enabled
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1, "Foreign key support is not enabled!"
    print(f"[+] Foreign keys PRAGMA verified: {fk}")
    conn.close()

    # Verify empty dashboard stats
    empty_stats = db.get_dashboard_stats(test_db)
    assert empty_stats["total_books"] == 0
    assert empty_stats["total_copies"] == 0
    assert empty_stats["available_copies"] == 0
    assert empty_stats["borrowed_copies"] == 0
    assert empty_stats["total_students"] == 0
    assert empty_stats["overdue_loans"] == 0
    print("[+] Empty database dashboard statistics handled gracefully: all zeros")

    # =========================================================================
    # Step 2: Book Management
    # =========================================================================
    print("\n--- 2. Testing Book Management ---")
    # Add valid books
    ok, msg = db.add_book("Book A", "Author One", "ISBN-001", "Computer Science", 3, test_db)
    assert ok, f"Failed to add Book A: {msg}"
    print(f"[+] Added Book A: {msg}")

    ok, msg = db.add_book("Book B", "Author Two", "ISBN-002", "Mathematics", 2, test_db)
    assert ok, f"Failed to add Book B: {msg}"
    print(f"[+] Added Book B: {msg}")

    # Validation: Duplicate ISBN
    ok, msg = db.add_book("Book A Dup", "Author One", "ISBN-001", "Computer Science", 1, test_db)
    assert not ok and "already exists" in msg, f"Duplicate ISBN was not rejected! {msg}"
    print("[+] Duplicate ISBN correctly rejected")

    # Validation: Invalid copy count (0 copies)
    ok, msg = db.add_book("Invalid Copies", "Author", "ISBN-003", "Tech", 0, test_db)
    assert not ok and "at least 1" in msg, f"0 copies was not rejected! {msg}"
    print("[+] Invalid copy count (< 1) correctly rejected")

    # Validation: Empty required fields
    ok, msg = db.add_book("   ", "Author", "ISBN-004", "Tech", 1, test_db)
    assert not ok and "empty" in msg, f"Empty title was not rejected! {msg}"
    print("[+] Empty required field (title) correctly rejected")

    # Search functionality
    search_res = db.get_all_books("Book A", db_file=test_db)
    assert len(search_res) == 1 and search_res[0]["isbn"] == "ISBN-001"
    print(f"[+] Search by title returned 1 match: {search_res[0]['title']}")

    search_isbn = db.get_all_books("ISBN-002", db_file=test_db)
    assert len(search_isbn) == 1 and search_isbn[0]["title"] == "Book B"
    print(f"[+] Search by ISBN returned 1 match: {search_isbn[0]['title']}")

    # Category filter
    cat_res = db.get_all_books(category_filter="Mathematics", db_file=test_db)
    assert len(cat_res) == 1 and cat_res[0]["title"] == "Book B"
    print(f"[+] Category filter returned 1 match: {cat_res[0]['title']}")

    # =========================================================================
    # Step 3: Student Management
    # =========================================================================
    print("\n--- 3. Testing Student Management ---")
    # Add valid students
    ok, msg = db.add_student("STU-101", "Student Alpha", "alpha@college.edu", test_db)
    assert ok, f"Failed to add student: {msg}"
    print(f"[+] Registered student STU-101: {msg}")

    ok, msg = db.add_student("STU-102", "Student Beta", "beta@college.edu", test_db)
    assert ok, f"Failed to add student: {msg}"
    print(f"[+] Registered student STU-102: {msg}")

    # Duplicate Student ID prevention
    ok, msg = db.add_student("STU-101", "Duplicate Person", "dup@college.edu", test_db)
    assert not ok and "already registered" in msg, f"Duplicate student ID was not rejected! {msg}"
    print("[+] Duplicate student ID correctly rejected")

    # Invalid email format
    ok, msg = db.add_student("STU-103", "Invalid Email", "notanemail", test_db)
    assert not ok and "not a valid email" in msg, f"Invalid email was not rejected! {msg}"
    print("[+] Invalid email address format correctly rejected")

    # Search students
    found_stu = db.get_all_students("Alpha", test_db)
    assert len(found_stu) == 1 and found_stu[0]["student_id"] == "STU-101"
    print(f"[+] Student search returned 1 match: {found_stu[0]['name']}")

    # =========================================================================
    # Step 4: Issue Books
    # =========================================================================
    print("\n--- 4. Testing Book Issuing ---")
    book_b = db.get_all_books("Book B", db_file=test_db)[0]
    stu_1 = db.get_all_students("STU-101", db_file=test_db)[0]
    stu_2 = db.get_all_students("STU-102", db_file=test_db)[0]

    today_str = date.today().isoformat()
    due_str = (date.today() + timedelta(days=14)).isoformat()
    invalid_past_due = (date.today() - timedelta(days=2)).isoformat()

    # Invalid date check (due date earlier than issue date)
    ok, msg = db.issue_book(book_b["id"], stu_1["id"], today_str, invalid_past_due, test_db)
    assert not ok and "earlier than issue date" in msg, f"Invalid date logic was not rejected! {msg}"
    print("[+] Invalid date range (due < issue) correctly rejected")

    # Issue Copy 1 of Book B to Student Alpha
    ok, msg = db.issue_book(book_b["id"], stu_1["id"], today_str, due_str, test_db)
    assert ok, f"Failed to issue book: {msg}"
    print(f"[+] Issued Book B copy 1: {msg}")

    # Verify inventory decremented
    b_updated = db.get_book_by_id(book_b["id"], test_db)
    assert b_updated["available_copies"] == 1, f"Available copies mismatch: {b_updated['available_copies']}"
    print(f"[+] Available copies decremented: {b_updated['available_copies']}/{b_updated['total_copies']}")

    # Duplicate active loan prevention: Try issuing same book to Student Alpha again
    ok, msg = db.issue_book(book_b["id"], stu_1["id"], today_str, due_str, test_db)
    assert not ok and "already has an active loan" in msg, f"Duplicate loan was not rejected! {msg}"
    print("[+] Duplicate active loan for same student and book correctly rejected")

    # Issue Copy 2 of Book B to Student Beta
    ok, msg = db.issue_book(book_b["id"], stu_2["id"], today_str, due_str, test_db)
    assert ok, f"Failed to issue copy 2: {msg}"
    print(f"[+] Issued Book B copy 2: {msg}")

    b_updated2 = db.get_book_by_id(book_b["id"], test_db)
    assert b_updated2["available_copies"] == 0, f"Available copies should be 0, got {b_updated2['available_copies']}"
    print(f"[+] Available copies now 0: {b_updated2['available_copies']}/{b_updated2['total_copies']}")

    # Prevent issuing when 0 copies available
    ok, msg = db.add_student("STU-104", "Gamma", "gamma@college.edu", test_db)
    stu_3 = db.get_all_students("STU-104", db_file=test_db)[0]
    ok, msg = db.issue_book(book_b["id"], stu_3["id"], today_str, due_str, test_db)
    assert not ok and "No available copies" in msg, f"Issued when 0 copies available! {msg}"
    print("[+] Zero available copies barrier correctly enforced")

    # =========================================================================
    # Step 5: Book Deletion & Update Restrictions
    # =========================================================================
    print("\n--- 5. Testing Book Edit & Delete Safeguards ---")
    # Deletion blocked because Book B has 2 active loans
    ok, msg = db.delete_book(book_b["id"], test_db)
    assert not ok and "active loan(s)" in msg, f"Deleted book with active loans! {msg}"
    print("[+] Delete book blocked while active loans exist")

    # Update total copies cannot be reduced below active loans (2 borrowed)
    ok, msg = db.update_book(book_b["id"], book_b["title"], book_b["author"], book_b["isbn"], book_b["category"], 1, test_db)
    assert not ok and "actively borrowed" in msg, f"Allowed reducing copies below active loans! {msg}"
    print("[+] Reducing total copies below active loans correctly rejected")

    # =========================================================================
    # Step 6: Return Books
    # =========================================================================
    print("\n--- 6. Testing Book Returns ---")
    active_loans = db.get_active_loans(db_file=test_db)
    assert len(active_loans) == 2, f"Expected 2 active loans, got {len(active_loans)}"
    loan_to_return = active_loans[0]

    # Return book
    ok, msg = db.return_book(loan_to_return["id"], today_str, test_db)
    assert ok, f"Return failed: {msg}"
    print(f"[+] Book return processed: {msg}")

    # Check inventory incremented
    b_after_ret = db.get_book_by_id(book_b["id"], test_db)
    assert b_after_ret["available_copies"] == 1, f"Expected 1 available copy, got {b_after_ret['available_copies']}"
    print(f"[+] Available copies restored: {b_after_ret['available_copies']}/{b_after_ret['total_copies']}")

    # Prevent double return
    ok, msg = db.return_book(loan_to_return["id"], today_str, test_db)
    assert not ok and "already marked as RETURNED" in msg, f"Double return was not rejected! {msg}"
    print("[+] Double return attempt correctly rejected")

    # =========================================================================
    # Step 7: Overdue Tracking
    # =========================================================================
    print("\n--- 7. Testing Overdue Tracking ---")
    # Add a book and an overdue loan (due date in the past)
    db.add_book("Overdue Title", "Author X", "ISBN-OD-99", "Literature", 2, test_db)
    od_book = db.get_all_books("ISBN-OD-99", db_file=test_db)[0]
    past_issue = (date.today() - timedelta(days=25)).isoformat()
    past_due = (date.today() - timedelta(days=7)).isoformat()

    db.issue_book(od_book["id"], stu_3["id"], past_issue, past_due, test_db)

    # Check overdue loans
    overdue_list = db.get_overdue_loans(db_file=test_db)
    assert len(overdue_list) == 1, f"Expected 1 overdue loan, got {len(overdue_list)}"
    od_item = overdue_list[0]
    assert od_item["is_overdue"] is True
    assert od_item["days_overdue"] == 7, f"Expected 7 days overdue, got {od_item['days_overdue']}"
    print(f"[+] Overdue loan identified: {od_item['book_title']} - {od_item['days_overdue']} days overdue")

    # Verify that returning the overdue loan removes it from overdue list
    ok, msg = db.return_book(od_item["id"], today_str, test_db)
    assert ok
    overdue_after = db.get_overdue_loans(db_file=test_db)
    assert len(overdue_after) == 0, f"Returned loan is still listed as overdue! {overdue_after}"
    print("[+] Returned loan immediately removed from overdue list (never treated as overdue)")

    # =========================================================================
    # Step 8: Dashboard Accuracy
    # =========================================================================
    print("\n--- 8. Testing Real-time Dashboard Aggregations ---")
    stats = db.get_dashboard_stats(test_db)
    # Expected: 3 books (Book A: 3, Book B: 2, Overdue Title: 2) -> total_books = 3, total_copies = 7
    # Loans: Book B has 1 active loan (stu_2). Available copies = 3 (Book A) + 1 (Book B) + 2 (Overdue Title) = 6
    # Borrowed copies = 1.
    # Total students = 3 (Alpha, Beta, Gamma).
    # Overdue loans = 0.
    print(f"[+] Computed Dashboard Stats: {stats}")
    assert stats["total_books"] == 3
    assert stats["total_copies"] == 7
    assert stats["available_copies"] == 6
    assert stats["borrowed_copies"] == 1
    assert stats["total_students"] == 3
    assert stats["overdue_loans"] == 0
    print("[+] All dashboard metrics match actual database records with 100% precision")

    # Cleanup test DB
    try:
        os.remove(test_db)
        os.rmdir(temp_dir)
    except Exception:
        pass

    print("\n=======================================================")
    print(" ALL VERIFICATION CHECKS PASSED WITH 100% SUCCESS! ")
    print("=======================================================\n")


if __name__ == "__main__":
    run_checks()
