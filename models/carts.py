from pydantic import BaseModel
from models.advisor import AdvisorMatch
from typing import Optional

class Cart(BaseModel):
    """Data model for a cart. to describe PhD application with advisor"""
    advisor: AdvisorMatch
    university: str
    application_deadline: Optional[str]
    gpa_requirement: Optional[str]
    gre_requirement: Optional[str]
    funding_available: Optional[str] # could be "Full", "Partial", "None"

class Carts(BaseModel):
    """Data model for a list of carts."""

    carts: list[Cart]