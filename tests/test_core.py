from datetime import date
from app.services.business_days import calculate_business_days, urgency
from app.services.rules import classify_scope, evaluate_hard_rules
from app.services.scoring import score_tender

def test_blacklist_zero():
    r = evaluate_hard_rules('Iran','engineering consultancy',False)
    s = score_tender(scope=r['scope'],country='Iran',days=20,analysis=None,hard_reject=r['hard_reject'])
    assert r['hard_reject'] and s['overall'] == 0

def test_mixed_not_rejected():
    scope, reject = classify_scope('EPC design and build with engineering consultancy and supervision')
    assert scope == 'MIXED_SCOPE' and reject is None

def test_urgent():
    assert urgency(7) == 'URGENT'

def test_score_max_100():
    s=score_tender(scope='CONSULTANCY',country='Saudi Arabia',days=20,analysis={'eligibility_match_score':20,'client_quality_score':10,'strategic_value_score':10,'competition_score':10},hard_reject=False)
    assert s['overall'] == 100

def test_business_days_egypt_weekend():
    # Thu -> Sun: Fri/Sat excluded, Sun counts
    assert calculate_business_days('Egypt', date(2026,8,13), date(2026,8,16)) == 1

from app.services.dedup import fingerprint

def test_fingerprint_stable():
    a=fingerprint(title=' Design  Tender ',client='ABC',country='Egypt',deadline=date(2026,9,1),reference='RFP-1')
    b=fingerprint(title='design tender',client='abc',country='egypt',deadline=date(2026,9,1),reference='RFP-1')
    assert a == b
