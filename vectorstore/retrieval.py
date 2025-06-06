from llama_index.core import VectorStoreIndex
from typing import List
from llama_index.core.schema import NodeRelationship
from llama_index.core.schema import NodeWithScore
from llama_index.llms.openai import OpenAI
from llama_index.core.schema import MetadataMode
from llama_index.core import StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.postprocessor.cohere_rerank import CohereRerank

from config import get_settings
from qdrant_client import QdrantClient
from llama_index.core.program import LLMTextCompletionProgram


from models.carts import Carts

from llama_index.core import Settings
import os


def retrieve_advisors(original_question: str, question: str):
    settings = get_settings()
    # Initialize Qdrant client
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )

    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY,
    )
    Settings.llm = OpenAI(
        model="gpt-4o-mini",
        api_key=settings.OPENAI_API_KEY,
    )
    vector_store = QdrantVectorStore(client=client, collection_name="advisors2")


    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=Settings.embed_model)
    # setup reranking with cohere
    cohere_rerank = CohereRerank(
        api_key=settings.COHERE_API_KEY,
        model="rerank-english-v3.0",
        top_n=10,
    )
    # # Create a query engine, with reranking
    retriever= index.as_retriever(
        similarity_top_k=20,
        node_postprocessor=[cohere_rerank],
    )

    # Get initial results
    raw_results = retriever.retrieve(
        f"""Find potential PhD advisors based on the following interests with the following questions:
        {question}. 
        Consider their research areas, publication history, and university affiliation."""
    )

    context_builded = build_context(raw_results)
    # internet_search_results = search_university_info_internet(raw_results[:5])
    # mixed_context = mixed_context_with_internet(context_builded, internet_search_results)
    # print(mixed_context)
    # Format results into Carts structure
    advisor_prompt = """\
    Given the following retrieved information:
    {context}

    Based on the retrieved professors and their research work, generate a list of recommended advisors 
    for a PhD student with the following questions:
    {questions}

    Consider:
    1. Research area alignment with student interests
    2. Publication impact in relevant areas
    3. University reputation
    4. Current research activities

    Format the response as a structured list of advisors with their key strengths and fit. Generate at least 3 to 6 results.
    """

    program = LLMTextCompletionProgram.from_defaults(
        llm=Settings.llm,
        output_cls=Carts,
        prompt_template_str=advisor_prompt,
        verbose=True,
    )

    final_results = program(
        question=original_question,
        context=context_builded,
        verbose=True,
    )
   
    return final_results


def build_context(raw_results: List[NodeWithScore]) -> str:
    context = []
    for i, result in enumerate(raw_results):
        # Get main advisor content
        context_str = ""
        content = result.get_content(MetadataMode.ALL)
        context_str += f"Advisor {i+1} (Match Score: {result.score})\n{content}\n"
        context.append(context_str)
        

    return context


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
