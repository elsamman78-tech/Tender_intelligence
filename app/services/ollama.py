import json
import httpx
from ..config import OLLAMA_URL, OLLAMA_MODEL

SYSTEM_PROMPT = '''You analyze engineering consultancy tenders. Return JSON only. Never make final BID/NO-BID decisions. Extract facts conservatively. Scores requested below are sub-scores only.\nSchema:\n{\n  "project_summary": string,\n  "eligibility": {"minimum_years_experience": number|null, "similar_projects_required": number|null, "local_registration_required": boolean|null, "local_partner_required": boolean|null, "joint_venture_allowed": boolean|null},\n  "risks": [string],\n  "key_experts": [string],\n  "eligibility_match_score": integer 0..20,\n  "client_quality_score": integer 0..10,\n  "strategic_value_score": integer 0..10,\n  "competition_score": integer 0..10,\n  "confidence": number 0..1\n}'''


def health() -> dict:
    try:
        r = httpx.get(f'{OLLAMA_URL}/api/tags', timeout=2.5)
        return {'ok': r.status_code == 200, 'detail': r.text[:200]}
    except Exception as e:
        return {'ok': False, 'detail': str(e)}


def analyze(text: str) -> tuple[str, dict | None]:
    if not health()['ok']:
        return 'UNAVAILABLE', None
    sample = text[:18000]
    payload = {
        'model': OLLAMA_MODEL,
        'stream': False,
        'format': 'json',
        'messages': [
            {'role':'system','content':SYSTEM_PROMPT},
            {'role':'user','content':sample}
        ],
        'options': {'temperature': 0.1}
    }
    try:
        r = httpx.post(f'{OLLAMA_URL}/api/chat', json=payload, timeout=120)
        r.raise_for_status()
        content = r.json()['message']['content']
        return 'DONE', json.loads(content)
    except Exception as e:
        return f'FAILED: {e}', None
