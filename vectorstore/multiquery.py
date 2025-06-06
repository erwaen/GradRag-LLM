from llama_index.core import PromptTemplate
from llama_index.llms.openai import OpenAI
from config import get_settings

settings = get_settings()

query_gen_str = """\
You are a helpful assistant that generates multiple search queries based on the user's single input query. \
Generate {num_queries} search queries, one on each line, focusing on searching \
for the perfect advisor related to the following input query: 
Query: {query} 
Queries:
"""
query_gen_prompt = PromptTemplate(query_gen_str)




def generate_queries(query: str, num_queries: int = 4):
    llm = OpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
    response = llm.predict(
        query_gen_prompt, num_queries=num_queries, query=query
    )
    # assume LLM proper put each query on a newline
    queries = response.split("\n")
    return queries