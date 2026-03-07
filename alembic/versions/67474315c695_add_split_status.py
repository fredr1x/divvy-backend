"""add split status

Revision ID: 67474315c695
Revises: 528e8570972c
Create Date: 2026-03-02 08:09:06.381137

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '67474315c695'
down_revision: Union[str, Sequence[str], None] = '528e8570972c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

split_status_enum = postgresql.ENUM(
    'PAYER', 'PENDING', 'PAID', name='split_status', create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    split_status_enum.create(bind, checkfirst=True)
    op.add_column(
        'expense_splits',
        sa.Column(
            'split_status',
            split_status_enum,
            nullable=False,
            server_default=sa.text("'PENDING'::split_status"),
        ),
    )
    op.add_column('expense_splits', sa.Column('paid_at', sa.DateTime(), nullable=True))
    op.alter_column('expense_splits', 'split_status', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    op.drop_column('expense_splits', 'paid_at')
    op.drop_column('expense_splits', 'split_status')
    split_status_enum.drop(bind, checkfirst=True)
