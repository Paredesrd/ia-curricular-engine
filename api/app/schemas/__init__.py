"""
api/app/schemas/__init__.py
Schemas Pydantic de request/response de la API.
"""

from api.app.schemas.tenant import (
    TenantResponse,
    TenantDetailResponse,
    AccreditationRulesPayload,
)
from api.app.schemas.user import (
    UserRegisterRequest,
    UserResponse,
    UserWithTenantResponse,
    TokenResponse,
)
from api.app.schemas.course import (
    CourseCreateRequest,
    CourseSummary,
    CourseResponse,
)

__all__ = [
    "TenantResponse",
    "TenantDetailResponse",
    "AccreditationRulesPayload",
    "UserRegisterRequest",
    "UserResponse",
    "UserWithTenantResponse",
    "TokenResponse",
    "CourseCreateRequest",
    "CourseSummary",
    "CourseResponse",
]