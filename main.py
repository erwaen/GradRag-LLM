from config import get_settings
from fastapi import FastAPI
from crawler.crawler import router as crawler_router
from vectorstore.router import router as vectorstore_router
from crawler.professor_router import router as professor_router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI() 

settings = get_settings()

# allow cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(crawler_router, prefix="/api", tags=["crawler"])
app.include_router(vectorstore_router, prefix="/api", tags=["vectorstore"])
app.include_router(professor_router, prefix="/api", tags=["professor"])