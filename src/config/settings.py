"""
Configuration module for the Research Paper Summarization System.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
AUDIO_DIR = BASE_DIR / "audio"
TEMPLATES_DIR = BASE_DIR / "templates"

# Create necessary directories
for directory in [UPLOADS_DIR, AUDIO_DIR, TEMPLATES_DIR]:
    directory.mkdir(exist_ok=True)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./research_papers.db")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))
API_RELOAD = os.getenv("API_RELOAD", "False").lower() == "true"

# External API URLs
ARXIV_BASE_URL = "http://export.arxiv.org/api/query"
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1/"

# Model configuration
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Only used if heavy models are enabled
SUMMARIZATION_MODELS = [
    # Heavy models (only loaded if DISABLE_HEAVY_MODELS = False)
    "facebook/bart-large-cnn",
    "t5-small", 
    "google/pegasus-xsum"
]  # Currently using extractive methods instead

# Model behavior configuration
USE_EXTRACTIVE_SUMMARIZATION = False  # Set to False to use heavy ML models for summarization
DISABLE_HEAVY_MODELS = False  # Set to False to enable transformers/sentence-transformers loading

# Note: To use heavy models, set BOTH flags above to False
# Heavy models require: pip install transformers sentence-transformers torch

# Processing limits
MAX_PAPERS_DEFAULT = 10
MAX_CHUNK_LENGTH = 1024
MAX_SUMMARY_LENGTH = 200
MIN_SUMMARY_LENGTH = 50

# SSL Configuration
try:
    import certifi
    CERTIFI_AVAILABLE = True
except ImportError:
    CERTIFI_AVAILABLE = False

class Settings:
    """Application settings class"""
    
    def __init__(self):
        self.database_url = DATABASE_URL
        self.api_host = API_HOST
        self.api_port = API_PORT
        self.api_reload = API_RELOAD
        
        self.uploads_dir = UPLOADS_DIR
        self.audio_dir = AUDIO_DIR
        self.templates_dir = TEMPLATES_DIR
        
        self.arxiv_base_url = ARXIV_BASE_URL
        self.pubmed_base_url = PUBMED_BASE_URL
        self.semantic_scholar_base_url = SEMANTIC_SCHOLAR_BASE_URL
        
        self.default_embedding_model = DEFAULT_EMBEDDING_MODEL
        self.summarization_models = SUMMARIZATION_MODELS
        
        self.max_papers_default = MAX_PAPERS_DEFAULT
        self.max_chunk_length = MAX_CHUNK_LENGTH
        self.max_summary_length = MAX_SUMMARY_LENGTH
        self.min_summary_length = MIN_SUMMARY_LENGTH
        
        self.use_extractive_summarization = USE_EXTRACTIVE_SUMMARIZATION
        self.disable_heavy_models = DISABLE_HEAVY_MODELS
        self.certifi_available = CERTIFI_AVAILABLE

# Global settings instance
settings = Settings()
