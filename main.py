from typing import Union
from config import get_settings
from fastapi import FastAPI
from llm import llm,  genereate_list_of_advisors
from endpoints import router as advisors_router
from crawler.crawler import router as crawler_router
app = FastAPI() 

settings = get_settings()

@app.get("/complete")
def complete(q: str):
    response = llm.complete(q)
    print(response)
    return {"response": response.text}


@app.get("/advisors")
def get_advisors(q:str):
    advisors =genereate_list_of_advisors(q)
    return {"advisors": advisors}

app.include_router(advisors_router, prefix="/api", tags=["advisors"])
app.include_router(crawler_router, prefix="/api", tags=["crawler"])