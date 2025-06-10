import fitz  # PyMuPDF
import openai
from config import get_settings
from typing import List

settings = get_settings()
openai.api_key = settings.OPENAI_API_KEY

def extract_cv_text(file_data: bytes) -> str:
    doc = fitz.open(stream=file_data, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def extract_subquestions_from_cv(cv_text: str, num_questions: int = 5) -> List[str]:
    prompt = f"""\
You are a helpful assistant that reads a student's academic CV and generates specific research-related questions \
they might ask when looking for a PhD advisor. Based on the CV below, generate {num_questions} relevant questions \
they might ask a potential advisor. Output one question per line.

CV:
{cv_text}

Questions:
"""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You're an assistant that extracts research interests from CVs."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    content = response.choices[0].message.content
    questions = content.strip().split("\n")
    return [q.strip("-•1234567890. ") for q in questions if q.strip()]
