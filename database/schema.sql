-- =============================================================================
-- DATABASE SCHEMA: Priority-Based Hospital Resource Allocation and Emergency Response System
-- Team: SysForge | Academic Focus: DBMS + OS Concepts
-- Target Database: MySQL 8.0+
-- =============================================================================

CREATE DATABASE IF NOT EXISTS emergency_resource_db;
USE emergency_resource_db;

-- -----------------------------------------------------------------------------
-- 1. PATIENTS TABLE
-- Captures demographic and core intake data.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    national_id VARCHAR(50) UNIQUE NULL,            -- Nullable for unidentified trauma arrivals
    full_name VARCHAR(150) NOT NULL,
    date_of_birth DATE NULL,
    gender ENUM('MALE', 'FEMALE', 'OTHER', 'UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
    contact_phone VARCHAR(20) NULL,
    emergency_contact VARCHAR(150) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 2. STAFF TABLE
-- Tracks hospital personnel who manage triage and authorize resource allocations.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    role ENUM('DOCTOR', 'NURSE', 'TRIAGE_OFFICER', 'ADMINISTRATOR') NOT NULL,
    specialty VARCHAR(100) NULL,
    contact_phone VARCHAR(20) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 3. EMERGENCY_CASES TABLE
-- Models the core acute triage incident (represents the OS Priority Queue element).
-- Priority levels 1-5 follow standard Emergency Severity Index (ESI):
-- 1 = Resuscitation / Immediate
-- 2 = Emergent
-- 3 = Urgent
-- 4 = Less Urgent
-- 5 = Non-urgent
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS emergency_cases (
    case_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    priority_level INT NOT NULL,
    chief_complaint TEXT NOT NULL,
    triage_status ENUM('QUEUED', 'IN_TREATMENT', 'RESOLVED', 'TRANSFERRED') NOT NULL DEFAULT 'QUEUED',
    admitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_priority_range CHECK (priority_level BETWEEN 1 AND 5),
    CONSTRAINT fk_emergency_patient FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
        
    -- Index supporting OS Priority Scheduling queries:
    INDEX idx_priority_triage (priority_level ASC, admitted_at ASC, triage_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 4. RESOURCES TABLE
-- Physical inventory of finite clinical assets subject to mutual exclusion.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resources (
    resource_id INT AUTO_INCREMENT PRIMARY KEY,
    resource_code VARCHAR(50) NOT NULL UNIQUE,      -- e.g., 'ICU-BED-01', 'AMB-03', 'VENT-08'
    resource_type ENUM('BED_GENERAL', 'BED_ICU', 'AMBULANCE', 'VENTILATOR', 'DEFIBRILLATOR') NOT NULL,
    location_unit VARCHAR(100) NOT NULL,            -- e.g., 'Emergency Ward A', 'ICU Bay 2'
    status ENUM('AVAILABLE', 'ALLOCATED', 'MAINTENANCE', 'DISINFECTING') NOT NULL DEFAULT 'AVAILABLE',
    is_operational BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for fast lookup of available resources during allocation:
    INDEX idx_resource_availability (resource_type, status, is_operational)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 5. RESOURCE_ALLOCATIONS TABLE
-- Represents active binding of a resource to an emergency case (OS Mutex / Grant).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resource_allocations (
    allocation_id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL,
    resource_id INT NOT NULL,
    allocated_by_staff_id INT NOT NULL,
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMP NULL,
    status ENUM('ACTIVE', 'RELEASED', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
    
    CONSTRAINT fk_alloc_case FOREIGN KEY (case_id)
        REFERENCES emergency_cases(case_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_alloc_resource FOREIGN KEY (resource_id)
        REFERENCES resources(resource_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_alloc_staff FOREIGN KEY (allocated_by_staff_id)
        REFERENCES staff(staff_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
        
    INDEX idx_active_allocations (resource_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 6. ALLOCATION_HISTORY TABLE
-- Immutable historical audit log for tracking state changes and resource lifecycle.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS allocation_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    allocation_id INT NOT NULL,
    action_type ENUM('GRANTED', 'RELEASED', 'PREEMPTED') NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remarks VARCHAR(255) NULL,
    
    CONSTRAINT fk_history_allocation FOREIGN KEY (allocation_id)
        REFERENCES resource_allocations(allocation_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
