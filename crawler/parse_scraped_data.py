#!/usr/bin/env python3
import requests
import re
import pandas as pd
import io
import math
import json
from collections import defaultdict
import sys
import time
from copy import deepcopy
from datetime import datetime
from os import getcwd

# --- Constants and Configuration ---
INPUT_JSON_PATH = getcwd() + "/logs/" + "scraped_professors.json"
# Updated output path for the sorted structured format
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_JSON_PATH = getcwd() + f"/data/raw/csrankings_{timestamp}.json"
START_YEAR = 2014
END_YEAR = 2024
RANKING_AREAS = "all" # Use "all" or specify a list like ["ai", "systems"]

# Define URLs for the CSV files
AUTHOR_URL = "https://csrankings.org/csrankings.csv" # Contains name, homepage, scholarid
AUTHOR_INFO_URL = "https://csrankings.org/generated-author-info.csv" # Contains name, dept, area, year, count, adjustedcount

# Regex to match name and note like in the JS code
NAME_MATCHER = re.compile(r"^(.*)\s+\[(.*?)\]$")

# --- Area Definitions and Mappings ---
# Based on data_model.py
AREA_DEFINITIONS = {
    "ai": "Artificial intelligence",
    "vision": "Computer vision",
    "mlmining": "Machine Learning",
    "nlp": "Natural language processing",
    "inforet": "The Web & information retrieval",
    "arch": "Computer architecture",
    "comm": "Computer networks",
    "sec": "Computer security",
    "mod": "Databases",
    "da": "Design automation",
    "bed": "Embedded & real-time systems",
    "hpc": "High performance computing",
    "mobile": "Mobile computing",
    "metrics": "Measurement & perf. analysis",
    "ops": "Operating systems",
    "plan": "Programming languages",
    "soft": "Software engineering",
    "act": "Algorithms and complexity",
    "crypt": "Cryptography",
    "log": "Logic & verification",
    "graph": "Computer graphics",
    "bio": "Computational biology & bioinformatics",
    "csed": "Computer science education",
    "ecom": "Economics & computation",
    "chi": "Human-computer interaction",
    "robotics": "Robotics",
    "visualization": "Visualization"
}

