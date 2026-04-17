"""add card_balance, currency_rate tables

Revision ID: 91e9f0d36eac
Revises: e75a437845a7
Create Date: 2026-04-17 08:55:56.610346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '91e9f0d36eac'
down_revision: Union[str, Sequence[str], None] = 'e75a437845a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    currency_enum = postgresql.ENUM(
        "USD", "EUR", "KZT", "JPY", "CNY", "RUB",
        name="currency",
        create_type=False,
    )

    op.create_table(
        "card_balances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("currency", currency_enum, nullable=False),
        sa.Column("balance", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["virtual_cards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "currency", name="unique_card_currency"),
    )

    op.create_table(
        "currency_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("currency", currency_enum, nullable=False),
        sa.Column("base_currency", currency_enum, nullable=False),
        sa.Column("rate", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("currency"),
    )

    op.execute(
        """
        INSERT INTO card_balances (card_id, currency, balance)
        SELECT id, 'USD'::currency, balance
        FROM virtual_cards
        """
    )
    op.drop_column("virtual_cards", "balance")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "virtual_cards",
        sa.Column(
            "balance",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.execute(
        """
        UPDATE virtual_cards AS vc
        SET balance = cb.balance
        FROM card_balances AS cb
        WHERE cb.card_id = vc.id
          AND cb.currency = 'USD'::currency
        """
    )
    op.alter_column("virtual_cards", "balance", server_default=None)

    op.drop_table("currency_rates")
    op.drop_table("card_balances")
