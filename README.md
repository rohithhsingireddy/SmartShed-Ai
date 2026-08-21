# SmartShed AI: AI-Based Automated Timetable Generator

**Project Type**: B.Tech IV-Year Summer Mini Project  
**Target Users**: College Administrators / Timetable Coordinators / Academic Heads  
**Architecture**: Local-First, Zero Paid APIs, Offline Pure-Python Constraint Satisfaction Scheduling  
**Version**: 1.0  

---

# How to run
 python .\run.py

## 1. Project Overview & Problem Statement

Manual timetable preparation in engineering colleges is an NP-hard combinatorial problem that requires dozens of manual hours. It frequently results in faculty double-booking, classroom capacity deficits, laboratory scheduling collisions, and faculty availability violations.

**SmartShed AI** solves this problem by using a deterministic, explainable **Constraint Satisfaction Problem (CSP) Backtracking Algorithm** with **Minimum Remaining Values (MRV)** heuristics and **Soft Penalty Heuristics**. It requires **zero paid APIs, no OpenAI/Gemini keys, no subscriptions, and runs 100% offline** on local hardware.

```
Browser (Bootstrap 5 UI)
   ↕ (HTTP / JSON / Forms)
Flask Web Application (backend/app.py)
   ↕ (Parameterized SQL via mysql-connector-python)
MySQL Database (admins, faculty, subjects, classrooms, sections, timetable)
   ↕ (In-Memory CSP Solving)
Constraint-Based Scheduler (ai/scheduler.py)
```

---

## 2. Key Features

- **Secure Admin Authentication**: Flask session management with Werkzeug `generate_password_hash` & `check_password_hash`.
- **Master Data CRUD**:
  - **Faculty**: Department, email, subject associations, and day-wise period availability matrix.
  - **Subjects & Labs**: Theory courses (1 period) vs Lab practicals (consecutive multi-period blocks, e.g. 2 or 3 periods).
  - **Classrooms & Labs**: Seating capacity validation (`capacity >= student_strength`) and facility type matching (`Classroom` vs `Lab`).
  - **Student Sections**: Year, engineering branch, section name, and student strength.
- **Interactive Weekly Faculty Availability Grid**: Visually click and toggle periods between *Available* and *Busy*.
- **Constraint-Based AI Scheduler (`ai/scheduler.py`)**:
  - **Hard Constraints**: 0 section double-booking, 0 faculty double-booking, 0 room double-booking, 100% faculty availability respected, strict room type & capacity compliance, lab block continuity.
  - **Soft Optimization**: Balanced daily student loads, avoidance of subject clustering, distributed faculty teaching loads, optimal room capacity utilization.
  - **Independent Validation Suite**: Rigorously re-verifies every scheduled period before committing to MySQL.
  - **Conflict Diagnostic Analyzer**: Provides human-readable bottleneck reports if master data is mathematically over-constrained.
- **Visual Timetable Matrix**: Multi-tab views by **Section**, **Faculty Schedule**, and **Room Allocation**.
- **One-Click Export**: Browser printing with dedicated `@media print` CSS layout and client-side CSV export.

---

## 3. Project Structure

```
SmartShed AI/
├── ai/
│   ├── __init__.py
│   └── scheduler.py            # CSP Backtracking, MRV heuristics, conflict diagnostics
├── backend/
│   ├── __init__.py
│   ├── app.py                  # Flask web controller & CRUD routes
│   ├── config.py               # Environment configuration & matrix timings
│   └── db.py                   # MySQL connection helper with parameterized queries
├── database/
│   ├── schema.sql              # Relational MySQL schema DDL
│   └── seed.py                 # Idempotent realistic sample data seeder
├── static/
│   └── style.css               # Modern UI, glassmorphic login, print stylesheet
├── templates/
│   ├── base.html               # Master sidebar & navigation layout
│   ├── login.html              # Secure glassmorphism login view
│   ├── dashboard.html          # Analytics metrics & generation status
│   ├── faculty.html            # Faculty master table & modal forms
│   ├── faculty_availability.html # Interactive weekly availability grid editor
│   ├── subjects.html           # Subject & lab configuration table
│   ├── classrooms.html         # Classrooms & laboratory management
│   ├── sections.html           # Student sections management
│   └── timetable.html          # Interactive timetable grid & print/export
├── .env.example                # Template environment variables
├── .env                        # Local database credentials
├── README.md                   # Comprehensive project documentation
├── requirements.txt            # Python dependencies (Python 3.14+ compatible)
└── run.py                      # Application entry point
```

---

## 4. Technology Stack

| Component | Technology / Library | Description |
|---|---|---|
| **Backend** | Python 3.14+ / Flask | Lightweight, robust web framework |
| **Database** | MySQL Community Server | Relational storage with foreign key cascades |
| **DB Driver** | `mysql-connector-python` | Parameterized, SQL-injection safe queries |
| **Security** | `Werkzeug.security` | Cryptographic password hashing |
| **Frontend** | HTML5, CSS3, Bootstrap 5 | Responsive college ERP UI |
| **Icons** | Bootstrap Icons | Clean iconography |
| **Algorithm** | Pure Python CSP Engine | Constraint satisfaction, MRV, backtracking |

---

## 5. Step-by-Step Setup Instructions

### Step 1: Prerequisites
- **Python 3.14+** installed. (Check with `python --version`)
- **MySQL Community Server** installed and running on port 3306.