# Map conferences to their top-level area code (keys from AREA_DEFINITIONS)
_area_map_full = [
    {"area": "ai", "title": "AI"}, 
    {"area": "aaai", "title": "AI"}, 
    {"area": "ijcai", "title": "AI"},
    {"area": "vision", "title": "Vision"}, 
    {"area": "cvpr", "title": "Vision"}, 
    {"area": "eccv", "title": "Vision"}, 
    {"area": "iccv", "title": "Vision"},
    {"area": "mlmining", "title": "ML"}, 
    {"area": "icml", "title": "ML"}, 
    {"area": "kdd", "title": "ML"}, 
    {"area": "iclr", "title": "ML"}, 
    {"area": "nips", "title": "ML"},
    {"area": "nlp", "title": "NLP"}, 
    {"area": "acl", "title": "NLP"},
    {"area": "emnlp", "title": "NLP"}, 
    {"area": "naacl", "title": "NLP"},
    {"area": "inforet", "title": "Web+IR"}, 
    {"area": "sigir", "title": "Web+IR"}, 
    {"area": "www", "title": "Web+IR"},
    {"area": "arch", "title": "Arch"}, 
    {"area": "asplos", "title": "Arch"}, 
    {"area": "isca", "title": "Arch"}, 
    {"area": "micro", "title": "Arch"}, 
    {"area": "hpca", "title": "Arch"},
    {"area": "comm", "title": "Networks"}, 
    {"area": "sigcomm", "title": "Networks"}, 
    {"area": "nsdi", "title": "Networks"},
    {"area": "sec", "title": "Security"}, 
    {"area": "ccs", "title": "Security"}, 
    {"area": "oakland", "title": "Security"}, 
    {"area": "usenixsec", "title": "Security"}, 
    {"area": "ndss", "title": "Security"}, 
    {"area": "pets", "title": "Security"},
    {"area": "mod", "title": "DB"}, 
    {"area": "sigmod", "title": "DB"}, 
    {"area": "vldb", "title": "DB"}, 
    {"area": "icde", "title": "DB"}, 
    {"area": "pods", "title": "DB"},
    {"area": "hpc", "title": "HPC"}, 
    {"area": "sc", "title": "HPC"}, 
    {"area": "hpdc", "title": "HPC"}, 
    {"area": "ics", "title": "HPC"},
    {"area": "mobile", "title": "Mobile"}, 
    {"area": "mobicom", "title": "Mobile"}, 
    {"area": "mobisys", "title": "Mobile"}, 
    {"area": "sensys", "title": "Mobile"},
    {"area": "metrics", "title": "Metrics"}, 
    {"area": "imc", "title": "Metrics"}, 
    {"area": "sigmetrics", "title": "Metrics"},
    {"area": "ops", "title": "OS"}, 
    {"area": "sosp", "title": "OS"}, 
    {"area": "osdi", "title": "OS"}, 
    {"area": "fast", "title": "OS"}, 
    {"area": "usenixatc", "title": "OS"}, 
    {"area": "eurosys", "title": "OS"},
    {"area": "plan", "title": "PL"}, 
    {"area": "pldi", "title": "PL"}, 
    {"area": "popl", "title": "PL"}, 
    {"area": "icfp", "title": "PL"}, 
    {"area": "oopsla", "title": "PL"},
    {"area": "soft", "title": "SE"}, 
    {"area": "fse", "title": "SE"}, 
    {"area": "icse", "title": "SE"}, 
    {"area": "ase", "title": "SE"}, 
    {"area": "issta", "title": "SE"},
    {"area": "act", "title": "Theory"}, 
    {"area": "focs", "title": "Theory"}, 
    {"area": "soda", "title": "Theory"}, 
    {"area": "stoc", "title": "Theory"},
    {"area": "crypt", "title": "Crypto"}, 
    {"area": "crypto", "title": "Crypto"}, 
    {"area": "eurocrypt", "title": "Crypto"},
    {"area": "log", "title": "Logic"}, 
    {"area": "cav", "title": "Logic"}, 
    {"area": "lics", "title": "Logic"},
    {"area": "graph", "title": "Graphics"}, 
    {"area": "siggraph", "title": "Graphics"}, 
    {"area": "siggraph-asia", "title": "Graphics"}, 
    {"area": "eurographics", "title": "Graphics"},
    {"area": "chi", "title": "HCI"}, 
    {"area": "chiconf", "title": "HCI"}, 
    {"area": "ubicomp", "title": "HCI"}, 
    {"area": "uist", "title": "HCI"},
    {"area": "robotics", "title": "Robotics"}, 
    {"area": "icra", "title": "Robotics"}, 
    {"area": "iros", "title": "Robotics"}, 
    {"area": "rss", "title": "Robotics"},
    {"area": "bio", "title": "Comp. Bio"}, 
    {"area": "ismb", "title": "Comp. Bio"}, 
    {"area": "recomb", "title": "Comp. Bio"},
    {"area": "da", "title": "EDA"}, 
    {"area": "dac", "title": "EDA"}, 
    {"area": "iccad", "title": "EDA"},
    {"area": "bed", "title": "Embedded"}, 
    {"area": "emsoft", "title": "Embedded"}, 
    {"area": "rtas", "title": "Embedded"}, 
    {"area": "rtss", "title": "Embedded"},
    {"area": "visualization", "title": "Visualization"}, 
    {"area": "vis", "title": "Visualization"}, 
    {"area": "vr", "title": "Visualization"},
    {"area": "ecom", "title": "ECom"}, 
    {"area": "ec", "title": "ECom"}, 
    {"area": "wine", "title": "ECom"},
    {"area": "csed", "title": "CSEd"}, 
    {"area": "sigcse", "title": "CSEd"}
]

