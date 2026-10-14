"""
Hospital Resource Inventory API Route Stubs.
Endpoints return HTTP 501 (Not Implemented) to indicate scaffold status.
"""

from flask import Blueprint, jsonify, request

resource_bp = Blueprint('resource_api', __name__, url_prefix='/api')

@resource_bp.route('/resources', methods=['GET'])
def list_resources():
    """
    Stub for retrieving hospital resource inventory (Beds, ICUs, Ambulances, Devices).
    TODO (Phase 3 - Akshit Chauhan): Query MySQL `resources` table with optional type/status filter.
    """
    return jsonify({
        "status": "not_implemented",
        "module": "Resource Inventory",
        "message": "Resource status query logic is scaffolded. Implementation deferred to Phase 3.",
        "assigned_to": "Akshit Chauhan (Resource Engine)"
    }), 501

@resource_bp.route('/resources/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    """
    Stub for retrieving single resource detail.
    TODO (Phase 3 - Akshit Chauhan): Fetch resource record by ID.
    """
    return jsonify({
        "status": "not_implemented",
        "module": "Resource Detail",
        "resource_id": resource_id,
        "message": "Resource retrieval logic is scaffolded. Implementation deferred to Phase 3.",
        "assigned_to": "Akshit Chauhan (Resource Engine)"
    }), 501
