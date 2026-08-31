"""Participation and partnering rules for engineering opportunities.

This module is deliberately deterministic. AI may explain a decision later, but it
must not invent eligibility. The engine identifies a practical bid route from the
published notice text and the company's known local presence.
"""
from dataclasses import dataclass, asdict
from ..geography import normalize_country, has_local_presence
from ..discovery.keywords import SAUDI_DB_TERMS, CONSULTANCY_TERMS


@dataclass
class ParticipationResult:
    bid_route: str = 'DIRECT'
    eligibility_status: str = 'ELIGIBLE'
    partner_requirement: str = 'NONE'
    submission_language: str = 'UNKNOWN'
    language_status: str = 'UNKNOWN'
    local_presence: bool = False
    saudi_design_build: bool = False
    notes: str = ''

    def to_dict(self):
        return asdict(self)


LOCAL_ONLY_TERMS = [
    'local firms only','local companies only','national firms only','national consultants only',
    'domestic firms only','domestic consultants only','registered local firms only',
    'only locally registered','must be locally registered','national consulting firms',
    'للشركات المحلية فقط','للمكاتب المحلية فقط','للمكاتب الاستشارية الوطنية','للشركات الوطنية فقط'
]

JV_TERMS = [
    'joint venture','joint-venture',' jv ','consortium','jointly with','in joint venture with',
    'تحالف','ائتلاف','مشروع مشترك'
]

LOCAL_ASSOCIATION_TERMS = [
    'in association with a local consultant','associate with a local consultant','local consultant required',
    'must associate with','local partner required','national partner required','association with national consultant',
    'بالتحالف مع استشاري محلي','شريك محلي مطلوب','بالتعاون مع مكتب استشاري محلي'
]

SUBCONSULTANT_TERMS = [
    'subconsultant','sub-consultant','sub consultant','specialist subconsultant','design subconsultant',
    'استشاري فرعي','مستشار فرعي'
]

INTERNATIONAL_ALLOWED_TERMS = [
    'international firms are eligible','international consultants are eligible','open to international firms',
    'foreign firms may participate','international competitive','international consultancy firms',
    'الشركات الدولية','المكاتب الاستشارية الدولية','يسمح للشركات الأجنبية','منافسة دولية'
]

CONTRACTOR_PARTNER_TERMS = [
    'main contractor','general contractor','design-build contractor','epc contractor','contractor and consultant',
    'المقاول الرئيسي','مقاول التصميم والتنفيذ','مقاول عام'
]

ENGLISH_LANGUAGE_TERMS = [
    'proposal shall be in english','proposals shall be in english','bid shall be in english',
    'submission language: english','language of proposal: english','english language'
]
ARABIC_LANGUAGE_TERMS = [
    'proposal shall be in arabic','bid shall be in arabic','submission language: arabic',
    'language of proposal: arabic','اللغة العربية','العروض باللغة العربية','العرض باللغة العربية'
]
NON_ALLOWED_ONLY_TERMS = [
    'proposal shall be in french only','bid shall be in french only','submission language: french only',
    'proposal shall be in portuguese only','submission language: portuguese only',
    'العروض باللغة الفرنسية فقط'
]


def _has_any(text: str, terms) -> bool:
    return any(term in text for term in terms)


def _language(text: str):
    if _has_any(text, NON_ALLOWED_ONLY_TERMS):
        return 'OTHER_ONLY', 'NOT_ALLOWED'
    en=_has_any(text, ENGLISH_LANGUAGE_TERMS)
    ar=_has_any(text, ARABIC_LANGUAGE_TERMS)
    if en and ar: return 'AR/EN', 'ALLOWED'
    if en: return 'EN', 'ALLOWED'
    if ar: return 'AR', 'ALLOWED'
    return 'UNKNOWN', 'UNKNOWN'


