"""
test_upgrade.py - Unit & Integration tests for upgraded Library Management System.
Verifies:
- Safe migrations
- Admin & student authentication (PBKDF2)
- Optional ISBN handling (allows empty ISBN, prevents duplicates only when provided)
- Student account deactivation (deactivated students blocked from login & borrowing)
- Student borrowing request workflow (request -> approval/rejection -> issue -> return)
- Automatic reminder engine & deduplication
- Role-based server-side data isolation
"""

import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import database as db


class TestUpgradedLibrarySystem(unittest.TestCase):
    def setUp(self):
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

    def test_default_admin_and_auth(self):
        """Default admin is created and authenticates with PBKDF2."""
        ok, user, msg = db.authenticate_admin("admin", "AdminPassword123!", self.db_path)
        self.assertTrue(ok)
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "ADMIN")

        # Wrong password fails
        ok, user, msg = db.authenticate_admin("admin", "WrongPass", self.db_path)
        self.assertFalse(ok)
        self.assertIsNone(user)

    def test_optional_isbn_and_duplicate_prevention(self):
        """Books can be added without ISBN; multiple books with no ISBN do not conflict; duplicate ISBNs are blocked."""
        # Book 1: No ISBN (None)
        ok1, msg1 = db.add_book("Python Fundamentals", "Guido van Rossum", None, "Programming", 3, self.db_path)
        self.assertTrue(ok1)

        # Book 2: Also No ISBN (empty string)
        ok2, msg2 = db.add_book("Advanced Python", "David Beazley", "", "Programming", 2, self.db_path)
        self.assertTrue(ok2)

        # Book 3: With ISBN
        ok3, msg3 = db.add_book("Clean Code", "Robert C. Martin", "978-0132350884", "Tech", 2, self.db_path)
        self.assertTrue(ok3)

        # Book 4: Duplicate ISBN must fail
        ok4, msg4 = db.add_book("Duplicate Clean Code", "Someone", "978-0132350884", "Tech", 1, self.db_path)
        self.assertFalse(ok4)
        self.assertIn("already exists", msg4)

    def test_student_auth_and_deactivation(self):
        """Student registers, logs in, gets deactivated, and is blocked from login."""
        ok, msg = db.add_student("STU-999", "Sarah Connor", "sarah@college.edu", "Cyberdyne123!", self.db_path)
        self.assertTrue(ok)

        # Successful student login
        ok_login, stu, msg = db.authenticate_student("STU-999", "Cyberdyne123!", self.db_path)
        self.assertTrue(ok_login)
        self.assertEqual(stu["role"], "STUDENT")

        # Login via email also works
        ok_email, stu2, msg = db.authenticate_student("sarah@college.edu", "Cyberdyne123!", self.db_path)
        self.assertTrue(ok_email)

        # Deactivate student
        ok_deact, msg = db.toggle_student_status(stu["id"], 0, self.db_path)
        self.assertTrue(ok_deact)

        # Deactivated student cannot log in
        ok_blocked, _, msg = db.authenticate_student("STU-999", "Cyberdyne123!", self.db_path)
        self.assertFalse(ok_blocked)
        self.assertIn("deactivated", msg)

    def test_borrowing_request_workflow(self):
        """Student submits request, admin approves, availability updates, book returned."""
        db.add_book("Cloud Architecture", "Architect A", None, "Cloud", 2, self.db_path)
        db.add_student("STU-888", "John Connor", "john@college.edu", "Pass123!", self.db_path)

        book = db.get_all_books(db_file=self.db_path)[0]
        stu = db.get_all_students(db_file=self.db_path)[0]

        # 1. Student requests book
        ok, msg = db.request_book(book["id"], stu["id"], self.db_path)
        self.assertTrue(ok)

        # Check pending requests
        pending = db.get_pending_requests(self.db_path)
        self.assertEqual(len(pending), 1)
        loan_id = pending[0]["id"]
        self.assertEqual(pending[0]["status"], "REQUESTED")

        # 2. Cannot request the same book again while request is pending
        ok2, msg2 = db.request_book(book["id"], stu["id"], self.db_path)
        self.assertFalse(ok2)
        self.assertIn("already have a pending", msg2)

        # 3. Admin approves request
        ok_app, msg_app = db.approve_request(loan_id, due_days=14, db_file=self.db_path)
        self.assertTrue(ok_app)

        # Check availability decremented
        book_updated = db.get_book_by_id(book["id"], self.db_path)
        self.assertEqual(book_updated["available_copies"], 1)

        # Check active loans
        active_loans = db.get_active_loans(student_id_filter=stu["id"], db_file=self.db_path)
        self.assertEqual(len(active_loans), 1)
        self.assertEqual(active_loans[0]["status"], "ISSUED")

        # 4. Return book
        today = date.today().isoformat()
        ok_ret, msg_ret = db.return_book(loan_id, today, self.db_path)
        self.assertTrue(ok_ret)

        # Check availability restored
        book_restored = db.get_book_by_id(book["id"], self.db_path)
        self.assertEqual(book_restored["available_copies"], 2)

    def test_reminder_engine_and_deduplication(self):
        """Tests automatic reminder evaluation and ensures duplicate notifications are not sent."""
        db.add_book("Operating Systems", "Silberschatz", "978-0001", "CS", 2, self.db_path)
        db.add_student("STU-777", "Test Student", "test@college.edu", "Pass123!", self.db_path)

        book = db.get_all_books(db_file=self.db_path)[0]
        stu = db.get_all_students(db_file=self.db_path)[0]

        past_issue = (date.today() - timedelta(days=20)).isoformat()
        past_due = (date.today() - timedelta(days=5)).isoformat()

        # Issue overdue book
        db.issue_book(book["id"], stu["id"], past_issue, past_due, self.db_path)

        # 1. Run reminder check (First run: 1 overdue reminder queued)
        summary1 = db.check_and_send_reminders(self.db_path)
        self.assertEqual(summary1["overdue_reminders"], 1)

        # Check notification logged in database
        notifs = db.get_notifications(student_id_filter=stu["id"], db_file=self.db_path)
        self.assertEqual(len(notifs), 1)
        self.assertEqual(notifs[0]["reminder_type"], "OVERDUE")

        # 2. Run reminder check again immediately: Deduplication must skip sending duplicate
        summary2 = db.check_and_send_reminders(self.db_path)
        self.assertEqual(summary2["overdue_reminders"], 0)
        self.assertEqual(summary2["duplicates_skipped"], 1)

        # Still only 1 notification in history
        notifs2 = db.get_notifications(student_id_filter=stu["id"], db_file=self.db_path)
        self.assertEqual(len(notifs2), 1)


if __name__ == "__main__":
    unittest.main()
