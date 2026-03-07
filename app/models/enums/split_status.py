import enum

class SplitStatus(str, enum.Enum):
    PAYER = "PAYER"
    PENDING = "PENDING"
    PAID = "PAID"
