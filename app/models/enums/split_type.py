import enum

class SplitType(str, enum.Enum):
    ORIGINAL = "ORIGINAL"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"
