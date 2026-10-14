"""
Main Web Presentation Routes.
Serves Jinja2 HTML templates and basic health status.
"""

from flask import Blueprint, render_template, jsonify
from database.db import check_db_health

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Renders the landing page with project summary, architecture, and team roles."""
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """Renders the high-level system dashboard placeholder."""
    return render_template('dashboard.html')

@main_bp.route('/patients')
def patients_view():
    """Renders the patient registry and intake form placeholder."""
    return render_template('patients.html')

@main_bp.route('/emergency-cases')
def emergency_cases_view():
    """Renders the emergency triage priority queue view placeholder."""
    return render_template('emergency_cases.html')

@main_bp.route('/resources')
def resources_view():
    """Renders the hospital resource inventory overview placeholder."""
    return render_template('resources.html')

@main_bp.route('/allocations')
def allocations_view():
    """Renders the active resource allocation and release management view placeholder."""
    return render_template('allocations.html')

@main_bp.route('/api/health')
def health_check():
    """
    Health check endpoint returning application state and database reachability.
    """
    db_status = check_db_health()
    return jsonify({
        "status": "healthy",
        "service": "Priority-Based Hospital Resource Allocation and Emergency Response System",
        "phase": "Phase 2 (Scaffold)",
        "database": db_status
    }), 200
