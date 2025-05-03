from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from .chunking import get_advisor_documents, store_advisor_documents
from .retrieval import retrieve_advisors_stream
from pydantic import BaseModel
from .multiquery import generate_queries
router = APIRouter()


# @router.get("/doc_advisor")
# def doc_advisor():
#     documents = get_advisor_documents()
#     index = store_advisor_documents(documents)
#     return {"message": "Documents stored"} 

class Body(BaseModel):
    q: str

@router.post("/retrieve_advisors")
def retrieve_advisors_api(body: Body):
    print(body)
    queries = generate_queries(body.q)
    stream = retrieve_advisors_stream(body.q, queries)
    return StreamingResponse(stream, media_type="text/plain")