"""update currency enum values

Revision ID: e7b1c2a9f4d8
Revises: 2b6b6f0f9a12
Create Date: 2026-03-30
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e7b1c2a9f4d8"
down_revision: Union[str, Sequence[str], None] = "2b6b6f0f9a12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'currency' AND e.enumlabel = 'TNG'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'currency' AND e.enumlabel = 'KZT'
            ) THEN
                ALTER TYPE currency RENAME VALUE 'TNG' TO 'KZT';
            END IF;
        END $$;
        """
    )

    op.execute("ALTER TYPE currency ADD VALUE IF NOT EXISTS 'JPY'")
    op.execute("ALTER TYPE currency ADD VALUE IF NOT EXISTS 'CNY'")
    op.execute("ALTER TYPE currency ADD VALUE IF NOT EXISTS 'RUB'")


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'currency' AND e.enumlabel = 'KZT'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'currency' AND e.enumlabel = 'TNG'
            ) THEN
                ALTER TYPE currency RENAME VALUE 'KZT' TO 'TNG';
            END IF;
        END $$;
        """
    )