### Step 2: Open Project Folder & Create Virtual Environment
Open PowerShell or Command Prompt in the project folder:
```powershell
# Navigate to project folder
cd "c:\Users\saisr\OneDrive\Desktop\SmartShed AI"

# Create a virtual environment
python -m venv venv

# Activate virtual environment on Windows
.\venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Database Credentials
Check `.env` file in the root folder and verify your MySQL password:
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=smartshed_ai
SECRET_KEY=smartshed_super_secret_key_2026
```

### Step 5: Initialize Schema & Seed Realistic Sample Data
Run the automated idempotent seed script:
```powershell
python database/seed.py
```
*This command creates the database, all tables, inserts the default admin account, 8 faculty members, 9 subjects & labs, 7 classrooms & specialized labs, 3 student sections, and faculty availability schedules.*

### Step 6: Start SmartShed AI Web Application
```powershell
python run.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 6. Default Admin Credentials

| Role | Username | Password |
|---|---|---|
| **Administrator** | `admin` | `admin123` |

### How to change the admin password:
You can update the admin password at any time via Python:
```python
from werkzeug.security import generate_password_hash
from backend.db import execute_query

new_hash = generate_password_hash("YourNewPassword")
execute_query("UPDATE admins SET password_hash = %s WHERE username = 'admin'", (new_hash,), commit=True)
```

---

## 7. How the AI Scheduling Algorithm Works (Academic Review Guide)

The timetable scheduler is implemented in [`ai/scheduler.py`](ai/scheduler.py).

### 1. Discrete Unit Expansion
- Every course requirement is converted into indivisible scheduling units:
  - **Theory Course** (e.g. 4 periods/week) $\rightarrow$ 4 separate 1-period units.
  - **Lab Course** (e.g. 2 periods/week with `lab_duration=2`) $\rightarrow$ 1 consecutive 2-period lab block.
  - **AI Lab Course** (e.g. 3 periods/week with `lab_duration=3`) $\rightarrow$ 1 consecutive 3-period lab block.

### 2. MRV (Minimum Remaining Values) / Most Constrained First Heuristic
Units are sorted to process the hardest-to-place items first:
$$\text{Priority} = (\text{Duration } \downarrow, \text{Domain Size } \uparrow, \text{Eligible Rooms } \uparrow)$$
1. Multi-period lab blocks (require contiguous slots in specialized labs).
2. Faculty members with restricted availability.
3. Large student sections requiring large lecture halls.

### 3. Forward Checking & Pruning
Before placing any unit at $(\text{Day}, \text{Start Period}, \text{Room})$, all 8 Hard Constraints are tested in $O(1)$ time:
- **HC1**: `section_schedule[section_id][(day, p)]` is vacant.
- **HC2**: `faculty_schedule[faculty_id][(day, p)]` is vacant.
- **HC3**: `room_schedule[room_id][(day, p)]` is vacant.
- **HC4**: `faculty_availability[faculty_id][(day, p)] == 1`.
- **HC5**: $\text{Room Type} == \text{Subject Type}$ (Theory in Classroom, Lab in Lab).
- **HC6**: $\text{Room Capacity} \ge \text{Section Student Strength}$.
- **HC7**: Multi-period block fits completely within the same day without wrapping.
- **HC8**: Total assigned periods match course curriculum.

### 4. Soft Optimization & Domain Ordering (LCV)
Valid candidate slots are ranked using a penalty function:
- **Daily Load Penalty**: Prefers distributing classes evenly across Monday–Friday.
- **Subject Fatigue Penalty**: Strongly discourages more than 1 theory lecture of the same subject on the same day for a section.
- **Capacity Fit Penalty**: Assigns the smallest suitable room to minimize wasted hall capacity.
- **Faculty Load Balance**: Distributes faculty teaching load smoothly across the week.

### 5. Final Independent Validation Suite
After backtracking finds a complete solution, [`validate_timetable_solution()`](ai/scheduler.py) runs an independent audit across every timetable entry before committing to MySQL.

---

## 8. Troubleshooting & FAQ

### Q: "Cannot connect to MySQL server"
- Ensure MySQL Community Server is running in Windows Services (`services.msc` $\rightarrow$ MySQL80 $\rightarrow$ Start).
- Verify the password in `.env` matches your local MySQL root password.

### Q: "Timetable generation failed due to constraint conflicts"
- SmartShed AI will show a detailed diagnostic alert. Common reasons:
  - Total weekly periods requested by a section exceeds $5 \text{ days} \times 7 \text{ periods} = 35 \text{ slots}$.
  - A faculty member is assigned 15 periods of teaching but only marked available for 10 slots in the availability matrix.
  - No lab room has capacity $\ge$ student strength.
- Simply adjust availability in the **Faculty & Avail** tab or increase room capacity in **Classrooms & Labs**.

---

## 9. Academic Project Review Checklist

- [x] Complete, runnable local-first Python/Flask architecture
- [x] Zero paid APIs / No external cloud dependencies
- [x] MySQL schema with foreign keys, cascades, and indexes
- [x] Full CRUD on Faculty, Subjects, Classrooms, and Sections
- [x] Interactive Faculty Availability Weekly Matrix
- [x] Pure-Python CSP Backtracking Scheduler with MRV Heuristics
- [x] Independent Hard Constraint Validation Engine
- [x] Multi-tab Timetable Grid (Section / Faculty / Room views)
- [x] One-click Print & CSV Export
- [x] Idempotent Seed Data with realistic engineering curriculum
