"""Vercel entrypoint for the SmartShed AI Flask application."""

from backend.app import create_app

app = create_app()
