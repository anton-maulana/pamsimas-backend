"""add_officer_id_and_remaining_columns_to_customer

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-05-20 00:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customer", sa.Column("officer_id", sa.Integer(), nullable=True))
    op.create_index(op.f('ix_customer_officer_id'), 'customer', ['officer_id'], unique=False)
    op.create_foreign_key('fk_customer_officer_id', 'customer', 'user', ['officer_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_customer_officer_id', 'customer', type_='foreignkey')
    op.drop_index(op.f('ix_customer_officer_id'), table_name='customer')
    op.drop_column("customer", "officer_id")
