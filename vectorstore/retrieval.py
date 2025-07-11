from config import get_settings
from qdrant_client import QdrantClient
import openai
from openai import OpenAI
from qdrant_client.models import SearchParams 
from qdrant_client.http.models import  ScoredPoint
from typing import Generator
import time
import json
import re
from typing import List
from models.cards import Cards as CardsModel, Card as OneCardModel
from json import JSONDecodeError

settings = get_settings()
OPENAI_CLIENT = OpenAI(api_key=settings.OPENAI_API_KEY) 

QDRANT_CLIENT = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)

import json

import json

def generate_advisor_prompt(top_results, original_question):
    """
    Generates a structured prompt for LLM advisor recommendation based on top results.

    Args:
        top_results (List[ScoredPoint]): Top scored advisor results.
        original_question (str): The student's original question.

    Returns:
        str: Fully constructed prompt string.
    """
    IRRELEVANT_KEYS = {
        "_node_content", "_node_type", "document_id", "doc_id", "ref_doc_id",
        "vector", "shard_key", "order_value"
    }

    context_blocks = []
    for i, result in enumerate(top_results):
        payload = result.payload.copy()

        # Clean irrelevant fields
        for key in list(payload.keys()):
            if key in IRRELEVANT_KEYS:
                del payload[key]

        # Convert research_areas from dict to list of strings
        if isinstance(payload.get("research_areas"), dict):
            payload["research_areas"] = list(payload["research_areas"].keys())

        # Add match score
        payload["match_score"] = f"{round(result.score * 100, 2)}%"

        block = f"Advisor {i+1} (from: '{payload.get('origin_query', '')}'):\n{json.dumps(payload, indent=2)}\n"
        context_blocks.append(block)

    context_str = "\n".join(context_blocks)

    advisor_prompt = f"""
Given the following retrieved information:
{context_str}

Based on the retrieved professors and their research work, generate a list of recommended advisors 
for a PhD student with the following questions:
{original_question}

- Output 3 to 6 such objects.
- gpa_requirement — Generate based on the university's computer science PhD program requirements.
- gre_requirement — Generate based on the university's computer science PhD program requirements.
- funding_available — Generate based on the university's program or general knowledge

Now generate the recommendations:
"""
    
    return advisor_prompt



def get_embedding(question: str) -> List[float]:
    response=OPENAI_CLIENT.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def retrieve_advisors_stream(original_question: str, subquestions: List[str]) -> Generator[str, None, None]:
    start_time = time.time()

    embedding_search_start = time.time()
    # Step 1 & 2: Embed and search for each subquestion
    all_results: List[ScoredPoint] = []
    seen_ids = set()
    for subq in subquestions:
        query_vector = get_embedding(subq)
        search_results: List[ScoredPoint] = QDRANT_CLIENT.search(
            collection_name=settings.COLLECTION_NAME,
            query_vector=query_vector, limit=5,
            search_params=SearchParams(hnsw_ef=512),
        )
        for res in search_results:
            if res.id not in seen_ids:
                res.payload["origin_query"] = subq
                all_results.append(res)
                seen_ids.add(res.id)

    embedding_search_time = time.time() - embedding_search_start
    print(f"Embedding and search time: {embedding_search_time:.2f} seconds")


    # 3. Sort and build context from top results
    top_results = sorted(all_results, key=lambda r: r.score, reverse=True)[:10]
    
    # generate prompt
    advisor_prompt = generate_advisor_prompt(top_results, original_question)

    #5 Return response in stream using OpenAI's streaming response behaviour
    response_start = time.time()

    buffer = ""
    # Regex pattern to match complete Card objects (not nested advisor objects)
    # Look for objects that start with {"advisor": and contain all required fields
    json_pattern = re.compile(r'\{"advisor":\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^}]*\}')

    with OPENAI_CLIENT.responses.stream(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": "You are an academic advisor match expert who answer the user with a list of suggested advisors for them"},
            {"role": "user", "content": advisor_prompt}
        ],
        temperature=0,
        text_format=CardsModel,
    ) as stream:
        for event in stream:
            if event.type == "response.output_text.delta":
                print(event.delta, end="")
                buffer += event.delta

                # Extract all complete Card JSON objects from the buffer
                for match in json_pattern.finditer(buffer):
                    json_str = match.group(0).strip()
                    try:
                        card_obj = json.loads(json_str)
                        card = OneCardModel.parse_obj(card_obj)
                        yield json.dumps(card.model_dump()) + "\n"
                    except Exception as e:
                        print(f"Error parsing card: {e}")
                        continue

                # Keep only the remainder after the last complete match
                matches = list(json_pattern.finditer(buffer))
                if matches:
                    last_match = matches[-1]
                    buffer = buffer[last_match.end():]

            elif event.type == "response.refusal.delta":
                print(event.delta, end="")

            elif event.type == "response.error":
                print(event.error, end="")

            elif event.type == "response.completed":
                print("Completed")

            


    # Pattern to match complete JSON objects
    
    # for chunk in response:
    #     delta = chunk.choices[0].delta
    #     if hasattr(delta, "content") and delta.content:
    #         buffer += delta.content
    #
    #         # Extract all complete JSON objects
    #         for match in json_pattern.finditer(buffer):
    #             json_str = match.group(0).strip()
    #             try:
    #                 data = json.loads(json_str)
    #                 cart = CardModel(**data)
    #                 yield json.dumps(cart.model_dump()) + "\n"
    #             except Exception as e:
    #                 print(f"Skipping malformed JSON object: {e}")
    #
    #         # Keep only the remainder after the last complete match
    #
    #         # Find all matches of complete JSON objects in the buffer
    #         matches = list(json_pattern.finditer(buffer))
    #
    #         # Check if there are any matches
    #         if matches:
    #             # Get the last complete match
    #             last_match = matches[-1]
    #
    #             # Remove everything from the buffer up to and including the last match
                # buffer = buffer[last_match.end():]

    response_time = time.time() - response_start
    print(f"Response time: {response_time:.2f} seconds")
    total_time = time.time() - start_time
    print(f"Total time: {total_time:.2f} seconds")
