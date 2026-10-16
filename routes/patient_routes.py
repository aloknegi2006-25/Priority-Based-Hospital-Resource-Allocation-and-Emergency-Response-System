"""
Patient and Emergency Case Management API Routes.
Provides endpoints for patient registration and emergency triage case management.
Features server-side validation, parameterized queries, priority queue sorting, and ACID compliance.
"""

import logging
from datetime import datetime, date
from flask import Blueprint, jsonify, request
from database.db import execute_query

logger = logging.getLogger(__name__)
patient_bp = Blueprint('patient_api', __name__, url_prefix='/api')

VALID_GENDERS = {'MALE', 'FEMALE', 'OTHER', 'UNKNOWN'}
VALID_CASE_STATUSES = {'QUEUED', 'IN_TREATMENT', 'RESOLVED', 'TRANSFERRED'}

# -----------------------------------------------------------------------------
# PATIENT VALIDATION & ENDPOINTS
# -----------------------------------------------------------------------------

def validate_patient_payload(data):
    """
    Validates and cleans patient input payload.
    Returns:
        tuple: (cleaned_dict, error_string or None)
    """
    if not isinstance(data, dict):
        return None, "Invalid request payload format. Expected JSON or form data."

    # Validate full_name (Required, 2-150 chars)
    full_name = str(data.get('full_name', '')).strip()
    if not full_name:
        return None, "Full legal name is required."
    if len(full_name) < 2 or len(full_name) > 150:
        return None, "Full name must be between 2 and 150 characters."

    # Validate gender (Optional, default UNKNOWN; reject invalid values)
    raw_gender = data.get('gender')
    if raw_gender is None or str(raw_gender).strip() == "":
        gender = 'UNKNOWN'
    else:
        gender_upper = str(raw_gender).strip().upper()
        if gender_upper not in VALID_GENDERS:
            return None, "Invalid gender value. Supported values are: MALE, FEMALE, OTHER, UNKNOWN."
        gender = gender_upper

    # Validate national_id (Optional, nullable for trauma intake)
    raw_national_id = data.get('national_id')
    national_id = str(raw_national_id).strip() if raw_national_id else None
    if national_id == "":
        national_id = None
    if national_id and len(national_id) > 50:
        return None, "National ID cannot exceed 50 characters."

    # Validate date_of_birth (Optional, format YYYY-MM-DD, not in future)
    raw_dob = data.get('date_of_birth')
    dob = str(raw_dob).strip() if raw_dob else None
    if dob == "":
        dob = None
    if dob:
        try:
            parsed_dob = datetime.strptime(dob, '%Y-%m-%d').date()
            if parsed_dob > date.today():
                return None, "Date of birth cannot be in the future."
        except ValueError:
            return None, "Date of birth must be a valid date in YYYY-MM-DD format."

    # Validate contact_phone (Optional, max 20 chars)
    raw_phone = data.get('contact_phone')
    contact_phone = str(raw_phone).strip() if raw_phone else None
    if contact_phone == "":
        contact_phone = None
    if contact_phone and len(contact_phone) > 20:
        return None, "Contact phone number cannot exceed 20 characters."

    # Validate emergency_contact (Optional, max 150 chars)
    raw_ec = data.get('emergency_contact')
    emergency_contact = str(raw_ec).strip() if raw_ec else None
    if emergency_contact == "":
        emergency_contact = None
    if emergency_contact and len(emergency_contact) > 150:
        return None, "Emergency contact cannot exceed 150 characters."

    cleaned = {
        'national_id': national_id,
        'full_name': full_name,
        'date_of_birth': dob,
        'gender': gender,
        'contact_phone': contact_phone,
        'emergency_contact': emergency_contact
    }
    return cleaned, None


@patient_bp.route('/patients', methods=['GET'])
def list_patients():
    """Retrieves all registered patients ordered by registration timestamp descending."""
    try:
        patients = execute_query(
            "SELECT patient_id, national_id, full_name, date_of_birth, gender, "
            "contact_phone, emergency_contact, created_at "
            "FROM patients ORDER BY patient_id DESC",
            fetch='all'
        ) or []

        for p in patients:
            if p.get('date_of_birth') and hasattr(p['date_of_birth'], 'isoformat'):
                p['date_of_birth'] = p['date_of_birth'].isoformat()
            if p.get('created_at') and hasattr(p['created_at'], 'isoformat'):
                p['created_at'] = p['created_at'].isoformat()

        return jsonify({
            "status": "success",
            "count": len(patients),
            "data": patients
        }), 200

    except Exception as e:
        logger.error("Error retrieving patient records: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve patient directory records at this time."
        }), 500


