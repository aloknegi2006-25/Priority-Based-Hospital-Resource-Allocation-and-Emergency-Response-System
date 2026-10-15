"""
Resource Allocation and Release API Routes.
Implements ACID transactions, concurrency control via row-level locks (SELECT ... FOR UPDATE),
duplicate-allocation prevention, and audit history logging.
"""

import logging
from flask import Blueprint, jsonify, request
from database.db import get_db_transaction, execute_query

logger = logging.getLogger(__name__)
allocation_bp = Blueprint('allocation_api', __name__, url_prefix='/api')

@allocation_bp.route('/allocations', methods=['GET'])
def list_allocations():
    """
    Retrieves all resource allocations with joined patient, emergency case, and staff details.
    """
    try:
        query = """
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
        """
        allocations = execute_query(query, fetch='all') or []

        for item in allocations:
            if item.get('allocated_at') and hasattr(item['allocated_at'], 'isoformat'):
                item['allocated_at'] = item['allocated_at'].isoformat()
            if item.get('released_at') and hasattr(item['released_at'], 'isoformat'):
                item['released_at'] = item['released_at'].isoformat()

        return jsonify({
            "status": "success",
            "count": len(allocations),
            "data": allocations
        }), 200

    except Exception as e:
        logger.error("Error retrieving allocations: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve allocation records at this time."
        }), 500


@allocation_bp.route('/allocations', methods=['POST'])
def allocate_resource():
    """
    Allocates an available resource to an emergency case inside an isolated atomic transaction.
    Enforces row-level locking (SELECT ... FOR UPDATE) to prevent race conditions & double allocation.
    """
    payload = request.get_json(silent=True) or request.form.to_dict()
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "message": "Invalid request format."}), 400

    raw_case_id = payload.get('case_id')
    raw_resource_id = payload.get('resource_id')
    raw_staff_id = payload.get('staff_id')

    if not raw_case_id or not raw_resource_id:
        return jsonify({"status": "error", "message": "Both case_id and resource_id are required."}), 400

    try:
        case_id = int(raw_case_id)
        resource_id = int(raw_resource_id)
        staff_id = int(raw_staff_id) if raw_staff_id else None
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Case ID and Resource ID must be valid integers."}), 400

    try:
        with get_db_transaction() as tx:
            # 1. Lock and inspect resource row to prevent concurrent double-booking
            resource = tx.fetchone(
                "SELECT resource_id, resource_code, resource_type, status, is_operational "
                "FROM resources WHERE resource_id = %s FOR UPDATE",
                (resource_id,)
            )
            if not resource:
                return jsonify({"status": "error", "message": f"Resource #{resource_id} not found."}), 404

            if not resource.get('is_operational', True):
                return jsonify({
                    "status": "error",
                    "message": f"Resource '{resource['resource_code']}' is currently non-operational."
                }), 400

            if resource['status'] != 'AVAILABLE':
                return jsonify({
                    "status": "error",
                    "message": f"Resource '{resource['resource_code']}' is currently {resource['status']} and cannot be allocated."
                }), 409

            # 2. Verify emergency case exists and is eligible for care
            case = tx.fetchone(
                "SELECT case_id, patient_id, priority_level, triage_status "
                "FROM emergency_cases WHERE case_id = %s FOR UPDATE",
                (case_id,)
            )
            if not case:
                return jsonify({"status": "error", "message": f"Emergency case #{case_id} not found."}), 404

            if case['triage_status'] == 'RESOLVED':
                return jsonify({
                    "status": "error",
                    "message": f"Emergency case #{case_id} is marked as RESOLVED and cannot receive new allocations."
                }), 400

            # 3. Check for existing active allocation on this specific resource
            existing_active = tx.fetchone(
                "SELECT allocation_id FROM resource_allocations WHERE resource_id = %s AND status = 'ACTIVE'",
                (resource_id,)
            )
            if existing_active:
                return jsonify({
                    "status": "error",
                    "message": f"Resource '{resource['resource_code']}' is already assigned to an active case."
                }), 409

            # 4. Resolve staff authorization (use provided or fallback to active on-duty staff)
            staff_record = None
            if staff_id:
                staff_record = tx.fetchone("SELECT staff_id FROM staff WHERE staff_id = %s", (staff_id,))
                if not staff_record:
                    return jsonify({"status": "error", "message": f"Authorizing Staff ID #{staff_id} not found."}), 404

            if not staff_record:
                active_staff = tx.fetchone("SELECT staff_id FROM staff WHERE is_active = 1 ORDER BY staff_id ASC LIMIT 1")
                if not active_staff:
                    active_staff = tx.fetchone("SELECT staff_id FROM staff ORDER BY staff_id ASC LIMIT 1")
                if not active_staff:
                    return jsonify({"status": "error", "message": "No registered hospital staff found to authorize allocation."}), 400
                staff_id = active_staff['staff_id']

            # 5. Insert allocation record
            tx.execute(
                """
                INSERT INTO resource_allocations (case_id, resource_id, allocated_by_staff_id, status)
                VALUES (%s, %s, %s, 'ACTIVE')
                """,
                (case_id, resource_id, staff_id)
            )
            allocation_id = tx.lastrowid

            # 6. Update resource status to ALLOCATED
            tx.execute(
                "UPDATE resources SET status = 'ALLOCATED' WHERE resource_id = %s",
                (resource_id,)
            )

            # 7. Advance case status to IN_TREATMENT if it was previously QUEUED
            if case['triage_status'] == 'QUEUED':
                tx.execute(
                    "UPDATE emergency_cases SET triage_status = 'IN_TREATMENT' WHERE case_id = %s",
                    (case_id,)
                )

            # 8. Record audit log in allocation_history
            tx.execute(
                """
                INSERT INTO allocation_history (allocation_id, action_type, remarks)
                VALUES (%s, 'GRANTED', %s)
                """,
                (allocation_id, f"Allocated resource {resource['resource_code']} to case #{case_id}")
            )

        return jsonify({
            "status": "success",
            "message": f"Resource '{resource['resource_code']}' successfully allocated to Case #{case_id}.",
            "allocation_id": allocation_id,
            "resource_code": resource['resource_code'],
            "case_id": case_id
        }), 201

    except Exception as e:
        logger.error("Error during resource allocation transaction: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Resource allocation failed due to a database error."
        }), 500


