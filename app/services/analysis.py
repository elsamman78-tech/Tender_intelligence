from datetime import date
from .business_days import calculate_business_days, urgency
from .rules import evaluate_hard_rules
from .scoring import score_tender
from .ollama import analyze as ollama_analyze


def run_analysis(country: str | None, deadline, text: str, use_ai: bool = True) -> dict:
    today = date.today()
    days = calculate_business_days(country or '', today, deadline) if deadline else None
    urg = urgency(days)
    hard = evaluate_hard_rules(country, text, is_expired=(days is not None and days <= 0))

    ai_status, ai_data = ('SKIPPED', None)
    if use_ai and not hard['hard_reject'] and text.strip():
        ai_status, ai_data = ollama_analyze(text)

    score = score_tender(
        scope=hard['scope'], country=country, days=days,
        analysis=ai_data, hard_reject=hard['hard_reject']
    )
    return {
        'business_days_remaining': days,
        'urgency_level': urg,
        'hard_reject': hard['hard_reject'],
        'hard_reject_reason': hard['reason'],
        'scope_classification': hard['scope'],
        'ai_status': ai_status,
        'analysis_json': ai_data,
        'score_json': score,
        'overall_score': score['overall'],
        'recommendation': score['recommendation']
    }