def analyze_participation(country: str | None, text: str | None) -> dict:
    country=normalize_country(country)
    low=' '+(text or '').lower().replace('\n',' ')+' '
    local_presence=has_local_presence(country)
    language,language_status=_language(low)

    result=ParticipationResult(
        local_presence=local_presence,
        submission_language=language,
        language_status=language_status,
    )

    if language_status == 'NOT_ALLOWED':
        result.eligibility_status='NOT_ELIGIBLE_LANGUAGE'
        result.bid_route='NOT_ELIGIBLE'
        result.notes='Published notice explicitly requires a submission language other than Arabic/English.'
        return result.to_dict()

    local_only=_has_any(low, LOCAL_ONLY_TERMS)
    jv=_has_any(low, JV_TERMS)
    local_association=_has_any(low, LOCAL_ASSOCIATION_TERMS)
    subconsultant=_has_any(low, SUBCONSULTANT_TERMS)
    international=_has_any(low, INTERNATIONAL_ALLOWED_TERMS)

    # Saudi Arabia gets a deliberate commercial exception: D&B / EPC / turnkey
    # opportunities are retained when a real engineering/design scope exists.
    if country == 'Saudi Arabia':
        db_scope=_has_any(low, SAUDI_DB_TERMS)
        design_scope=_has_any(low, CONSULTANCY_TERMS) or any(term in low for term in [
            'detailed design','engineering design','architectural design','structural design','mep design',
            'infrastructure design','design review','ifc drawings','bim','hydraulic design',
            'تصميم تفصيلي','تصميم هندسي','مخططات تنفيذية','نمذجة معلومات المباني'
        ])
        if db_scope and design_scope:
            result.saudi_design_build=True
            result.bid_route='SAUDI_DB_PARTNER'
            result.eligibility_status='PARTNER_OPPORTUNITY'
            result.partner_requirement='CONTRACTOR'
            result.notes='Saudi D&B/EPC opportunity with detectable engineering scope; pursue as design/engineering partner, consortium member or subconsultant subject to tender rules.'
            return result.to_dict()

    if local_only:
        if local_presence:
            result.bid_route='DIRECT_LOCAL'
            result.eligibility_status='ELIGIBLE_LOCAL'
            result.partner_requirement='NONE'
            result.notes='Local-only restriction detected, but the company has known local presence in this country; verify tender-specific registrations/classification.'
            return result.to_dict()
        if local_association:
            result.bid_route='LOCAL_ASSOCIATION'
            result.eligibility_status='ELIGIBLE_WITH_PARTNER'
            result.partner_requirement='LOCAL_CONSULTANT'
            result.notes='Local participation restriction detected with an association route through a local consultant.'
            return result.to_dict()
        if jv:
            result.bid_route='JV'
            result.eligibility_status='ELIGIBLE_VIA_JV'
            result.partner_requirement='LOCAL_OR_ELIGIBLE_CONSULTANT'
            result.notes='Local restriction detected, but the notice indicates a JV/consortium route.'
            return result.to_dict()
        if subconsultant:
            result.bid_route='SUBCONSULTANT'
            result.eligibility_status='ELIGIBLE_AS_SUBCONSULTANT'
            result.partner_requirement='LEAD_CONSULTANT'
            result.notes='Direct local eligibility is restricted; participation may be possible as an accepted subconsultant.'
            return result.to_dict()
        result.bid_route='NOT_ELIGIBLE'
        result.eligibility_status='LOCAL_RESTRICTION'
        result.partner_requirement='NONE_IDENTIFIED'
        result.notes='Local/national-only restriction detected and no permitted JV/association/subconsultancy route was found in the extracted text.'
        return result.to_dict()

    if local_association:
        result.bid_route='LOCAL_ASSOCIATION'
        result.eligibility_status='ELIGIBLE_WITH_PARTNER'
        result.partner_requirement='LOCAL_CONSULTANT'
        result.notes='Notice requires or clearly anticipates association with a local consultant.'
        return result.to_dict()

    if jv:
        result.bid_route='JV'
        result.eligibility_status='ELIGIBLE_VIA_JV'
        result.partner_requirement='CONSULTANT'
        result.notes='JV/consortium participation is indicated by the notice.'
        return result.to_dict()

    if subconsultant:
        result.bid_route='SUBCONSULTANT'
        result.eligibility_status='PARTNER_OPTION'
        result.partner_requirement='LEAD_CONSULTANT'
        result.notes='Subconsultancy is referenced in the notice; retain as a partnering option.'
        return result.to_dict()

    result.bid_route='DIRECT'
    result.eligibility_status='ELIGIBLE' if international or local_presence else 'ELIGIBILITY_TO_VERIFY'
    result.partner_requirement='NONE'
    result.notes='No hard participation restriction was detected.' if result.eligibility_status=='ELIGIBLE' else 'No hard restriction detected, but international/local eligibility is not explicit in the extracted text.'
    return result.to_dict()
