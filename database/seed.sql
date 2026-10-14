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
INSERT INTO patients (national_id, full_name, date_of_birth, gender, contact_phone, emergency_contact)
VALUES
    ('NAT-1001', 'Rohan Gupta', '1988-04-12', 'MALE', '+91-9811122233', 'Kavita Gupta (+91-9811122234)'),
    ('NAT-1002', 'Anjali Joshi', '1995-11-20', 'FEMALE', '+91-9822233344', 'Suresh Joshi (+91-9822233345)'),
    (NULL, 'Unidentified Male Trauma #1', NULL, 'MALE', NULL, 'Brought by Bystander')
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- 4. Insert Emergency Cases (Demonstrating Multi-Level Priority Queue)
INSERT INTO emergency_cases (patient_id, priority_level, chief_complaint, triage_status)
VALUES
    (1, 2, 'Acute Chest Pain, Dyspnea, Suspected Myocardial Infarction', 'QUEUED'),
    (2, 4, 'Moderate Forearm Fracture, Hemodynamically Stable', 'QUEUED'),
    (3, 1, 'Severe Polytrauma, Unresponsive, Immediate Resuscitation Required', 'QUEUED')
ON DUPLICATE KEY UPDATE chief_complaint=VALUES(chief_complaint);
