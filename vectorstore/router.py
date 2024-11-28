from fastapi import APIRouter
from fastapi.responses import JSONResponse
from .chunking import get_advisor_documents, store_advisor_documents
from .retrieval import retrieve_advisors

router = APIRouter()


@router.get("/doc_advisor")
def doc_advisor():
    documents = get_advisor_documents()
    index = store_advisor_documents(documents)
    return {"message": "Documents stored"} 

@router.get("/retrieve_advisors")
def retrieve_advisors_api(question: str):
    results = retrieve_advisors(question)
    return {"results": results}