_title_to_area_code_map = {
    "AI": "ai", "Vision": "vision", "ML": "mlmining", "NLP": "nlp", "Web+IR": "inforet",
    "Arch": "arch", "Networks": "comm", "Security": "sec", "DB": "mod", "EDA": "da",
    "Embedded": "bed", "HPC": "hpc", "Mobile": "mobile", "Metrics": "metrics", "OS": "ops",
    "PL": "plan", "SE": "soft", "Theory": "act", "Crypto": "crypt", "Logic": "log",
    "Graphics": "graph", "Comp. Bio": "bio", "CSEd": "csed", "ECom": "ecom", "HCI": "chi",
    "Robotics": "robotics", "Visualization": "visualization"
}

CONF_TO_AREA_CODE = {}
for item in _area_map_full:
    conf = item["area"]
    title = item["title"]
    area_code = _title_to_area_code_map.get(title)
    if area_code:
        CONF_TO_AREA_CODE[conf] = area_code

# --- Data Loading Functions ---
def download_csv_to_dataframe(url):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Attempting to download: {url} (Attempt {attempt + 1}/{max_retries})")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            csv_content = io.StringIO(response.text)
            df = pd.read_csv(csv_content, header=0, keep_default_na=False, dtype=str)
            print(f"Successfully downloaded and parsed CSV from {url}")
            return df
        except requests.exceptions.Timeout:
            print(f"Timeout downloading {url}. Retrying in 5 seconds...")
            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading CSV from {url}: {e}")
            if attempt == max_retries - 1: return None
            time.sleep(5)
        except pd.errors.EmptyDataError:
            print(f"Error: No data or empty CSV found at {url}"); return None
        except Exception as e:
            print(f"Error processing CSV from {url}: {e}"); return None
    return None

def load_authors_publications(url=AUTHOR_INFO_URL):
    df = download_csv_to_dataframe(url)
    if df is None: print("Failed to load author publications."); return pd.DataFrame()
    try:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["count"] = pd.to_numeric(df["count"], errors="coerce")
        df["adjustedcount"] = pd.to_numeric(df["adjustedcount"], errors="coerce")
        df = df.dropna(subset=["year", "adjustedcount"])
        df["year"] = df["year"].astype(int)
        df["name"] = df["name"].astype(str).str.strip()
        df["dept"] = df["dept"].astype(str).str.strip()
        df["area"] = df["area"].astype(str).str.strip()
    except KeyError as e: print(f"Error processing Author Publications: Missing expected column {e}"); return pd.DataFrame()
    except Exception as e: print(f"Error converting types in Author Publications: {e}")
    print(f"Successfully processed author publications from {url}")
    return df

def load_author_details(url=AUTHOR_URL):
    author_details = {}
    df = download_csv_to_dataframe(url)
    if df is None: print("Failed to load author details."); return {}
    try:
        for _, row in df.iterrows():
            name = str(row["name"]).strip()
            match = NAME_MATCHER.match(name)
            if match: name = match.group(1).strip()
            if name:
                homepage = str(row["homepage"]).strip()
                scholar_id = str(row["scholarid"]).strip()
                author_details[name] = {"homepage": homepage, "scholar_id": scholar_id}
                if scholar_id: author_details[scholar_id] = {"name": name, "homepage": homepage}
        print(f"Successfully processed author details from {url}")
        return author_details
    except KeyError as e: print(f"Error processing Author details: Missing expected column {e}"); return {}
    except Exception as e: print(f"Error processing author details from {url}: {e}"); return {}
def load_author_info(url=AUTHOR_URL):
    """Loads author info (homepage, scholarid) from URL and extracts notes."""
    homepages = {}
    scholar_info = {}
    notes = {}
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_content = io.StringIO(response.text)
        df = pd.read_csv(csv_content, header=0, keep_default_na=False)
        print(f"Successfully downloaded and parsed CSV from {url}")

        for index, row in df.iterrows():
            name = str(row["name"]).strip()
            match = NAME_MATCHER.match(name)
            if match:
                name = match.group(1).strip()
                notes[name] = match.group(2)

            if name:
                homepages[name] = str(row["homepage"])
                scholar_info[name] = str(row["scholarid"])

        print(f"Successfully processed author info from {url}")
        return homepages, scholar_info, notes

    except requests.exceptions.RequestException as e:
        print(f"Error downloading CSV from {url}: {e}")
        return {}, {}, {}
    except pd.errors.EmptyDataError:
        print(f"Error: No data or empty CSV found at {url}")
        return {}, {}, {}
    except KeyError as e:
        print(f"Error processing Author info: Missing expected column {e}")
        return {}, {}, {}
    except Exception as e:
        print(f"Error processing author info from {url}: {e}")
        return {}, {}, {}
    
    
