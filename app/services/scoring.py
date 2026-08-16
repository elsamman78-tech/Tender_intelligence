from .rules import geographic_score


def _scope_score(scope: str) -> int:
    return {'CONSULTANCY':25,'MIXED_SCOPE':15,'UNKNOWN':8}.get(scope,0)


def _deadline_score(days: int | None) -> int:
    if days is None: return 4
    if days <= 0: return 0
    if days <= 4: return 2
    if days <= 9: return 5
    if days <= 14: return 8
    return 10


def recommendation(score: float, hard_reject: bool=False, expired: bool=False) -> str:
    if hard_reject: return 'HARD_REJECT'
    if expired: return 'EXPIRED'
    if score >= 90: return 'STRONG_BID'
    if score >= 80: return 'RECOMMENDED'
    if score >= 70: return 'REVIEW_REQUIRED'
    if score >= 60: return 'LOW_PRIORITY'
    return 'NO_BID'


def score_tender(*, scope: str, country: str | None, days: int | None, analysis: dict | None, hard_reject: bool) -> dict:
    if hard_reject:
        components = {'scope':0,'eligibility':0,'geography':0,'deadline':0,'client':0,'strategic':0,'competition':0}
        return {'components':components,'overall':0.0,'recommendation':'HARD_REJECT','explanation':['Hard reject rule triggered.']}

    analysis = analysis or {}
    eligibility = analysis.get('eligibility_match_score')
    if not isinstance(eligibility, (int,float)):
        eligibility = 10
    eligibility = max(0, min(20, int(round(eligibility))))

    client = max(0, min(10, int(analysis.get('client_quality_score', 7) or 7)))
    strategic = max(0, min(10, int(analysis.get('strategic_value_score', 7) or 7)))
    competition = max(0, min(10, int(analysis.get('competition_score', 6) or 6)))

    components = {
        'scope': _scope_score(scope),
        'eligibility': eligibility,
        'geography': geographic_score(country),
        'deadline': _deadline_score(days),
        'client': client,
        'strategic': strategic,
        'competition': competition,
    }
    overall = float(sum(components.values()))
    rec = recommendation(overall, expired=(days is not None and days <= 0))
    explanation = [
        f"Scope fit: {components['scope']}/25 ({scope}).",
        f"Geographic fit: {components['geography']}/15.",
        f"Deadline feasibility: {components['deadline']}/10 ({days if days is not None else 'unknown'} business days).",
        f"Eligibility: {components['eligibility']}/20.",
    ]
    return {'components': components, 'overall': overall, 'recommendation': rec, 'explanation': explanation}
