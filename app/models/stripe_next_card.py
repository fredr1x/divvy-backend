from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class StripeNextCard(Base):
    __tablename__ = 'stripe_next_card'

    id: Mapped[int] = mapped_column(primary_key=True)

    number: Mapped[int] = mapped_column("number", Integer, default=0)
