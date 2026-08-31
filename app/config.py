from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Persistent storage root. When TENDER_DATA_HOME is set (for example
# E:\\Pro\\Tenders on Windows), all durable application data lives there.
_tender_data_home_raw = (os.getenv('TENDER_DATA_HOME') or '').strip()
TENDER_DATA_HOME = Path(_tender_data_home_raw) if _tender_data_home_raw else BASE_DIR
DATA_DIR = TENDER_DATA_HOME / 'data'
UPLOAD_DIR = DATA_DIR / 'uploads'
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = 'Tender Intelligence Zero Cost V2 Discovery'
ZERO_COST_MODE = os.getenv('ZERO_COST_MODE', 'true').lower() == 'true'
ALLOW_PAID_APIS = False if ZERO_COST_MODE else os.getenv('ALLOW_PAID_APIS','false').lower() == 'true'

_database_url_raw = (os.getenv('DATABASE_URL') or '').strip()
DATABASE_URL = _database_url_raw or f"sqlite:///{(DATA_DIR / 'tenders.db').as_posix()}"

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:4b')
AUTONOMOUS_AGENTS_ENABLED = os.getenv('AUTONOMOUS_AGENTS_ENABLED', 'true').lower() == 'true'
AUTONOMOUS_AGENT_MAX_CYCLES = max(1, min(int(os.getenv('AUTONOMOUS_AGENT_MAX_CYCLES', '2')), 3))
AUTONOMOUS_AGENT_INTERVAL_MINUTES = max(60, int(os.getenv('AUTONOMOUS_AGENT_INTERVAL_MINUTES', '720')))
TIMEZONE = os.getenv('TIMEZONE', 'Africa/Cairo')

AGENT_REACH_ENABLED = os.getenv('AGENT_REACH_ENABLED', 'false').lower() == 'true'
AGENT_REACH_SEARCH_COMMAND = os.getenv('AGENT_REACH_SEARCH_COMMAND', '').strip()
SEARXNG_URL = os.getenv('SEARXNG_URL', '').strip()
DDG_HTML_ENABLED = os.getenv('DDG_HTML_ENABLED', 'true').lower() == 'true'

CHANGEDETECTION_ENABLED = os.getenv('CHANGEDETECTION_ENABLED', 'true').lower() == 'true'
CHANGEDETECTION_URL = os.getenv('CHANGEDETECTION_URL', '').strip()
CHANGEDETECTION_API_KEY = os.getenv('CHANGEDETECTION_API_KEY', '').strip()
RSS_BRIDGE_ENABLED = os.getenv('RSS_BRIDGE_ENABLED', 'true').lower() == 'true'
RSS_BRIDGE_URL = os.getenv('RSS_BRIDGE_URL', '').strip()

OCR_ENABLED = os.getenv('OCR_ENABLED', 'true').lower() == 'true'
OCR_DOCKER_FALLBACK = os.getenv('OCR_DOCKER_FALLBACK', 'true').lower() == 'true'
OCR_DOCKER_IMAGE = os.getenv('OCR_DOCKER_IMAGE', 'tender-ocrmypdf:latest').strip()
OCR_LANGUAGES = os.getenv('OCR_LANGUAGES', 'eng+ara+fra').strip() or 'eng'
OCR_MIN_TEXT_CHARS = max(50, int(os.getenv('OCR_MIN_TEXT_CHARS', '180')))

DISCOVERY_ENABLED = os.getenv('DISCOVERY_ENABLED', 'true').lower() == 'true'
DISCOVERY_SCAN_INTERVAL_MINUTES = int(os.getenv('DISCOVERY_SCAN_INTERVAL_MINUTES', '360'))
OPEN_DISCOVERY_INTERVAL_MINUTES = int(os.getenv('OPEN_DISCOVERY_INTERVAL_MINUTES', '720'))
SOURCE_HEALTH_AUDIT_INTERVAL_MINUTES = max(60, int(os.getenv('SOURCE_HEALTH_AUDIT_INTERVAL_MINUTES', '360')))
SOURCE_HEALTH_AUDIT_BATCH = max(5, min(int(os.getenv('SOURCE_HEALTH_AUDIT_BATCH', '30')), 100))
DISCOVERY_QUERY_BATCH = int(os.getenv('DISCOVERY_QUERY_BATCH', '8'))
DISCOVERY_MAX_RESULTS_PER_QUERY = int(os.getenv('DISCOVERY_MAX_RESULTS_PER_QUERY', '15'))
DISCOVERY_REQUEST_TIMEOUT = int(os.getenv('DISCOVERY_REQUEST_TIMEOUT', '20'))
AUTO_PROMOTE_TENDERS = os.getenv('AUTO_PROMOTE_TENDERS', 'true').lower() == 'true'
MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '50'))
USER_AGENT = os.getenv('DISCOVERY_USER_AGENT', 'TenderIntelligenceZeroCost/2.1 (+local-business-discovery)')
