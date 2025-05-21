from config import get_settings
from qdrant_client import QdrantClient
from models.carts import Cart
import openai
from openai import OpenAI
from qdrant_client.models import Filter, SearchParams, PointStruct
from qdrant_client.http.models import SearchRequest, ScoredPoint
from typing import Generator
import time
import json
import re
from typing import List


def get_embedding(question: str) -> List[float]:
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response=client.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )

    return response.data[0].embedding


def retrieve_advisors_stream(original_question: str, subquestions: List[str]) -> Generator[str, None, None]:
    start_time = time.time()  # Start measuring time
    settings = get_settings()

    openai.api_key = settings.OPENAI_API_KEY
    client = QdrantClient(
        #url="http://localhost:6333"
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )
    embedding_search_start = time.time()
    # Step 1 & 2: Embed and search each subquestion
    all_results: List[ScoredPoint] = []
    seen_ids = set()
    for subq in subquestions:
        query_vector = get_embedding(subq)
        search_results: List[ScoredPoint] = client.search(
            collection_name="advisors2",
            query_vector=query_vector,
            limit=5,
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
    context = []
    for i, result in enumerate(top_results):
        payload = result.payload
        payload["match_score"] = f"{round(result.score * 100, 2)}%"
        context.append(f"Advisor {i+1} (from: '{payload.get('origin_query', '')}'):\n{json.dumps(payload, indent=2)}\n")

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

**Instructions**:
- Output each advisor recommendation as an individual JSON object (do not wrap in a list).
- Each JSON object must follow this structure:

{{
  "advisor": {{
    "name": string,
    "university": string,
    "research_areas": [string, ...],
    "email": string,
    "website": string,
    "match_score": float (0 to 1),
    "why_good_fit": string
  }},
  "university": string,
  "application_deadline": string or null,
  "gpa_requirement": string or null,
  "gre_requirement": string or null,
  "funding_available": "Full", "Partial", "None", or null
}}

- Output 3 to 6 such objects.
- Each object should be printed **on its own line** with no explanation.
- End each object with a newline \\n.
- Do not output any surrounding commentary, text, or list brackets.

Now generate the recommendations:

"""

    #5 Updated OpenAI API usage with streaming response
    response_start = time.time()

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an academic advisor match expert who outputs structured JSON. Each advisor must be returned as a valid JSON object with no explanation or surrounding text. One object per line."},
            {"role": "user", "content": advisor_prompt}
        ],
        temperature=0.7,
        stream=True,
    )


    buffer = ""
    # Pattern to match complete JSON objects
    json_pattern = re.compile(r'\{.*?\}(?=\s*\n|$)', re.DOTALL)

    for chunk in response:
        delta = chunk.choices[0].delta
        if hasattr(delta, "content") and delta.content:
            buffer += delta.content

            # Extract all complete JSON objects
            for match in json_pattern.finditer(buffer):
                json_str = match.group(0).strip()
                try:
                    data = json.loads(json_str)
                    cart = Cart(**data)
                    yield json.dumps(cart.model_dump()) + "\n"
                except Exception as e:
                    print(f"Skipping malformed JSON object: {e}")

            # Keep only the remainder after the last complete match
            last_match = list(json_pattern.finditer(buffer))[-1] if json_pattern.findall(buffer) else None
            if last_match:
                buffer = buffer[last_match.end():]

    response_time = time.time() - response_start
    print(f"Response time: {response_time:.2f} seconds")
    total_time = time.time() - start_time
    print(f"Total time: {total_time:.2f} seconds")