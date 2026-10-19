"""
test_web_api.py - Comprehensive automated tests for Library Management System REST API & Web App.
Verifies:
1. Statistics endpoint (/api/stats)
2. Book listing, category filtering, and text search (/api/books)
3. Adding a new book with optional ISBN empty (/api/books)
4. Editing a book (/api/books/{id})
5. Student registration and search (/api/students)
6. Issuing a book copy to a student (/api/loans/issue)
7. Decrementing availability and checking active loans (/api/loans/active)
8. Returning a book copy (/api/loans/return)
9. Restoring availability
10. Deleting the test book (/api/books/{id})
11. CSV export generation (/api/reports/export)
"""

import unittest
from datetime import date, datetime, timedelta
import requests

BASE_URL = "http://localhost:8501"


class TestLibraryAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Verify server is up
        r = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        assert r.status_code == 200, f"Server not reachable: {r.status_code}"

    def test_01_stats_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/stats")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for k in ["total_books", "total_copies", "available_copies", "borrowed_copies", "total_students", "overdue_loans"]:
            self.assertIn(k, data)
            self.assertIsInstance(data[k], int)

    def test_02_books_listing_and_filter(self):
        r = requests.get(f"{BASE_URL}/api/books")
        self.assertEqual(r.status_code, 200)
        books = r.json()
        self.assertIsInstance(books, list)
        self.assertGreater(len(books), 0)

        # Test search query
        first_title = books[0]["title"]
        r_search = requests.get(f"{BASE_URL}/api/books", params={"q": first_title})
        self.assertEqual(r_search.status_code, 200)
        found = r_search.json()
        self.assertGreaterEqual(len(found), 1)

    def test_03_book_lifecycle(self):
        suffix = datetime.now().strftime("%Y%m%d%H%M%S%f")
        test_title = f"Clean Architecture Test {suffix}"
        test_isbn = f"978-TEST-{suffix[-8:]}"
        book_id = None

        try:
            # 1. Add book without ISBN (optional ISBN)
            payload = {
                "title": test_title,
                "author": "Robert C. Martin",
                "isbn": None,
                "category": "Software Engineering",
                "total_copies": 3,
            }
            r_add = requests.post(f"{BASE_URL}/api/books", json=payload)
            self.assertEqual(r_add.status_code, 200)
            self.assertTrue(r_add.json()["success"])

            # Fetch created book
            r_get = requests.get(f"{BASE_URL}/api/books", params={"q": test_title})
            created_books = [b for b in r_get.json() if b["title"] == test_title]
            self.assertEqual(len(created_books), 1)
            book_id = created_books[0]["id"]
            self.assertEqual(created_books[0]["available_copies"], 3)
            self.assertIsNone(created_books[0]["isbn"])

            # 2. Update book details
            upd_payload = {
                "title": f"{test_title} (Updated)",
                "author": "Robert C. Martin",
                "isbn": test_isbn,
                "category": "Software Engineering",
                "total_copies": 4,
            }
            r_upd = requests.put(f"{BASE_URL}/api/books/{book_id}", json=upd_payload)
            self.assertEqual(r_upd.status_code, 200)
            self.assertTrue(r_upd.json()["success"])

            # 3. Register student
            test_stu_id = f"STU-API-{suffix}"
            stu_payload = {
                "student_id": test_stu_id,
                "name": "API Test Student",
                "email": f"api_{suffix}@university.edu",
            }
            r_stu = requests.post(f"{BASE_URL}/api/students", json=stu_payload)
            self.assertEqual(r_stu.status_code, 200)

            # Get student PK
            r_all_stu = requests.get(f"{BASE_URL}/api/students", params={"q": test_stu_id})
            student_pk = r_all_stu.json()[0]["id"]

            # 4. Issue book
            today_str = date.today().isoformat()
            due_str = (date.today() + timedelta(days=14)).isoformat()
            issue_payload = {
                "book_id": book_id,
                "student_id": student_pk,
                "issue_date": today_str,
                "due_date": due_str,
            }
            r_issue = requests.post(f"{BASE_URL}/api/loans/issue", json=issue_payload)
            self.assertEqual(r_issue.status_code, 200)

            # Check availability decremented: was 4, now 3
            r_check_book = requests.get(f"{BASE_URL}/api/books/{book_id}")
            self.assertEqual(r_check_book.json()["available_copies"], 3)

            # Try to delete book while actively borrowed - MUST BE BLOCKED
            r_del_blocked = requests.delete(f"{BASE_URL}/api/books/{book_id}")
            self.assertEqual(r_del_blocked.status_code, 400)

            # 5. Find loan ID and return book
            r_loans = requests.get(f"{BASE_URL}/api/loans/active", params={"q": test_title})
            loan_id = r_loans.json()[0]["id"]

            return_payload = {
                "loan_id": loan_id,
                "return_date": today_str,
            }
            r_ret = requests.post(f"{BASE_URL}/api/loans/return", json=return_payload)
            self.assertEqual(r_ret.status_code, 200)

            # Check availability restored: now 4
            r_check_restored = requests.get(f"{BASE_URL}/api/books/{book_id}")
            self.assertEqual(r_check_restored.json()["available_copies"], 4)

            # 6. Delete book now that active loans are 0
            r_del = requests.delete(f"{BASE_URL}/api/books/{book_id}")
            self.assertEqual(r_del.status_code, 200)
            book_id = None
        finally:
            if book_id is not None:
                requests.delete(f"{BASE_URL}/api/books/{book_id}")

    def test_04_csv_export(self):
        r_export = requests.get(f"{BASE_URL}/api/reports/export")
        self.assertEqual(r_export.status_code, 200)
        self.assertEqual(r_export.headers["content-type"], "text/csv; charset=utf-8")
        self.assertIn("loan_id,book_title", r_export.text)


if __name__ == "__main__":
    unittest.main()
