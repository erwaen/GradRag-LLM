#!/usr/bin/env python3
"""
Usage: python scripts/build_embed_index.py

Indexes scraped professor data into Qdrant:
  1. Parse logs/scraped_professors.json → data/raw/csrankings_<timestamp>.json
  2. Build LlamaIndex documents from structured data
  3. Embed with OpenAI and store in Qdrant
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.parse_scraped_data import main as parse_main
from vectorstore.chunking import get_advisor_documents
from config import get_settings
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import VectorStoreIndex, StorageContext, Settings


def main():
    settings = get_settings()

    print("Step 1/3 — Parsing scraped data into structured JSON...")
    parse_main()

    print("\nStep 2/3 — Building documents from structured data...")
    documents = get_advisor_documents()
    if not documents:
        print("ERROR: No documents found. Make sure data/raw/csrankings_*.json exists and has raw_text content.")
        sys.exit(1)
    print(f"  Built {len(documents)} advisor documents")

    print(f"\nStep 3/3 — Embedding and uploading to Qdrant ({settings.QDRANT_URL}, collection: {settings.COLLECTION_NAME})...")
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)

    Settings.embed_model = OpenAIEmbedding(
        api_key=settings.OPENAI_API_KEY,
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )
    Settings.chunk_size = 512

    vector_store = QdrantVectorStore(client=client, collection_name=settings.COLLECTION_NAME)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex.from_documents(documents, storage_context=storage_context, show_progress=True)

    print(f"\nDone. {len(documents)} advisors indexed into '{settings.COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
