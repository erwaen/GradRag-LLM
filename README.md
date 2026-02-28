# GradRag LLM

A RAG-based API for retrieving advisor recommendations based on CS Rankings data.

## Quick Start

### 1. Start Qdrant

```bash
docker compose up qdrant
```

### 2. Scrape professor data

```bash
python scripts/scrape.py                    # scrape all professors
python scripts/scrape.py --max-professors 50  # limit to first 50
python scripts/scrape.py --workers 20         # use 20 parallel workers
python scripts/scrape.py --help               # show all options
```

Results are saved to `logs/scraped_professors.json`.

### 3. Start the API

```bash
uvicorn main:app --reload
```

### Active endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/professor/scrape` | Start background scraping task |
| `GET` | `/api/professor/status` | Cache stats and task status |
| `POST` | `/api/retrieve_advisors` | Query advisors via RAG |

---

# Qdrant + Docker Setup with Snapshot Restore (Linux)

Instructions for running Qdrant using Docker and restoring a collection from a snapshot.

---

## Running Qdrant with Docker

### 1. Pull the Qdrant Docker image

```bash
docker pull qdrant/qdrant
```

### Run the container

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```
* -p exposes the port
* -v $(pwd)/qdrant_storage:/qdrant/storage  creates a volume to persist qdrant's data

### Load a collection with a snapshot

* Open your browser and go to the url localhost:6333/dashboard
* Head to the "Collections" section
![image](https://github.com/user-attachments/assets/ffdc7ccc-588d-40e9-b8b9-1898635e8437)
* Click on "UPLOAD SNAPSHOT" and load your snapshot file
![image](https://github.com/user-attachments/assets/13bae6c1-bd31-467a-aba8-f812984ffe07)

---

# Running Qdrant with Docker Desktop (Windows)

Instructions for running Qdrant using Docker Desktop and restoring a collection from a snapshot.

---

###  Install and run Docker Desktop
![image](https://github.com/user-attachments/assets/7d62aa72-35b5-484e-ae40-f2033aa1d0a2)

### Click on the search bar and search for the qdrant image, then pull the desired version.

![image](https://github.com/user-attachments/assets/158e08e2-5e7b-4230-8790-add629d1a207)

### Head to the *Images* section 
![image](https://github.com/user-attachments/assets/acf4ae46-be40-4b70-915e-76c2a2b0f9a2)

### Click on the  *Run* icon on the qdrant image and then following window pops up

![image](https://github.com/user-attachments/assets/19a2e606-8100-48c3-8384-397d16c73d1b)

### Expand *Optional Settings* and customize your container according to your needs (name, port, volume for persistance, etc.)

![image](https://github.com/user-attachments/assets/c14739ab-50e5-43c2-80a2-adc21aa67cd3)

## Note that for the *Container path* you must use the same as the previous guide (/qdrant/storage).

## To load the snapshot follow the same steps as in the Linux guide
 
