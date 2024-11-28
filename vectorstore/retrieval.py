from llama_index.core import VectorStoreIndex
from llama_index.llms.openai import OpenAI

from llama_index.core import StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from config import get_settings
from qdrant_client import QdrantClient
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

    # storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=Settings.embed_model)
    # Create a query engine
    query_engine = index.as_query_engine(llm=Settings.llm)

    
    # Retrieve relevant documents
    results = query_engine.query(question)
    
    return results

