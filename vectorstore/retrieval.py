from llama_index.core import VectorStoreIndex
from llama_index.llms.openai import OpenAI

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

def retrieve_advisors(question: str):
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

    # # Retrieve relevant documents
    # results = query_engine.query(question)

    # Get initial results
    raw_results = retriever.retrieve(
        f"""Find potential PhD advisors based on the following interest: {question}. 
        Consider their research areas, publication history, and university affiliation."""
    )

    # Format results into Carts structure
    advisor_prompt = """\
    Given the following retrieved information:
    {context}

    Based on the retrieved professors and their research work, generate a list of recommended advisors 
    for a PhD student with the following question: {question}

    Consider:
    1. Research area alignment with student interests
    2. Publication impact in relevant areas
    3. University reputation
    4. Current research activities

    Format the response as a structured list of advisors with their key strengths and fit.
    """

    program = LLMTextCompletionProgram.from_defaults(
        llm=Settings.llm,
        output_cls=Carts,
        prompt_template_str=advisor_prompt,
    )
    final_results = program(
        question=question,
        context=raw_results
    )
    
    return final_results


def build_context(raw_results):
    context = ""
    for result in raw_results:
        context += f"Name: {result.node.text}\n"
        context += f"Research: {result.node.metadata['research']}\n"
        context += f"University: {result.node.metadata['university']}\n\n"
    return context