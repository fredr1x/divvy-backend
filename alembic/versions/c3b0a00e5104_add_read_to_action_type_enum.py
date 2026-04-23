"""add READ to action_type enum

Revision ID: c3b0a00e5104
Revises: b27a073aeeba
Create Date: 2026-04-23 11:36:06.009943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3b0a00e5104'
down_revision: Union[str, Sequence[str], None] = 'b27a073aeeba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TYPE action_type ADD VALUE 'READ'")


def downgrade():
    # PostgreSQL does NOT support removing enum values easily
    pass
