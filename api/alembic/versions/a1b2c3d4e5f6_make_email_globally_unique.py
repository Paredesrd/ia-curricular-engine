"""make email globally unique

Elimina la unicidad de email POR tenant (uq_user_tenant_email) y la
reemplaza por unicidad GLOBAL del email (uq_user_email), de modo que el
login pueda hacerse solo con email + password y el backend deduzca el
tenant del propio usuario.

NOTA: si existen emails duplicados entre tenants, el upgrade fallará a
propósito (SQLite recrea la tabla en batch mode y el UNIQUE global
rechazará los duplicados). En desarrollo, borra la BD y regenera; en
producción, limpia duplicados antes de migrar.

Revision ID: a1b2c3d4e5f6
Revises: 841364055659
Create Date: 2026-07-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "841364055659"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("uq_user_tenant_email", type_="unique")
        batch_op.create_unique_constraint("uq_user_email", ["email"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("uq_user_email", type_="unique")
        batch_op.create_unique_constraint(
            "uq_user_tenant_email", ["tenant_id", "email"]
        )