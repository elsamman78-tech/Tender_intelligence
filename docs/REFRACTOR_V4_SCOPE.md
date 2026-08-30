# Tender Intelligence V4 Refactor Scope

## Product rule: tender opportunities only
The primary opportunity pipeline must not surface generic news articles, personal LinkedIn profiles, social posts, recruitment pages, biographies, opinion pieces, or unrelated corporate pages as tenders.

### Allowed discovery classes
- Official procurement portal notices
- Procuring entity tender / procurement pages
- Private-company RFP / EOI / PQ notices
- Development-bank and UN procurement notices
- Newspaper / gazette tender advertisements
- E-paper / PDF tender advertisements
- Verified tender documents (RFP, EOI, REOI, PQ, TOR, tender notice)
- Saudi Design & Build / EPC / turnkey opportunities when a material engineering/design scope exists

### Non-tender content policy
- Generic news: reject from the tender pipeline.
- Personal LinkedIn profile: reject.
- Social media post/page: do not create a tender. Social discovery is disabled in the primary pipeline.
- Newspaper article about a project: may be stored only as an early signal if useful, never as a tender without a procurement notice.
- Newspaper tender advertisement: eligible as NEWSPAPER_NOTICE and must preserve evidence URL/file/page.

## Participation engine
Supported bid routes:
- DIRECT
- JV
- CONSORTIUM
- LOCAL_ASSOCIATION
- SUBCONSULTANT
- LEAD_WITH_PARTNERS
- PARTNER_REQUIRED
- NOT_ELIGIBLE
- UNKNOWN

Company local presence exists in:
- Egypt
- Saudi Arabia
- United Arab Emirates
- Qatar
- Libya
- Yemen

Local-only opportunities in those markets must not be rejected solely because they are local-only. Registration/classification requirements must be checked separately.

Across all target countries, opportunities that permit JV, consortium, association, local partner, or subconsultancy remain eligible for review.

## Saudi special rule
Saudi Arabia includes both direct consultancy opportunities and contractor-led Design & Build / EPC / turnkey opportunities where the company could participate as design/engineering consultant, JV/consortium member, or subconsultant.

Construction-only opportunities with no material engineering/design scope remain excluded.

## Date / relevance rules
- Publication age: <= 20 calendar days.
- Working days remaining: >= 10.
- Working week: Sunday-Thursday.
- Friday/Saturday are non-working days.
- Only Arabic or English submission language where explicitly stated.
- Expired, cancelled and award-only notices are excluded.

## UI direction
Replace the legacy table-first interface with a professional tender-intelligence dashboard emphasizing:
- Qualified opportunities
- Direct bids
- JV / consortium opportunities
- Saudi D&B partner opportunities
- Registration / eligibility review
- Upcoming deadlines
- Source quality / verification
- Evidence links
- Clear filters by country, discipline, participation route, source type, deadline, status and score

The main dashboard must never display raw search results or unverified social/news noise as tender opportunities.
