from enum import Enum

class Type(str, Enum):
    DEPOSIT = "DEPOSIT"
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
