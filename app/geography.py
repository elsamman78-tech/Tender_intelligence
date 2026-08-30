"""Shared discovery/scoring geography policy for Tender Intelligence V4.

Business scope approved for the current build:
- Egypt and all African countries.
- GCC: Saudi Arabia, UAE, Qatar, Kuwait, Oman and Bahrain.
- Middle East additions: Jordan, Iraq and Yemen.
- Explicitly exclude Palestine, Israel, Syria, Lebanon, Turkey and Iran.

The list is explicit so discovery coverage remains measurable and auditable.
"""

GCC = ['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Oman', 'Bahrain']
MIDDLE_EAST_ADDITIONS = ['Jordan', 'Iraq', 'Yemen']
LOCAL_PRESENCE_COUNTRIES = ['Egypt', 'Saudi Arabia', 'UAE', 'Qatar', 'Libya', 'Yemen']
PRIORITY_COUNTRIES = LOCAL_PRESENCE_COUNTRIES + ['Kuwait', 'Oman', 'Bahrain', 'Jordan', 'Iraq']

AFRICA = [
    'Algeria','Angola','Benin','Botswana','Burkina Faso','Burundi','Cabo Verde','Cameroon',
    'Central African Republic','Chad','Comoros','Democratic Republic of the Congo',
    'Republic of the Congo',"Cote d'Ivoire",'Djibouti','Egypt','Equatorial Guinea','Eritrea',
    'Eswatini','Ethiopia','Gabon','Gambia','Ghana','Guinea','Guinea-Bissau','Kenya','Lesotho',
    'Liberia','Libya','Madagascar','Malawi','Mali','Mauritania','Mauritius','Morocco','Mozambique',
    'Namibia','Niger','Nigeria','Rwanda','Sao Tome and Principe','Senegal','Seychelles',
    'Sierra Leone','Somalia','South Africa','South Sudan','Sudan','Tanzania','Togo','Tunisia',
    'Uganda','Zambia','Zimbabwe'
]

TARGET_COUNTRIES = list(dict.fromkeys(AFRICA + GCC + MIDDLE_EAST_ADDITIONS))

EXPLICIT_EXCLUDED = {
    'Palestine','Israel','Syria','Lebanon','Turkey','Iran'
}
EXCLUDED_COUNTRIES = EXPLICIT_EXCLUDED
ALL_KNOWN_COUNTRIES = list(dict.fromkeys(TARGET_COUNTRIES + sorted(EXCLUDED_COUNTRIES)))

COUNTRY_ALIASES = {
    'UAE':['united arab emirates','u.a.e.','emirates','الإمارات','الامارات'],
    'Saudi Arabia':['kingdom of saudi arabia','ksa','السعودية','المملكة العربية السعودية'],
    'Egypt':['arab republic of egypt','مصر'],
    'Qatar':['state of qatar','دولة قطر','قطر'],
    'Kuwait':['state of kuwait','دولة الكويت','الكويت'],
    'Oman':['sultanate of oman','سلطنة عمان','عمان'],
    'Bahrain':['kingdom of bahrain','مملكة البحرين','البحرين'],
    'Jordan':['hashemite kingdom of jordan','الأردن','الاردن'],
    'Iraq':['republic of iraq','العراق'],
    'Yemen':['republic of yemen','اليمن'],
    'Libya':['state of libya','ليبيا'],
    'Democratic Republic of the Congo':['drc','dr congo','congo-kinshasa'],
    'Republic of the Congo':['congo-brazzaville'],
    "Cote d'Ivoire":["côte d’ivoire","côte d'ivoire",'ivory coast'],
    'Palestine':['state of palestine','palestinian territories','occupied palestinian territory','فلسطين'],
    'Israel':['state of israel','إسرائيل','اسرائيل'],
    'Syria':['syrian arab republic','سوريا'],
    'Lebanon':['lebanese republic','لبنان'],
    'Turkey':['turkiye','türkiye','تركيا'],
    'Iran':['islamic republic of iran','إيران','ايران'],
}

NORMALIZED = {c.lower(): c for c in ALL_KNOWN_COUNTRIES}
for canonical, aliases in COUNTRY_ALIASES.items():
    for alias in aliases:
        NORMALIZED[alias.lower()] = canonical


def normalize_country(value: str | None) -> str | None:
    if not value:
        return None
    v=' '.join(value.strip().lower().split())
    return NORMALIZED.get(v, value.strip())


def is_excluded_country(value: str | None) -> bool:
    c=normalize_country(value)
    return bool(c and c in EXCLUDED_COUNTRIES)


def is_target_country(value: str | None) -> bool:
    c=normalize_country(value)
    return bool(c and c in TARGET_COUNTRIES)


def has_local_presence(value: str | None) -> bool:
    c=normalize_country(value)
    return bool(c and c in LOCAL_PRESENCE_COUNTRIES)


def country_priority(value: str | None) -> int:
    c=normalize_country(value)
    if c in LOCAL_PRESENCE_COUNTRIES: return 100
    if c in PRIORITY_COUNTRIES: return 90
    if c in TARGET_COUNTRIES: return 70
    if c in EXCLUDED_COUNTRIES: return 0
    return 0


def infer_country_from_text(text: str) -> str | None:
    low=' '+(text or '').lower()+' '
    candidates=[]
    for alias, canonical in NORMALIZED.items():
        pos=low.find(' '+alias+' ')
        if pos >= 0:
            candidates.append((pos, -len(alias), canonical))
    if not candidates:
        for alias, canonical in NORMALIZED.items():
            if len(alias) >= 5 and alias in low:
                candidates.append((low.find(alias), -len(alias), canonical))
    return sorted(candidates)[0][2] if candidates else None


def geography_policy_summary() -> dict:
    return {
        'target_country_count': len(TARGET_COUNTRIES),
        'priority_countries': PRIORITY_COUNTRIES,
        'local_presence_countries': LOCAL_PRESENCE_COUNTRIES,
        'excluded_country_count': len(EXCLUDED_COUNTRIES),
        'explicit_excluded': sorted(EXPLICIT_EXCLUDED),
        'regions': ['Africa', 'GCC', 'Jordan', 'Iraq', 'Yemen'],
    }
