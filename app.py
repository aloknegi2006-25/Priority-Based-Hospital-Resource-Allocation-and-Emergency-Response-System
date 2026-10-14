"""
Application Entry Point: Priority-Based Hospital Resource Allocation and Emergency Response System
Team: SysForge | Academic Focus: DBMS + OS Concepts
Phase 2: Scaffolding Only. Business logic and algorithms deferred to Phase 3.
"""

from flask import Flask, jsonify
from config import Config
from routes import main_bp, patient_bp, resource_bp, allocation_bp

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
    # Local development server execution (port 5001 avoids macOS AirPlay conflict)
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
