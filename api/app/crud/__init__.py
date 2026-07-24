"""
api/app/crud/__init__.py
Operaciones CRUD sobre los modelos ORM.
"""

from api.app.crud import tenant as tenant_crud
from api.app.crud import user as user_crud
from api.app.crud import course as course_crud

__all__ = ["tenant_crud", "user_crud", "course_crud"]