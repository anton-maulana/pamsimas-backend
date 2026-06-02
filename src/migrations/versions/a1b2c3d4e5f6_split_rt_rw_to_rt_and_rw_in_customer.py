"""split_rt_rw_to_rt_and_rw_in_customer

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-06-02 00:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customer", sa.Column("rt", sa.String(length=20), nullable=False, server_default=""))
    op.add_column("customer", sa.Column("rw", sa.String(length=20), nullable=False, server_default=""))
    # Migrate existing data: split rt_rw on '/'
    op.execute(sa.text(
        "UPDATE customer SET rt = TRIM(SPLIT_PART(rt_rw, '/', 1)), rw = TRIM(SPLIT_PART(rt_rw, '/', 2))"
    ))
    op.drop_column("customer", "rt_rw")


def downgrade() -> None:
    op.add_column("customer", sa.Column("rt_rw", sa.String(length=50), nullable=False, server_default=""))
    op.execute(sa.text(
        "UPDATE customer SET rt_rw = rt || '/' || rw"
    ))
    op.drop_column("customer", "rt")
    op.drop_column("customer", "rw")