@allocation_bp.route('/allocations/<int:allocation_id>/release', methods=['POST'])
def release_resource(allocation_id):
    """
    Releases an active allocation, reverts resource status to AVAILABLE,
    and logs the deallocation in allocation_history within an atomic transaction.
    """
    try:
        with get_db_transaction() as tx:
            # 1. Fetch and lock allocation record
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
                return jsonify({"status": "error", "message": f"Allocation #{allocation_id} not found."}), 404

            if alloc['status'] != 'ACTIVE':
                return jsonify({
                    "status": "error",
                    "message": f"Allocation #{allocation_id} is already marked as {alloc['status']} and cannot be released again."
                }), 400

            # 2. Mark allocation as RELEASED with timestamp
            tx.execute(
                """
                UPDATE resource_allocations
                SET status = 'RELEASED', released_at = CURRENT_TIMESTAMP
                WHERE allocation_id = %s
                """,
                (allocation_id,)
            )

            # 3. Return resource back to AVAILABLE pool
            tx.execute(
                "UPDATE resources SET status = 'AVAILABLE' WHERE resource_id = %s",
                (alloc['resource_id'],)
            )

            # 4. Record release in allocation_history
            tx.execute(
                """
                INSERT INTO allocation_history (allocation_id, action_type, remarks)
                VALUES (%s, 'RELEASED', %s)
                """,
                (allocation_id, f"Resource {alloc['resource_code']} released back to available pool")
            )

        return jsonify({
            "status": "success",
            "message": f"Resource '{alloc['resource_code']}' released successfully. Allocation #{allocation_id} closed."
        }), 200

    except Exception as e:
        logger.error("Error releasing allocation #%s: %s", allocation_id, str(e))
        return jsonify({
            "status": "error",
            "message": "Failed to release resource due to a database error."
        }), 500
