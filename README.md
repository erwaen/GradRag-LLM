# GradRag LLM

RAG API that recommends PhD advisors based on CS Rankings data.

## Setup

**1. Start Qdrant**
```bash
docker compose up qdrant
```

**2. Scrape professor homepages**
```bash
docker compose run --rm gradrag-app python scripts/scrape.py --max-professors 100
```

**3. Start the API**
```bash
docker compose up --build
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/professor/status` | Cache stats |
| `POST` | `/api/retrieve_advisors` | Query advisors (body: `{"q": "...", "model": "gpt"}`) |
| `POST` | `/api/match_cv_advisors` | Match advisors from a CV file |

Interactive docs: `http://localhost:8102/docs`
