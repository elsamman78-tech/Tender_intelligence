from ..geography import is_excluded_country, normalize_country, PRIORITY_COUNTRIES, is_target_country

TIER1 = {x.lower() for x in PRIORITY_COUNTRIES} | {'saudi','ksa','united arab emirates'}

CONSULTING_TERMS = [
    'consultancy','consulting services','consultant','engineering services','detailed design',
    'concept design','engineering design','architectural design','structural design','mep design','infrastructure design',
    'design supervision','construction supervision','site supervision','project management consultancy',
    'pmc','cost management','cost consultant','master planning','feasibility study',"owner's engineer",'owners engineer',
    'geotechnical','surveying','environmental and social impact assessment','esia','transport planning','bim',
    'استشاري','استشارية','تصميم','إشراف','اشراف','ادارة مشروعات','إدارة مشروعات','دراسة جدوى','مخطط عام','دراسات هندسية'
]
CONSTRUCTION_TERMS = [
    'construction contractor','civil works','construction works','build contractor','execution of works',
    'أعمال مقاولات','مقاولات','تنفيذ أعمال','أعمال مدنية'
]
SUPPLY_TERMS = ['equipment supply','supply only','supply of equipment','توريد أجهزة','توريد معدات','توريد فقط']
FM_TERMS = ['facility management','maintenance contract','operation and maintenance','تشغيل وصيانة','إدارة مرافق','صيانة تشغيلية']
MIXED_TERMS = [
    'design and build','design & build','design-build','epc','epcm','engineering procurement construction','turnkey',
    'تصميم وتنفيذ','تصميم وبناء','الهندسة والتوريد والإنشاء','تسليم مفتاح'
]


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


def evaluate_hard_rules(
    country: str | None,
    text: str,
    is_expired: bool,
    business_days_remaining: int | None = None,
    publication_age_days: int | None = None,
) -> dict:
    c=normalize_country(country)
    if is_excluded_country(c) or (c and not is_target_country(c)):
        return {'hard_reject': True, 'reason': 'EXCLUDED_GEOGRAPHY', 'scope': 'N/A'}
    scope, scope_reject = classify_scope(text)
    if is_expired:
        return {'hard_reject': True, 'reason': 'EXPIRED', 'scope': scope}
    if publication_age_days is not None and publication_age_days > 20:
        return {'hard_reject': True, 'reason': 'PUBLICATION_OLDER_THAN_20_DAYS', 'scope': scope}
    if business_days_remaining is not None and business_days_remaining < 10:
        return {'hard_reject': True, 'reason': 'LESS_THAN_10_WORKING_DAYS', 'scope': scope}
    if scope_reject:
        return {'hard_reject': True, 'reason': scope_reject, 'scope': scope}
    if scope == 'MIXED_SCOPE' and c != 'Saudi Arabia':
        return {'hard_reject': True, 'reason': 'MIXED_CONSTRUCTION_SCOPE_OUTSIDE_SAUDI', 'scope': scope}
    return {'hard_reject': False, 'reason': None, 'scope': scope}


def geographic_score(country: str | None) -> int:
    c = normalize_country(country)
    if is_excluded_country(c) or (c and not is_target_country(c)):
        return 0
    if (c or '').lower() in TIER1:
        return 15
    if is_target_country(c):
        return 9
    return 3 if not c else 0
