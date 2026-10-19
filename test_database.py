"""
Unit & Integration tests for database.py
Validates all requirements, edge cases, and transaction handling.
"""

import os
import unittest
from datetime import date, timedelta
from pathlib import Path
import tempfile

import database as db


class TestLibraryDatabase(unittest.TestCase):
    def setUp(self):
        # Use an isolated temporary database for each test
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_file.name)
        self.temp_file.close()
        db.init_db(self.db_path)

    def tearDown(self):
        if self.db_path.exists():
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_empty_database_dashboard_stats(self):
        """Dashboard stats on fresh empty database should return zeros without failing."""
        stats = db.get_dashboard_stats(self.db_path)
        self.assertEqual(stats["total_books"], 0)
        self.assertEqual(stats["total_copies"], 0)
        self.assertEqual(stats["available_copies"], 0)
        self.assertEqual(stats["borrowed_copies"], 0)
        self.assertEqual(stats["total_students"], 0)
        self.assertEqual(stats["overdue_loans"], 0)

        # Empty lists
        self.assertEqual(db.get_all_books(db_file=self.db_path), [])
        self.assertEqual(db.get_all_students(db_file=self.db_path), [])
        self.assertEqual(db.get_loans(db_file=self.db_path), [])
        self.assertEqual(db.get_overdue_loans(db_file=self.db_path), [])
        self.assertEqual(db.get_recent_activity(db_file=self.db_path), [])

    def test_add_book_and_constraints(self):
        """Test adding books, validating constraints, and duplicate ISBN detection."""
        # Valid book
        ok, msg = db.add_book("Clean Code", "Robert C. Martin", "978-0132350884", "Computer Science", 3, self.db_path)
        self.assertTrue(ok)

        # Duplicate ISBN must fail
        ok, msg = db.add_book("Another Clean Code", "Someone Else", "978-0132350884", "Tech", 1, self.db_path)
        self.assertFalse(ok)
        self.assertIn("already exists", msg)

        # Invalid copy count (0 or negative)
        ok, msg = db.add_book("Bad Copy Book", "Author", "ISBN-111", "Fiction", 0, self.db_path)
        self.assertFalse(ok)
        self.assertIn("at least 1", msg)

        # Empty required fields
        ok, msg = db.add_book("", "Author", "ISBN-222", "Fiction", 1, self.db_path)
        self.assertFalse(ok)

    def test_student_registration_and_constraints(self):
        """Test student registration and duplicate student ID prevention."""
        # Valid student
        ok, msg = db.add_student("CS2026-001", "Alice Smith", "alice@college.edu", self.db_path)
        self.assertTrue(ok)

        # Duplicate student ID must fail
        ok, msg = db.add_student("CS2026-001", "Bob Johnson", "bob@college.edu", self.db_path)
        self.assertFalse(ok)
        self.assertIn("already registered", msg)

        # Invalid email format
        ok, msg = db.add_student("CS2026-002", "Charlie", "not-an-email", self.db_path)
        self.assertFalse(ok)
        self.assertIn("not a valid email", msg)

    def test_issue_book_and_return_lifecycle(self):
        """Test complete loan lifecycle: issue, inventory decrement, return, double return prevention."""
        # Seed 1 book with 1 copy, and 2 students
        db.add_book("The Pragmatic Programmer", "David Thomas", "978-0135957059", "Tech", 1, self.db_path)
        db.add_student("STU-1", "John Doe", "john@college.edu", self.db_path)
        db.add_student("STU-2", "Jane Roe", "jane@college.edu", self.db_path)

        book = db.get_all_books(db_file=self.db_path)[0]
        stu1 = db.get_all_students(db_file=self.db_path)[0]
        stu2 = db.get_all_students(db_file=self.db_path)[1]

        today = date.today().isoformat()
        future_due = (date.today() + timedelta(days=14)).isoformat()

        # 1. Successful issue
        ok, msg = db.issue_book(book["id"], stu1["id"], today, future_due, self.db_path)
        self.assertTrue(ok)

        # Available copies should now be 0
        updated_book = db.get_book_by_id(book["id"], self.db_path)
        self.assertEqual(updated_book["available_copies"], 0)

        # 2. Try to issue the same book to stu2 when 0 copies available -> must fail
        ok, msg = db.issue_book(book["id"], stu2["id"], today, future_due, self.db_path)
        self.assertFalse(ok)
        self.assertIn("No available copies", msg)

        # 3. Duplicate active loan prevention: Try to issue to stu1 again -> must fail
        ok, msg = db.issue_book(book["id"], stu1["id"], today, future_due, self.db_path)
        self.assertFalse(ok)

        # 4. Return the book
        loans = db.get_active_loans(db_file=self.db_path)
        self.assertEqual(len(loans), 1)
        loan_id = loans[0]["id"]

        ok, msg = db.return_book(loan_id, today, self.db_path)
        self.assertTrue(ok)

        # Check copies restored
        updated_book = db.get_book_by_id(book["id"], self.db_path)
        self.assertEqual(updated_book["available_copies"], 1)

        # 5. Try to return again (double return prevention) -> must fail
        ok, msg = db.return_book(loan_id, today, self.db_path)
        self.assertFalse(ok)
        self.assertIn("already marked as RETURNED", msg)

    def test_overdue_calculation(self):
        """Active loans past due date are overdue; returned loans are never overdue."""
        db.add_book("Design Patterns", "GoF", "978-0201633610", "Tech", 2, self.db_path)
        db.add_student("STU-100", "David", "david@college.edu", self.db_path)
        db.add_student("STU-200", "Emma", "emma@college.edu", self.db_path)

        book = db.get_all_books(db_file=self.db_path)[0]
        david = db.get_all_students(db_file=self.db_path)[0]
        emma = db.get_all_students(db_file=self.db_path)[1]

        past_issue = (date.today() - timedelta(days=20)).isoformat()
        past_due = (date.today() - timedelta(days=5)).isoformat()
        today = date.today().isoformat()

        # Issue 1: Overdue active loan to David
        db.issue_book(book["id"], david["id"], past_issue, past_due, self.db_path)

        # Issue 2: Overdue loan to Emma, but Emma returns it today
        db.issue_book(book["id"], emma["id"], past_issue, past_due, self.db_path)
        emma_loan = [l for l in db.get_active_loans(db_file=self.db_path) if l["student_pk"] == emma["id"]][0]
        db.return_book(emma_loan["id"], today, self.db_path)

        # Check overdue loans
        overdue_loans = db.get_overdue_loans(db_file=self.db_path)
        self.assertEqual(len(overdue_loans), 1)
        self.assertEqual(overdue_loans[0]["student_code"], "STU-100")
        self.assertTrue(overdue_loans[0]["is_overdue"])
        self.assertEqual(overdue_loans[0]["days_overdue"], 5)

        # Check dashboard stats reflect exactly 1 overdue loan
        stats = db.get_dashboard_stats(self.db_path)
        self.assertEqual(stats["overdue_loans"], 1)

    def test_delete_book_restrictions(self):
        """Books with active loans cannot be deleted; books with no active loans can be deleted."""
        db.add_book("Refactoring", "Martin Fowler", "978-0201485677", "Tech", 2, self.db_path)
        db.add_student("STU-300", "Frank", "frank@college.edu", self.db_path)

        book = db.get_all_books(db_file=self.db_path)[0]
        frank = db.get_all_students(db_file=self.db_path)[0]

        # Issue book
        today = date.today().isoformat()
        db.issue_book(book["id"], frank["id"], today, today, self.db_path)

        # Attempt to delete book with active loan -> MUST FAIL
        ok, msg = db.delete_book(book["id"], self.db_path)
        self.assertFalse(ok)
        self.assertIn("active loan(s)", msg)

        # Return the loan
        loan = db.get_active_loans(db_file=self.db_path)[0]
        db.return_book(loan["id"], today, self.db_path)

        # Now attempt to delete book -> MUST SUCCEED
        ok, msg = db.delete_book(book["id"], self.db_path)
        self.assertTrue(ok)
        self.assertIsNone(db.get_book_by_id(book["id"], self.db_path))

    def test_update_book_copy_limits(self):
        """Cannot reduce total copies below active loans."""
        db.add_book("Algorithms", "Robert Sedgewick", "978-0321573513", "Algorithms", 3, self.db_path)
        db.add_student("STU-401", "Grace", "grace@college.edu", self.db_path)
        db.add_student("STU-402", "Hank", "hank@college.edu", self.db_path)

        book = db.get_all_books(db_file=self.db_path)[0]
        grace = db.get_all_students(db_file=self.db_path)[0]
        hank = db.get_all_students(db_file=self.db_path)[1]

        today = date.today().isoformat()
        db.issue_book(book["id"], grace["id"], today, today, self.db_path)
        db.issue_book(book["id"], hank["id"], today, today, self.db_path)

        # 2 copies are currently borrowed. Reducing total copies to 1 must fail!
        ok, msg = db.update_book(book["id"], book["title"], book["author"], book["isbn"], book["category"], 1, self.db_path)
        self.assertFalse(ok)
        self.assertIn("actively borrowed", msg)

        # Setting total copies to 2 is valid (available becomes 0)
        ok, msg = db.update_book(book["id"], book["title"], book["author"], book["isbn"], book["category"], 2, self.db_path)
        self.assertTrue(ok)
        updated = db.get_book_by_id(book["id"], self.db_path)
        self.assertEqual(updated["total_copies"], 2)
        self.assertEqual(updated["available_copies"], 0)


if __name__ == "__main__":
    unittest.main()
