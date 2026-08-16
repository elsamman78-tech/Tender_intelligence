import re

BLACKLIST = {'palestine','occupied palestinian territory','occupied territories','india','iran'}
TIER1 = {'egypt','saudi arabia','saudi','ksa','united arab emirates','uae','libya','bangladesh'}

CONSULTING_TERMS = [
    'consultancy','consulting services','consultant','engineering services','detailed design',
    'design supervision','construction supervision','site supervision','project management consultancy',
    'pmc','cost management','cost consultant','master planning','feasibility study',"owner's engineer",'owners engineer',
    'استشاري','استشارية','تصميم','إشراف','ادارة مشروعات','إدارة مشروعات','دراسة جدوى','مخطط عام'
]
CONSTRUCTION_TERMS = [
    'construction contractor','civil works','construction works','build contractor','execution of works',
    'أعمال مقاولات','مقاولات','تنفيذ أعمال','أعمال مدنية'
]
SUPPLY_TERMS = ['equipment supply','supply only','supply of equipment','توريد أجهزة','توريد معدات','توريد فقط']
FM_TERMS = ['facility management','maintenance contract','operation and maintenance','تشغيل وصيانة','إدارة مرافق','صيانة تشغيلية']
MIXED_TERMS = ['design and build','design & build','epc','engineering procurement construction']


def _contains(text: str, terms: list[str]) -> bool:
    t = (text or '').lower()
    return any(term.lower() in t for term in terms)


def classify_scope(text: str) -> tuple[str, str | None]:
    has_consulting = _contains(text, CONSULTING_TERMS)
    has_mixed = _contains(text, MIXED_TERMS)
    has_construction = _contains(text, CONSTRUCTION_TERMS)
    has_supply = _contains(text, SUPPLY_TERMS)
    has_fm = _contains(text, FM_TERMS)

    if has_mixed or (has_consulting and (has_construction or has_supply or has_fm)):
        return 'MIXED_SCOPE', None
    if has_consulting:
        return 'CONSULTANCY', None
    if has_construction:
        return 'PURE_CONSTRUCTION', 'PURE_CONSTRUCTION'
    if has_supply:
        return 'PURE_EQUIPMENT_SUPPLY', 'PURE_EQUIPMENT_SUPPLY'
    if has_fm:
        return 'FACILITY_MANAGEMENT', 'FACILITY_MANAGEMENT'
    return 'UNKNOWN', None


def evaluate_hard_rules(country: str | None, text: str, is_expired: bool) -> dict:
    c = (country or '').strip().lower()
    if c in BLACKLIST:
        return {'hard_reject': True, 'reason': 'BLACKLIST_COUNTRY', 'scope': 'N/A'}
    if is_expired:
        return {'hard_reject': False, 'reason': 'EXPIRED', 'scope': classify_scope(text)[0]}
    scope, scope_reject = classify_scope(text)
    if scope_reject:
        return {'hard_reject': True, 'reason': scope_reject, 'scope': scope}
    return {'hard_reject': False, 'reason': None, 'scope': scope}


def geographic_score(country: str | None) -> int:
    c = (country or '').strip().lower()
    if c in BLACKLIST:
        return 0
    if c in TIER1:
        return 15
    return 9 if c else 5
