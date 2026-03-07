"""normalize split_status enum name

Revision ID: 9a6f2c1b4d10
Revises: d15ce5338985
Create Date: 2026-03-06 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9a6f2c1b4d10"
down_revision: Union[str, Sequence[str], None] = "d15ce5338985"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'splitstatus'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'split_status'
            ) THEN
                ALTER TYPE splitstatus RENAME TO split_status;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'split_status'
            ) THEN
                CREATE TYPE split_status AS ENUM ('PAYER', 'PENDING', 'PAID');
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        DECLARE current_udt text;
        BEGIN
            SELECT c.udt_name
            INTO current_udt
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.table_name = 'expense_splits'
              AND c.column_name = 'split_status';

            IF current_udt IS NOT NULL AND current_udt <> 'split_status' THEN
                EXECUTE '
                    ALTER TABLE expense_splits
                    ALTER COLUMN split_status TYPE split_status
                    USING split_status::text::split_status
                ';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'split_status'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'splitstatus'
            ) THEN
                ALTER TYPE split_status RENAME TO splitstatus;
            END IF;
        END $$;
        """
    )
