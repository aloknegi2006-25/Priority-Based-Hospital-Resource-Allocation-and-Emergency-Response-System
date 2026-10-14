"""
Routes package initialization.
Exports all blueprints for registration in the Flask app.
"""

from .main_routes import main_bp
from .patient_routes import patient_bp
from .resource_routes import resource_bp
from .allocation_routes import allocation_bp

__all__ = ['main_bp', 'patient_bp', 'resource_bp', 'allocation_bp']
