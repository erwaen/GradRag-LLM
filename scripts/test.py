from typing import List
import time
import logging
import openai
from openai import OpenAI
from config import get_settings
settings = get_settings()
# Setup API key and client
OPENAI_API_KEY = settings.OPENAI_API_KEY  # Replace with your key or load from environment
EMBEDDING_MODEL = "text-embedding-3-small"  # or text-embedding-ada-002
client = OpenAI(api_key=OPENAI_API_KEY)

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def generate_embeddings_with_openai(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using OpenAI's updated API client.
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key is not set. Please set OPENAI_API_KEY.")
        return [[] for _ in texts]  # Return empty embeddings

    embeddings = []

    try:
        for i, text in enumerate(texts):
            if len(text) > 25000:
                logger.warning(f"Text {i} is too long ({len(text)} chars), truncating...")
                text = text[:25000]

            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
            )
            embedding = response.data[0].embedding
            embeddings.append(embedding)

            time.sleep(0.5)  # Basic rate limit avoidance

        return embeddings

    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        return [[] for _ in texts]


# Test the function
if __name__ == "__main__":
    test_texts = [
        "OpenAI develops artificial general intelligence for the benefit of all humanity.",
        "The quick brown fox jumps over the lazy dog."
    ]
    results = generate_embeddings_with_openai(test_texts)
    
    for i, embedding in enumerate(results):
        print(f"Embedding {i} (length: {len(embedding)}):\n{embedding[:5]}...\n")  # Show first 5 values
