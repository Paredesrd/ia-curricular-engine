"""
api/app/models/__init__.py
Registro central de modelos ORM.
Importar este paquete garantiza que todos los modelos queden
registrados en Base.metadata (necesario para create_all / Alembic).
"""

from api.app.core.db import Base
from api.app.models.tenant import Tenant
from api.app.models.user import User
from api.app.models.course import Course

__all__ = [
    "Base",
    "Tenant",
    "User",
    "Course",
]