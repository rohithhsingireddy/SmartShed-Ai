"""
SmartShed AI - Database Seed Script
Populates the MySQL database with realistic sample college data:
- Admin Account: admin / admin123
- 8 Faculty Members
- 9 Subjects (6 Core Theory + 3 Multi-period Labs)
- 7 Classrooms & Specialized Labs
- 3 Student Sections (CSE-A, CSE-B, AI&DS-A)
- Complete Faculty Availability Matrix
- Section Subject Mappings

Usage:
    python database/seed.py
"""

import os
import sys
from werkzeug.security import generate_password_hash

# Ensure root directory is on Python module path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import Config
from backend.db import get_db_connection, execute_script, test_connection

def seed_database():
    print("=" * 60)
    print(" SmartShed AI - College Database Seeder")
    print("=" * 60)

    # 1. Test MySQL Server Connection
    is_ok, msg = test_connection()
    if not is_ok:
        print(f"[!] ERROR: Cannot connect to MySQL server: {msg}")
        print("Please ensure MySQL Community Server is running and .env credentials are correct.")
        sys.exit(1)

    # 2. Run schema.sql to ensure tables exist
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    print(f"[*] Applying database schema from: {schema_path}")
    ok, schema_msg = execute_script(schema_path)
    if not ok:
        print(f"[!] Schema initialization failed: {schema_msg}")
        sys.exit(1)
    print("[+] Database schema created/verified successfully.")

    conn = get_db_connection(use_database=True)
    cursor = conn.cursor(dictionary=True)

    try:
        # 3. Clean existing sample data (safe re-seed)
        print("[*] Clearing previous records...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE timetable;")
        cursor.execute("TRUNCATE TABLE section_subjects;")
        cursor.execute("TRUNCATE TABLE faculty_availability;")
        cursor.execute("TRUNCATE TABLE subjects;")
        cursor.execute("TRUNCATE TABLE classrooms;")
        cursor.execute("TRUNCATE TABLE sections;")
        cursor.execute("TRUNCATE TABLE faculty;")
        cursor.execute("TRUNCATE TABLE admins;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # 4. Insert Admin Account
        admin_username = "admin"
        admin_pass = "admin123"
        hashed_pw = generate_password_hash(admin_pass)
        cursor.execute(
            "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
            (admin_username, hashed_pw)
        )
        print(f"[+] Admin account created: Username='{admin_username}' | Password='{admin_pass}'")

        # 5. Insert Faculty Members
        faculty_data = [
            ("Dr. Robert Smith", "Computer Science & Engineering", "robert.smith@college.edu"),
            ("Dr. Emily Davis", "Computer Science & Engineering", "emily.davis@college.edu"),
            ("Prof. Alan Turing", "Computer Science & Engineering", "alan.turing@college.edu"),
            ("Prof. Grace Hopper", "Information Technology", "grace.hopper@college.edu"),
            ("Prof. John Von Neumann", "Computer Science & Engineering", "john.vn@college.edu"),
            ("Dr. Ada Lovelace", "Artificial Intelligence & Data Science", "ada.lovelace@college.edu"),
            ("Prof. Claude Shannon", "Information Technology", "claude.shannon@college.edu"),
            ("Dr. Barbara Liskov", "Computer Science & Engineering", "barbara.liskov@college.edu"),
        ]
        faculty_ids = {}
        for name, dept, email in faculty_data:
            cursor.execute(
                "INSERT INTO faculty (name, department, email) VALUES (%s, %s, %s)",
                (name, dept, email)
            )
            faculty_ids[name] = cursor.lastrowid
        print(f"[+] Inserted {len(faculty_ids)} Faculty members.")

        # 6. Insert Classrooms and Computer Labs
        classrooms_data = [
            ("LH-101", "Classroom", 70, "Main Academic Block"),
            ("LH-102", "Classroom", 70, "Main Academic Block"),
            ("LH-103", "Classroom", 65, "Main Academic Block"),
            ("LH-201", "Classroom", 80, "Science Block"),
            ("CS-LAB-1", "Lab", 70, "Turing Computing Wing"),
            ("CS-LAB-2", "Lab", 70, "Hopper Computing Wing"),
            ("AI-LAB-1", "Lab", 65, "Lovelace AI Center"),
        ]
        room_ids = {}
        for r_num, r_type, cap, bld in classrooms_data:
            cursor.execute(
                "INSERT INTO classrooms (room_number, room_type, capacity, building) VALUES (%s, %s, %s, %s)",
                (r_num, r_type, cap, bld)
            )
            room_ids[r_num] = cursor.lastrowid
        print(f"[+] Inserted {len(room_ids)} Classrooms & Labs.")

        # 7. Insert Student Sections
        sections_data = [
            ("III Year", "CSE", "Sec-A", 60),
            ("III Year", "CSE", "Sec-B", 60),
            ("III Year", "AI & DS", "Sec-A", 55),
        ]
        sec_ids = {}
        for yr, br, sname, strength in sections_data:
            cursor.execute(
                "INSERT INTO sections (year, branch, section_name, student_strength) VALUES (%s, %s, %s, %s)",
                (yr, br, sname, strength)
            )
            sec_ids[f"{br}-{sname}"] = cursor.lastrowid
        print(f"[+] Inserted {len(sec_ids)} Student Sections.")

        # 8. Insert Subjects (Theory & Labs with Durations)
        subjects_data = [
            # Code, Name, Type, Periods/Wk, Lab Duration, Preferred Faculty Name
            ("CS301", "Data Structures & Algorithms", "Theory", 4, 1, "Dr. Emily Davis"),
            ("CS302", "Database Management Systems", "Theory", 4, 1, "Prof. Grace Hopper"),
            ("CS303", "Operating Systems", "Theory", 4, 1, "Dr. Barbara Liskov"),
            ("CS304", "Computer Networks", "Theory", 3, 1, "Prof. Claude Shannon"),
            ("CS305", "Artificial Intelligence", "Theory", 3, 1, "Dr. Robert Smith"),
            ("CS306", "Theory of Computation", "Theory", 3, 1, "Prof. Alan Turing"),
            ("AI301", "Machine Learning Fundamentals", "Theory", 3, 1, "Dr. Ada Lovelace"),
            ("CS391", "Data Structures Lab", "Lab", 2, 2, "Dr. Emily Davis"),
            ("CS392", "DBMS & SQL Lab", "Lab", 2, 2, "Prof. Grace Hopper"),
            ("AI391", "AI & Deep Learning Lab", "Lab", 3, 3, "Dr. Ada Lovelace"),
        ]
        subject_ids = {}
        for code, sname, stype, pw, ldur, fac_name in subjects_data:
            pref_fid = faculty_ids.get(fac_name)
            cursor.execute(
                "INSERT INTO subjects (code, name, type, periods_per_week, lab_duration, preferred_faculty_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (code, sname, stype, pw, ldur, pref_fid)
            )
            subject_ids[code] = {
                "id": cursor.lastrowid,
                "type": stype,
                "preferred_fid": pref_fid
            }
        print(f"[+] Inserted {len(subject_ids)} Subjects (Theory & Labs).")

        # 9. Populate Faculty Availability (Mon-Fri, Periods 1-7)
        # Give ample availability with realistic busy slots
        days = Config.DEFAULT_DAYS
        periods = list(range(1, Config.DEFAULT_PERIODS + 1))
        avail_count = 0

        for f_name, f_id in faculty_ids.items():
            for day in days:
                for p in periods:
                    is_avail = 1
                    # Realistic busy constraints:
                    # Prof. Alan Turing has research meeting on Friday Period 6 & 7
                    if "Turing" in f_name and day == "Friday" and p in (6, 7):
                        is_avail = 0
                    # Dr. Robert Smith has Departmental meeting on Wednesday Period 4
                    elif "Smith" in f_name and day == "Wednesday" and p == 4:
                        is_avail = 0
                    # Dr. Ada Lovelace has Dean sync on Monday Period 1
                    elif "Lovelace" in f_name and day == "Monday" and p == 1:
                        is_avail = 0

                    cursor.execute(
                        "INSERT INTO faculty_availability (faculty_id, day, period, is_available) "
                        "VALUES (%s, %s, %s, %s)",
                        (f_id, day, p, is_avail)
                    )
                    avail_count += 1
        print(f"[+] Generated {avail_count} Faculty Availability slots across all periods.")

        # 10. Map Sections to Curriculum Subjects
        # CSE Sections (Sec-A and Sec-B): CS301, CS302, CS303, CS304, CS305, CS306, CS391, CS392
        cse_curriculum = ["CS301", "CS302", "CS303", "CS304", "CS305", "CS306", "CS391", "CS392"]
        # AI&DS Section (Sec-A): CS301, CS302, CS303, CS305, AI301, CS391, AI391
        aids_curriculum = ["CS301", "CS302", "CS303", "CS305", "AI301", "CS391", "AI391"]

        sec_sub_count = 0
        for sec_key, sec_id in sec_ids.items():
            curr = aids_curriculum if "AI & DS" in sec_key else cse_curriculum
            for code in curr:
                sub_info = subject_ids[code]
                sub_id = sub_info["id"]
                fac_id = sub_info["preferred_fid"]
                cursor.execute(
                    "INSERT INTO section_subjects (section_id, subject_id, faculty_id) VALUES (%s, %s, %s)",
                    (sec_id, sub_id, fac_id)
                )
                sec_sub_count += 1
        print(f"[+] Configured {sec_sub_count} Section-Subject curriculum assignments.")

        conn.commit()
        print("=" * 60)
        print(" [SUCCESS] Database successfully initialized and seeded!")
        print(" Admin Credentials: admin / admin123")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"[!] Error seeding database: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_database()
