import logging
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from .storage import CrawlerStorage
from selenium.webdriver.chrome.options import Options
from fastapi import APIRouter
from .data_model import DataModel, University, Rankings, Advisor, Papers
from config import get_settings
import re 
router = APIRouter()
CSV_URL = "https://csrankings.org/csrankings.csv"

# https://csrankings.org/#/index?vision
cs_categories = {
    # "ai": "Artificial intelligence",
    # "vision": "Computer vision",
    # "mlmining": "Machine Learning",
    # "nlp": "Natural language processing",
    # "inforet": "The Web & information retrieval",
    # "arch": "Computer architecture",
    # "comm": "Computer networks",
    # "sec": "Computer security",
    # "mod": "Databases",
    # "da": "Design automation",
    # "bed": "Embedded & real-time systems",
    # "hpc": "High-performance computing",
    # "mobile": "Mobile computing",
    # "metrics": "Measurement & perf. analysis",
    # "ops": "Operating systems",
    # "plan": "Programming languages",
    # "soft": "Software engineering",
    # "act": "Algorithms & complexity",
    # "crypt": "Cryptography",
    # "log": "Logic & verification",
    # "graph": "Computer graphics",
    # "bio": "Comp. bio & bioinformatics",
    # "csed": "Computer science education",
    "ecom": "Economics & computation",
    "chi": "Human-computer interaction",
    "robotics": "Robotics",
    "visualization": "Visualization",
}

import requests
from pathlib import Path
import json
import logging
from typing import Dict, Set

