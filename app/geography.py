"""Shared discovery/scoring geography policy.

Current business scope: search worldwide except the Americas and explicit excluded
European/Asian countries. The list is intentionally explicit so coverage is
measurable and auditable rather than relying on vague region labels.
"""

PRIORITY_COUNTRIES = ['Egypt','Saudi Arabia','UAE','Libya','Bangladesh']

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

ASIA_MIDDLE_EAST = [
    'Afghanistan','Armenia','Azerbaijan','Bahrain','Bangladesh','Bhutan','Brunei','Cambodia','China',
    'Cyprus','Georgia','Indonesia','Iran','Iraq','Israel','Japan','Jordan','Kazakhstan','Kuwait',
    'Kyrgyzstan','Laos','Lebanon','Malaysia','Maldives','Mongolia','Myanmar','Nepal','North Korea',
    'Oman','Pakistan','Palestine','Philippines','Qatar','Saudi Arabia','Singapore','South Korea',
    'Sri Lanka','Syria','Taiwan','Tajikistan','Thailand','Timor-Leste','Turkmenistan','UAE',
    'Uzbekistan','Vietnam','Yemen'
]

EUROPE_ALLOWED = [
    'Albania','Andorra','Austria','Belarus','Belgium','Bosnia and Herzegovina','Bulgaria','Croatia',
    'Czechia','Denmark','Estonia','Finland','Greece','Hungary','Iceland','Ireland','Italy','Kosovo',
    'Latvia','Liechtenstein','Lithuania','Luxembourg','Malta','Moldova','Monaco','Montenegro',
    'Netherlands','North Macedonia','Norway','Poland','Portugal','Romania','San Marino','Serbia',
    'Slovakia','Slovenia','Sweden','Switzerland','Vatican City'
]

OCEANIA = [
    'Australia','Fiji','Kiribati','Marshall Islands','Micronesia','Nauru','New Zealand','Palau',
    'Papua New Guinea','Samoa','Solomon Islands','Tonga','Tuvalu','Vanuatu'
]

TARGET_COUNTRIES = list(dict.fromkeys(PRIORITY_COUNTRIES + AFRICA + ASIA_MIDDLE_EAST + EUROPE_ALLOWED + OCEANIA))

EXPLICIT_EXCLUDED = {
    'United Kingdom','England','Germany','France','Russia','Ukraine','Turkey','Spain','India'
}

AMERICAS = {
    'Antigua and Barbuda','Argentina','Bahamas','Barbados','Belize','Bolivia','Brazil','Canada',
    'Chile','Colombia','Costa Rica','Cuba','Dominica','Dominican Republic','Ecuador','El Salvador',
    'Grenada','Guatemala','Guyana','Haiti','Honduras','Jamaica','Mexico','Nicaragua','Panama',
    'Paraguay','Peru','Saint Kitts and Nevis','Saint Lucia','Saint Vincent and the Grenadines',
    'Suriname','Trinidad and Tobago','United States','Uruguay','Venezuela'
}

EXCLUDED_COUNTRIES = EXPLICIT_EXCLUDED | AMERICAS
ALL_KNOWN_COUNTRIES = list(dict.fromkeys(TARGET_COUNTRIES + sorted(EXCLUDED_COUNTRIES)))

COUNTRY_ALIASES = {
    'UAE':['united arab emirates','u.a.e.','emirates','الإمارات','الامارات'],
    'Saudi Arabia':['kingdom of saudi arabia','ksa','السعودية','المملكة العربية السعودية'],
    'Egypt':['arab republic of egypt','مصر'],
    'United Kingdom':['united kingdom','uk','u.k.','great britain','britain','england','scotland','wales','northern ireland'],
    'United States':['united states of america','united states','usa','u.s.a.','u.s.'],
    'Democratic Republic of the Congo':['drc','dr congo','congo-kinshasa'],
    'Republic of the Congo':['congo-brazzaville'],
    "Cote d'Ivoire":["côte d’ivoire","côte d'ivoire",'ivory coast'],
    'South Korea':['republic of korea','korea republic'],
    'North Korea':["democratic people's republic of korea",'dprk'],
    'Taiwan':['taiwan, china','chinese taipei'],
    'Palestine':['state of palestine','palestinian territories','occupied palestinian territory'],
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


def country_priority(value: str | None) -> int:
    c=normalize_country(value)
    if c in PRIORITY_COUNTRIES: return 100
    if c in TARGET_COUNTRIES: return 70
    if c in EXCLUDED_COUNTRIES: return 0
    return 40


def infer_country_from_text(text: str) -> str | None:
    low=' '+(text or '').lower()+' '
    # aliases first because they are often more distinctive than canonical labels
    candidates=[]
    for alias, canonical in NORMALIZED.items():
        pos=low.find(' '+alias+' ')
        if pos >= 0:
            candidates.append((pos, -len(alias), canonical))
    if not candidates:
        # punctuation adjacent to names is common; fallback to substring for long names
        for alias, canonical in NORMALIZED.items():
            if len(alias) >= 5 and alias in low:
                candidates.append((low.find(alias), -len(alias), canonical))
    return sorted(candidates)[0][2] if candidates else None


def geography_policy_summary() -> dict:
    return {
        'target_country_count': len(TARGET_COUNTRIES),
        'priority_countries': PRIORITY_COUNTRIES,
        'excluded_country_count': len(EXCLUDED_COUNTRIES),
        'explicit_excluded': sorted(EXPLICIT_EXCLUDED),
        'americas_excluded': True,
    }
