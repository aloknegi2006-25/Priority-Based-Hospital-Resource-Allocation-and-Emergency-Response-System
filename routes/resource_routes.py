"""
Hospital Resource Inventory API Routes.
Provides endpoints for querying available, allocated, and maintenance hospital assets.
"""

import logging
from flask import Blueprint, jsonify, request
from database.db import execute_query

logger = logging.getLogger(__name__)
resource_bp = Blueprint('resource_api', __name__, url_prefix='/api')

@resource_bp.route('/resources', methods=['GET'])
def list_resources():
    """
    Retrieves hospital resource inventory (Beds, ICUs, Ambulances, Devices).
    Supports optional query filtering by status (?status=AVAILABLE) or type (?type=BED_ICU).
    """
    status_filter = request.args.get('status')
    type_filter = request.args.get('type')

    query = """
        SELECT resource_id, resource_code, resource_type, location_unit, status, is_operational, created_at
        FROM resources
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND status = %s"
        params.append(status_filter.upper())
    if type_filter:
        query += " AND resource_type = %s"
        params.append(type_filter.upper())

    query += " ORDER BY resource_type ASC, resource_code ASC"

    try:
        resources = execute_query(query, params, fetch='all') or []
        for r in resources:
            if r.get('created_at') and hasattr(r['created_at'], 'isoformat'):
                r['created_at'] = r['created_at'].isoformat()

        return jsonify({
            "status": "success",
            "count": len(resources),
            "data": resources
        }), 200

    except Exception as e:
        logger.error("Error retrieving resources: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve clinical resource inventory at this time."
        }), 500


@resource_bp.route('/resources/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    """Retrieves single clinical asset detail by ID."""
    try:
        resource = execute_query(
            "SELECT resource_id, resource_code, resource_type, location_unit, status, is_operational, created_at "
            "FROM resources WHERE resource_id = %s",
            (resource_id,),
            fetch='one'
        )
        if not resource:
            return jsonify({"status": "error", "message": f"Resource #{resource_id} not found."}), 404

        if resource.get('created_at') and hasattr(resource['created_at'], 'isoformat'):
            resource['created_at'] = resource['created_at'].isoformat()

        return jsonify({
            "status": "success",
            "data": resource
        }), 200

    except Exception as e:
        logger.error("Error fetching resource #%s: %s", resource_id, str(e))
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve resource record."
        }), 500
