-- =======================================================
-- SmartShed AI: AI-Based Automated Timetable Generator
-- Database Schema for MySQL Community Server
-- =======================================================

CREATE DATABASE IF NOT EXISTS smartshed_ai;
USE smartshed_ai;

-- 1. Administrator table for authentication
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Faculty master table
CREATE TABLE IF NOT EXISTS faculty (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    department VARCHAR(100) NOT NULL,
    email VARCHAR(150) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Faculty availability table (day and period slots)
CREATE TABLE IF NOT EXISTS faculty_availability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT NOT NULL,
    day VARCHAR(20) NOT NULL,
    period INT NOT NULL,
    is_available TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uq_faculty_day_period (faculty_id, day, period),
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Subjects master table (Theory or Lab)
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    type ENUM('Theory', 'Lab') NOT NULL DEFAULT 'Theory',
    periods_per_week INT NOT NULL DEFAULT 4,
    lab_duration INT NOT NULL DEFAULT 1,
    preferred_faculty_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (preferred_faculty_id) REFERENCES faculty(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Classrooms & Labs master table
CREATE TABLE IF NOT EXISTS classrooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_number VARCHAR(50) NOT NULL UNIQUE,
    room_type ENUM('Classroom', 'Lab') NOT NULL DEFAULT 'Classroom',
    capacity INT NOT NULL DEFAULT 60,
    building VARCHAR(100) DEFAULT 'Main Academic Block',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Student Sections master table
CREATE TABLE IF NOT EXISTS sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    year VARCHAR(20) NOT NULL,
    branch VARCHAR(100) NOT NULL,
    section_name VARCHAR(20) NOT NULL,
    student_strength INT NOT NULL DEFAULT 60,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_year_branch_sec (year, branch, section_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Section Subject Assignment (Optional link table if specific sections have specific subjects/faculty assigned)
CREATE TABLE IF NOT EXISTS section_subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    section_id INT NOT NULL,
    subject_id INT NOT NULL,
    faculty_id INT NULL,
    UNIQUE KEY uq_sec_sub (section_id, subject_id),
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Timetable generated schedule table
CREATE TABLE IF NOT EXISTS timetable (
    id INT AUTO_INCREMENT PRIMARY KEY,
    day VARCHAR(20) NOT NULL,
    period INT NOT NULL,
    subject_id INT NOT NULL,
    faculty_id INT NOT NULL,
    classroom_id INT NOT NULL,
    section_id INT NOT NULL,
    class_type ENUM('Theory', 'Lab') NOT NULL DEFAULT 'Theory',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
    INDEX idx_sec_slot (section_id, day, period),
    INDEX idx_fac_slot (faculty_id, day, period),
    INDEX idx_room_slot (classroom_id, day, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
