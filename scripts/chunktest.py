import json
from typing import List

def chunk_text_by_chars(text: str, chunk_size: int = 512) -> List[str]:
    """
    Splits `text` into consecutive chunks of at most `chunk_size` characters.
    """
    return [ text[i:i + chunk_size] for i in range(0, len(text), chunk_size) ]

def prepare_chunks(input_path: str, output_path: str):
    # 1. Load your original JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # If your file is a list of profiles, iterate; else wrap single dict in list
    profiles = data if isinstance(data, list) else [data]

    all_chunks = []
    for profile in profiles:
        name = profile.get("name", "unknown")
        homepage = profile.get("homepage", "")
        scholar_id = profile.get("scholar_id", "")
        note = profile.get("note", "")
        content = profile.get("content", "") 
        scrape_success = profile.get("scrape_success", "")
        chunks = chunk_text_by_chars(content, chunk_size=512)

        for idx, chunk in enumerate(chunks, start=1):
            all_chunks.append({
                "name": name,
                "homepage": homepage,
                "chunk_index": idx,
                "scholar_id": scholar_id,
                "note": note,
                "content": chunk,
                "scrape_success": scrape_success
            })

    # 3. Write out a new JSON with one object per chunk
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    prepare_chunks("filtered2.json", "filtered2_chunks.json")
    print("Done! Created filtered2_chunks.json with", 
          sum(1 for _ in open("filtered2_chunks.json")), "lines.")
