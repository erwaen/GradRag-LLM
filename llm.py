from llama_index.llms.ollama import Ollama
from pydantic import BaseModel
from typing import List
from guidance import models
from models.carts import Carts
from models.advisor import AdvisorMatch

from llama_index.program.guidance import GuidancePydanticProgram
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine



llm = Ollama(model="llama3.2", request_timeout=120)




prompt_advisors_tmp_str = """\
Generate a list of advisors based on a prospective PhD student's question. \
The question is: {question}\
"""
def genereate_list_of_advisors(question):
    program = LLMTextCompletionProgram.from_defaults(
        llm=llm,
        output_cls=Carts,
        prompt_template_str=prompt_advisors_tmp_str,
        verbose=True,
    )
    output = program(question=question)
    return output

def create_advisor_query_engine(index: VectorStoreIndex) -> RetrieverQueryEngine:
    # Configure query engine with structured output
    query_engine = index.as_query_engine(
        output_cls=AdvisorMatch,
        response_mode="compact",
        similarity_top_k=5  # Retrieve top 5 most relevant professors
    )
    return query_engine
