"""add split type, refund user id to expense_split, add share type, currency to group_expense

Revision ID: 434d2bbe4adb
Revises: a27e7f3335a5
Create Date: 2026-03-17 10:44:41.972095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '434d2bbe4adb'
down_revision: Union[str, Sequence[str], None] = 'a27e7f3335a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    split_type_enum = postgresql.ENUM('ORIGINAL', 'REFUND', 'ADJUSTMENT', name='split_type')
    split_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'expense_splits',
        sa.Column('split_type', split_type_enum, nullable=False, server_default='ORIGINAL'),
    )
    op.add_column('expense_splits', sa.Column('refund_to_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'expense_splits', 'users', ['refund_to_user_id'], ['id'])
    op.drop_column('expense_splits', 'share_type')
    op.add_column(
        'group_expenses',
        sa.Column(
            'currency',
            sa.Enum('USD', 'EUR', 'TNG', name='currency', create_constraint=True),
            nullable=False,
            server_default='USD',
        ),
    )
    op.add_column(
        'group_expenses',
        sa.Column(
            'share_type',
            sa.Enum('EQUAL', 'EXACT', 'PERCENTAGE', name='sharetype'),
            nullable=False,
            server_default='EQUAL',
        ),
    )
    op.alter_column('expense_splits', 'split_type', server_default=None)
    op.alter_column('group_expenses', 'currency', server_default=None)
    op.alter_column('group_expenses', 'share_type', server_default=None)

def downgrade() -> None:
    op.drop_column('group_expenses', 'share_type')
    op.drop_column('group_expenses', 'currency')
    op.add_column('expense_splits', sa.Column('share_type', postgresql.ENUM('EQUAL', 'EXACT', 'PERCENTAGE', name='sharetype'), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'expense_splits', type_='foreignkey')
    op.drop_column('expense_splits', 'refund_to_user_id')
    op.drop_column('expense_splits', 'split_type')
    split_type_enum = postgresql.ENUM('ORIGINAL', 'REFUND', 'ADJUSTMENT', name='split_type')
    split_type_enum.drop(op.get_bind(), checkfirst=True)
