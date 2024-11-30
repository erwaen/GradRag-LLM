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
    name: str
    university: str
    # department: str
    research_areas: List[str]
    # recent_publications: List[str]
    # current_projects: List[str]
    email: str
    website: str
    match_score: float  # Relevance to student's interests
    # application_details: AdvisorApplication
    why_good_fit: str  # Personalized explanation