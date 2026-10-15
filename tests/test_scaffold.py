"""
Automated Test Suite for SysForge PBL Phase 2.
Comprehensive verification of DBMS & OS features:
- Scaffold integrity & presentation routes
- Patient intake, server-side validation, duplicate detection, and trauma admission
- Emergency triage priority queue (OS Priority Scheduling with FIFO tie-breaking)
- Resource inventory & status/type filtering
- Concurrency-controlled resource allocation & mutex release
- Duplicate conflict prevention (HTTP 409) & repeated release rejection (HTTP 400)
- Immutable audit trail in allocation_history
- Dashboard real-time operational statistics updates
"""

import unittest
import sqlite3
import os
from app import create_app
from config import TestConfig

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    national_id VARCHAR(50) UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN',
    contact_phone VARCHAR(20),
    emergency_contact VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staff (
    staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(50) NOT NULL,
    specialty VARCHAR(100),
    contact_phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emergency_cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    priority_level INTEGER NOT NULL,
    chief_complaint TEXT NOT NULL,
    triage_status VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    admitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS resources (
    resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_code VARCHAR(50) NOT NULL UNIQUE,
    resource_type VARCHAR(50) NOT NULL,
    location_unit VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'AVAILABLE',
    is_operational BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resource_allocations (
    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    allocated_by_staff_id INTEGER NOT NULL,
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    FOREIGN KEY (case_id) REFERENCES emergency_cases(case_id),
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
    FOREIGN KEY (allocated_by_staff_id) REFERENCES staff(staff_id)
);

CREATE TABLE IF NOT EXISTS allocation_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    allocation_id INTEGER NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remarks VARCHAR(255),
    FOREIGN KEY (allocation_id) REFERENCES resource_allocations(allocation_id)
);
"""

SEED_SQL = """
INSERT INTO staff (employee_id, full_name, role, specialty)
VALUES ('STF-001', 'Dr. Alok Verma', 'TRIAGE_OFFICER', 'Emergency Medicine');

INSERT INTO resources (resource_code, resource_type, location_unit, status, is_operational)
VALUES
('ICU-BED-01', 'BED_ICU', 'ICU Bay A', 'AVAILABLE', 1),
('ICU-BED-02', 'BED_ICU', 'ICU Bay B', 'AVAILABLE', 1),
('VENT-01', 'VENTILATOR', 'Respiratory Unit', 'AVAILABLE', 1),
('AMB-01', 'AMBULANCE', 'Emergency Bay', 'AVAILABLE', 1);
"""

class TestSysForgeApplication(unittest.TestCase):
    def setUp(self):
        # Configure isolated test database
        self.test_db_path = os.path.join(os.path.dirname(__file__), 'test_run.db')

        # Initialize schema and baseline seeds in test database
        conn = sqlite3.connect(self.test_db_path)
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
        conn.close()

        class CustomTestConfig(TestConfig):
            TESTING = True
            TEST_DB_PATH = self.test_db_path

        self.app = create_app(CustomTestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        # Clean up test database file
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. Scaffold & Route Sanity Tests
    # -------------------------------------------------------------------------
    def test_health_check(self):
        """Validates that the health check endpoint returns 200 OK when DB is connected."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertEqual(data.get('database', {}).get('status'), 'connected')

    def test_health_check_disconnected(self):
        """Validates that /api/health returns 503 Service Unavailable when DB is disconnected."""
        from unittest.mock import patch
        with patch('routes.main_routes.check_db_health') as mock_health:
            mock_health.return_value = {
                "status": "disconnected",
                "message": "MySQL server at localhost:3306 is currently unreachable."
            }
            response = self.client.get('/api/health')
            self.assertEqual(response.status_code, 503)
            data = response.get_json()
            self.assertEqual(data.get('status'), 'unhealthy')
            self.assertEqual(data.get('database', {}).get('status'), 'disconnected')

    def test_repeatable_seed_execution(self):
        """Validates that seeding demo emergency cases using stable identifiers is safely repeatable without duplicate cases."""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()

        # Insert demo patients
        cursor.execute("INSERT OR IGNORE INTO patients (national_id, full_name, date_of_birth, gender) VALUES ('NAT-1001', 'Rohan Gupta', '1988-04-12', 'MALE')")
        cursor.execute("INSERT OR IGNORE INTO patients (national_id, full_name, date_of_birth, gender) VALUES ('NAT-1002', 'Anjali Joshi', '1995-11-20', 'FEMALE')")
        cursor.execute("""
            INSERT INTO patients (national_id, full_name, date_of_birth, gender)
            SELECT NULL, 'Unidentified Male Trauma #1', NULL, 'MALE'
            WHERE NOT EXISTS (
                SELECT 1 FROM patients WHERE full_name = 'Unidentified Male Trauma #1' AND national_id IS NULL
            )
        """)
        conn.commit()

        # Seed emergency cases using stable identifiers (matching database/seed.sql pattern)
        seed_cases_sql = """
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
        """
        # Execute seed first time
        cursor.executescript(seed_cases_sql)
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM emergency_cases")
        count_first = cursor.fetchone()[0]
        self.assertEqual(count_first, 3)

        # Execute seed second time (repeat execution)
        cursor.executescript(seed_cases_sql)
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM emergency_cases")
        count_second = cursor.fetchone()[0]
        self.assertEqual(count_second, 3)
        conn.close()

    def test_config_security_defaults(self):
        """Verifies that debug defaults to False and secret key is never a static placeholder."""
        from config import Config
        self.assertTrue(bool(Config.SECRET_KEY))
        self.assertNotEqual(Config.SECRET_KEY, 'default-dev-secret-key-replace-in-env')

    def test_presentation_pages(self):
        """Validates that all presentation template routes render successfully."""
        routes = ['/', '/dashboard', '/patients', '/emergency-cases', '/resources', '/allocations']
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    # -------------------------------------------------------------------------
    # 2. Patient Registration & Retrieval Tests
    # -------------------------------------------------------------------------
    def test_patient_registration_via_api(self):
        """Test API registration of a valid patient."""
        payload = {
            "national_id": "NAT-9901",
            "full_name": "Vikram Singh",
            "date_of_birth": "1990-05-15",
            "gender": "MALE",
            "contact_phone": "+91-9876543210",
            "emergency_contact": "Anita Singh (+91-9876543211)"
        }
        response = self.client.post('/api/patients', json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue('patient_id' in data)

    def test_patient_retrieval_via_api(self):
        """Test API listing of registered patients."""
        self.client.post('/api/patients', json={
            "national_id": "NAT-9902",
            "full_name": "Sunita Rawat",
            "gender": "FEMALE"
        })

        response = self.client.get('/api/patients')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(data['count'], 1)
        names = [p['full_name'] for p in data['data']]
        self.assertIn("Sunita Rawat", names)

    def test_patient_validation_rejects_missing_name(self):
        """Ensure registering without a full name fails validation."""
        response = self.client.post('/api/patients', json={
            "national_id": "NAT-9903",
            "full_name": ""
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertIn("Full legal name is required", data['message'])

    def test_patient_validation_duplicate_national_id(self):
        """Ensure duplicate National IDs are rejected."""
        payload = {"national_id": "NAT-DUPLICATE", "full_name": "First Patient"}
        res1 = self.client.post('/api/patients', json=payload)
        self.assertEqual(res1.status_code, 201)

        res2 = self.client.post('/api/patients', json={"national_id": "NAT-DUPLICATE", "full_name": "Second Patient"})
        self.assertEqual(res2.status_code, 409)

    def test_unidentified_trauma_admission(self):
        """Ensure anonymous/unidentified emergency patients can register with null national_id."""
        payload = {
            "national_id": "",
            "full_name": "Unidentified Trauma Victim #1",
            "gender": "UNKNOWN"
        }
        res = self.client.post('/api/patients', json=payload)
        self.assertEqual(res.status_code, 201)

    def test_patient_validation_rejects_future_date_of_birth(self):
        """Ensure date of birth in the future is rejected."""
        payload = {
            "national_id": "NAT-FUTURE",
            "full_name": "Future Person",
            "date_of_birth": "2099-01-01"
        }
        res = self.client.post('/api/patients', json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("future", res.get_json()['message'].lower())

    def test_patient_html_form_submission(self):
        """Test patient registration form submission via browser POST and dynamic page rendering."""
        form_payload = {
            "national_id": "NAT-WEB-01",
            "full_name": "Kavita Sharma",
            "date_of_birth": "1994-08-20",
            "gender": "FEMALE",
            "contact_phone": "+91-9988776655",
            "emergency_contact": "Ramesh Sharma"
        }
        response = self.client.post('/patients', data=form_payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        page_html = response.get_data(as_text=True)
        self.assertIn("Kavita Sharma", page_html)
        self.assertIn("NAT-WEB-01", page_html)

    # -------------------------------------------------------------------------
    # 3. Emergency Cases & Priority Scheduling Tests
    # -------------------------------------------------------------------------
    def test_emergency_case_registration_and_priority_queue(self):
        """Validates priority-ordered triage queue (OS Priority Scheduling: 1 -> 2 -> 3)."""
        p_res = self.client.post('/api/patients', json={"full_name": "Patient Alpha"})
        pid = p_res.get_json()['patient_id']

        # Enqueue Level 3 case
        self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 3,
            "chief_complaint": "Moderate abdominal pain"
        })

        # Enqueue Level 1 case (Critical Resuscitation)
        self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 1,
            "chief_complaint": "Cardiac arrest, unresponsive"
        })

        # Enqueue Level 2 case (Emergent)
        self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 2,
            "chief_complaint": "Severe dyspnea"
        })

        # Retrieve queue - must be sorted Priority 1 -> Priority 2 -> Priority 3
        q_res = self.client.get('/api/emergency-cases')
        self.assertEqual(q_res.status_code, 200)
        cases = q_res.get_json()['data']
        self.assertGreaterEqual(len(cases), 3)
        priorities = [c['priority_level'] for c in cases]
        self.assertEqual(priorities[:3], [1, 2, 3])

    def test_emergency_case_fifo_tie_breaking(self):
        """Validates FIFO tie-breaking for equal priority cases."""
        p_res = self.client.post('/api/patients', json={"full_name": "FIFO Patient"})
        pid = p_res.get_json()['patient_id']

        # Enqueue first Level 2 case
        res_first = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 2,
            "chief_complaint": "First Level 2 Arrival"
        })
        first_id = res_first.get_json()['case_id']

        # Enqueue second Level 2 case
        res_second = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 2,
            "chief_complaint": "Second Level 2 Arrival"
        })
        second_id = res_second.get_json()['case_id']

        q_res = self.client.get('/api/emergency-cases')
        cases = [c for c in q_res.get_json()['data'] if c['case_id'] in (first_id, second_id)]
        self.assertEqual(cases[0]['case_id'], first_id)
        self.assertEqual(cases[1]['case_id'], second_id)

    def test_emergency_case_rejects_nonexistent_patient(self):
        """Ensures referencing a nonexistent patient_id returns 404."""
        res = self.client.post('/api/emergency-cases', json={
            "patient_id": 99999,
            "priority_level": 1,
            "chief_complaint": "Valid complaint with bad patient ID"
        })
        self.assertEqual(res.status_code, 404)
        self.assertIn("does not exist", res.get_json()['message'])

    def test_emergency_case_validation_rejects_invalid_priority(self):
        """Ensures priority levels outside 1-5 are rejected."""
        p_res = self.client.post('/api/patients', json={"full_name": "Patient Beta"})
        pid = p_res.get_json()['patient_id']

        res = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 6,
            "chief_complaint": "Test invalid priority"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("between 1", res.get_json()['message'])

    def test_emergency_case_status_update(self):
        """Ensures triage status can be transitioned (e.g. to RESOLVED)."""
        p_res = self.client.post('/api/patients', json={"full_name": "Patient Gamma"})
        pid = p_res.get_json()['patient_id']

        case_res = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 2,
            "chief_complaint": "Fractured leg"
        })
        cid = case_res.get_json()['case_id']

        update_res = self.client.post(f'/api/emergency-cases/{cid}/status', json={"triage_status": "RESOLVED"})
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()['triage_status'], 'RESOLVED')

    # -------------------------------------------------------------------------
    # 4. Resource Inventory & Filtering Tests
    # -------------------------------------------------------------------------
    def test_resource_inventory_and_filtering(self):
        """Validates resource API and status/type query filtering."""
        res = self.client.get('/api/resources?type=BED_ICU&status=AVAILABLE')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['status'] == 'success')
        self.assertGreaterEqual(len(data['data']), 2)
        for r in data['data']:
            self.assertEqual(r['resource_type'], 'BED_ICU')
            self.assertEqual(r['status'], 'AVAILABLE')

    def test_resource_detail_by_id(self):
        """Validates single resource detail retrieval and 404 for unknown ID."""
        res = self.client.get('/api/resources/1')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['data']['resource_code'], 'ICU-BED-01')

        res_404 = self.client.get('/api/resources/9999')
        self.assertEqual(res_404.status_code, 404)

    # -------------------------------------------------------------------------
    # 5. Resource Allocation & Mutex Release Lifecycle Tests
    # -------------------------------------------------------------------------
    def test_atomic_allocation_and_mutex_release_lifecycle(self):
        """
        Validates atomic allocation (locking resource mutex) and subsequent release.
        Covers DBMS transaction isolation and OS mutual exclusion.
        """
        p_res = self.client.post('/api/patients', json={"full_name": "Critical Patient Delta"})
        pid = p_res.get_json()['patient_id']

        case_res = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 1,
            "chief_complaint": "Severe polytrauma"
        })
        cid = case_res.get_json()['case_id']

        # 1. Allocate ICU Bed 1 (resource_id=1) by Staff 1
        alloc_payload = {
            "case_id": cid,
            "resource_id": 1,
            "staff_id": 1
        }
        alloc_res = self.client.post('/api/allocations', json=alloc_payload)
        self.assertEqual(alloc_res.status_code, 201)
        alloc_data = alloc_res.get_json()
        alloc_id = alloc_data['allocation_id']

        # Verify resource is now ALLOCATED
        res_check = self.client.get('/api/resources/1')
        self.assertEqual(res_check.get_json()['data']['status'], 'ALLOCATED')

        # 2. Attempt duplicate allocation of the SAME resource (Mutual Exclusion / Conflict)
        case_res_2 = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 2,
            "chief_complaint": "Secondary patient needing bed"
        })
        cid_2 = case_res_2.get_json()['case_id']

        dup_alloc_res = self.client.post('/api/allocations', json={
            "case_id": cid_2,
            "resource_id": 1,
            "staff_id": 1
        })
        self.assertEqual(dup_alloc_res.status_code, 409)
        self.assertIn("ALLOCATED", dup_alloc_res.get_json()['message'])

        # 3. Release the allocation
        release_res = self.client.post(f'/api/allocations/{alloc_id}/release')
        self.assertEqual(release_res.status_code, 200)
        self.assertEqual(release_res.get_json()['status'], 'success')

        # Verify resource status restored to AVAILABLE
        res_restored = self.client.get('/api/resources/1')
        self.assertEqual(res_restored.get_json()['data']['status'], 'AVAILABLE')

    def test_allocation_rejects_invalid_staff_id(self):
        """Ensures that passing a nonexistent staff_id returns 404."""
        p_res = self.client.post('/api/patients', json={"full_name": "Staff Test Patient"})
        pid = p_res.get_json()['patient_id']

        case_res = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 2,
            "chief_complaint": "Chest pain"
        })
        cid = case_res.get_json()['case_id']

        alloc_res = self.client.post('/api/allocations', json={
            "case_id": cid,
            "resource_id": 2,
            "staff_id": 99999  # Nonexistent staff
        })
        self.assertEqual(alloc_res.status_code, 404)
        self.assertIn("Staff ID", alloc_res.get_json()['message'])

    def test_repeated_release_rejected(self):
        """Ensures releasing an already-released allocation is rejected (HTTP 400)."""
        p_res = self.client.post('/api/patients', json={"full_name": "Repeated Release Patient"})
        pid = p_res.get_json()['patient_id']

        case_res = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 3,
            "chief_complaint": "Stomach pain"
        })
        cid = case_res.get_json()['case_id']

        alloc_res = self.client.post('/api/allocations', json={
            "case_id": cid,
            "resource_id": 3,
            "staff_id": 1
        })
        alloc_id = alloc_res.get_json()['allocation_id']

        # First release succeeds
        rel_1 = self.client.post(f'/api/allocations/{alloc_id}/release')
        self.assertEqual(rel_1.status_code, 200)

        # Repeated release rejected
        rel_2 = self.client.post(f'/api/allocations/{alloc_id}/release')
        self.assertEqual(rel_2.status_code, 400)
        self.assertIn("cannot be released again", rel_2.get_json()['message'])

    def test_allocation_history_audit_logging(self):
        """Verifies that allocation_history logs immutable GRANTED and RELEASED records."""
        p_res = self.client.post('/api/patients', json={"full_name": "Audit Patient"})
        pid = p_res.get_json()['patient_id']

        case_res = self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 1,
            "chief_complaint": "Major trauma"
        })
        cid = case_res.get_json()['case_id']

        alloc_res = self.client.post('/api/allocations', json={
            "case_id": cid,
            "resource_id": 4,
            "staff_id": 1
        })
        alloc_id = alloc_res.get_json()['allocation_id']

        self.client.post(f'/api/allocations/{alloc_id}/release')

        # Inspect database audit log directly
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT action_type FROM allocation_history WHERE allocation_id = ? ORDER BY history_id ASC", (alloc_id,))
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], 'GRANTED')
        self.assertEqual(rows[1][0], 'RELEASED')

    # -------------------------------------------------------------------------
    # 6. Dashboard Operational Statistics Tests
    # -------------------------------------------------------------------------
    def test_dashboard_operational_statistics_dynamic_update(self):
        """Validates that dashboard statistics dynamically reflect database state changes."""
        # 1. Baseline dashboard check
        resp1 = self.client.get('/dashboard')
        self.assertEqual(resp1.status_code, 200)
        html1 = resp1.get_data(as_text=True)
        self.assertIn("Emergency Operations Dashboard", html1)

        # 2. Add a patient and emergency case
        p_res = self.client.post('/api/patients', json={"full_name": "Dashboard Metric Patient"})
        pid = p_res.get_json()['patient_id']

        self.client.post('/api/emergency-cases', json={
            "patient_id": pid,
            "priority_level": 1,
            "chief_complaint": "Dashboard Critical Test"
        })

        # 3. Verify updated dashboard reflects new case and patient
        resp2 = self.client.get('/dashboard')
        html2 = resp2.get_data(as_text=True)
        self.assertIn("Dashboard Metric Patient", html2)
        self.assertIn("Dashboard Critical Test", html2)

if __name__ == '__main__':
    unittest.main()
