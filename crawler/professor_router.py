from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import logging
import os
import json
import time
import hashlib
import sys
from config import get_settings
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
from qdrant_client import QdrantClient
from qdrant_client.http import models
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import io
import math
from collections import defaultdict
from openai import OpenAI


# --- Configuration & Data Definitions ---

# Define URLs for the CSV files
TURING_URL = "https://csrankings.org/turing.csv"
ACMFELLOW_URL = "https://csrankings.org/acm-fellows.csv"
AUTHOR_URL = "https://csrankings.org/csrankings.csv"
AUTHOR_INFO_URL = "https://csrankings.org/generated-author-info.csv"
COUNTRY_INFO_URL = "https://csrankings.org/country-info.csv"

# Regex to match name and note like in the JS code
NAME_MATCHER = re.compile(r"^(.*)\s+\[(.*?)\]$")

# Area definitions based on csrankings.js
AREA_MAP = [
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
    {"area": "icde", "title": "DB"},  # next tier
    {"area": "pods", "title": "DB"},  # next tier
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
    {"area": "fast", "title": "OS"},  # next tier
    {"area": "usenixatc", "title": "OS"},  # next tier
    {"area": "eurosys", "title": "OS"},
    {"area": "pldi", "title": "PL"},
    {"area": "popl", "title": "PL"},
    {"area": "icfp", "title": "PL"},  # next tier
    {"area": "oopsla", "title": "PL"},  # next tier
    {"area": "plan", "title": "PL"},
    {"area": "soft", "title": "SE"},
    {"area": "fse", "title": "SE"},
    {"area": "icse", "title": "SE"},
    {"area": "ase", "title": "SE"},  # next tier
    {"area": "issta", "title": "SE"},  # next tier
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

AI_AREAS = ["ai", "vision", "mlmining", "nlp", "inforet"]
SYSTEMS_AREAS = ["arch", "comm", "sec", "mod", "da", "bed", "hpc", "mobile", "metrics", "ops", "plan", "soft"]
THEORY_AREAS = ["act", "crypt", "log"]
INTERDISCIPLINARY_AREAS = ["bio", "graph", "csed", "ecom", "chi", "robotics", "visualization"]

# Build derived area structures
AREAS = [item["area"] for item in AREA_MAP]
AREA_TITLES = {item["area"]: item["title"] for item in AREA_MAP}

# Parent map (conference -> area)
PARENT_MAP = {item["area"]: item["title"] for item in AREA_MAP if
              item["area"] != item["title"].lower().replace("+", "").replace(".", "")}

# Top-level areas (those that are titles)
TOP_LEVEL_AREAS = {item["title"].lower().replace("+", "").replace(".", ""): item["title"] for item in AREA_MAP}
TOP_LEVEL_AREA_KEYS = list(TOP_LEVEL_AREAS.keys())

# Next tier conferences (used for exclusion in some counts)
NEXT_TIER = {
    "icde": True, "pods": True, "fast": True, "usenixatc": True,
    "icfp": True, "oopsla": True, "ase": True, "issta": True
}

# Top tier areas (excluding next tier)
TOP_TIER_AREAS = {area: True for area in AREAS if area not in NEXT_TIER}

# Map conferences to their top-level area
CONF_TO_TOP_AREA = {conf: AREA_TITLES[conf].lower().replace("+", "").replace(".", "")
                    for conf in PARENT_MAP}


# --- Data Loading Functions (Modified for Error Handling) ---

def download_csv_to_dataframe(url):
    """Downloads CSV from a URL and returns a pandas DataFrame."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        csv_content = io.StringIO(response.text)
        df = pd.read_csv(csv_content, header=0)
        print(f"Successfully downloaded and parsed CSV from {url}")
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error downloading CSV from {url}: {e}")
        return None
    except pd.errors.EmptyDataError:
        print(f"Error: No data or empty CSV found at {url}")
        return None
    except Exception as e:
        print(f"Error processing CSV from {url}: {e}")
        return None


def load_turing_data(url=TURING_URL):
    """Loads Turing award data from a URL."""
    df = download_csv_to_dataframe(url)
    if df is None:
        return {}
    try:
        turing_data = df.set_index("name")["year"].to_dict()
        print(f"Successfully processed Turing data from {url}")
        return turing_data
    except KeyError as e:
        print(f"Error processing Turing data: Missing expected column {e}")
        return {}
    except Exception as e:
        print(f"Error processing Turing data from {url}: {e}")
        return {}


def load_acm_fellow_data(url=ACMFELLOW_URL):
    """Loads ACM Fellow data from a URL."""
    df = download_csv_to_dataframe(url)
    if df is None:
        return {}
    try:
        acm_fellow_data = df.set_index("name")["year"].to_dict()
        print(f"Successfully processed ACM Fellow data from {url}")
        return acm_fellow_data
    except KeyError as e:
        print(f"Error processing ACM Fellow data: Missing expected column {e}")
        return {}
    except Exception as e:
        print(f"Error processing ACM Fellow data from {url}: {e}")
        return {}


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


def load_authors_publications(url=AUTHOR_INFO_URL):
    """Loads author publication data from the generated CSV file URL."""
    df = download_csv_to_dataframe(url)
    if df is None:
        return pd.DataFrame()
    # Ensure correct types
    try:
        df["year"] = pd.to_numeric(df["year"])
        df["count"] = pd.to_numeric(df["count"])
        df["adjustedcount"] = pd.to_numeric(df["adjustedcount"])
    except KeyError as e:
        print(f"Error processing Author Publications: Missing expected column {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error converting types in Author Publications: {e}")
        # Return df anyway, maybe calculations fail later

    print(f"Successfully processed author publications from {url}")
    return df


def load_country_info(url=COUNTRY_INFO_URL):
    """Loads country/region information for institutions from URL."""
    country_info = {}
    country_abbrv = {}
    df = download_csv_to_dataframe(url)
    if df is None:
        return {}, {}
    try:
        for index, row in df.iterrows():
            institution = row["institution"]
            country_info[institution] = row["region"]
            country_abbrv[institution] = row["countryabbrv"]
        print(f"Successfully processed country info from {url}")
        return country_info, country_abbrv
    except KeyError as e:
        print(f"Error processing Country info: Missing expected column {e}")
        return {}, {}
    except Exception as e:
        print(f"Error processing country info from {url}: {e}")
        return {}, {}


# --- Ranking Logic Functions ---

def is_in_region(dept, target_region, country_regions, country_abbreviations):
    """Checks if a department is in the target region."""
    dept_region = country_regions.get(dept)
    dept_abbrv = country_abbreviations.get(dept)

    if target_region == "us":
        return dept not in country_regions
    elif target_region == "northamerica":
        # US (not in country_regions) or Canada
        return dept not in country_regions or dept_region == "canada"
    elif target_region == "world":
        return True
    elif target_region in ["europe", "asia", "australasia", "southamerica", "africa", "canada"]:
        return dept_region == target_region
    else:  # Specific country abbreviation
        return dept_abbrv == target_region


def _filter_publications(author_publications_df, selected_areas, start_year, end_year):
    """Helper function to filter publications by area and year."""
    if author_publications_df.empty:
        return pd.DataFrame()

    valid_areas = {area for area in selected_areas if area in TOP_LEVEL_AREA_KEYS}
    if not valid_areas:
        print("Warning: No valid top-level areas selected.")
        return pd.DataFrame()

    # Filter by year first
    filtered_df = author_publications_df[
        (author_publications_df["year"] >= start_year) &
        (author_publications_df["year"] <= end_year)
        ].copy()

    # Map publication area (conference) to top-level area
    filtered_df["top_area"] = filtered_df["area"].map(CONF_TO_TOP_AREA)

    # Keep only publications in selected top-level areas
    filtered_df = filtered_df[filtered_df["top_area"].isin(valid_areas)]

    return filtered_df, valid_areas


def calculate_ranking(author_publications_df, country_regions, country_abbreviations,
                      selected_areas, start_year, end_year, target_region="world"):
    """Calculates institution rankings based on selected criteria."""

    filtered_df, valid_areas = _filter_publications(author_publications_df, selected_areas, start_year, end_year)

    if filtered_df.empty:
        print(f"Warning: No publications found for selected areas {selected_areas} between {start_year}-{end_year}.")
        return pd.DataFrame()

    # Aggregate adjusted counts per institution per top-level area & count faculty
    inst_area_counts = defaultdict(lambda: defaultdict(float))
    inst_faculty_count = defaultdict(int)
    inst_faculty_names = defaultdict(set)

    for _, row in filtered_df.iterrows():
        dept = row["dept"]
        name = row["name"]
        top_area = row["top_area"]
        adj_count = row["adjustedcount"]

        # Filter by region
        if not is_in_region(dept, target_region, country_regions, country_abbreviations):
            continue

        inst_area_counts[dept][top_area] += adj_count

        if name not in inst_faculty_names[dept]:
            inst_faculty_names[dept].add(name)
            inst_faculty_count[dept] += 1

    if not inst_area_counts:
        print(f"Warning: No institutions found matching the region ",
              f"\"{target_region}\" with publications in selected areas/years.")
        return pd.DataFrame()

    # Calculate geometric mean score for each institution
    num_selected_areas = len(valid_areas)
    inst_scores = {}
    for dept, area_counts in inst_area_counts.items():
        product = 1.0
        for area in valid_areas:
            product *= (area_counts.get(area, 0.0) + 1.0)

        if num_selected_areas > 0:
            geo_mean = math.pow(product, 1.0 / num_selected_areas)
            inst_scores[dept] = geo_mean
        else:
            inst_scores[dept] = 0.0

    # Create ranked DataFrame
    ranked_list = sorted(inst_scores.items(), key=lambda item: item[1], reverse=True)

    results = []
    current_rank = 0
    last_score = float("inf")
    tie_count = 1

    for i, (dept, score) in enumerate(ranked_list):
        if score < last_score:
            current_rank += tie_count
            tie_count = 1
        else:
            tie_count += 1

        last_score = score

        results.append({
            "Rank": current_rank,
            "Institution": dept,
            "Score": round(score, 1),
            "Faculty Count": inst_faculty_count.get(dept, 0)
        })

    ranked_df = pd.DataFrame(results)
    return ranked_df


def get_ranked_professors(institution_name, author_publications_df,
                          selected_areas, start_year, end_year):
    """Gets a ranked list of professors for a specific institution based on criteria."""

    filtered_df, valid_areas = _filter_publications(author_publications_df, selected_areas, start_year, end_year)

    if filtered_df.empty:
        print(f"Warning: No publications found for selected areas {selected_areas} between {start_year}-{end_year}.")
        return pd.DataFrame()

    # Filter for the specific institution
    inst_df = filtered_df[filtered_df["dept"] == institution_name].copy()

    if inst_df.empty:
        print(f"Warning: No publications found for institution ",
              f"\"{institution_name}\" with selected areas/years.")
        return pd.DataFrame()

    # Aggregate counts per professor
    prof_counts = defaultdict(lambda: {"total_count": 0, "adj_count": 0.0})
    for _, row in inst_df.iterrows():
        name = row["name"]
        prof_counts[name]["total_count"] += row["count"]
        prof_counts[name]["adj_count"] += row["adjustedcount"]

    # Create list of professors with their counts
    prof_list = [
        {
            "Professor": name,
            "Pubs": data["total_count"],
            "Adj Pubs": round(data["adj_count"], 1)
        }
        for name, data in prof_counts.items()
    ]

    # Sort according to JS logic: Pubs (desc), Adj Pubs (desc), Name (asc)
    # Note: Python's sort is stable, so we can sort multiple times.
    # Sort by name ascending
    prof_list.sort(key=lambda x: x["Professor"])
    # Sort by adjusted count descending
    prof_list.sort(key=lambda x: x["Adj Pubs"], reverse=True)
    # Sort by total count descending (this is the primary sort key)
    prof_list.sort(key=lambda x: x["Pubs"], reverse=True)

    ranked_prof_df = pd.DataFrame(prof_list)
    return ranked_prof_df

settings = get_settings()
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("professor_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ProfessorScraper")

# Qdrant configuration
QDRANT_URL = settings.QDRANT_URL
QDRANT_API_KEY = settings.QDRANT_API_KEY
COLLECTION_NAME = "professors"

# Constants for scraping
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
REQUEST_TIMEOUT = 2  # seconds - reduced from 10
RATE_LIMIT_DELAY = 0.1  # seconds between requests - reduced from 1
MAX_WORKERS = 10  # Number of parallel workers for scraping
CACHE_DIR = "scrape_cache"  # Directory to store cached responses

# OpenAI configuration
# Note: The user will need to add their OpenAI API key
OPENAI_API_KEY = settings.OPENAI_API_KEY  # User needs to fill this in
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI's embedding model
EMBEDDING_DIMENSION = 1536  # Dimension of OpenAI's text-embedding-ada-002 model
MAX_TOKENS = 8191  # Maximum tokens for text-embedding-ada-002

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def clean_text(text):
    """Clean and normalize text from web pages."""
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters and normalize
    text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
    return text.strip()


def extract_text_from_html(html_content):
    """Extract meaningful text from HTML content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script_or_style in soup(["script", "style", "header", "footer", "nav"]):
            script_or_style.extract()

        # Get text
        text = soup.get_text()

        # Clean text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return clean_text(text)
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {str(e)}")
        return ""

def get_cache_filename(url):
    """Generate a cache filename for a URL."""
    # Create a hash of the URL to use as filename
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.json")

def is_cached(url):
    """Check if a URL is already cached."""
    cache_file = get_cache_filename(url)
    return os.path.exists(cache_file)

def get_from_cache(url):
    """Get cached scrape result for a URL."""
    cache_file = get_cache_filename(url)
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading from cache for {url}: {str(e)}")
    return None

def save_to_cache(url, result):
    """Save scrape result to cache."""
    cache_file = get_cache_filename(url)
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving to cache for {url}: {str(e)}")
        return False


def scrape_professor_homepage(url):
    """Scrape text content from a professor's homepage with caching."""
    if not url or url == "" or url.lower() == "noscholarpage":
        return {"success": False, "error": "Invalid URL", "text": "", "cached": False}

    # Ensure URL has a scheme
    if not urlparse(url).scheme:
        url = "https://" + url

    # Check cache first
    cached_result = get_from_cache(url)
    if cached_result:
        logger.info(f"Using cached result for: {url}")
        cached_result["cached"] = True
        return cached_result

    try:
        logger.info(f"Scraping: {url}")
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        # Check if request was successful
        if response.status_code != 200:
            result = {
                "success": False,
                "error": f"HTTP error {response.status_code}",
                "text": "",
                "cached": False
            }
            save_to_cache(url, result)
            return result

        # Extract text from HTML
        text = extract_text_from_html(response.text)

        # Check if we got meaningful content
        if len(text) < 50:  # Arbitrary threshold for meaningful content
            logger.warning(f"Limited content found at {url}: only {len(text)} characters")

        result = {
            "success": True,
            "error": "",
            "text": text,
            "url": url,
            "cached": False
        }

        # Save to cache
        save_to_cache(url, result)

        return result

    except requests.exceptions.Timeout:
        logger.error(f"Timeout while scraping {url}")
        result = {"success": False, "error": "Request timeout", "text": "", "cached": False}
        save_to_cache(url, result)
        return result
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error while scraping {url}")
        result = {"success": False, "error": "Connection error", "text": "", "cached": False}
        save_to_cache(url, result)
        return result
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        result = {"success": False, "error": str(e), "text": "", "cached": False}
        save_to_cache(url, result)
        return result


def scrape_professor_worker(professor):
    """Worker function for parallel scraping."""
    try:
        # Scrape the homepage
        scrape_result = scrape_professor_homepage(professor['homepage'])

        # Combine professor metadata with scrape results
        professor_data = {
            **professor,
            "scrape_success": scrape_result["success"],
            "scrape_error": scrape_result["error"],
            "content": scrape_result["text"],
            "cached": scrape_result.get("cached", False)
        }

        return professor_data
    except Exception as e:
        logger.error(f"Error in worker processing {professor['name']}: {str(e)}")
        return {
            **professor,
            "scrape_success": False,
            "scrape_error": f"Worker error: {str(e)}",
            "content": "",
            "cached": False
        }


def scrape_professors_parallel(professors, max_professors=None, max_workers=MAX_WORKERS):
    """Scrape data from professor homepages in parallel with caching."""
    # Limit the number of professors if specified
    if max_professors:
        professors = professors[:max_professors]

    total = len(professors)
    logger.info(f"Starting to scrape {total} professor homepages in parallel (max workers: {max_workers})...")

    results = []
    cached_count = 0
    start_time = time.time()

    # Use ThreadPoolExecutor for parallel scraping
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_professor = {executor.submit(scrape_professor_worker, professor): professor for professor in
                               professors}

        # Process results as they complete
        for i, future in enumerate(future_to_professor):
            professor = future_to_professor[future]
            try:
                professor_data = future.result()
                results.append(professor_data)

                # Track cache hits
                if professor_data.get("cached", False):
                    cached_count += 1

                # Log progress periodically
                if (i + 1) % 10 == 0 or (i + 1) == total:
                    elapsed = time.time() - start_time
                    logger.info(
                        f"Progress: {i + 1}/{total} professors processed ({elapsed:.2f}s elapsed, {cached_count} from cache)")

            except Exception as e:
                logger.error(f"Error processing result for {professor['name']}: {str(e)}")
                # Add error result
                results.append({
                    **professor,
                    "scrape_success": False,
                    "scrape_error": f"Future error: {str(e)}",
                    "content": "",
                    "cached": False
                })

    elapsed_time = time.time() - start_time
    logger.info(f"Completed scraping {len(results)} professors in {elapsed_time:.2f}s ({cached_count} from cache)")

    # Calculate stats
    stats = {
        "total_professors": len(results),
        "cached_count": cached_count,
        "cache_hit_rate": cached_count / len(results) if results else 0,
        "elapsed_seconds": elapsed_time,
        "professors_per_second": len(results) / elapsed_time if elapsed_time > 0 else 0
    }

    return results, stats


def get_professors_from_ranking():
    """Extract professor information from the ranking data."""
    try:
        # Load the ranking script to access its functions
        # Load the necessary data
        logger.info("Loading professor data from ranking file...")
        homepages, scholar_ids, author_notes = load_author_info()
        author_publications = load_authors_publications()

        # Create a list of professors with their metadata
        professors = []
        for name, homepage in homepages.items():
            if homepage and homepage.strip():
                professor = {
                    "name": name,
                    "homepage": homepage,
                    "scholar_id": scholar_ids.get(name, ""),
                    "note": author_notes.get(name, "")
                }
                professors.append(professor)

        logger.info(f"Found {len(professors)} professors with homepages")
        return professors

    except Exception as e:
        logger.error(f"Error loading professor data: {str(e)}")
        return []


def save_scraped_data(data, output_file="scraped_professors.json"):
    """Save the scraped data to a JSON file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved scraped data to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving scraped data: {str(e)}")
        return False


def load_scraped_data(input_file="scraped_professors.json"):
    """Load previously scraped data from a JSON file."""
    try:
        if not os.path.exists(input_file):
            logger.error(f"File not found: {input_file}")
            return []

        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} scraped professor records from {input_file}")
        return data
    except Exception as e:
        logger.error(f"Error loading scraped data: {str(e)}")
        return []

client = OpenAI(api_key=OPENAI_API_KEY)
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


def create_stable_id(name, homepage):
    """Create a stable ID for a professor based on name and homepage."""
    # Create a unique string
    unique_string = f"{name}|{homepage}"

    # Generate a hash
    hash_object = hashlib.md5(unique_string.encode())
    hex_dig = hash_object.hexdigest()

    # Convert to integer (Qdrant uses int64)
    # Take first 16 chars of hex (64 bits) and convert to int
    int_id = int(hex_dig[:16], 16) % (2 ** 63)  # Ensure it fits in int64

    return int_id


def prepare_for_qdrant(scraped_data, with_embeddings=False):
    """Prepare the scraped data for Qdrant storage."""
    prepared_data = []

    # Extract texts for embedding if needed
    texts = []
    valid_indices = []
    if with_embeddings:
        for i, item in enumerate(scraped_data):
            if item["scrape_success"] and item["content"]:
                texts.append(item["content"])
                valid_indices.append(i)

    # Generate embeddings if requested
    embeddings = []
    if with_embeddings and texts:
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        embeddings = generate_embeddings_with_openai(texts)
        logger.info(f"Generated {len(embeddings)} embeddings")

    # Create records for Qdrant
    embedding_idx = 0
    for i, item in enumerate(scraped_data):
        if not item["scrape_success"] or not item["content"]:
            logger.warning(f"Skipping failed/empty scrape for {item['name']}")
            continue

        # Create a stable ID
        unique_id = create_stable_id(item["name"], item["homepage"])

        # Create the record
        record = {
            "id": unique_id,
            "payload": {
                "name": item["name"],
                "homepage": item["homepage"],
                "chunk_index": item["chunk_index"],
                "scholar_id": item["scholar_id"],
                "note": item["note"]
            }
        }

        # Add embedding if available
        if with_embeddings and i in valid_indices and embedding_idx < len(embeddings):
            record["vector"] = embeddings[embedding_idx]
            embedding_idx += 1

        prepared_data.append(record)

    return prepared_data


def setup_qdrant_collection():
    """Set up the Qdrant collection for professor data."""
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        if COLLECTION_NAME in collection_names:
            logger.info(f"Collection {COLLECTION_NAME} already exists")
        else:
            # Create a new collection
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Created new collection: {COLLECTION_NAME}")

        return client
    except Exception as e:
        logger.error(f"Error setting up Qdrant collection: {str(e)}")
        return None


def upload_to_qdrant(client, prepared_data):
    """Upload prepared data to Qdrant."""
    if not client:
        logger.error("Qdrant client is not initialized")
        return False

    if not prepared_data:
        logger.warning("No data to upload to Qdrant")
        return False

    try:
        # Check if vectors are included
        has_vectors = "vector" in prepared_data[0]

        if has_vectors:
            # Upload data with vectors
            logger.info(f"Uploading {len(prepared_data)} records with embeddings to Qdrant...")

            # Prepare points in Qdrant format
            points = [
                models.PointStruct(
                    id=item["id"],
                    vector=item["vector"],
                    payload=item["payload"]
                )
                for item in prepared_data
            ]

            # Upload in batches to avoid timeouts
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=batch
                )
                logger.info(f"Uploaded batch {i // batch_size + 1}/{(len(points) - 1) // batch_size + 1}")
                time.sleep(1)  # Avoid overwhelming the server

            logger.info(f"Successfully uploaded {len(prepared_data)} records with embeddings to Qdrant")
        else:
            logger.warning("Data does not contain embeddings, cannot upload to Qdrant")
            return False

        return True
    except Exception as e:
        logger.error(f"Error uploading to Qdrant: {str(e)}")
        return False


def test_qdrant_search(client, query_text, top_k=5):
    """Test search functionality in Qdrant."""
    if not client:
        logger.error("Qdrant client is not initialized")
        return []

    if not OPENAI_API_KEY:
        logger.error("OpenAI API key is not set. Cannot generate query embedding.")
        return []

    try:
        # Generate embedding for query text
        import openai
        openai.api_key = OPENAI_API_KEY

        response = openai.Embedding.create(
            model=EMBEDDING_MODEL,
            input=query_text
        )
        query_vector = response['data'][0]['embedding']

        # Search Qdrant
        search_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k
        )

        # Format results
        results = []
        for result in search_results:
            results.append({
                "score": result.score,
                "name": result.payload.get("name", "Unknown"),
                "homepage": result.payload.get("homepage", ""),
                "content_preview": result.payload.get("content_preview", "")[:200] + "..."
            })

        return results
    except Exception as e:
        logger.error(f"Error searching Qdrant: {str(e)}")
        return []


def clear_cache():
    """Clear the scraping cache."""
    try:
        count = 0
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith('.json'):
                os.remove(os.path.join(CACHE_DIR, filename))
                count += 1
        logger.info(f"Cleared {count} files from cache")
        return count
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return 0


def get_cache_stats():
    """Get statistics about the cache."""
    try:
        files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.json')]
        total_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) for f in files)
        return {
            "count": len(files),
            "size_bytes": total_size,
            "size_mb": total_size / (1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return {"count": 0, "size_bytes": 0, "size_mb": 0}


# FastAPI Router and Models
router = APIRouter()


# Define Pydantic models for request/response
class ScrapeRequest(BaseModel):
    max_professors: int = Field(10, description="Maximum number of professors to scrape")
    save_file: str = Field("scraped_professors.json", description="Filename to save scraped data")
    max_workers: int = Field(MAX_WORKERS, description="Maximum number of parallel workers")
    use_cache: bool = Field(True, description="Whether to use cache for scraping")


class EmbeddingRequest(BaseModel):
    input_file: str = Field("scraped_professors.json", description="Input file with scraped data")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (if not set in environment)")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    top_k: int = Field(5, description="Number of results to return")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (if not set in environment)")


class CacheRequest(BaseModel):
    clear: bool = Field(False, description="Whether to clear the cache")


class ProfessorData(BaseModel):
    name: str
    homepage: str
    scholar_id: Optional[str] = None
    note: Optional[str] = None
    content: Optional[str] = None
    scrape_success: bool = True
    scrape_error: str = ""
    cached: Optional[bool] = None


class TaskStatus(BaseModel):
    task_id: str
    status: str
    message: str
    progress: Optional[float] = None
    result_file: Optional[str] = None
    stats: Optional[Dict] = None


# Store for background tasks
task_store = {}


def generate_task_id():
    """Generate a unique task ID"""
    return hashlib.md5(str(time.time()).encode()).hexdigest()


# Background task functions
async def scrape_task(task_id: str, max_professors: int, save_file: str, max_workers: int, use_cache: bool):
    """Background task for scraping professor data"""
    try:
        task_store[task_id] = {"status": "running", "message": "Starting scraping task", "progress": 0}

        # If not using cache, clear it first
        if not use_cache:
            clear_cache()
            task_store[task_id]["message"] = "Cache cleared, starting scraping"

        # Get professor data
        professors = get_professors_from_ranking()
        task_store[task_id]["progress"] = 10
        task_store[task_id]["message"] = f"Found {len(professors)} professors"
        logger.info(f"Found {len(professors)} professors")

        # Scrape professor homepages in parallel
        scraped_data, stats = scrape_professors_parallel(
            professors,
            max_professors=max_professors,
            max_workers=max_workers
        )
        task_store[task_id]["progress"] = 90
        task_store[task_id]["message"] = f"Scraped {len(scraped_data)} professors ({stats['cached_count']} from cache)"

        # Save the scraped data
        save_scraped_data(scraped_data, save_file)

        task_store[task_id] = {
            "status": "completed",
            "message": f"Completed scraping {len(scraped_data)} professors in {stats['elapsed_seconds']:.2f}s",
            "progress": 100,
            "result_file": save_file,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error in scraping task: {str(e)}")
        task_store[task_id] = {"status": "failed", "message": f"Error: {str(e)}", "progress": 100}


async def embedding_task(task_id: str, input_file: str, openai_api_key: Optional[str] = None):
    """Background task for generating embeddings and uploading to Qdrant"""
    try:
        task_store[task_id] = {"status": "running", "message": "Starting embedding task", "progress": 0}

        # Set OpenAI API key if provided
        global OPENAI_API_KEY
        if openai_api_key:
            OPENAI_API_KEY = openai_api_key

        # Check if OpenAI API key is set
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key is not set")

        # Load scraped data
        scraped_data = load_scraped_data(input_file)
        if not scraped_data:
            raise ValueError(f"No data found in {input_file}")

        task_store[task_id]["progress"] = 10
        task_store[task_id]["message"] = f"Loaded {len(scraped_data)} professor records"

        # Prepare data for Qdrant with embeddings
        prepared_data = prepare_for_qdrant(scraped_data, with_embeddings=True)
        task_store[task_id]["progress"] = 70
        task_store[task_id]["message"] = f"Generated embeddings for {len(prepared_data)} records"

        # Set up Qdrant collection
        qdrant_client = setup_qdrant_collection()
        if not qdrant_client:
            raise ValueError("Failed to connect to Qdrant")

        task_store[task_id]["progress"] = 80
        task_store[task_id]["message"] = "Connected to Qdrant, uploading data"

        # Upload to Qdrant
        upload_success = upload_to_qdrant(qdrant_client, prepared_data)
        if not upload_success:
            raise ValueError("Failed to upload data to Qdrant")

        # Save the result file with IDs for reference
        result_file = f"qdrant_upload_{int(time.time())}.json"
        with open(result_file, 'w') as f:
            json.dump([{"id": item["id"], "name": item["payload"]["name"]} for item in prepared_data], f)

        task_store[task_id] = {
            "status": "completed",
            "message": f"Uploaded {len(prepared_data)} records to Qdrant",
            "progress": 100,
            "result_file": result_file
        }
    except Exception as e:
        logger.error(f"Error in embedding task: {str(e)}")
        task_store[task_id] = {"status": "failed", "message": f"Error: {str(e)}", "progress": 100}


# API Endpoints
@router.get("/professor/status")
async def professor_status():
    """Check if the professor API is running and get cache statistics"""
    cache_stats = get_cache_stats()
    return {
        "message": "Professor Data API is running",
        "cache": {
            "enabled": True,
            "directory": CACHE_DIR,
            "files": cache_stats["count"],
            "size_mb": cache_stats["size_mb"]
        },
        "parallel_processing": {
            "enabled": True,
            "max_workers": MAX_WORKERS
        }
    }


@router.post("/professor/scrape", response_model=TaskStatus)
async def scrape_professors_endpoint(
        background_tasks: BackgroundTasks,
        request: ScrapeRequest
):
    """Start a background task to scrape professor data"""
    task_id = generate_task_id()
    task_store[task_id] = {"status": "queued", "message": "Task queued", "progress": 0}
    background_tasks.add_task(
        scrape_task,
        task_id,
        request.max_professors,
        request.save_file,
        request.max_workers,
        request.use_cache
    )
    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"Scraping task started with {request.max_workers} workers, cache {'enabled' if request.use_cache else 'disabled'}"
    }


@router.post("/professor/embed", response_model=TaskStatus)
async def generate_embeddings_endpoint(
        background_tasks: BackgroundTasks,
        request: EmbeddingRequest
):
    """Start a background task to generate embeddings and upload to Qdrant"""
    task_id = generate_task_id()
    task_store[task_id] = {"status": "queued", "message": "Task queued", "progress": 0}
    background_tasks.add_task(embedding_task, task_id, request.input_file, request.openai_api_key)
    return {"task_id": task_id, "status": "queued", "message": "Embedding task started"}


@router.get("/professor/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a background task"""
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, **task_store[task_id]}


