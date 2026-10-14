"""
Patient and Emergency Case API Route Stubs.
Endpoints return HTTP 501 (Not Implemented) to indicate scaffold status.
"""

from flask import Blueprint, jsonify, request

patient_bp = Blueprint('patient_api', __name__, url_prefix='/api')

@patient_bp.route('/patients', methods=['GET'])
def list_patients():
    """
    Stub for retrieving patient directory records.
    TODO (Phase 3 - Alok Negi): Query MySQL `patients` table with pagination.
    """
    return jsonify({
        "status": "not_implemented",
        "module": "Patient Records",
        "message": "Patient retrieval logic is scaffolded. Implementation deferred to Phase 3.",
        "assigned_to": "Alok Negi (Data Layer)"
    }), 501

@patient_bp.route('/patients', methods=['POST'])
def create_patient():
    """
    Stub for registering a new patient.
    TODO (Phase 3 - Alok Negi): Validate input and execute parameterized INSERT into `patients`.
    """
    return jsonify({
        "status": "not_implemented",
        "module": "Patient Intake",
        "message": "Patient registration logic is scaffolded. Implementation deferred to Phase 3.",
        "assigned_to": "Alok Negi (Data Layer)"
    }), 501

@patient_bp.route('/emergency-cases', methods=['GET'])
def list_emergency_cases():
    """
    Stub for listing active emergency cases ordered by priority.
    TODO (Phase 3 - Apoorv Barthwal): Implement OS Priority Queue retrieval logic.
    """
    return jsonify({
        "status": "not_implemented",
        "module": "Emergency Cases",
        "message": "Priority Queue retrieval logic is scaffolded. Implementation deferred to Phase 3.",
        "assigned_to": "Apoorv Barthwal (Priority Engine)"
    }), 501

@patient_bp.route('/emergency-cases', methods=['POST'])
def create_emergency_case():
    """
    Stub for submitting an emergency triage case with assigned priority.
    TODO (Phase 3 - Apoorv Barthwal): Compute priority tier and enqueue case in database.
    """
    return jsonify({
        "status": "not_implemented",
        "module": "Emergency Triage",
        "message": "Triage intake logic is scaffolded. Implementation deferred to Phase 3.",
        "assigned_to": "Apoorv Barthwal (Priority Engine)"
    }), 501
