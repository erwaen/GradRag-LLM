from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from .retrieval import retrieve_advisors_stream
from .multiquery import is_relevant_question
from pydantic import BaseModel
from .multiquery import generate_queries
from fastapi import HTTPException
from fastapi import UploadFile
from .cv_retrieval import match_advisors_from_cv_file

router = APIRouter()


@router.post("/match_cv_advisors")
def match_cv_advisors(cv_file: UploadFile):
    stream = match_advisors_from_cv_file(cv_file)
    return StreamingResponse(stream, media_type="text/plain")


class Body(BaseModel):
    q: str
    model: str = "gpt"

@router.post("/retrieve_advisors")
def retrieve_advisors_api(body: Body):
    print(body)
    model = body.model.lower()

    # Perform query validation before starting the advisors retrieval
    if not is_relevant_question(body.q):
        raise HTTPException(
            status_code=422,
            detail="Query is not related to PhD advisor matching or academic research."
        )
    queries = generate_queries(body.q)
    stream = retrieve_advisors_stream(body.q, queries, model)
    return StreamingResponse(stream, media_type="text/plain")
