"""
Main Web Presentation Routes.
Serves Jinja2 HTML templates, handles browser form submissions, and renders live data.
"""

import logging
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from database.db import check_db_health, execute_query, get_db_transaction
from routes.patient_routes import (
    validate_patient_payload,
    validate_emergency_case_payload,
    VALID_CASE_STATUSES
)

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Renders the landing page with clinical department overview and quick access."""
    return render_template('index.html')


@main_bp.route('/dashboard')
def dashboard():
    """
    Renders the operational dashboard with live aggregated database statistics:
    - Active emergency queue count
    - Priority 1 (Resuscitation) active cases
    - Available vs total ICU beds
    - Active clinical resource allocations
    - Top pending triage cases
    """
    stats = {
        'total_patients': 0,
        'total_resources': 0,
        'active_queue': 0,
        'priority_1_count': 0,
        'icu_available': 0,
        'icu_total': 0,
        'active_allocations': 0,
        'recent_cases': [],
        'vent_available': 0,
        'vent_total': 0,
        'amb_available': 0,
        'amb_total': 0
    }

    try:
        # 0. Total Patients Registered
        pt_row = execute_query("SELECT COUNT(*) AS cnt FROM patients", fetch='one')
        if pt_row:
            stats['total_patients'] = pt_row['cnt']

        # Total Resources in Inventory
        res_tot_row = execute_query("SELECT COUNT(*) AS cnt FROM resources", fetch='one')
        if res_tot_row:
            stats['total_resources'] = res_tot_row['cnt']

        # 1. Active Emergency Queue (QUEUED or IN_TREATMENT)
        q_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM emergency_cases WHERE triage_status IN ('QUEUED', 'IN_TREATMENT')",
            fetch='one'
        )
        if q_row:
            stats['active_queue'] = q_row['cnt']

        # 2. Priority 1 (Critical Resuscitation) Cases
        p1_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM emergency_cases WHERE priority_level = 1 AND triage_status IN ('QUEUED', 'IN_TREATMENT')",
            fetch='one'
        )
        if p1_row:
            stats['priority_1_count'] = p1_row['cnt']

        # 3. ICU Beds Availability
        icu_avail_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM resources WHERE resource_type = 'BED_ICU' AND status = 'AVAILABLE' AND is_operational = 1",
            fetch='one'
        )
        icu_tot_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM resources WHERE resource_type = 'BED_ICU' AND is_operational = 1",
            fetch='one'
        )
        if icu_avail_row:
            stats['icu_available'] = icu_avail_row['cnt']
        if icu_tot_row:
            stats['icu_total'] = icu_tot_row['cnt']

        # 4. Ventilators Availability
        vent_avail_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM resources WHERE resource_type = 'VENTILATOR' AND status = 'AVAILABLE' AND is_operational = 1",
            fetch='one'
        )
        vent_tot_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM resources WHERE resource_type = 'VENTILATOR' AND is_operational = 1",
            fetch='one'
        )
        if vent_avail_row:
            stats['vent_available'] = vent_avail_row['cnt']
        if vent_tot_row:
            stats['vent_total'] = vent_tot_row['cnt']

        # 5. Ambulances Availability
        amb_avail_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM resources WHERE resource_type = 'AMBULANCE' AND status = 'AVAILABLE' AND is_operational = 1",
            fetch='one'
        )
        amb_tot_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM resources WHERE resource_type = 'AMBULANCE' AND is_operational = 1",
            fetch='one'
        )
        if amb_avail_row:
            stats['amb_available'] = amb_avail_row['cnt']
        if amb_tot_row:
            stats['amb_total'] = amb_tot_row['cnt']

        # 6. Active Allocations
        alloc_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM resource_allocations WHERE status = 'ACTIVE'",
            fetch='one'
        )
        if alloc_row:
            stats['active_allocations'] = alloc_row['cnt']

        # 7. Top 5 Pending Triage Queue Cases (Priority ASC, Arrival ASC)
        stats['recent_cases'] = execute_query(
            """
            SELECT c.case_id, c.priority_level, c.chief_complaint, c.triage_status, c.admitted_at,
                   p.full_name AS patient_name
            FROM emergency_cases c
            JOIN patients p ON c.patient_id = p.patient_id
            WHERE c.triage_status IN ('QUEUED', 'IN_TREATMENT')
            ORDER BY c.priority_level ASC, c.admitted_at ASC, c.case_id ASC
            LIMIT 5
            """,
            fetch='all'
        ) or []

    except Exception as e:
        logger.error("Error calculating dashboard statistics: %s", str(e))
        flash("Notice: Operational statistics could not be loaded from database.", 'warning')

    return render_template('dashboard.html', stats=stats)


# -----------------------------------------------------------------------------
# PATIENTS PRESENTATION VIEW
# -----------------------------------------------------------------------------
@main_bp.route('/patients', methods=['GET', 'POST'])
def patients_view():
    """
    Renders the patient registry and processes patient registration form submissions.
    """
    if request.method == 'POST':
        form_data = request.form.to_dict()
        cleaned_data, error = validate_patient_payload(form_data)

        if error:
            flash(error, 'danger')
            return redirect(url_for('main.patients_view'))

        try:
            # Check duplicate National ID if provided
            if cleaned_data['national_id']:
                existing = execute_query(
                    "SELECT patient_id FROM patients WHERE national_id = %s",
                    (cleaned_data['national_id'],),
                    fetch='one'
                )
                if existing:
                    flash(f"A patient with National ID '{cleaned_data['national_id']}' is already registered.", 'warning')
                    return redirect(url_for('main.patients_view'))

            insert_sql = """
                INSERT INTO patients (national_id, full_name, date_of_birth, gender, contact_phone, emergency_contact)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                cleaned_data['national_id'],
                cleaned_data['full_name'],
                cleaned_data['date_of_birth'],
                cleaned_data['gender'],
                cleaned_data['contact_phone'],
                cleaned_data['emergency_contact']
            )
            new_id = execute_query(insert_sql, params)
            flash(f"Patient '{cleaned_data['full_name']}' registered successfully with ID #{new_id}.", 'success')
            return redirect(url_for('main.patients_view'))
        except Exception as e:
            err_msg = str(e).lower()
            if 'duplicate' in err_msg or 'unique' in err_msg:
                flash(f"A patient with National ID '{cleaned_data.get('national_id')}' is already registered.", 'warning')
            else:
                logger.error("Database error while saving patient: %s", str(e))
                flash("Unable to complete patient registration due to a database error.", 'danger')
            return redirect(url_for('main.patients_view'))

    # GET request: Retrieve patients from database
    try:
        patients = execute_query(
            "SELECT patient_id, national_id, full_name, date_of_birth, gender, "
            "contact_phone, emergency_contact, created_at "
            "FROM patients ORDER BY patient_id DESC",
            fetch='all'
        ) or []
    except Exception as e:
        patients = []
        logger.error("Database error loading patients view: %s", str(e))
        flash("Notice: Patient directory could not be loaded from database.", 'warning')

    return render_template('patients.html', patients=patients)


