import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.discovery.agent_reach import doctor
from app.services.ollama import health
from app.config import ZERO_COST_MODE, DATABASE_URL

print('=== Tender Intelligence Doctor ===')
print('Zero-Cost Mode:', 'ACTIVE' if ZERO_COST_MODE else 'OFF')
print('Database:', DATABASE_URL)
print('Ollama:', health())
print('Agent-Reach:', doctor())
print('Core: OPERATIONAL if app dependencies are installed')
