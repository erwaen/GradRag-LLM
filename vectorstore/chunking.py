from llama_index.core import Document
from typing import List
from pathlib import Path
import json
import logging
import glob
import re
from crawler.data_model import University, Advisor, DataModel, Papers
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import  OpenAIEmbedding

from llama_index.core import GPTVectorStoreIndex, VectorStoreIndex, StorageContext
from llama_index.core import Settings

from config import get_settings

logger = logging.getLogger(__name__)

def get_advisor_documents() -> List[Document]:
    raw_data_path = "data/raw"
    files = glob.glob(f"{raw_data_path}/csrankings_*.json")
    latest_file = max(files, key=lambda x: re.search(r'(\d{8}_\d{6})', x).group(1))

    with open(latest_file, 'r') as f:
        data = json.load(f)

    data = DataModel.model_validate(data)    
    universities = data.universities

    advisor_documents = []
    for university in universities:
        for advisor in university.advisors:
            advisor_size = len(str(advisor).encode('utf-8'))
            # skip advisor with more than 5mb, there is a problem when chunking  
            if advisor_size > 5_000_000:
                print("skipping advisor", advisor.name)
                continue

            if "raw_text" in advisor.raw_content and advisor.raw_content["raw_text"] != "":
                # Filter papers with count > 0
                active_areas = {
                    papers["name"]: papers["count"]
                    for area, papers in advisor.papers.model_dump().items() 
                    if papers["count"] > 0
                } 
                total_papers = sum(count for count in active_areas.values())
                clean_text = re.sub(r'[^\w\s,.!?]', '', advisor.raw_content["raw_text"])
 
                # Create document with enhanced metadata
                doc = Document(
                    text=clean_text,
                    metadata={
                        "name": advisor.name,
                        "university": university.name,
                        "research_areas": active_areas,
                        # "research_areas": advisor.papers.model_dump(),
                        "total_papers": total_papers,
                        "homepage": advisor.href
                    }
                )
                advisor_documents.append(doc)
    
    return advisor_documents
    
def store_advisor_documents(documents: List[Document]):
    settings = get_settings()
    # Initialize Qdrant client
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )
    
    # service_context = ServiceContext.from_defaults(chunk_size_limit=512)
    # Settings.embed_model = HuggingFaceEmbedding(
    #     model_name="BAAI/bge-small-en-v1.5"
    # )
    Settings.embed_model = OpenAIEmbedding(
        api_key=settings.OPENAI_API_KEY,
        model="text-embedding-3-small"
    )
    
    Settings.chunk_size= 512 
    # Create vector store
    vector_store = QdrantVectorStore(client=client, collection_name="advisors2")
    

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context, show_progress=True)
    # index = VectorStoreIndex.from_documents(documents,  show_progress=True)
   
    print("here2")
    
    logger.info(f"Stored {len(documents)} advisor documents in Qdrant")
    return index

    
    