# -----------------------------------------------------------------------------
# EMERGENCY CASES PRESENTATION VIEW
# -----------------------------------------------------------------------------
@main_bp.route('/emergency-cases', methods=['GET', 'POST'])
def emergency_cases_view():
    """
    Renders the emergency triage queue and processes case intake submissions.
    Populates registered patients for the intake dropdown.
    """
    if request.method == 'POST':
        form_data = request.form.to_dict()
        cleaned_data, error = validate_emergency_case_payload(form_data)

        if error:
            flash(error, 'danger')
            return redirect(url_for('main.emergency_cases_view'))

        try:
            # Verify patient exists
            patient = execute_query(
                "SELECT patient_id, full_name FROM patients WHERE patient_id = %s",
                (cleaned_data['patient_id'],),
                fetch='one'
            )
            if not patient:
                flash(f"Referenced Patient ID #{cleaned_data['patient_id']} does not exist.", 'danger')
                return redirect(url_for('main.emergency_cases_view'))

            insert_sql = """
                INSERT INTO emergency_cases (patient_id, priority_level, chief_complaint, triage_status)
                VALUES (%s, %s, %s, %s)
            """
            params = (
                cleaned_data['patient_id'],
                cleaned_data['priority_level'],
                cleaned_data['chief_complaint'],
                cleaned_data['triage_status']
            )
            new_case_id = execute_query(insert_sql, params)
            flash(f"Emergency case #{new_case_id} for '{patient['full_name']}' enqueued with Priority Level {cleaned_data['priority_level']}.", 'success')
            return redirect(url_for('main.emergency_cases_view'))

        except Exception as e:
            logger.error("Database error creating emergency case via form: %s", str(e))
            flash("Unable to create emergency case due to a database error.", 'danger')
            return redirect(url_for('main.emergency_cases_view'))

    # GET: Retrieve registered patients for dropdown and cases for queue table
    try:
        patients = execute_query(
            "SELECT patient_id, full_name, national_id FROM patients ORDER BY full_name ASC",
            fetch='all'
        ) or []
    except Exception as e:
        patients = []
        logger.error("Error retrieving patients for case selector: %s", str(e))

    try:
        cases = execute_query(
            """
            SELECT c.case_id, c.patient_id, p.full_name AS patient_name, p.national_id,
                   c.priority_level, c.chief_complaint, c.triage_status, c.admitted_at
            FROM emergency_cases c
            JOIN patients p ON c.patient_id = p.patient_id
            ORDER BY c.priority_level ASC, c.admitted_at ASC, c.case_id ASC
            """,
            fetch='all'
        ) or []
    except Exception as e:
        cases = []
        logger.error("Error loading emergency queue: %s", str(e))
        flash("Notice: Emergency cases could not be loaded from database.", 'warning')

    return render_template('emergency_cases.html', patients=patients, cases=cases)


