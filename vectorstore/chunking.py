from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from typing import List
from pathlib import Path
import json
import logging

def load_advisor_data(data_dir: str = "data/advisors") -> List[Document]:
    """Load advisor data and create documents with metadata"""
    documents = []
    advisor_dir = Path(data_dir)
    
    for file in advisor_dir.glob("*.json"):
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                
            # Extract text content
            raw_content = data.get('raw_content', {})
            text = raw_content.get('raw_text', '')
            
            # Create metadata
            metadata = {
                'advisor_name': data.get('name', ''),
                'university': data.get('university', ''),
                'papers': data.get('papers', {}),
                'url': raw_content.get('url', ''),
                'page_title': raw_content.get('page_title', ''),
                'source_type': 'advisor_profile'
            }
            
            # Create document with metadata
            doc = Document(text=text, metadata=metadata)
            documents.append(doc)
            
        except Exception as e:
            logging.error(f"Error processing {file}: {e}")
    
    return documents

def create_contextual_chunks(documents: List[Document]) -> List[Document]:
    """Create contextual chunks from documents"""
    parser = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separator=" ",
        paragraph_separator="\n\n",
        secondary_chunking_regex="[^.!?]+[.!?]"
    )
    
    chunked_documents = []
    for doc in documents:
        chunks = parser.split_text(doc.text)
        for i, chunk in enumerate(chunks):
            # Create new metadata with chunk info
            chunk_metadata = {
                **doc.metadata,
                'chunk_id': i,
                'total_chunks': len(chunks)
            }
            chunked_doc = Document(text=chunk, metadata=chunk_metadata)
            chunked_documents.append(chunked_doc)
    
    return chunked_documents