class AdvisorCrawler:
    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.storage_dir = Path("data/advisors")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load previously crawled URLs
        self._load_visited_urls()
    
    def _load_visited_urls(self):
        """Load previously crawled URLs from saved files"""
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if 'url' in data.get('raw_content', {}):
                        self.visited_urls.add(data['raw_content']['url'])
            except Exception as e:
                logging.error(f"Error loading {file}: {e}")

    async def crawl_advisor_details(self, advisor_href: str) -> Dict:
        """Crawl advisor webpage using requests first, fallback to Selenium if needed"""
        if advisor_href in self.visited_urls:
            logging.info(f"Already crawled {advisor_href}")
            return None
            
        # First attempt with requests
        try:
            response = requests.get(advisor_href, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            content = self._parse_content(soup, advisor_href)
            
            # If content is empty, raise exception to trigger Selenium fallback
            if not content['raw_text'].strip() or len(content['raw_text']) < 100:
                raise ValueError("Empty content")
                
            self.visited_urls.add(advisor_href)
            return content
            
        except (requests.RequestException, ValueError) as e:
            logging.warning(f"Requests failed for {advisor_href}, trying Selenium: {str(e)}")
            
            # Fallback to Selenium
            try:
                content = await self._try_selenium_fallback(advisor_href)
                if content and content['raw_text'].strip():
                    self.visited_urls.add(advisor_href)
                    return content
            except Exception as se:
                logging.error(f"Selenium also failed for {advisor_href}: {str(se)}")
            
            return self._create_error_content(advisor_href, str(e))

    async def _try_selenium_fallback(self, url: str) -> Dict:
        """Fallback method using Selenium"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.page_load_strategy = 'eager'
        
        try:
            browser = webdriver.Chrome(options=options)
            browser.set_page_load_timeout(10)
            browser.set_script_timeout(10)
            
            browser.get(url)
            time.sleep(2)  # Short wait for dynamic content
            
            soup = BeautifulSoup(browser.page_source, "html.parser")
            return self._parse_content(soup, url)
            
        finally:
            try:
                browser.quit()
            except:
                pass

    def _parse_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Parse BeautifulSoup content into structured dictionary"""
        raw_context = soup.get_text(separator=' ', strip=True)
        raw_context_without_spaces = re.sub(r'\s+', ' ', raw_context)
        raw_context_without_lines_extra = re.sub(r'\n+', '\n', raw_context_without_spaces)
        raw_text = raw_context_without_lines_extra.strip()
        return {
            'raw_text': raw_text,
            'links': [a.get('href') for a in soup.find_all('a', href=True)],
            'page_title': soup.title.string if soup.title else '',
            'url': url,
            'crawl_status': 'success'
        }

    def _create_error_content(self, url: str, error: str) -> Dict:
        return {
            'raw_text': '',
            'links': [],
            'page_title': '',
            'url': url,
            'crawl_status': 'failed',
            'error': error
        }


@router.get("/scrap", response_model=dict)
async def scrap():
    """Scrape data from csrankings.org"""
    # Configurar opciones de Chrome para modo headless
    advisor_crawler = AdvisorCrawler()
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    scraped_data = DataModel(universities=[])
    storage = CrawlerStorage()

    for k, category in cs_categories.items():

        browser = webdriver.Chrome(options=options)
        base_url = "https://csrankings.org/#/index?{}&us"
        url = base_url.format(k)
        logging.info(f"Scraping data for {category} from {url}")
        print(f"Scraping data for {category} from {url}")
        browser.get(url)
        time.sleep(2)  # Esperar a que cargue la página

        soup = BeautifulSoup(browser.page_source, "html.parser")

        table = soup.select_one("#ranking")
        if not table:
            logging.warning(f"Failed to retrieve data for {category}")
            browser.quit()
            continue

        tbody = table.find("tbody")
        if not tbody:
            logging.warning(f"Failed to retrieve tbody for {category}")
            browser.quit()
            continue

        rows = tbody.find_all("tr", recursive=False)

        for i in range(0, len(rows), 3):
            # Extraer ranking y nombre de la universidad
            rank_text = rows[i].find("td").text.strip()
            try:
                rank = int(rank_text)
            except ValueError:
                rank = 0  # O manejar de otra manera si el ranking no es un número

            u_name = rows[i].find_all("td")[1].find_all("span")[1].text.strip()
            logging.info(f"Category: {category} | Rank: {rank} | University: {u_name}")

            # Verificar si la universidad ya está en scraped_data
            university = next((u for u in scraped_data.universities if u.name == u_name), None)
            if not university:
                university = University(name=u_name, rankings=Rankings(), advisors=[])
                scraped_data.universities.append(university)

            # Update university ranking while preserving category name
            rank_category = getattr(university.rankings, k)
            rank_category.count = rank
            setattr(university.rankings, k, rank_category)

            # Procesar asesores
            try:
                faculties_row = rows[i + 2]
            except IndexError:
                logging.warning(f"No faculty row found for {u_name} in category {category}")
                continue

            faculties_table = faculties_row.find("table")
            if not faculties_table:
                logging.warning(f"Failed to retrieve faculties for {u_name} in category {category}")
                continue
            faculties_tbody = faculties_table.find("tbody")
            if not faculties_tbody:
                logging.warning(f"Failed to retrieve faculties tbody for {u_name} in category {category}")
                continue

            faculties_rows = faculties_tbody.find_all("tr")
            for j in range(0, len(faculties_rows), 2):
                faculty_link = faculties_rows[j].find("a")
                if not faculty_link:
                    logging.warning(f"Missing link for faculty in {u_name} for category {category}")
                    continue
                faculty_name = faculty_link.text.strip()
                faculty_href = faculty_link.get("href")

                faculty_no_pub_text = faculties_rows[j].find_all("td")[2].find("a").text.strip()
                try:
                    faculty_no_pub = int(faculty_no_pub_text)
                except ValueError:
                    faculty_no_pub = 0  # O manejar de otra manera

                logging.info(f"Faculty: {faculty_name} | Href: {faculty_href} | Papers in {category}: {faculty_no_pub}")

                # Buscar si el asesor ya existe en la universidad
                advisor = next((a for a in university.advisors if a.href == faculty_href), None)
                if not advisor:
                    advisor = Advisor(name=faculty_name, href=faculty_href, papers=Papers())
                    university.advisors.append(advisor)

                # Actualizar el número de publicaciones en la categoría actual
                paper_category = getattr(advisor.papers, k)
                paper_category.count = faculty_no_pub
                setattr(advisor.papers, k, paper_category)


                if advisor and not advisor.raw_content:  # Only crawl if no content
                    advisor_details = await advisor_crawler.crawl_advisor_details(faculty_href)
                    if advisor_details:
                        advisor.raw_content = advisor_details
    

        browser.quit()
    storage.save_crawl_result(scraped_data)
    return {"status": "success"}

from pathlib import Path
import json
from datetime import datetime
from config import get_settings

async def save_scraped_data(scraped_data: DataModel):
    """Save scraped data using Pydantic's model_dump"""
    settings = get_settings()
    storage_dir = Path(settings.STORAGE_DIR)
    storage_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save complete data
    data_file = storage_dir / f"csrankings_{timestamp}.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(scraped_data.model_dump(), f, ensure_ascii=False, indent=2)
    
    # Save individual advisor files
    advisors_dir = storage_dir / "advisors"
    advisors_dir.mkdir(exist_ok=True)
    
    for university in scraped_data.universities:
        for advisor in university.advisors:
            if advisor.raw_content:  # Only save if we have crawled content
                advisor_file = advisors_dir / f"{advisor.name.replace(' ', '_')}_{timestamp}.json"
                advisor_data = {
                    **advisor.model_dump(),
                    "university": university.name,
                    "university_rankings": university.rankings.model_dump()
                }
                with open(advisor_file, "w", encoding="utf-8") as f:
                    json.dump(advisor_data, f, ensure_ascii=False, indent=2)