@router.post("/professor/search")
async def search_professors(request: SearchRequest):
    """Search for professors using vector similarity"""
    try:
        # Set OpenAI API key if provided
        global OPENAI_API_KEY
        if request.openai_api_key:
            OPENAI_API_KEY = request.openai_api_key

        # Check if OpenAI API key is set
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=400, detail="OpenAI API key is not set")

        # Set up Qdrant client
        qdrant_client = setup_qdrant_collection()
        if not qdrant_client:
            raise HTTPException(status_code=500, detail="Failed to connect to Qdrant")

        # Search Qdrant
        search_results = test_qdrant_search(qdrant_client, request.query, request.top_k)

        if not search_results:
            return {"results": [], "message": "No results found"}

        return {"results": search_results, "count": len(search_results)}

    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/professor/list", response_model=List[ProfessorData])
async def get_professors(
        limit: int = Query(10, description="Maximum number of professors to return"),
        offset: int = Query(0, description="Offset for pagination")
):
    """Get a list of professors from the scraped data"""
    try:
        # Load the most recent scraped data file
        files = [f for f in os.listdir() if f.startswith("scraped_professors") and f.endswith(".json")]
        if not files:
            raise HTTPException(status_code=404, detail="No scraped data found")

        # Sort by modification time (most recent first)
        latest_file = max(files, key=lambda f: os.path.getmtime(f))

        # Load the data
        scraped_data = load_scraped_data(latest_file)

        # Apply pagination
        paginated_data = scraped_data[offset:offset + limit]

        return paginated_data

    except Exception as e:
        logger.error(f"Error getting professors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/professor/cache")
async def manage_cache(request: CacheRequest):
    """Manage the scraping cache"""
    try:
        stats = get_cache_stats()

        if request.clear:
            cleared = clear_cache()
            return {
                "message": f"Cache cleared: {cleared} files removed",
                "previous_stats": stats,
                "current_stats": get_cache_stats()
            }
        else:
            return {
                "message": "Cache statistics",
                "stats": stats
            }

    except Exception as e:
        logger.error(f"Error managing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
