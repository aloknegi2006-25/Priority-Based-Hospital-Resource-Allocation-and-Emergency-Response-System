"""
Application Entry Point: Priority-Based Hospital Resource Allocation and Emergency Response System
Team: SysForge | Phase 2: Functional Implementation (~40-50% Verified Completion).
Patient management, triage priority scheduling, resource inventory, atomic allocation/release, and live dashboard.
"""

from flask import Flask, jsonify, request, redirect, url_for, session
from config import Config
from routes import main_bp, patient_bp, resource_bp, allocation_bp, auth_bp

def create_app(config_class=Config):
    """
    Application factory for initializing the Flask web application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(resource_bp)
    app.register_blueprint(allocation_bp)
    app.register_blueprint(auth_bp)

   
   
    @app.before_request
    def require_login():
        allowed_endpoints = ('auth.login', 'static', 'main.health_check')

        if request.endpoint in allowed_endpoints:
            return

        if not session.get('user_id'):
            return redirect(url_for('auth.login'))

        role = session.get('role')

        # Only Admin can manage resources
        admin_only = {
        'main.resources_view',
    'resource_api.list_resources',
    'resource_api.get_resource',
   
}

        # Only Admin and Doctor can manage allocations
        doctor_and_admin = {
    'main.allocations_view',
    'main.release_allocation_view',
    'allocation_api.list_allocations',
    'allocation_api.allocate_resource',
    'allocation_api.release_resource',
    'main.update_case_status_view',
    'patient_api.update_case_status',
}

        # All authenticated roles can access patient and emergency records.
        # Only Admin and Doctor can update case status or allocations.

        if request.endpoint in admin_only and role != 'ADMIN':
            return "Access Denied: Admin only.", 403

        if request.endpoint in doctor_and_admin and role not in ('ADMIN', 'DOCTOR'):
            return "Access Denied: Doctors and Admin only.", 403



    # Global Error Handlers for Clean API Responses
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({
            "error": "Not Found",
            "message": "The requested route does not exist on this server."
        }), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected server condition was encountered."
        }), 500

    return app

# Instantiate application object for WSGI servers / direct execution
app = create_app()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    # Default host to 127.0.0.1 for local isolation unless HOST env var explicitly specifies network access (e.g. 0.0.0.0)
    host = os.environ.get('HOST', '127.0.0.1')
    app.run(host=host, port=port, debug=Config.DEBUG)
