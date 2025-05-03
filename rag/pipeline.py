from llama_index.core import VectorStoreIndex, Document
from typing import List
from models.advisor import AdvisorMatch
from config import get_settings
from llm import create_advisor_query_engine
from pathlib import Path
import json