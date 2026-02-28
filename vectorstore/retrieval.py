from config import get_settings
from qdrant_client import QdrantClient
from typing import List, Literal, Generator
from openai import OpenAI
from qdrant_client.models import SearchParams
from qdrant_client.http.models import ScoredPoint
import time
import json
import re
from models.cards import Cards as CardsModel, Card as OneCardModel
from json import JSONDecodeError
from llmmodels.llm import LLMFactory

settings = get_settings()
OPENAI_CLIENT = OpenAI(api_key=settings.OPENAI_API_KEY)

QDRANT_CLIENT = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY or None,
)


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
    response = OPENAI_CLIENT.embeddings.create(
        input=question.replace("\n", " "),
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def retrieve_advisors_stream(original_question: str, subquestions: List[str], model: Literal["gemini", "gpt"]) -> Generator[str, None, None]:
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
    advisor_prompt = generate_advisor_prompt(top_results, original_question)

    response_start = time.time()

    buffer = ""
    json_pattern = re.compile(r'\{"advisor":\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^}]*\}')

    llm_model = LLMFactory.create_model(model)

    for chunk in llm_model.stream(
        messages=[
            {"role": "system", "content": "You are an academic advisor match expert who answer the user with a list of suggested advisors for them"},
            {"role": "user", "content": advisor_prompt}
        ],
        temperature=0,
        structure_model=CardsModel,
    ):
        buffer += chunk
        for match in json_pattern.finditer(buffer):
            json_str = match.group(0).strip()
            try:
                card_obj = json.loads(json_str)
                card = OneCardModel.parse_obj(card_obj)
                yield json.dumps(card.model_dump()) + "\n"
            except JSONDecodeError as e:
                print(f"Error parsing card: {e}")
                continue

        matches = list(json_pattern.finditer(buffer))
        if matches:
            last_match = matches[-1]
            buffer = buffer[last_match.end():]

    response_time = time.time() - response_start
    print(f"Response time: {response_time:.2f} seconds")
    total_time = time.time() - start_time
    print(f"Total time: {total_time:.2f} seconds")
