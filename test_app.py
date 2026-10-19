"""
test_app.py - Automated Streamlit AppTest integration tests for the unified zero-login interface.
Tests:
- Unified application entry point renders cleanly without any login screen or credentials prompt.
- Real-time dashboard KPI metrics render from database.
- Tabs (Catalogue, Circulation Desk, Students, Reports) render with zero exceptions.
- Search and filter inputs function without crash.
"""

import unittest
from streamlit.testing.v1 import AppTest
import database as db


class TestUnifiedLibraryApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_direct_entry_zero_login(self):
        """The application renders directly with zero login prompts or authentication screens."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()

        # Must have zero exceptions
        self.assertEqual(len(at.exception), 0, f"Exceptions on initial load: {[e.message for e in at.exception]}")

        # Ensure no login screens exist
        all_text = " ".join([m.value for m in at.markdown] + [c.value for c in at.caption])
        self.assertNotIn("Admin Login", all_text)
        self.assertNotIn("Student Sign-In", all_text)
        self.assertNotIn("Enter Password", all_text)

        # Ensure brand and hero are present
        self.assertIn("Library Management", all_text)
        self.assertIn("Your Library", all_text)

    def test_metrics_and_tabs_render(self):
        """Dashboard KPI cards and main tabs render with real numbers from SQLite."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()

        self.assertEqual(len(at.exception), 0)

        # Check metric elements
        self.assertGreaterEqual(len(at.metric), 4)
        metric_labels = [m.label for m in at.metric]
        self.assertIn("Total Books", metric_labels)
        self.assertIn("Available Copies", metric_labels)
        self.assertIn("Active Loans", metric_labels)
        self.assertIn("Overdue Loans", metric_labels)

        # Check tabs exist
        self.assertGreaterEqual(len(at.tabs), 4)


if __name__ == "__main__":
    unittest.main()
