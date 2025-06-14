from .cv_utils import extract_cv_text, extract_subquestions_from_cv
from .retrieval import retrieve_advisors_stream
from fastapi import UploadFile
from typing import Generator


def match_advisors_from_cv_file(cv_file: UploadFile) -> Generator[str, None, None]:
    file_bytes = cv_file.file.read()
    cv_text = extract_cv_text(file_bytes)
    subquestions = extract_subquestions_from_cv(cv_text)

    original_question = "These are the inferred research interests from my CV: " + "; ".join(subquestions)
    return retrieve_advisors_stream(original_question, subquestions)
