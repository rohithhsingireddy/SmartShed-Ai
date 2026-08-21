"""
SmartShed AI - Configuration Module
Loads environment variables and sets up application configuration defaults.
"""

import os
from dotenv import load_dotenv

# Load project settings even when an older shell environment variable exists.
load_dotenv(override=True)

class Config:
    # Flask Settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "smartshed-default-dev-secret-key-3.14")
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "t")

    # MySQL Database Settings
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
    DB_NAME = os.environ.get("DB_NAME", "smartshed_ai")

    # Timetable Matrix Defaults
    DEFAULT_DAYS = [
        d.strip() for d in os.environ.get("DEFAULT_DAYS", "Monday,Tuesday,Wednesday,Thursday,Friday").split(",") if d.strip()
    ]
    DEFAULT_PERIODS = int(os.environ.get("DEFAULT_PERIODS", 7))

    # Standard Period Time Slots (for visual display & printout)
    PERIOD_TIMINGS = {
        1: "09:00 AM - 09:55 AM",
        2: "09:55 AM - 10:50 AM",
        3: "11:05 AM - 12:00 PM",
        4: "12:00 PM - 12:55 PM",
        5: "01:45 PM - 02:40 PM",
        6: "02:40 PM - 03:35 PM",
        7: "03:35 PM - 04:30 PM",
    }
