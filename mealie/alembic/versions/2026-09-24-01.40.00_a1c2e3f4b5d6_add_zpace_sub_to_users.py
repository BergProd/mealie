"""add zpace_sub to users

Revision ID: a1c2e3f4b5d6
Revises: 3527efeeec34
Create Date: 2026-09-24 01:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a1c2e3f4b5d6"
down_revision: str | None = "3527efeeec34"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("zpace_sub", sa.String(), nullable=True))
    op.create_index("ix_users_zpace_sub", "users", ["zpace_sub"], unique=True)


def downgrade():
    op.drop_index("ix_users_zpace_sub", table_name="users")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("zpace_sub")