@main_bp.route('/emergency-cases/<int:case_id>/status', methods=['POST'])
def update_case_status_view(case_id):
    """Updates the triage status of an emergency case via web form."""
    new_status = request.form.get('status', '').strip().upper()
    if new_status not in VALID_CASE_STATUSES:
        flash(f"Invalid status '{new_status}'.", 'danger')
        return redirect(url_for('main.emergency_cases_view'))

    try:
        case = execute_query("SELECT case_id FROM emergency_cases WHERE case_id = %s", (case_id,), fetch='one')
        if not case:
            flash(f"Emergency case #{case_id} not found.", 'danger')
            return redirect(url_for('main.emergency_cases_view'))

        execute_query("UPDATE emergency_cases SET triage_status = %s WHERE case_id = %s", (new_status, case_id))
        flash(f"Case #{case_id} status updated to '{new_status}'.", 'success')
    except Exception as e:
        logger.error("Error updating case status: %s", str(e))
        flash("Failed to update case status.", 'danger')

    return redirect(url_for('main.emergency_cases_view'))


# -----------------------------------------------------------------------------
# RESOURCES PRESENTATION VIEW
# -----------------------------------------------------------------------------
@main_bp.route('/resources')
def resources_view():
    """
    Renders hospital resource inventory with real database records.
    Supports filtering by resource_type (?type=BED_ICU) and status (?status=AVAILABLE).
    """
    type_filter = request.args.get('type', '').strip().upper()
    status_filter = request.args.get('status', '').strip().upper()

    query = """
        SELECT resource_id, resource_code, resource_type, location_unit, status, is_operational, created_at
        FROM resources
        WHERE 1=1
    """
    params = []
    if type_filter:
        query += " AND resource_type = %s"
        params.append(type_filter)
    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)

    query += " ORDER BY resource_type ASC, resource_code ASC"

    try:
        resources = execute_query(query, params, fetch='all') or []
    except Exception as e:
        resources = []
        logger.error("Error loading resources view: %s", str(e))
        flash("Notice: Resource inventory could not be loaded from database.", 'warning')

    return render_template(
        'resources.html',
        resources=resources,
        current_type=type_filter,
        current_status=status_filter
    )


