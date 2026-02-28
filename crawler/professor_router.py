from fastapi import APIRouter
import logging
import os
import json
import time
import hashlib
from config import get_settings
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from . import parse_scraped_data as psd
# --- Configuration & Data Definitions ---
settings = get_settings()
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
       # logging.FileHandler("professor_scraper.log"),
        #logging.StreamHandler()
    ]
)
logger = logging.getLogger("ProfessorScraper")

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
        homepages, scholar_ids, author_notes = psd.load_author_info()

        # Create a list of professors with their metadata, deduplicating by homepage URL
        professors = []
        seen_urls = set()
        for name, homepage in homepages.items():
            if homepage and homepage.strip() and homepage not in seen_urls:
                seen_urls.add(homepage)
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


def save_scraped_data(data, output_file=os.getcwd() + "/logs/" + "scraped_professors.json"):
    """Save the scraped data to a JSON file."""
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved scraped data to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving scraped data: {str(e)}")
        return False


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


router = APIRouter()


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

