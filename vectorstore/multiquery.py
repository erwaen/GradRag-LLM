# from llama_index.core import PromptTemplate
# from llama_index.llms.openai import OpenAI
import openai
from config import get_settings

settings = get_settings()
openai.api_key = settings.OPENAI_API_KEY
#query_gen_prompt = PromptTemplate(query_gen_str)




def generate_queries(query: str, num_queries: int = 4):
    prompt =  f"""\
You are a helpful assistant that generates multiple search queries based on the user's single input query. \
Generate {num_queries} search queries, one on each line, focusing on searching \
for the perfect advisor related to the following input query: 
Query: {query} 
Queries:
"""
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates multiple questions from the user's query"},
            {"role": "user", "content": prompt}
        ],
        temperature= 0.6
    )
    content = response.choices[0].message.content
    queries = content.strip().split("\n")
    return [q.strip("-•1234567890. ") for q in queries if q.strip()]