@patient_bp.route('/patients', methods=['POST'])
def create_patient():
    """Registers a new patient with parameterized SQL query."""
    payload = request.get_json(silent=True) or request.form.to_dict()
    cleaned_data, error = validate_patient_payload(payload)

    if error:
        return jsonify({"status": "error", "message": error}), 400

    try:
        if cleaned_data['national_id']:
            existing = execute_query(
                "SELECT patient_id FROM patients WHERE national_id = %s",
                (cleaned_data['national_id'],),
                fetch='one'
            )
            if existing:
                return jsonify({
                    "status": "error",
                    "message": f"A patient with National ID '{cleaned_data['national_id']}' is already registered."
                }), 409

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

        return jsonify({
            "status": "success",
            "message": "Patient record registered successfully.",
            "patient_id": new_id,
            "data": cleaned_data
        }), 201

    except Exception as e:
        err_msg = str(e).lower()
        if 'duplicate' in err_msg or 'unique' in err_msg:
            return jsonify({
                "status": "error",
                "message": f"A patient with National ID '{cleaned_data.get('national_id')}' already exists."
            }), 409
        logger.error("Database error during patient registration: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Failed to complete patient registration due to a database error."
        }), 500


# -----------------------------------------------------------------------------
# EMERGENCY CASE VALIDATION & ENDPOINTS (STAGE B)
# -----------------------------------------------------------------------------

def validate_emergency_case_payload(data):
    """
    Validates payload for creating or updating an emergency case.
    Enforces foreign-key existence, priority 1-5, and non-empty chief complaint.
    Returns:
        tuple: (cleaned_dict, error_string or None)
    """
    if not isinstance(data, dict):
        return None, "Invalid request payload format. Expected JSON or form data."

    # Validate patient_id (Required integer)
    raw_patient_id = data.get('patient_id')
    if raw_patient_id is None or str(raw_patient_id).strip() == "":
        return None, "Patient selection is required for emergency intake."
    try:
        patient_id = int(raw_patient_id)
        if patient_id <= 0:
            return None, "Patient ID must be a positive integer."
    except (ValueError, TypeError):
        return None, "Invalid Patient ID format."

    # Validate priority_level (Required integer between 1 and 5)
    # Priority 1 = Resuscitation (highest), 5 = Non-urgent
    raw_priority = data.get('priority_level')
    if raw_priority is None or str(raw_priority).strip() == "":
        return None, "Clinical priority tier (1 to 5) is required."
    try:
        priority_level = int(raw_priority)
        if priority_level < 1 or priority_level > 5:
            return None, "Priority level must be an integer between 1 (Immediate) and 5 (Non-urgent)."
    except (ValueError, TypeError):
        return None, "Priority level must be a numeric integer between 1 and 5."

    # Validate chief_complaint (Required text)
    chief_complaint = str(data.get('chief_complaint', '')).strip()
    if not chief_complaint:
        return None, "Chief complaint description is required."
    if len(chief_complaint) < 3:
        return None, "Chief complaint must be at least 3 characters long."

    # Validate triage_status (Optional, default QUEUED)
    raw_status = data.get('triage_status')
    if raw_status is None or str(raw_status).strip() == "":
        triage_status = 'QUEUED'
    else:
        status_upper = str(raw_status).strip().upper()
        if status_upper not in VALID_CASE_STATUSES:
            return None, f"Invalid triage status. Supported statuses are: {', '.join(sorted(VALID_CASE_STATUSES))}."
        triage_status = status_upper

    cleaned = {
        'patient_id': patient_id,
        'priority_level': priority_level,
        'chief_complaint': chief_complaint,
        'triage_status': triage_status
    }
    return cleaned, None


