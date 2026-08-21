"""
SmartShed AI - Flask Routes & View Templates Test Suite
Verifies:
1. Flask app creation and configuration
2. Route status codes (login, static assets, templates)
3. Session protection on protected routes (@login_required)
"""

import unittest
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app

class TestFlaskRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def test_login_page_renders(self):
        """Verify login page is accessible and returns HTTP 200."""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SmartShed AI", response.data)
        self.assertIn(b"Admin Username", response.data)

    def test_protected_routes_redirect_to_login(self):
        """Verify protected routes redirect unauthorized users to login."""
        protected_urls = ["/dashboard", "/faculty", "/subjects", "/classrooms", "/sections", "/timetable"]
        for url in protected_urls:
            response = self.client.get(url, follow_redirects=False)
            self.assertEqual(response.status_code, 302, f"Failed for {url}")
            self.assertIn("/login", response.headers["Location"])

    def test_static_css_exists(self):
        """Verify static CSS stylesheet is served."""
        response = self.client.get("/static/style.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SmartShed AI", response.data)


if __name__ == "__main__":
    unittest.main()
