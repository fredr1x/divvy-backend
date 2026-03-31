"""add ITEMIZED to sharetype enum

Revision ID: 2b6b6f0f9a12
Revises: adc5be67ab79
Create Date: 2026-03-28 21:10:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2b6b6f0f9a12"
down_revision: Union[str, Sequence[str], None] = "adc5be67ab79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE sharetype ADD VALUE IF NOT EXISTS 'ITEMIZED'")


def downgrade() -> None:
    # PostgreSQL doesn't support dropping enum values in most versions.
    pass