@patient_bp.route('/emergency-cases', methods=['GET'])
def list_emergency_cases():
    """
    Retrieves active emergency cases sorted by clinical priority (OS Priority Queue):
    Primary sort: priority_level ASC (1 is highest urgency)
    Secondary sort: admitted_at ASC (FIFO for equal priority)
    Tie-breaker: case_id ASC
    """
    try:
        query = """
            SELECT c.case_id, c.patient_id, p.full_name AS patient_name, p.national_id,
                   c.priority_level, c.chief_complaint, c.triage_status, c.admitted_at, c.updated_at
            FROM emergency_cases c
            JOIN patients p ON c.patient_id = p.patient_id
            ORDER BY c.priority_level ASC, c.admitted_at ASC, c.case_id ASC
        """
        cases = execute_query(query, fetch='all') or []

        for c in cases:
            if c.get('admitted_at') and hasattr(c['admitted_at'], 'isoformat'):
                c['admitted_at'] = c['admitted_at'].isoformat()
            if c.get('updated_at') and hasattr(c['updated_at'], 'isoformat'):
                c['updated_at'] = c['updated_at'].isoformat()

        return jsonify({
            "status": "success",
            "count": len(cases),
            "data": cases
        }), 200

    except Exception as e:
        logger.error("Error retrieving emergency cases: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve emergency queue records at this time."
        }), 500


@patient_bp.route('/emergency-cases', methods=['POST'])
def create_emergency_case():
    """
    Creates a new emergency case under staff confirmation.
    Validates patient foreign key reference, priority scale, and inserts record.
    """
    payload = request.get_json(silent=True) or request.form.to_dict()
    cleaned_data, error = validate_emergency_case_payload(payload)

    if error:
        return jsonify({"status": "error", "message": error}), 400

    try:
        # Verify foreign key: Patient must exist
        patient = execute_query(
            "SELECT patient_id, full_name FROM patients WHERE patient_id = %s",
            (cleaned_data['patient_id'],),
            fetch='one'
        )
        if not patient:
            return jsonify({
                "status": "error",
                "message": f"Referenced Patient ID #{cleaned_data['patient_id']} does not exist."
            }), 404

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

        return jsonify({
            "status": "success",
            "message": "Emergency case queued successfully.",
            "case_id": new_case_id,
            "patient_name": patient['full_name'],
            "priority_level": cleaned_data['priority_level'],
            "triage_status": cleaned_data['triage_status']
        }), 201

    except Exception as e:
        logger.error("Database error creating emergency case: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Failed to create emergency case due to a database error."
        }), 500


@patient_bp.route('/emergency-cases/<int:case_id>/status', methods=['POST'])
def update_case_status(case_id):
    """Updates the triage status of an existing emergency case.

    Prevents marking a case RESOLVED while any active resource allocations remain,
    ensuring case, allocation, and resource records stay consistent.
    """
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    new_status = str(payload.get('status') or payload.get('triage_status') or '').strip().upper()

    if new_status not in VALID_CASE_STATUSES:
        return jsonify({
            "status": "error",
            "message": f"Invalid status. Supported statuses are: {', '.join(sorted(VALID_CASE_STATUSES))}."
        }), 400

    try:
        case = execute_query(
            "SELECT case_id, triage_status FROM emergency_cases WHERE case_id = %s",
            (case_id,),
            fetch='one'
        )
        if not case:
            return jsonify({"status": "error", "message": f"Emergency case #{case_id} not found."}), 404

        # Prevent RESOLVED if active allocations still exist for this case.
        if new_status == 'RESOLVED':
            active_allocs = execute_query(
                "SELECT COUNT(*) AS cnt FROM resource_allocations "
                "WHERE case_id = %s AND status = 'ACTIVE'",
                (case_id,),
                fetch='one'
            )
            if active_allocs and active_allocs['cnt'] > 0:
                return jsonify({
                    "status": "error",
                    "message": (
                        f"Case #{case_id} cannot be marked RESOLVED while "
                        f"{active_allocs['cnt']} active allocation(s) remain. "
                        "Release all resources before closing the case."
                    )
                }), 409

        execute_query(
            "UPDATE emergency_cases SET triage_status = %s WHERE case_id = %s",
            (new_status, case_id)
        )
        return jsonify({
            "status": "success",
            "message": f"Case #{case_id} status updated to {new_status}.",
            "triage_status": new_status
        }), 200

    except Exception as e:
        logger.error("Error updating case status: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Failed to update case status due to a database error."
        }), 500
