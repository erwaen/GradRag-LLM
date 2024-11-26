from pydantic import BaseModel
from typing import List

class StudentQuery(BaseModel):
    research_interests: List[str]
    preferred_locations: List[str]
    background: str
    specific_interests: str
    gpa: float
    test_scores: dict