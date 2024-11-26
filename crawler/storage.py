from pathlib import Path
import json
from datetime import datetime
from .data_model import DataModel, Advisor
import logging
from typing import Dict
from typing import Optional
   
class CrawlerStorage:
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.advisors_dir = self.base_dir / "advisors"
        self.latest_data: Optional[DataModel] = None
        
        # Create directories
        for directory in [self.raw_dir, self.advisors_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self._load_latest_data()
    
    def _load_latest_data(self):
        """Load most recent data file"""
        try:
            data_files = sorted(self.raw_dir.glob("csrankings_*.json"))
            if data_files:
                with open(data_files[-1], 'r') as f:
                    data = json.load(f)
                    self.latest_data = DataModel.model_validate(data)
                    self.logger.info(f"Loaded previous data from {data_files[-1]}")
        except Exception as e:
            self.logger.error(f"Error loading previous data: {e}")
            self.latest_data = None

    def merge_data(self, new_data: DataModel) -> DataModel:
        """Merge new data with existing data"""
        if not self.latest_data:
            return new_data
            
        merged = self.latest_data
        
        for new_uni in new_data.universities:
            existing_uni = next(
                (u for u in merged.universities if u.name == new_uni.name), 
                None
            )
            
            if not existing_uni:
                merged.universities.append(new_uni)
                continue
            
            # Update rankings
            for field in new_uni.rankings.model_fields:
                new_rank = getattr(new_uni.rankings, field)
                if new_rank.count > 0:  # Only update if new data exists
                    setattr(existing_uni.rankings, field, new_rank)
            
            # Update/add advisors
            for new_advisor in new_uni.advisors:
                existing_advisor = next(
                    (a for a in existing_uni.advisors if a.href == new_advisor.href),
                    None
                )
                
                if not existing_advisor:
                    existing_uni.advisors.append(new_advisor)
                else:
                    # Update papers
                    for field in new_advisor.papers.model_fields:
                        new_count = getattr(new_advisor.papers, field)
                        if new_count.count > 0:
                            setattr(existing_advisor.papers, field, new_count)
                    
                    # Update raw_content if new one exists
                    if new_advisor.raw_content:
                        existing_advisor.raw_content = new_advisor.raw_content
        
        return merged

    def save_crawl_result(self, data: DataModel):
        """Save complete crawl results"""
        # Merge with existing data
        merged_data = self.merge_data(data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"csrankings_{timestamp}.json"
        
        # Save complete merged data
        with open(self.raw_dir / filename, "w", encoding="utf-8") as f:
            json.dump(merged_data.model_dump(), f, ensure_ascii=False, indent=2)
        
        # Save individual advisor files
        for university in merged_data.universities:
            for advisor in university.advisors:
                if advisor.raw_content:
                    self.save_advisor_details(advisor, university.name)    
    def save_advisor_details(self, advisor: Advisor, university_name: str):
        """Save individual advisor details"""
        safe_name = "".join(c if c.isalnum() else "_" for c in advisor.name)
        filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        advisor_data = {
            **advisor.model_dump(),
            "university": university_name,
            "crawled_at": datetime.now().isoformat()
        }
        
        with open(self.advisors_dir / filename, "w", encoding="utf-8") as f:
            json.dump(advisor_data, f, ensure_ascii=False, indent=2)