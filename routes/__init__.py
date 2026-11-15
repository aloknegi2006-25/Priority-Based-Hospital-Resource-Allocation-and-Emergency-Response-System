from .main_routes import main_bp
from .patient_routes import patient_bp
from .resource_routes import resource_bp
from .allocation_routes import allocation_bp
from .auth_routes import auth_bp

__all__ = [
    'main_bp',
    'patient_bp',
    'resource_bp',
    'allocation_bp',
    'auth_bp'
]