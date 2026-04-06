from pydantic import BaseModel

class StripeCreateCardResponse(BaseModel):
    customer_id: str
    payment_method_id: str
    card_number: str
    card_last4: str
    card_exp_month: int
    card_exp_year: int
    card_brand: str
    card_description: str
