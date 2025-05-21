from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AdvisorApplication(BaseModel):
    deadline: datetime
    requirements: List[str]
    funding_available: bool
    gre_required: bool
    minimum_gpa: Optional[float]

class AdvisorMatch(BaseModel):
    """
    Data model for an advisor match.

    The explanation of why this advisor is a good fit should be one paragraph long, based on the user's question, to clearly articulate the reasons.
    """
    name: str
    university: str
    research_areas: List[str]
    email:  Optional[str] = None
    website: str
    match_score: float  
    why_good_fit: str  # Personalized explanation