# -----------------------------------------------------------------------------
# ALLOCATIONS PRESENTATION VIEW
# -----------------------------------------------------------------------------
@main_bp.route('/allocations', methods=['GET', 'POST'])
def allocations_view():
    """
    Renders active and historical resource allocations.
    Handles allocation creation submissions with atomic transaction and row locking.
    """
    if request.method == 'POST':
        raw_case_id = request.form.get('case_id')
        raw_resource_id = request.form.get('resource_id')
        raw_staff_id = request.form.get('staff_id')

        if not raw_case_id or not raw_resource_id:
            flash("Both an emergency case and a clinical resource must be selected.", 'danger')
            return redirect(url_for('main.allocations_view'))

        try:
            case_id = int(raw_case_id)
            resource_id = int(raw_resource_id)
            staff_id = int(raw_staff_id) if raw_staff_id else None
        except (ValueError, TypeError):
            flash("Invalid Case ID or Resource ID selected.", 'danger')
            return redirect(url_for('main.allocations_view'))

        try:
            with get_db_transaction() as tx:
                # 1. Lock resource row
                resource = tx.fetchone(
                    "SELECT resource_id, resource_code, status, is_operational FROM resources WHERE resource_id = %s FOR UPDATE",
                    (resource_id,)
                )
                if not resource:
                    flash("Selected resource was not found.", 'danger')
                    return redirect(url_for('main.allocations_view'))

                if not resource.get('is_operational', True):
                    flash(f"Resource '{resource['resource_code']}' is currently non-operational.", 'danger')
                    return redirect(url_for('main.allocations_view'))

                if resource['status'] != 'AVAILABLE':
                    flash(f"Resource '{resource['resource_code']}' is currently {resource['status']} and cannot be allocated.", 'warning')
                    return redirect(url_for('main.allocations_view'))

                # 2. Lock emergency case row
                case = tx.fetchone(
                    "SELECT case_id, triage_status FROM emergency_cases WHERE case_id = %s FOR UPDATE",
                    (case_id,)
                )
                if not case:
                    flash("Selected emergency case was not found.", 'danger')
                    return redirect(url_for('main.allocations_view'))

                if case['triage_status'] == 'RESOLVED':
                    flash("Cannot allocate resources to a resolved emergency case.", 'warning')
                    return redirect(url_for('main.allocations_view'))

                # 3. Check duplicate active allocation
                existing_active = tx.fetchone(
                    "SELECT allocation_id FROM resource_allocations WHERE resource_id = %s AND status = 'ACTIVE'",
                    (resource_id,)
                )
                if existing_active:
                    flash(f"Resource '{resource['resource_code']}' already has an active allocation.", 'warning')
                    return redirect(url_for('main.allocations_view'))

                # 4. Resolve staff ID
                staff_record = None
                if staff_id:
                    staff_record = tx.fetchone("SELECT staff_id FROM staff WHERE staff_id = %s", (staff_id,))
                    if not staff_record:
                        flash(f"Authorizing Staff ID #{staff_id} was not found.", 'danger')
                        return redirect(url_for('main.allocations_view'))

                if not staff_record:
                    active_staff = tx.fetchone("SELECT staff_id FROM staff WHERE is_active = 1 ORDER BY staff_id ASC LIMIT 1")
                    if not active_staff:
                        active_staff = tx.fetchone("SELECT staff_id FROM staff ORDER BY staff_id ASC LIMIT 1")
                    if not active_staff:
                        flash("No registered hospital staff found to authorize allocation.", 'danger')
                        return redirect(url_for('main.allocations_view'))
                    staff_id = active_staff['staff_id']

                # 5. Insert allocation
                tx.execute(
                    """
                    INSERT INTO resource_allocations (case_id, resource_id, allocated_by_staff_id, status)
                    VALUES (%s, %s, %s, 'ACTIVE')
                    """,
                    (case_id, resource_id, staff_id)
                )
                alloc_id = tx.lastrowid

                # 6. Update resource status
                tx.execute("UPDATE resources SET status = 'ALLOCATED' WHERE resource_id = %s", (resource_id,))

                # 7. Update case status to IN_TREATMENT if QUEUED
                if case['triage_status'] == 'QUEUED':
                    tx.execute("UPDATE emergency_cases SET triage_status = 'IN_TREATMENT' WHERE case_id = %s", (case_id,))

                # 8. Record in audit history
                tx.execute(
                    """
                    INSERT INTO allocation_history (allocation_id, action_type, remarks)
                    VALUES (%s, 'GRANTED', %s)
                    """,
                    (alloc_id, f"Allocated resource {resource['resource_code']} to case #{case_id}")
                )

            flash(f"Resource '{resource['resource_code']}' successfully allocated to Case #{case_id} (Allocation #{alloc_id}).", 'success')
            return redirect(url_for('main.allocations_view'))

        except Exception as e:
            logger.error("Error creating allocation via form: %s", str(e))
            flash("Failed to allocate resource due to a database error.", 'danger')
            return redirect(url_for('main.allocations_view'))

    # GET request: Load allocations, available resources, and eligible cases
    try:
        allocations = execute_query(
            """
            SELECT a.allocation_id, a.case_id, a.resource_id, a.allocated_by_staff_id,
                   a.allocated_at, a.released_at, a.status AS allocation_status,
                   r.resource_code, r.resource_type, r.location_unit,
                   c.priority_level, c.chief_complaint, c.triage_status,
                   p.full_name AS patient_name,
                   COALESCE(s.full_name, 'On-Duty Clinician') AS staff_name
            FROM resource_allocations a
            JOIN resources r ON a.resource_id = r.resource_id
            JOIN emergency_cases c ON a.case_id = c.case_id
            JOIN patients p ON c.patient_id = p.patient_id
            LEFT JOIN staff s ON a.allocated_by_staff_id = s.staff_id
            ORDER BY a.allocation_id DESC
            """,
            fetch='all'
        ) or []
    except Exception as e:
        allocations = []
        logger.error("Error loading allocations: %s", str(e))

    # Eligible cases: QUEUED or IN_TREATMENT
    try:
        eligible_cases = execute_query(
            """
            SELECT c.case_id, c.priority_level, c.chief_complaint, p.full_name AS patient_name
            FROM emergency_cases c
            JOIN patients p ON c.patient_id = p.patient_id
            WHERE c.triage_status IN ('QUEUED', 'IN_TREATMENT')
            ORDER BY c.priority_level ASC, c.admitted_at ASC
            """,
            fetch='all'
        ) or []
    except Exception as e:
        eligible_cases = []

    # Available operational resources
    try:
        available_resources = execute_query(
            """
            SELECT resource_id, resource_code, resource_type, location_unit
            FROM resources
            WHERE status = 'AVAILABLE' AND is_operational = 1
            ORDER BY resource_type ASC, resource_code ASC
            """,
            fetch='all'
        ) or []
    except Exception as e:
        available_resources = []

    # Active staff members
    try:
        staff_members = execute_query(
            "SELECT staff_id, full_name, role FROM staff WHERE is_active = 1 ORDER BY full_name ASC",
            fetch='all'
        ) or []
    except Exception as e:
        staff_members = []

    return render_template(
        'allocations.html',
        allocations=allocations,
        eligible_cases=eligible_cases,
        available_resources=available_resources,
        staff_members=staff_members
    )


