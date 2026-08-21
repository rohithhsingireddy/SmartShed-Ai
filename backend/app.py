"""
SmartShed AI - Flask Web Application & Route Controller
Handles admin authentication, CRUD master data routes, constraint solver triggers,
and timetable visualization views.
"""

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from backend.config import Config
from backend.db import execute_query, execute_transaction, test_connection
from ai.scheduler import TimetableScheduler

def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )
    app.config.from_object(Config)

    # ----------------------------------------------------
    # Authentication Decorator
    # ----------------------------------------------------
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "admin_id" not in session:
                flash("Please log in to access the system.", "warning")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated_function

    # ----------------------------------------------------
    # Authentication Routes
    # ----------------------------------------------------
    @app.route("/")
    def index():
        if "admin_id" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            if not username or not password:
                flash("Please enter both username and password.", "error")
                return render_template("login.html")

            try:
                admin = execute_query(
                    "SELECT id, username, password_hash FROM admins WHERE username = %s",
                    (username,),
                    fetch="one"
                )
                if admin and check_password_hash(admin["password_hash"], password):
                    session.clear()
                    session["admin_id"] = admin["id"]
                    session["admin_username"] = admin["username"]
                    flash(f"Welcome back, {admin['username']}!", "success")
                    return redirect(url_for("dashboard"))
                else:
                    flash("Invalid username or password.", "error")
            except Exception as e:
                flash(f"Database error: {str(e)}", "error")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been signed out successfully.", "success")
        return redirect(url_for("login"))

    # ----------------------------------------------------
    # Dashboard
    # ----------------------------------------------------
    @app.route("/dashboard")
    @login_required
    def dashboard():
        try:
            fac_count = execute_query("SELECT COUNT(*) AS c FROM faculty", fetch="one")["c"]
            sub_count = execute_query("SELECT COUNT(*) AS c FROM subjects", fetch="one")["c"]
            theory_count = execute_query("SELECT COUNT(*) AS c FROM subjects WHERE type = 'Theory'", fetch="one")["c"]
            lab_count = execute_query("SELECT COUNT(*) AS c FROM subjects WHERE type = 'Lab'", fetch="one")["c"]
            
            room_count = execute_query("SELECT COUNT(*) AS c FROM classrooms", fetch="one")["c"]
            classroom_count = execute_query("SELECT COUNT(*) AS c FROM classrooms WHERE room_type = 'Classroom'", fetch="one")["c"]
            lab_room_count = execute_query("SELECT COUNT(*) AS c FROM classrooms WHERE room_type = 'Lab'", fetch="one")["c"]

            sec_count = execute_query("SELECT COUNT(*) AS c FROM sections", fetch="one")["c"]
            tt_count = execute_query("SELECT COUNT(*) AS c FROM timetable", fetch="one")["c"]

            stats = {
                "faculty_count": fac_count,
                "subject_count": sub_count,
                "theory_count": theory_count,
                "lab_count": lab_count,
                "room_count": room_count,
                "classroom_count": classroom_count,
                "lab_room_count": lab_room_count,
                "section_count": sec_count,
                "timetable_count": tt_count
            }

            sections_summary = execute_query("SELECT * FROM sections ORDER BY year, branch, section_name", fetch="all") or []
            faculty_summary = execute_query("SELECT * FROM faculty ORDER BY name LIMIT 5", fetch="all") or []

            days = Config.DEFAULT_DAYS
            periods = list(range(1, Config.DEFAULT_PERIODS + 1))

            return render_template(
                "dashboard.html",
                stats=stats,
                sections_summary=sections_summary,
                faculty_summary=faculty_summary,
                days=days,
                periods=periods
            )
        except Exception as e:
            flash(f"Error loading dashboard: {str(e)}", "error")
            return render_template("dashboard.html", stats={}, sections_summary=[], faculty_summary=[], days=[], periods=[])

    # ----------------------------------------------------
    # Faculty Management & Availability
    # ----------------------------------------------------
    @app.route("/faculty")
    @login_required
    def faculty_list():
        try:
            faculty = execute_query("SELECT * FROM faculty ORDER BY name", fetch="all") or []
            return render_template("faculty.html", faculty=faculty)
        except Exception as e:
            flash(f"Error fetching faculty records: {str(e)}", "error")
            return render_template("faculty.html", faculty=[])

    @app.route("/faculty/add", methods=["POST"])
    @login_required
    def faculty_add():
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        email = request.form.get("email", "").strip() or None
        init_avail = bool(request.form.get("init_available"))

        if not name or not department:
            flash("Faculty name and department are required.", "error")
            return redirect(url_for("faculty_list"))

        try:
            fac_id = execute_query(
                "INSERT INTO faculty (name, department, email) VALUES (%s, %s, %s)",
                (name, department, email),
                fetch="lastrowid",
                commit=True
            )

            # Auto-initialize availability for default days and periods
            if init_avail and fac_id:
                days = Config.DEFAULT_DAYS
                periods = list(range(1, Config.DEFAULT_PERIODS + 1))
                avail_queries = [
                    ("INSERT INTO faculty_availability (faculty_id, day, period, is_available) VALUES (%s, %s, %s, 1)",
                     (fac_id, d, p))
                    for d in days for p in periods
                ]
                execute_transaction(avail_queries)

            flash(f"Faculty '{name}' added successfully!", "success")
        except Exception as e:
            flash(f"Error adding faculty: {str(e)}", "error")

        return redirect(url_for("faculty_list"))

    @app.route("/faculty/edit/<int:id>", methods=["POST"])
    @login_required
    def faculty_edit(id):
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        email = request.form.get("email", "").strip() or None

        if not name or not department:
            flash("Faculty name and department are required.", "error")
            return redirect(url_for("faculty_list"))

        try:
            execute_query(
                "UPDATE faculty SET name = %s, department = %s, email = %s WHERE id = %s",
                (name, department, email, id),
                commit=True
            )
            flash(f"Faculty '{name}' updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating faculty: {str(e)}", "error")

        return redirect(url_for("faculty_list"))

    @app.route("/faculty/delete/<int:id>")
    @login_required
    def faculty_delete(id):
        try:
            execute_query("DELETE FROM faculty WHERE id = %s", (id,), commit=True)
            flash("Faculty record deleted successfully.", "success")
        except Exception as e:
            flash(f"Error deleting faculty: {str(e)}", "error")
        return redirect(url_for("faculty_list"))

    @app.route("/faculty/<int:faculty_id>/availability")
    @login_required
    def faculty_availability_edit(faculty_id):
        try:
            faculty = execute_query("SELECT * FROM faculty WHERE id = %s", (faculty_id,), fetch="one")
            if not faculty:
                flash("Faculty not found.", "error")
                return redirect(url_for("faculty_list"))

            days = Config.DEFAULT_DAYS
            periods = list(range(1, Config.DEFAULT_PERIODS + 1))
            period_timings = Config.PERIOD_TIMINGS

            raw_avail = execute_query(
                "SELECT day, period, is_available FROM faculty_availability WHERE faculty_id = %s",
                (faculty_id,),
                fetch="all"
            ) or []
            avail_map = {(row["day"], row["period"]): row["is_available"] for row in raw_avail}

            return render_template(
                "faculty_availability.html",
                faculty=faculty,
                days=days,
                periods=periods,
                period_timings=period_timings,
                avail_map=avail_map
            )
        except Exception as e:
            flash(f"Error fetching availability: {str(e)}", "error")
            return redirect(url_for("faculty_list"))

    @app.route("/faculty/<int:faculty_id>/availability/save", methods=["POST"])
    @login_required
    def faculty_availability_save(faculty_id):
        try:
            days = Config.DEFAULT_DAYS
            periods = list(range(1, Config.DEFAULT_PERIODS + 1))

            queries = [("DELETE FROM faculty_availability WHERE faculty_id = %s", (faculty_id,))]

            for d in days:
                for p in periods:
                    field_name = f"slot_{d}_{p}"
                    is_avail = int(request.form.get(field_name, 1))
                    queries.append((
                        "INSERT INTO faculty_availability (faculty_id, day, period, is_available) VALUES (%s, %s, %s, %s)",
                        (faculty_id, d, p, is_avail)
                    ))

            execute_transaction(queries)
            flash("Faculty availability matrix saved successfully!", "success")
        except Exception as e:
            flash(f"Error saving availability: {str(e)}", "error")

        return redirect(url_for("faculty_availability_edit", faculty_id=faculty_id))

    # ----------------------------------------------------
    # Subject Management
    # ----------------------------------------------------
    @app.route("/subjects")
    @login_required
    def subjects_list():
        try:
            query = """
                SELECT s.*, f.name AS faculty_name, f.department AS faculty_dept
                FROM subjects s
                LEFT JOIN faculty f ON s.preferred_faculty_id = f.id
                ORDER BY s.type, s.code
            """
            subjects = execute_query(query, fetch="all") or []
            faculty_list = execute_query("SELECT id, name, department FROM faculty ORDER BY name", fetch="all") or []
            return render_template("subjects.html", subjects=subjects, faculty_list=faculty_list)
        except Exception as e:
            flash(f"Error loading subjects: {str(e)}", "error")
            return render_template("subjects.html", subjects=[], faculty_list=[])

    @app.route("/subjects/add", methods=["POST"])
    @login_required
    def subject_add():
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        sub_type = request.form.get("type", "Theory")
        periods_per_week = int(request.form.get("periods_per_week", 4))
        lab_duration = int(request.form.get("lab_duration", 1)) if sub_type == "Lab" else 1
        preferred_fac_id = request.form.get("preferred_faculty_id", "").strip() or None

        if not code or not name:
            flash("Course code and subject name are required.", "error")
            return redirect(url_for("subjects_list"))

        try:
            execute_query(
                """INSERT INTO subjects (code, name, type, periods_per_week, lab_duration, preferred_faculty_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (code, name, sub_type, periods_per_week, lab_duration, preferred_fac_id),
                commit=True
            )
            flash(f"Subject '{code} - {name}' added successfully!", "success")
        except Exception as e:
            flash(f"Error adding subject: {str(e)}", "error")

        return redirect(url_for("subjects_list"))

    @app.route("/subjects/edit/<int:id>", methods=["POST"])
    @login_required
    def subject_edit(id):
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        sub_type = request.form.get("type", "Theory")
        periods_per_week = int(request.form.get("periods_per_week", 4))
        lab_duration = int(request.form.get("lab_duration", 1)) if sub_type == "Lab" else 1
        preferred_fac_id = request.form.get("preferred_faculty_id", "").strip() or None

        if not code or not name:
            flash("Course code and subject name are required.", "error")
            return redirect(url_for("subjects_list"))

        try:
            execute_query(
                """UPDATE subjects
                   SET code = %s, name = %s, type = %s, periods_per_week = %s, lab_duration = %s, preferred_faculty_id = %s
                   WHERE id = %s""",
                (code, name, sub_type, periods_per_week, lab_duration, preferred_fac_id, id),
                commit=True
            )
            flash(f"Subject '{code}' updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating subject: {str(e)}", "error")

        return redirect(url_for("subjects_list"))

    @app.route("/subjects/delete/<int:id>")
    @login_required
    def subject_delete(id):
        try:
            execute_query("DELETE FROM subjects WHERE id = %s", (id,), commit=True)
            flash("Subject deleted successfully.", "success")
        except Exception as e:
            flash(f"Error deleting subject: {str(e)}", "error")
        return redirect(url_for("subjects_list"))

    # ----------------------------------------------------
    # Classroom / Lab Management
    # ----------------------------------------------------
    @app.route("/classrooms")
    @login_required
    def classrooms_list():
        try:
            classrooms = execute_query("SELECT * FROM classrooms ORDER BY room_type, room_number", fetch="all") or []
            return render_template("classrooms.html", classrooms=classrooms)
        except Exception as e:
            flash(f"Error fetching classrooms: {str(e)}", "error")
            return render_template("classrooms.html", classrooms=[])

    @app.route("/classrooms/add", methods=["POST"])
    @login_required
    def classroom_add():
        room_number = request.form.get("room_number", "").strip().upper()
        room_type = request.form.get("room_type", "Classroom")
        capacity = int(request.form.get("capacity", 60))
        building = request.form.get("building", "").strip() or None

        if not room_number:
            flash("Room number is required.", "error")
            return redirect(url_for("classrooms_list"))

        try:
            execute_query(
                "INSERT INTO classrooms (room_number, room_type, capacity, building) VALUES (%s, %s, %s, %s)",
                (room_number, room_type, capacity, building),
                commit=True
            )
            flash(f"Room '{room_number}' added successfully!", "success")
        except Exception as e:
            flash(f"Error adding classroom: {str(e)}", "error")

        return redirect(url_for("classrooms_list"))

    @app.route("/classrooms/edit/<int:id>", methods=["POST"])
    @login_required
    def classroom_edit(id):
        room_number = request.form.get("room_number", "").strip().upper()
        room_type = request.form.get("room_type", "Classroom")
        capacity = int(request.form.get("capacity", 60))
        building = request.form.get("building", "").strip() or None

        if not room_number:
            flash("Room number is required.", "error")
            return redirect(url_for("classrooms_list"))

        try:
            execute_query(
                "UPDATE classrooms SET room_number = %s, room_type = %s, capacity = %s, building = %s WHERE id = %s",
                (room_number, room_type, capacity, building, id),
                commit=True
            )
            flash(f"Room '{room_number}' updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating classroom: {str(e)}", "error")

        return redirect(url_for("classrooms_list"))

    @app.route("/classrooms/delete/<int:id>")
    @login_required
    def classroom_delete(id):
        try:
            execute_query("DELETE FROM classrooms WHERE id = %s", (id,), commit=True)
            flash("Classroom/Lab deleted successfully.", "success")
        except Exception as e:
            flash(f"Error deleting room: {str(e)}", "error")
        return redirect(url_for("classrooms_list"))

    # ----------------------------------------------------
    # Student Sections Management
    # ----------------------------------------------------
    @app.route("/sections")
    @login_required
    def sections_list():
        try:
            sections = execute_query("SELECT * FROM sections ORDER BY year, branch, section_name", fetch="all") or []
            return render_template("sections.html", sections=sections)
        except Exception as e:
            flash(f"Error fetching sections: {str(e)}", "error")
            return render_template("sections.html", sections=[])

    @app.route("/sections/add", methods=["POST"])
    @login_required
    def section_add():
        year = request.form.get("year", "").strip()
        branch = request.form.get("branch", "").strip().upper()
        section_name = request.form.get("section_name", "").strip()
        strength = int(request.form.get("student_strength", 60))

        if not year or not branch or not section_name:
            flash("Year, branch, and section name are required.", "error")
            return redirect(url_for("sections_list"))

        try:
            execute_query(
                "INSERT INTO sections (year, branch, section_name, student_strength) VALUES (%s, %s, %s, %s)",
                (year, branch, section_name, strength),
                commit=True
            )
            flash(f"Section '{branch} {section_name}' added successfully!", "success")
        except Exception as e:
            flash(f"Error adding section: {str(e)}", "error")

        return redirect(url_for("sections_list"))

    @app.route("/sections/edit/<int:id>", methods=["POST"])
    @login_required
    def section_edit(id):
        year = request.form.get("year", "").strip()
        branch = request.form.get("branch", "").strip().upper()
        section_name = request.form.get("section_name", "").strip()
        strength = int(request.form.get("student_strength", 60))

        if not year or not branch or not section_name:
            flash("Year, branch, and section name are required.", "error")
            return redirect(url_for("sections_list"))

        try:
            execute_query(
                "UPDATE sections SET year = %s, branch = %s, section_name = %s, student_strength = %s WHERE id = %s",
                (year, branch, section_name, strength, id),
                commit=True
            )
            flash(f"Section '{branch} {section_name}' updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating section: {str(e)}", "error")

        return redirect(url_for("sections_list"))

    @app.route("/sections/delete/<int:id>")
    @login_required
    def section_delete(id):
        try:
            execute_query("DELETE FROM sections WHERE id = %s", (id,), commit=True)
            flash("Section deleted successfully.", "success")
        except Exception as e:
            flash(f"Error deleting section: {str(e)}", "error")
        return redirect(url_for("sections_list"))

    # ----------------------------------------------------
    # AI Timetable Generation & Visualization
    # ----------------------------------------------------
    @app.route("/generate")
    @login_required
    def generate_timetable_route():
        try:
            # 1. Fetch all active master data
            sections = execute_query("SELECT * FROM sections", fetch="all") or []
            subjects = execute_query("SELECT * FROM subjects", fetch="all") or []
            faculty = execute_query("SELECT * FROM faculty", fetch="all") or []
            classrooms = execute_query("SELECT * FROM classrooms", fetch="all") or []
            faculty_avail = execute_query("SELECT * FROM faculty_availability", fetch="all") or []
            sec_subjects = execute_query("SELECT * FROM section_subjects", fetch="all") or []

            # Validation: Ensure basic master data exists
            if not sections or not subjects or not faculty or not classrooms:
                flash(
                    "Cannot generate timetable: Please ensure at least one Section, Subject, Faculty, "
                    "and Classroom/Lab exist in the master database.",
                    "error"
                )
                return redirect(url_for("dashboard"))

            days = Config.DEFAULT_DAYS
            periods = list(range(1, Config.DEFAULT_PERIODS + 1))

            # 2. Instantiate and run pure-Python CSP Solver
            scheduler = TimetableScheduler(
                days=days,
                periods=periods,
                sections=sections,
                subjects=subjects,
                faculty=faculty,
                classrooms=classrooms,
                faculty_availability=faculty_avail,
                section_subjects=sec_subjects
            )

            success, timetable_rows, conflict_reasons = scheduler.solve()

            if not success or not timetable_rows:
                # Infeasible or conflict occurred - show clear human-readable explanation
                error_summary = "Timetable generation failed due to constraint conflicts: <br>" + "<br>".join(
                    f"&bull; {r}" for r in conflict_reasons
                )
                flash(error_summary, "error")
                return redirect(url_for("view_timetable"))

            # 3. Transactionally store the generated validated timetable into MySQL
            save_queries = [("DELETE FROM timetable", ())]
            for row in timetable_rows:
                save_queries.append((
                    """INSERT INTO timetable
                       (day, period, subject_id, faculty_id, classroom_id, section_id, class_type)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (row["day"], row["period"], row["subject_id"], row["faculty_id"],
                     row["classroom_id"], row["section_id"], row["class_type"])
                ))

            execute_transaction(save_queries)
            flash(
                f"AI Timetable Generated Successfully! Scheduled {len(timetable_rows)} class periods "
                f"across {len(sections)} sections with 0 hard constraint conflicts.",
                "success"
            )
            return redirect(url_for("view_timetable"))

        except Exception as e:
            flash(f"Unexpected error during timetable generation: {str(e)}", "error")
            return redirect(url_for("view_timetable"))

    @app.route("/timetable")
    @login_required
    def view_timetable():
        try:
            section_id = request.args.get("section_id", type=int)
            faculty_id = request.args.get("faculty_id", type=int)
            room_id = request.args.get("room_id", type=int)

            days = Config.DEFAULT_DAYS
            periods = list(range(1, Config.DEFAULT_PERIODS + 1))
            period_timings = Config.PERIOD_TIMINGS

            sections = execute_query("SELECT * FROM sections ORDER BY year, branch, section_name", fetch="all") or []
            faculty_list = execute_query("SELECT * FROM faculty ORDER BY name", fetch="all") or []
            classrooms = execute_query("SELECT * FROM classrooms ORDER BY room_type, room_number", fetch="all") or []

            # If no filter is specified and sections exist, default to first section for clean grid display
            selected_section = None
            selected_faculty = None
            selected_room = None

            base_query = """
                SELECT t.*, 
                       s.code AS subject_code, s.name AS subject_name,
                       f.name AS faculty_name,
                       c.room_number, c.room_type,
                       sec.year, sec.branch, sec.section_name
                FROM timetable t
                JOIN subjects s ON t.subject_id = s.id
                JOIN faculty f ON t.faculty_id = f.id
                JOIN classrooms c ON t.classroom_id = c.id
                JOIN sections sec ON t.section_id = sec.id
                WHERE 1=1
            """
            params = []

            if section_id:
                base_query += " AND t.section_id = %s"
                params.append(section_id)
                selected_section = next((s for s in sections if s["id"] == section_id), None)
            elif faculty_id:
                base_query += " AND t.faculty_id = %s"
                params.append(faculty_id)
                selected_faculty = next((f for f in faculty_list if f["id"] == faculty_id), None)
            elif room_id:
                base_query += " AND t.classroom_id = %s"
                params.append(room_id)
                selected_room = next((r for r in classrooms if r["id"] == room_id), None)
            elif sections:
                # Default view: First section
                section_id = sections[0]["id"]
                base_query += " AND t.section_id = %s"
                params.append(section_id)
                selected_section = sections[0]

            base_query += " ORDER BY t.day, t.period"
            timetable_rows = execute_query(base_query, tuple(params), fetch="all") or []

            # Build matrix lookup: (day, period) -> list of entries
            schedule_matrix = {}
            for row in timetable_rows:
                key = (row["day"], row["period"])
                if key not in schedule_matrix:
                    schedule_matrix[key] = []
                schedule_matrix[key].append(row)

            return render_template(
                "timetable.html",
                timetable_rows=timetable_rows,
                schedule_matrix=schedule_matrix,
                days=days,
                periods=periods,
                period_timings=period_timings,
                sections=sections,
                faculty_list=faculty_list,
                classrooms=classrooms,
                selected_section=selected_section,
                selected_faculty=selected_faculty,
                selected_room=selected_room
            )
        except Exception as e:
            flash(f"Error fetching timetable: {str(e)}", "error")
            return render_template("timetable.html", timetable_rows=[], schedule_matrix={}, days=[], periods=[])

    @app.route("/timetable/clear")
    @login_required
    def clear_timetable_route():
        try:
            execute_query("TRUNCATE TABLE timetable", commit=True)
            flash("Timetable schedule cleared successfully.", "success")
        except Exception as e:
            flash(f"Error clearing timetable: {str(e)}", "error")
        return redirect(url_for("view_timetable"))

    return app
