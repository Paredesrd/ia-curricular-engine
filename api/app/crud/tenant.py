"""
api/app/crud/tenant.py
CRUD del modelo Tenant.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models.tenant import Tenant


# Reglas de acreditación por defecto para un tenant recién fundado.
# Estructura compatible con TenantRules del núcleo.
DEFAULT_ACCREDITATION_RULES: dict = {
    "min_total_hours": 20,
    "max_total_hours": 40,
    "min_module_hours": 4,
    "max_module_hours": 10,
    "required_bloom_levels": ["remember", "understand", "apply", "analyze"],
    "min_lessons_per_module": 2,
    "max_lessons_per_module": 5,
    "custom_restrictions": None,
}


def get_tenant_by_id(db: Session, tenant_id: uuid.UUID) -> Tenant | None:
    """Obtiene un tenant por su ID."""
    return db.get(Tenant, tenant_id)


def get_tenant_by_slug(db: Session, slug: str) -> Tenant | None:
    """Obtiene un tenant por su slug único."""
    stmt = select(Tenant).where(Tenant.slug == slug)
    return db.execute(stmt).scalar_one_or_none()


def create_tenant(
    db: Session,
    *,
    name: str,
    slug: str,
    accreditation_rules: dict | None = None,
) -> Tenant:
    """Crea un tenant. NO hace commit (lo decide el llamador)."""
    tenant = Tenant(
        name=name,
        slug=slug,
        accreditation_rules=accreditation_rules or DEFAULT_ACCREDITATION_RULES,
    )
    db.add(tenant)
    db.flush()
    return tenant


def update_tenant_rules(
    db: Session,
    tenant: Tenant,
    rules: dict,
) -> Tenant:
    """
    Reemplaza las reglas de acreditación del tenant. NO hace commit.
    Reasignación completa del dict para que SQLAlchemy detecte el cambio en JSON.
    """
    tenant.accreditation_rules = dict(rules)
    db.add(tenant)
    db.flush()
    return tenant