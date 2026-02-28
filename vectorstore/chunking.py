from llama_index.core import Document
from typing import List
import json
import logging
import glob
import re
import tiktoken
from crawler.data_model import DataModel

_tokenizer = tiktoken.get_encoding("cl100k_base")

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
    count_advisors = 0 
    for university in universities:
        for advisor in university.advisors:
            # remember to modify the json file to follow the aproppiate structure.
            count_advisors += 1
            advisor_size = len(str(advisor).encode('utf-8'))
            # skip advisor with more than 5mb, there is a problem when chunking  
            if advisor_size > 5_000_000:
                print("skipping advisor", advisor.name)
                continue

            if advisor.raw_content.get("content"):
                clean_text = re.sub(r'[^\w\s,.!?]', '', advisor.raw_content["content"])
                if len(_tokenizer.encode(clean_text)) > 8192:
                    print(f"skipping {advisor.name}: exceeds 8192 token limit")
                    continue

                # Filter papers with count > 0
                active_areas = {
                    papers["name"]: papers["count"]
                    for area, papers in advisor.papers.model_dump().items()
                    if papers["count"] > 0
                }
                total_papers = sum(count for count in active_areas.values())
 
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
    

