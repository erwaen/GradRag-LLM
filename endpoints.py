from fastapi import APIRouter, HTTPException
from typing import List
from models.advisor import AdvisorMatch
from models.student import StudentQuery
from config import get_settings

router = APIRouter()
settings = get_settings()

# @router.post("/advisors/match", response_model=List[AdvisorMatch])
# async def get_matching_advisors(query: StudentQuery):
#     try:
#         # Format the query string
#         query_str = f"""
#         Find professors matching:
#         Research Interests: {', '.join(query.research_interests)}
#         Locations: {', '.join(query.preferred_locations)}
#         Background: {query.background}
#         Specific Interests: {query.specific_interests}
#         GPA: {query.gpa}
#         """
        
#         matches = rag_pipeline.generate_list_of_advisors(query_str)
#         return matches
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
# @router.get("/scrape")
# async def scrape_csrankings():
#     try:
#         scraper = CSRankingsSpiderScraper(api_key=settings.SPIDER_API_KEY)
#         professors = scraper.scrape_and_save()
#         return {"message": f"Successfully scraped {len(professors)} professors"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))