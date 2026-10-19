"""
test_live_features.py - Systematically tests the exact 7 features required by the user:
1. Dashboard statistics
2. Add, search, edit, and delete books
3. Register and search students
4. Issue books
5. Return books
6. Overdue book tracking
7. Database persistence across page reloads / restarts
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
import database as db

def test_features():
    print("=======================================================")
    print(" STEP 5: COMPREHENSIVE FEATURE-BY-FEATURE VERIFICATION ")
    print("=======================================================")

    # Ensure schema is initialized
    db.init_db()

    # -----------------------------------------------------------------
    # Feature 1: Dashboard Statistics
    # -----------------------------------------------------------------
    print("\n[1/7] Testing Dashboard Statistics...")
    stats_before = db.get_dashboard_stats()
    assert isinstance(stats_before, dict)
    required_keys = ["total_books", "total_copies", "available_copies", "borrowed_copies", "total_students", "overdue_loans"]
    for k in required_keys:
        assert k in stats_before, f"Missing key: {k}"
        assert isinstance(stats_before[k], int)
    print(f" -> Current Live Dashboard Metrics: {stats_before}")
    print(" -> Feature 1 [Dashboard statistics]: PASSED")

    # -----------------------------------------------------------------
    # Feature 2: Add, search, edit, and delete books
    # -----------------------------------------------------------------
    print("\n[2/7] Testing Book Management (Add, Search, Edit, Delete)...")
    test_isbn = f"TEST-ISBN-{date.today().strftime('%Y%m%d%H%M%S')}"
    # Add
    ok, msg = db.add_book("Test Automation Guide", "QA Lead", test_isbn, "Quality Assurance", 4)
    assert ok, f"Failed to add book: {msg}"
    print(f" -> Add Book: SUCCESS ({msg})")

    # Search
    search_books = db.get_all_books(search_query="Test Automation Guide")
    assert len(search_books) >= 1, "Search by title failed"
    book_id = [b["id"] for b in search_books if b["isbn"] == test_isbn][0]
    print(f" -> Search Book: SUCCESS (Found book ID {book_id})")

    # Edit
    ok, msg = db.update_book(book_id, "Test Automation Handbook", "QA Lead", test_isbn, "Quality Assurance", 5)
    assert ok, f"Failed to edit book: {msg}"
    edited_book = db.get_book_by_id(book_id)
    assert edited_book["title"] == "Test Automation Handbook"
    assert edited_book["total_copies"] == 5
    print(f" -> Edit Book: SUCCESS (Updated title to '{edited_book['title']}', copies to {edited_book['total_copies']})")

    # Delete
    ok, msg = db.delete_book(book_id)
    assert ok, f"Failed to delete book: {msg}"
    assert db.get_book_by_id(book_id) is None, "Book still found after deletion"
    print(f" -> Delete Book: SUCCESS ({msg})")
    print(" -> Feature 2 [Add, search, edit, delete books]: PASSED")

    # -----------------------------------------------------------------
    # Feature 3: Register and search students
    # -----------------------------------------------------------------
    print("\n[3/7] Testing Student Management (Register & Search)...")
    test_stu_id = f"STU-LIVE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    # Register
    ok, msg = db.add_student(test_stu_id, "Automation Tester", f"{test_stu_id.lower()}@college.edu")
    assert ok, f"Failed to register student: {msg}"
    print(f" -> Register Student: SUCCESS ({msg})")

    # Duplicate rejection
    ok, msg = db.add_student(test_stu_id, "Duplicate Student", "dup@college.edu")
    assert not ok and "already registered" in msg, "Failed to prevent duplicate student ID"
    print(" -> Prevent Duplicate Student ID: SUCCESS")

    # Search
    search_stu = db.get_all_students(search_query=test_stu_id)
    assert len(search_stu) == 1, "Student search failed"
    stu_pk = search_stu[0]["id"]
    print(f" -> Search Student: SUCCESS (Found student PK {stu_pk})")
    print(" -> Feature 3 [Register and search students]: PASSED")

    # -----------------------------------------------------------------
    # Feature 4: Issue books
    # -----------------------------------------------------------------
    print("\n[4/7] Testing Issue Books...")
    # Add a temporary book to issue
    loan_isbn = f"LOAN-ISBN-{date.today().strftime('%H%M%S')}"
    db.add_book("Live Borrowing Demo", "Circulation Author", loan_isbn, "Circulation", 2)
    loan_book = [b for b in db.get_all_books(loan_isbn) if b["isbn"] == loan_isbn][0]
    loan_b_id = loan_book["id"]

    today = date.today().isoformat()
    due_date = (date.today() + timedelta(days=14)).isoformat()

    ok, msg = db.issue_book(loan_b_id, stu_pk, today, due_date)
    assert ok, f"Failed to issue book: {msg}"
    print(f" -> Issue Book: SUCCESS ({msg})")

    # Verify inventory decremented
    book_after_issue = db.get_book_by_id(loan_b_id)
    assert book_after_issue["available_copies"] == 1
    print(f" -> Availability Decremented: {book_after_issue['available_copies']}/{book_after_issue['total_copies']}")

    # Prevent duplicate active loan
    ok, msg = db.issue_book(loan_b_id, stu_pk, today, due_date)
    assert not ok and "already has an active loan" in msg
    print(" -> Prevent Duplicate Active Loan for Same Student & Book: SUCCESS")
    print(" -> Feature 4 [Issue books]: PASSED")

    # -----------------------------------------------------------------
    # Feature 5: Return books
    # -----------------------------------------------------------------
    print("\n[5/7] Testing Return Books...")
    active_loans = [l for l in db.get_active_loans() if l["book_id"] == loan_b_id and l["student_pk"] == stu_pk]
    assert len(active_loans) == 1, "Expected 1 active loan"
    target_loan_id = active_loans[0]["id"]

    ok, msg = db.return_book(target_loan_id, today)
    assert ok, f"Failed to return book: {msg}"
    print(f" -> Return Book: SUCCESS ({msg})")

    # Verify inventory restored
    book_after_return = db.get_book_by_id(loan_b_id)
    assert book_after_return["available_copies"] == 2
    print(f" -> Availability Restored: {book_after_return['available_copies']}/{book_after_return['total_copies']}")

    # Prevent double return
    ok, msg = db.return_book(target_loan_id, today)
    assert not ok and "already marked as RETURNED" in msg
    print(" -> Prevent Double Return: SUCCESS")
    print(" -> Feature 5 [Return books]: PASSED")

    # -----------------------------------------------------------------
    # Feature 6: Overdue Book Tracking
    # -----------------------------------------------------------------
    print("\n[6/7] Testing Overdue Tracking...")
    past_issue = (date.today() - timedelta(days=20)).isoformat()
    past_due = (date.today() - timedelta(days=5)).isoformat()

    # Issue an overdue loan
    ok, msg = db.issue_book(loan_b_id, stu_pk, past_issue, past_due)
    assert ok
    overdue_loans = [l for l in db.get_overdue_loans() if l["book_id"] == loan_b_id and l["student_pk"] == stu_pk]
    assert len(overdue_loans) == 1, "Overdue loan not detected"
    assert overdue_loans[0]["is_overdue"] is True
    assert overdue_loans[0]["days_overdue"] == 5
    print(f" -> Overdue Loan Correctly Flagged: {overdue_loans[0]['days_overdue']} days overdue")

    # Return the overdue book and ensure it leaves the overdue list
    od_loan_id = overdue_loans[0]["id"]
    ok, msg = db.return_book(od_loan_id, today)
    assert ok
    overdue_after = [l for l in db.get_overdue_loans() if l["id"] == od_loan_id]
    assert len(overdue_after) == 0, "Returned book still listed as overdue"
    print(" -> Returned Book Removed From Overdue Tracker: SUCCESS")
    print(" -> Feature 6 [Overdue book tracking]: PASSED")

    # Clean up demo book
    db.delete_book(loan_b_id)

    # -----------------------------------------------------------------
    # Feature 7: Database Persistence After Refreshing
    # -----------------------------------------------------------------
    print("\n[7/7] Testing Database Persistence...")
    # Add a persistent marker book
    marker_isbn = f"PERSIST-ISBN-{date.today().strftime('%H%M%S')}"
    db.add_book("Persistence Verification Record", "Database Architect", marker_isbn, "Architecture", 3)

    # Simulate fresh connection / reload
    conn2 = db.get_connection()
    cursor = conn2.cursor()
    row = cursor.execute("SELECT id, title, isbn, total_copies FROM books WHERE isbn = ?", (marker_isbn,)).fetchone()
    assert row is not None, "Marker book not found after closing and reopening connection!"
    assert row["title"] == "Persistence Verification Record"
    assert row["total_copies"] == 3
    conn2.close()
    print(" -> Record Retrieved After Connection Reset: SUCCESS (Data safely persisted in library.db)")

    # Clean up marker book
    db.delete_book(row["id"])
    print(" -> Feature 7 [Database persistence]: PASSED")

    print("\n=======================================================")
    print(" ALL 7 REQUIRED FEATURES TESTED AND WORKING 100%! ")
    print("=======================================================\n")

if __name__ == "__main__":
    test_features()
