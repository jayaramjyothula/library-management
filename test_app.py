"""
test_app.py - Automated tests for Library Management System entry point & frontend assets.
Verifies:
1. app.py is detected as a valid ASGI application by Streamlit's app discovery.
2. app.py properly mounts the server application and all core routes.
3. Frontend assets (static/index.html, static/styles.css, static/app.js) are present and valid.
4. static/index.html matches the required structure and text from reference screenshots.
5. Database initialization and statistics function properly.
"""

import unittest
from pathlib import Path
from streamlit.web.server.app_discovery import discover_asgi_app
import database as db
import server


class TestLibraryAppEntry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()

    def test_01_asgi_discovery(self):
        """Verify app.py is auto-discovered as an ASGI app for Streamlit and Uvicorn."""
        app_path = Path("app.py")
        self.assertTrue(app_path.exists(), "app.py must exist")

        res = discover_asgi_app(app_path)
        self.assertTrue(res.is_asgi_app, "app.py must be discovered as an ASGI application")
        self.assertEqual(res.import_string, "app:app")

    def test_02_routes_registered(self):
        """Verify core routes are registered on the FastAPI app."""
        import app
        route_paths = [r.path for r in app.app.routes]
        self.assertIn("/_stcore/health", route_paths)
        self.assertIn("/healthz", route_paths)

        # Check server routes
        server_routes = [r.path for r in server.app.routes]
        self.assertIn("/api/stats", server_routes)
        self.assertIn("/api/books", server_routes)
        self.assertIn("/api/students", server_routes)
        self.assertIn("/api/loans/issue", server_routes)
        self.assertIn("/api/loans/return", server_routes)
        self.assertIn("/api/reports/export", server_routes)

    def test_03_frontend_static_assets(self):
        """Verify static files exist and contain required components."""
        static_dir = Path("static")
        index_file = static_dir / "index.html"
        css_file = static_dir / "styles.css"
        js_file = static_dir / "app.js"

        self.assertTrue(index_file.exists(), "static/index.html must exist")
        self.assertTrue(css_file.exists(), "static/styles.css must exist")
        self.assertTrue(js_file.exists(), "static/app.js must exist")

        html_content = index_file.read_text(encoding="utf-8")
        
        # Verify Brand & Navigation
        self.assertIn("Library Management", html_content)
        self.assertIn("Campus Edition", html_content)
        self.assertIn('data-section="hero"', html_content)
        self.assertIn('data-section="catalogue"', html_content)
        self.assertIn('data-section="circulation"', html_content)
        self.assertIn('data-section="students"', html_content)
        self.assertIn('data-section="reports"', html_content)

        # Verify Hero Section
        self.assertIn("Your Library,", html_content)
        self.assertIn("Simplified.", html_content)
        self.assertIn("Intelligent book cataloguing", html_content)

        # Verify Metric Cards
        self.assertIn("Total Titles", html_content)
        self.assertIn("Available Copies", html_content)
        self.assertIn("Active Loans", html_content)
        self.assertIn("Overdue Loans", html_content)

        # Verify Modals
        self.assertIn('id="modalAddBook"', html_content)
        self.assertIn('id="modalEditBook"', html_content)
        self.assertIn('id="modalReturnBook"', html_content)
        self.assertIn('id="modalAddStudent"', html_content)
        self.assertIn('id="modalStudentHistory"', html_content)

    def test_04_database_stats(self):
        """Verify database statistics load successfully."""
        stats = db.get_dashboard_stats()
        self.assertIsInstance(stats, dict)
        for key in ["total_books", "total_copies", "available_copies", "borrowed_copies", "total_students", "overdue_loans"]:
            self.assertIn(key, stats)


if __name__ == "__main__":
    unittest.main()
