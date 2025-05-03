#from llama_index.core import VectorStoreIndex
#from typing import List
#from llama_index.core.schema import NodeRelationship
#from llama_index.core.schema import NodeWithScore
#from llama_index.llms.openai import OpenAI
#from llama_index.core.schema import MetadataMode
#from llama_index.core import StorageContext
#from llama_index.vector_stores.qdrant import QdrantVectorStore
#from llama_index.embeddings.openai import OpenAIEmbedding
#from llama_index.postprocessor.cohere_rerank import CohereRerank
#from llama_index.core.program import LLMTextCompletionProgram
#from llama_index.core import Settings
from config import get_settings
from qdrant_client import QdrantClient
#from models.carts import Carts
#import os


import openai
from openai import OpenAI
from qdrant_client.models import Filter, SearchParams, PointStruct
from qdrant_client.http.models import SearchRequest, ScoredPoint
from typing import Generator
import time

import json
from typing import List


def get_embedding(question: str) -> List[float]:
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response=client.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def retrieve_advisors_stream(original_question: str, question: str) -> Generator[str, None, None]:
    start_time = time.time()  # Start measuring time

    settings = get_settings()
    openai.api_key = settings.OPENAI_API_KEY

    client = QdrantClient(
        url="http://localhost:6333"
        #url=settings.QDRANT_URL,
        #api_key=settings.QDRANT_API_KEY,
    )
    embedding_start = time.time()
    # 1. Embed the query
    query_vector = get_embedding(question)
    embedding_time = time.time() - embedding_start
    print(f"Embedding time: {embedding_time:.2f} seconds")

    # 2. Perform vector search
    search_start = time.time()
    search_results: List[ScoredPoint] = client.search(
        collection_name="advisors2",
        query_vector=query_vector,
        limit=10,
        search_params=SearchParams(hnsw_ef=512),
    )
    search_time = time.time() - search_start
    print(f"Search time: {search_time:.2f} seconds")


    # 3. Build context from top results
    context = []
    for i, result in enumerate(search_results):
        payload = result.payload
        payload['match_score'] = f"{round(result.score * 100, 2)}%"
        context.append(f"Advisor {i+1} (Score: {result.score}):\n{json.dumps(payload, indent=2)}\n")

    context_str = "\n".join(context)

    # 4. Use OpenAI to generate structured advisor recommendations
    advisor_prompt = f"""
Given the following retrieved information:
{context_str}

Based on the retrieved professors and their research work, generate a list of recommended advisors 
for a PhD student with the following questions:
{original_question}

Consider:
1. Research area alignment with student interests
2. Publication impact in relevant areas
3. University reputation
4. Current research activities
5. Match score (importance of match to student query)

Format the response as a structured list of advisors with their key strengths and fit.Include their match score (from the vector search) to rank them. Generate at least 3 to 6 results.
"""

    # Updated OpenAI API usage
    response_start = time.time()

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an academic advisor match expert."},
            {"role": "user", "content": advisor_prompt}
        ],
        temperature=0.7,
        stream=True,
    )


    for chunk in response:
        delta = chunk.choices[0].delta
        if hasattr(delta, "content") and delta.content:
            yield delta.content

    response_time = time.time() - response_start
    print(f"Response time: {response_time:.2f} seconds")
    total_time = time.time() - start_time
    print(f"Total time: {total_time:.2f} seconds")

    #result_text = response.choices[0].message.content


    #return result_text






# def retrieve_advisors(original_question: str, question: str):
#     settings = get_settings()
#     # Initialize Qdrant client
#     client = QdrantClient(
#         url=settings.QDRANT_URL,
#         api_key=settings.QDRANT_API_KEY,
#     )
#
#     Settings.embed_model = OpenAIEmbedding(
#         model="text-embedding-3-small",
#         api_key=settings.OPENAI_API_KEY,
#     )
#     Settings.llm = OpenAI(
#         model="gpt-4o-mini",
#         api_key=settings.OPENAI_API_KEY,
#     )
#     vector_store = QdrantVectorStore(client=client, collection_name="advisors2")
#
#
#     index = VectorStoreIndex.from_vector_store(vector_store, embed_model=Settings.embed_model)
#     # setup reranking with cohere
#     cohere_rerank = CohereRerank(
#         api_key=settings.COHERE_API_KEY,
#         model="rerank-english-v3.0",
#         top_n=10,
#     )
#     # # Create a query engine, with reranking
#     retriever= index.as_retriever(
#         similarity_top_k=20,
#         node_postprocessor=[cohere_rerank],
#     )
#
#     # Get initial results
#     raw_results = retriever.retrieve(
#         f"""Find potential PhD advisors based on the following interests with the following questions:
#         {question}.
#         Consider their research areas, publication history, and university affiliation."""
#     )
#
#     context_builded = build_context(raw_results)
#     # internet_search_results = search_university_info_internet(raw_results[:5])
#     # mixed_context = mixed_context_with_internet(context_builded, internet_search_results)
#     # print(mixed_context)
#     # Format results into Carts structure
#     advisor_prompt = """\
#     Given the following retrieved information:
#     {context}
#
#     Based on the retrieved professors and their research work, generate a list of recommended advisors
#     for a PhD student with the following questions:
#     {questions}
#
#     Consider:
#     1. Research area alignment with student interests
#     2. Publication impact in relevant areas
#     3. University reputation
#     4. Current research activities
#
#     Format the response as a structured list of advisors with their key strengths and fit. Generate at least 3 to 6 results.
#     """
#
#     program = LLMTextCompletionProgram.from_defaults(
#         llm=Settings.llm,
#         output_cls=Carts,
#         prompt_template_str=advisor_prompt,
#         verbose=True,
#     )
#
#     final_results = program(
#         question=original_question,
#         context=context_builded,
#         verbose=True,
#     )
#
#     return final_results
#
#
# def build_context(raw_results: List[NodeWithScore]) -> str:
#     context = []
#     for i, result in enumerate(raw_results):
#         # Get main advisor content
#         context_str = ""
#         content = result.get_content(MetadataMode.ALL)
#         context_str += f"Advisor {i+1} (Match Score: {result.score})\n{content}\n"
#         context.append(context_str)
#
#
#     return context
#

# def search_university_info_internet(raw_results: List[NodeWithScore]) -> str:
#     settings = get_settings()
#     tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
 
     
#     search_results_str = ""
#     for result in raw_results:
#         university_name = result.metadata["university"]
#         web_result= tavily_client.search(query=f"What is the Deadline, GPA, and GRE requirement, to apply to a PhD in computer science at {university_name}")
#         search_results_str += f"Deadline, GPA, and GRE requirement for {university_name}: {web_result}\n"
    
#     return search_results_str

# def mixed_context_with_internet(context: str, internet_search_results: str) -> str:
#     mixed_context = []
#     for i, context_str in enumerate(context):
#         context_str += f"Internet search results for advisor {i+1} about gre, gpa, and deadline: {internet_search_results}\n"
#         mixed_context.append(context_str)
#     return mixed_context