# --- Helper Functions ---
def get_area_code(conf_area):
    return CONF_TO_AREA_CODE.get(conf_area)

def create_paper_category(area_code, count):
    # Round count to nearest integer for display, but keep float for potential calculations
    return {"count": int(round(count)), "name": AREA_DEFINITIONS.get(area_code, "Unknown Area"), "_raw_count": float(count)}

def calculate_geometric_mean_score(area_counts_dict):
    """Calculates the geometric mean score based on adjusted counts per area."""
    product = 1.0
    num_areas = len(AREA_DEFINITIONS)
    if num_areas == 0: return 0.0

    for area_code in AREA_DEFINITIONS:
        # Use the internal _raw_count for calculation if available, else use rounded count
        count = area_counts_dict.get(area_code, {}).get("_raw_count", 0.0)
        product *= (count + 1.0)

    # Handle potential case where product is zero or negative (shouldn't happen with +1)
    if product <= 0:
        return 0.0

    score = math.pow(product, 1.0 / num_areas) - 1.0 # Subtract 1 to scale back
    return score

# --- Main Processing Logic ---
def main():
    print("Starting professor data structuring and sorting process...")

    # 1. Load Data
    print("\n--- Loading CS Rankings Data ---")
    author_publications_df = load_authors_publications()
    author_details = load_author_details()
    if author_publications_df.empty or not author_details: sys.exit("Error: Failed to load essential data.")

    # 2. Filter Publications
    print(f"\n--- Filtering Publications ({START_YEAR}-{END_YEAR}) ---")
    filtered_pubs = author_publications_df[
        (author_publications_df["year"] >= START_YEAR) &
        (author_publications_df["year"] <= END_YEAR)
    ].copy()
    if filtered_pubs.empty: print(f"Warning: No publications found in the range {START_YEAR}-{END_YEAR}.")

    filtered_pubs["area_code"] = filtered_pubs["area"].apply(get_area_code)
    filtered_pubs = filtered_pubs.dropna(subset=["area_code"])
    print(f"Filtered down to {len(filtered_pubs)} publication entries.")

    # 3. Pre-calculate Aggregated Counts
    print("\n--- Pre-calculating Aggregated Counts ---")
    uni_area_counts = filtered_pubs.groupby(["dept", "area_code"])["adjustedcount"].sum().reset_index()
    uni_rankings_data = defaultdict(lambda: defaultdict(float))
    for _, row in uni_area_counts.iterrows():
        uni_rankings_data[row["dept"]][row["area_code"]] = row["adjustedcount"]
    print(f"Calculated area counts for {len(uni_rankings_data)} institutions.")

    prof_area_counts = filtered_pubs.groupby(["name", "area_code"])["adjustedcount"].sum().reset_index()
    prof_papers_data = defaultdict(lambda: defaultdict(float))
    for _, row in prof_area_counts.iterrows():
        prof_papers_data[row["name"]][row["area_code"]] = row["adjustedcount"]
    print(f"Calculated paper counts for {len(prof_papers_data)} professors.")

    prof_institution_map = filtered_pubs.groupby("name")["dept"].first().to_dict()
    print(f"Mapped {len(prof_institution_map)} professors to primary institutions.")

    # 4. Load Input JSON
    print(f"\n--- Loading Input JSON: {INPUT_JSON_PATH} ---")
    try:
        with open(INPUT_JSON_PATH, "r", encoding="utf-8") as f: input_data = json.load(f)
        print(f"Loaded {len(input_data)} entries from input JSON.")
    except Exception as e: sys.exit(f"Error loading input JSON: {e}")

    # 5. Process Input Data and Build University Objects
    print("\n--- Processing Input Entries and Building University Objects ---")
    output_universities = {} # Key: uni_name, Value: university_object
    processed_prof_keys = set()
    not_found_count = 0

    for input_entry in input_data:
        prof_name_input = input_entry.get("name")
        homepage_input = input_entry.get("homepage")
        scholar_id_input = input_entry.get("scholar_id")

        prof_key = homepage_input if homepage_input else prof_name_input
        if not prof_key or prof_key in processed_prof_keys: continue

        prof_name_cs, homepage_cs = None, None
        if scholar_id_input and scholar_id_input in author_details:
            details = author_details[scholar_id_input]
            prof_name_cs, homepage_cs = details.get("name"), details.get("homepage")
        elif prof_name_input and prof_name_input in author_details:
            details = author_details[prof_name_input]
            prof_name_cs, homepage_cs = prof_name_input, details.get("homepage")
        elif homepage_input:
             for key, details in author_details.items():
                 if details.get("homepage") == homepage_input:
                     prof_name_cs = details.get("name", key if not isinstance(details.get("name"), dict) else None)
                     homepage_cs = homepage_input
                     break

        institution = prof_institution_map.get(prof_name_cs) if prof_name_cs else None

        if not prof_name_cs or not institution:
            print(f"  - Warning: Could not find CS Rankings data for: {prof_name_input} (Homepage: {homepage_input})")
            not_found_count += 1
            continue

        final_homepage = homepage_cs if homepage_cs else homepage_input
        if not final_homepage:
             print(f"  - Warning: No homepage found for: {prof_name_cs}. Skipping.")
             continue

        # Create/Update University Object
        if institution not in output_universities:
            uni_rankings = {}
            uni_specific_counts = uni_rankings_data.get(institution, {})
            for area_code in AREA_DEFINITIONS:
                count = uni_specific_counts.get(area_code, 0.0)
                uni_rankings[area_code] = create_paper_category(area_code, count)

            output_universities[institution] = {
                "name": institution,
                "rankings": uni_rankings,
                "advisors": [],
                "_score": calculate_geometric_mean_score(uni_rankings) # Calculate and store score
            }

        # Create Advisor Object
        advisor_papers = {}
        prof_specific_counts = prof_papers_data.get(prof_name_cs, {})
        for area_code in AREA_DEFINITIONS:
            count = prof_specific_counts.get(area_code, 0.0)
            advisor_papers[area_code] = create_paper_category(area_code, count)

        raw_content_data = deepcopy(input_entry)
        raw_content_data.pop("scholar_id", None)

        advisor_obj = {
            "name": prof_name_cs,
            "href": final_homepage,
            "papers": advisor_papers,
            "raw_content": raw_content_data
        }

        output_universities[institution]["advisors"].append(advisor_obj)
        processed_prof_keys.add(prof_key)

    print(f"Finished processing input entries. Found {len(output_universities)} universities.")
    print(f"{not_found_count} input entries could not be matched.")

    # 6. Sort Universities by Score and Format Final Output
    print("\n--- Sorting Universities and Formatting Output ---")
    # Sort universities based on the calculated score in descending order
    sorted_university_list = sorted(output_universities.values(), key=lambda u: u.get("_score", 0.0), reverse=True)

    # Remove the temporary score before final output
    for uni in sorted_university_list:
        uni.pop("_score", None)
        # Also remove _raw_count from rankings and papers
        for area_code in uni.get("rankings", {}):
            uni["rankings"][area_code].pop("_raw_count", None)
        for advisor in uni.get("advisors", []):
             for area_code in advisor.get("papers", {}):
                 advisor["papers"][area_code].pop("_raw_count", None)

    final_output = {"universities": sorted_university_list}

    # 7. Write Output JSON
    print(f"\n--- Writing Sorted Structured JSON to: {OUTPUT_JSON_PATH} ---")
    try:
        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        print("Successfully wrote sorted structured JSON file.")
    except Exception as e:
        print(f"Error writing output JSON: {e}")
        sys.exit(1)

    print("\nStructuring and sorting process completed.")

if __name__ == "__main__":
    main()

