"""make new_values, old_values list

Revision ID: 14552c9ba0ea
Revises: c3b0a00e5104
Create Date: 2026-04-26 09:29:24.100160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14552c9ba0ea'
down_revision: Union[str, Sequence[str], None] = 'c3b0a00e5104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        UPDATE audit_logs
        SET old_values = json_build_array(old_values)
        WHERE old_values IS NOT NULL
          AND json_typeof(old_values) = 'object'
        """
    )
    op.execute(
        """
        UPDATE audit_logs
        SET new_values = json_build_array(new_values)
        WHERE new_values IS NOT NULL
          AND json_typeof(new_values) = 'object'
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        UPDATE audit_logs
        SET old_values = old_values -> 0
        WHERE old_values IS NOT NULL
          AND json_typeof(old_values) = 'array'
          AND json_array_length(old_values) = 1
          AND json_typeof(old_values -> 0) = 'object'
        """
    )
    op.execute(
        """
        UPDATE audit_logs
        SET new_values = new_values -> 0
        WHERE new_values IS NOT NULL
          AND json_typeof(new_values) = 'array'
          AND json_array_length(new_values) = 1
          AND json_typeof(new_values -> 0) = 'object'
        """
    )
