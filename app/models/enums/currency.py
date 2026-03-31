import enum


class Currency(str, enum.Enum):
    USD = "USD"
    EUR = "EUR"
    KZT = "KZT"
    JPY = "JPY"
    CNY = "CNY"
    RUB = "RUB"
