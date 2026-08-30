from datetime import date
from app.services.business_days import calculate_business_days, urgency
from app.services.rules import classify_scope, evaluate_hard_rules
from app.services.scoring import score_tender
from app.services.participation import analyze_participation
from app.geography import is_excluded_country, is_target_country, geography_policy_summary, has_local_presence


def test_current_target_geography():
    for country in ['Egypt','Saudi Arabia','UAE','Qatar','Kuwait','Oman','Bahrain','Jordan','Iraq','Yemen','Kenya','Ghana','South Africa']:
        assert is_target_country(country)
    for country in ['Palestine','Israel','Syria','Lebanon','Turkey','Iran','United States','India']:
        assert not is_target_country(country)


def test_explicit_exclusions_rejected():
    for country in ['Palestine','Israel','Syria','Lebanon','Turkey','Iran']:
        assert is_excluded_country(country)
        r=evaluate_hard_rules(country,'engineering consultancy tender',False,20,5)
        assert r['hard_reject']


def test_non_target_country_rejected():
    r=evaluate_hard_rules('India','engineering consultancy tender',False,20,5)
    assert r['hard_reject'] and r['reason']=='EXCLUDED_GEOGRAPHY'


def test_local_presence_markets():
    for country in ['Egypt','Saudi Arabia','UAE','Qatar','Libya','Yemen']:
        assert has_local_presence(country)


def test_saudi_mixed_scope_allowed():
    scope, reject = classify_scope('EPC design and build with detailed engineering design and supervision')
    assert scope == 'MIXED_SCOPE' and reject is None
    r=evaluate_hard_rules('Saudi Arabia','EPC design and build with detailed engineering design and supervision',False,20,5)
    assert not r['hard_reject']


def test_mixed_scope_outside_saudi_rejected():
    r=evaluate_hard_rules('Egypt','EPC design and build with engineering consultancy and supervision',False,20,5)
    assert r['hard_reject'] and r['reason']=='MIXED_CONSTRUCTION_SCOPE_OUTSIDE_SAUDI'


def test_minimum_working_days():
    r=evaluate_hard_rules('Egypt','engineering consultancy tender',False,9,5)
    assert r['hard_reject'] and r['reason']=='LESS_THAN_10_WORKING_DAYS'


def test_publication_age_limit():
    r=evaluate_hard_rules('Egypt','engineering consultancy tender',False,20,21)
    assert r['hard_reject'] and r['reason']=='PUBLICATION_OLDER_THAN_20_DAYS'


def test_participation_local_only_with_branch():
    r=analyze_participation('Qatar','This tender is for local firms only. Engineering consultancy services.')
    assert r['bid_route']=='DIRECT_LOCAL'
    assert r['eligibility_status']=='ELIGIBLE_LOCAL'


def test_participation_jv_in_africa():
    r=analyze_participation('Kenya','National consulting firms only. Foreign consultant may participate in joint venture with a local consultant.')
    assert r['bid_route'] in {'JV','LOCAL_ASSOCIATION'}
    assert r['eligibility_status'] in {'ELIGIBLE_VIA_JV','ELIGIBLE_WITH_PARTNER'}


def test_saudi_design_build_partner_route():
    r=analyze_participation('Saudi Arabia','Design and Build tender. Contractor shall provide detailed design, MEP design and BIM.')
    assert r['bid_route']=='SAUDI_DB_PARTNER'
    assert r['partner_requirement']=='CONTRACTOR'


def test_urgent():
    assert urgency(7) == 'URGENT'


def test_score_max_100():
    s=score_tender(scope='CONSULTANCY',country='Saudi Arabia',days=20,analysis={'eligibility_match_score':20,'client_quality_score':10,'strategic_value_score':10,'competition_score':10},hard_reject=False)
    assert s['overall'] == 100


def test_business_days_egypt_weekend():
    assert calculate_business_days('Egypt', date(2026,8,13), date(2026,8,16)) == 1


from app.services.dedup import fingerprint


def test_fingerprint_stable():
    a=fingerprint(title=' Design  Tender ',client='ABC',country='Egypt',deadline=date(2026,9,1),reference='RFP-1')
    b=fingerprint(title='design tender',client='abc',country='egypt',deadline=date(2026,9,1),reference='RFP-1')
    assert a == b
