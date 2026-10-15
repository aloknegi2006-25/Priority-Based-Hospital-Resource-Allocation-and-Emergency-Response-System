-- =============================================================================
-- SEED DATA: Development Sample Records for Testing and Demonstration
-- Priority-Based Hospital Resource Allocation and Emergency Response System
-- =============================================================================

USE emergency_resource_db;

-- 1. Insert Initial Hospital Staff
INSERT INTO staff (employee_id, full_name, role, specialty, contact_phone, is_active)
VALUES
    ('EMP-101', 'Dr. Rajesh Sharma', 'DOCTOR', 'Critical Care Medicine', '+91-9876543210', TRUE),
    ('EMP-102', 'Dr. Priya Mehta', 'DOCTOR', 'Trauma Surgery', '+91-9876543211', TRUE),
    ('EMP-103', 'Nurse Sunita Verma', 'TRIAGE_OFFICER', 'Emergency Triage', '+91-9876543212', TRUE),
    ('EMP-104', 'Nurse Amit Rawat', 'NURSE', 'General Intensive Care', '+91-9876543213', TRUE)
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- 2. Insert Finite Hospital Resources
INSERT INTO resources (resource_code, resource_type, location_unit, status, is_operational)
VALUES
    ('ICU-01', 'BED_ICU', 'ICU Ward A - Ground Floor', 'AVAILABLE', TRUE),
    ('ICU-02', 'BED_ICU', 'ICU Ward A - Ground Floor', 'AVAILABLE', TRUE),
    ('ICU-03', 'BED_ICU', 'ICU Ward B - First Floor', 'AVAILABLE', TRUE),
    ('GEN-01', 'BED_GENERAL', 'Emergency Ward 1', 'AVAILABLE', TRUE),
    ('GEN-02', 'BED_GENERAL', 'Emergency Ward 1', 'AVAILABLE', TRUE),
    ('GEN-03', 'BED_GENERAL', 'Emergency Ward 2', 'AVAILABLE', TRUE),
    ('AMB-01', 'AMBULANCE', 'Hospital Transport Bay 1', 'AVAILABLE', TRUE),
    ('AMB-02', 'AMBULANCE', 'Hospital Transport Bay 2', 'AVAILABLE', TRUE),
    ('VENT-01', 'VENTILATOR', 'Respiratory Unit Bay A', 'AVAILABLE', TRUE),
    ('VENT-02', 'VENTILATOR', 'Respiratory Unit Bay B', 'AVAILABLE', TRUE),
    ('DEFIB-01', 'DEFIBRILLATOR', 'Emergency Room Bay 1', 'AVAILABLE', TRUE)
ON DUPLICATE KEY UPDATE location_unit=VALUES(location_unit);

-- 3. Insert Initial Patients
-- Identified patients use ON DUPLICATE KEY UPDATE keyed on unique national_id.
INSERT INTO patients (national_id, full_name, date_of_birth, gender, contact_phone, emergency_contact)
VALUES
    ('NAT-1001', 'Rohan Gupta', '1988-04-12', 'MALE', '+91-9811122233', 'Kavita Gupta (+91-9811122234)'),
    ('NAT-1002', 'Anjali Joshi', '1995-11-20', 'FEMALE', '+91-9822233344', 'Suresh Joshi (+91-9822233345)')
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- Unidentified trauma patient (NULL national_id: check existence before insert to prevent duplicate rows)
INSERT INTO patients (national_id, full_name, date_of_birth, gender, contact_phone, emergency_contact)
SELECT NULL, 'Unidentified Male Trauma #1', NULL, 'MALE', NULL, 'Brought by Bystander'
WHERE NOT EXISTS (
    SELECT 1 FROM patients WHERE full_name = 'Unidentified Male Trauma #1' AND national_id IS NULL
);

-- 4. Insert Emergency Cases (Demonstrating Multi-Level Priority Queue)
-- Locate intended patients using stable identifiers (national_id / full_name) instead of assuming IDs 1, 2, 3.
-- Prevent duplicate demonstration cases if seed is executed repeatedly.

-- Case 1: Priority 2 (Emergent) for NAT-1001
INSERT INTO emergency_cases (patient_id, priority_level, chief_complaint, triage_status)
SELECT p.patient_id, 2, 'Acute Chest Pain, Dyspnea, Suspected Myocardial Infarction', 'QUEUED'
FROM patients p
WHERE p.national_id = 'NAT-1001'
  AND NOT EXISTS (
      SELECT 1 FROM emergency_cases ec
      WHERE ec.patient_id = p.patient_id
        AND ec.chief_complaint = 'Acute Chest Pain, Dyspnea, Suspected Myocardial Infarction'
  )
LIMIT 1;

-- Case 2: Priority 4 (Less Urgent) for NAT-1002
INSERT INTO emergency_cases (patient_id, priority_level, chief_complaint, triage_status)
SELECT p.patient_id, 4, 'Moderate Forearm Fracture, Hemodynamically Stable', 'QUEUED'
FROM patients p
WHERE p.national_id = 'NAT-1002'
  AND NOT EXISTS (
      SELECT 1 FROM emergency_cases ec
      WHERE ec.patient_id = p.patient_id
        AND ec.chief_complaint = 'Moderate Forearm Fracture, Hemodynamically Stable'
  )
LIMIT 1;

-- Case 3: Priority 1 (Resuscitation / Immediate) for Unidentified Trauma Patient
INSERT INTO emergency_cases (patient_id, priority_level, chief_complaint, triage_status)
SELECT p.patient_id, 1, 'Severe Polytrauma, Unresponsive, Immediate Resuscitation Required', 'QUEUED'
FROM patients p
WHERE p.full_name = 'Unidentified Male Trauma #1' AND p.national_id IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM emergency_cases ec
      WHERE ec.patient_id = p.patient_id
        AND ec.chief_complaint = 'Severe Polytrauma, Unresponsive, Immediate Resuscitation Required'
  )
LIMIT 1;
