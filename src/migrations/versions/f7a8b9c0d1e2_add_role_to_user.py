"""add_role_to_user

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-05-20 00:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "c35f88f56a91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('officer', 'superadmin');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.add_column(
        "user",
        sa.Column(
            "role",
            sa.Enum("officer", "superadmin", name="userrole", create_type=False),
            nullable=False,
            server_default="officer",
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "role")
    op.execute("DROP TYPE IF EXISTS userrole")
