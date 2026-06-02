"""normalize_rt_rw_to_number_in_customer

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-02 00:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Strip "RT " and "RW " prefixes so rt/rw store just the numeric part (e.g. "01")
    op.execute(sa.text("UPDATE customer SET rt = TRIM(REPLACE(rt, 'RT ', ''))"))
    op.execute(sa.text("UPDATE customer SET rw = TRIM(REPLACE(rw, 'RW ', ''))"))

    op.alter_column("customer", "rt", type_=sa.String(length=5), existing_type=sa.String(length=20))
    op.alter_column("customer", "rw", type_=sa.String(length=5), existing_type=sa.String(length=20))


def downgrade() -> None:
    op.alter_column("customer", "rt", type_=sa.String(length=20), existing_type=sa.String(length=5))
    op.alter_column("customer", "rw", type_=sa.String(length=20), existing_type=sa.String(length=5))

    # Restore "RT "/"RW " prefixes
    op.execute(sa.text("UPDATE customer SET rt = 'RT ' || rt"))
    op.execute(sa.text("UPDATE customer SET rw = 'RW ' || rw"))
