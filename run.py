"""
SmartShed AI - Application Entry Point
Starts the local Flask development server.

Usage:
    python run.py
"""

import os
import sys

# Ensure project root is in Python module search path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.app import create_app
from backend.db import test_connection

def main():
    print("=" * 65)
    print(" SmartShed AI - Automated Constraint-Based Timetable Generator")
    print(" B.Tech IV-Year Summer Mini Project (Local-First, Zero Paid APIs)")
    print("=" * 65)

    # Check MySQL server connectivity before starting
    is_connected, msg = test_connection()
    if is_connected:
        print("[+] MySQL Connection: OK (Ready)")
    else:
        print(f"[!] Warning: Cannot connect to MySQL server: {msg}")
        print("    Please ensure MySQL Community Server is running and .env is configured.")
        print("    Run 'python database/seed.py' after setting up your database.")

    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")

    print(f"[+] Starting SmartShed AI Web Server on http://{host}:{port}")
    print("=" * 65)
    app.run(host=host, port=port, debug=True)

if __name__ == "__main__":
    main()
