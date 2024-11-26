from pydantic import BaseModel
from models.advisor import AdvisorMatch


class Cart(BaseModel):
    """Data model for a cart. to describe PhD application with advisor"""
    advisor: AdvisorMatch
    university: str
    program: str
    deadline: str
    application_cost: str
    application_link: str

class Carts(BaseModel):
    """Data model for a list of carts."""

    carts: list[Cart] 