@main_bp.route('/allocations/<int:allocation_id>/release', methods=['POST'])
def release_allocation_view(allocation_id):
    """
    Releases an active allocation via web interface form submission.
    Executes inside an atomic transaction with row-level locks.
    """
    try:
        with get_db_transaction() as tx:
            alloc = tx.fetchone(
                """
                SELECT a.allocation_id, a.case_id, a.resource_id, a.status, r.resource_code
                FROM resource_allocations a
                JOIN resources r ON a.resource_id = r.resource_id
                WHERE a.allocation_id = %s FOR UPDATE
                """,
                (allocation_id,)
            )
            if not alloc:
                flash(f"Allocation record #{allocation_id} not found.", 'danger')
                return redirect(url_for('main.allocations_view'))

            if alloc['status'] != 'ACTIVE':
                flash(f"Allocation #{allocation_id} is already marked as {alloc['status']} and cannot be released again.", 'warning')
                return redirect(url_for('main.allocations_view'))

            # Mark allocation RELEASED
            tx.execute(
                """
                UPDATE resource_allocations
                SET status = 'RELEASED', released_at = CURRENT_TIMESTAMP
                WHERE allocation_id = %s
                """,
                (allocation_id,)
            )

            # Revert resource to AVAILABLE
            tx.execute("UPDATE resources SET status = 'AVAILABLE' WHERE resource_id = %s", (alloc['resource_id'],))

            # Record in audit history
            tx.execute(
                """
                INSERT INTO allocation_history (allocation_id, action_type, remarks)
                VALUES (%s, 'RELEASED', %s)
                """,
                (allocation_id, f"Resource {alloc['resource_code']} released back to available pool")
            )

        flash(f"Resource '{alloc['resource_code']}' released successfully. Allocation #{allocation_id} closed.", 'success')

    except Exception as e:
        logger.error("Error releasing allocation: %s", str(e))
        flash("Failed to release resource due to a database error.", 'danger')

    return redirect(url_for('main.allocations_view'))


# -----------------------------------------------------------------------------
# HEALTH CHECK API
# -----------------------------------------------------------------------------
@main_bp.route('/api/health')
def health_check():
    """Health check endpoint returning application state and database reachability."""
    db_status = check_db_health()
    is_connected = (db_status.get('status') == 'connected')
    status_code = 200 if is_connected else 503
    return jsonify({
        "status": "healthy" if is_connected else "unhealthy",
        "service": "Priority-Based Hospital Resource Allocation and Emergency Response System",
        "phase": "Phase 2 (Functional)",
        "database": db_status
    }), status_code
