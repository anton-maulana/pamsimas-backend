"""add_phone_address_to_user

Revision ID: b3c4d5e6f7a8
Revises: 2436edcb2870
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "2436edcb2870"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("user", sa.Column("address", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "address")
    op.drop_column("user", "phone")
