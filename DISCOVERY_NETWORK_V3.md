# Discovery Network V3 — Worldwide Multi-Engine Zero-Cost

## Geography policy

Discovery targets every country explicitly listed in `app/geography.py` across Africa, allowed Europe, Asia/Middle East and Oceania. The Americas are excluded. The explicit excluded list also contains United Kingdom/England, Germany, France, Russia, Ukraine, Turkey, Spain and India.

The policy is explicit and measurable. Results that clearly resolve to an excluded country are rejected as `EXCLUDED_GEOGRAPHY` instead of being promoted to a tender.

## Search engines

Open discovery fans out the same query to every available zero-cost provider:

- `SEARXNG_GOOGLE` — Google WEB engine through the user's local SearXNG instance.
- `SEARXNG_BING` — Bing WEB engine through the user's local SearXNG instance.
- `SEARXNG_META` — local SearXNG metasearch.
- `DDG_HTML` — direct public DuckDuckGo HTML search.
- `AGENT_REACH_UPSTREAM` — optional only when explicitly configured.

Direct Google Custom Search JSON is not a core dependency. New customers cannot currently sign up for that API and it requires API credentials/billing for extra usage. Direct Bing Search APIs are retired. Local SearXNG is therefore the zero-cost adapter for Google/Bing coverage.

## Source-discovery channels

The Query Intelligence bootstrap creates country and regional queries for:

- consultancy tenders/RFP/EOI/procurement;
- government procurement/e-procurement/tender portals;
- private developers, utilities, infrastructure operators, banks, universities and hospitals;
- newspapers/gazettes and public procurement notices;
- free/public tender aggregators as lead sources;
- PDF/TOR/RFP file discovery;
- procurement plans and general procurement notices / early signals;
- LinkedIn, Facebook, X and Twitter public-indexed signals;
- Arabic, English, French and Portuguese discovery patterns.

Known-source monitoring also starts with World Bank, UNGM, UNDP, AfDB, IsDB, ADB, EBRD, TED, Saudi Etimad, Bangladesh e-GP, UAE Federal Procurement, Dubai eSupply and Libya NOC.

## Social safety/trust rule

LinkedIn/Facebook/X/Twitter are lead-generation channels only. A social result is stored as `SOCIAL_LEAD` and cannot be automatically promoted to a tender. It must be resolved to a separately verified official/procuring-entity source first. This prevents social rumours or reposts becoming authoritative tender facts.

The system does not attempt CAPTCHA bypass, login bypass or prohibited private-data extraction.

## Coverage measurement

`SearchRun` and `SearchResult` persist provider-level performance. The Discovery dashboard shows runs, successful runs, result counts, new domains and new candidates per provider.

A benchmark is available at:

- UI: Discovery -> `مقارنة Coverage للمحركات`
- API: `POST /api/v1/discovery/coverage/benchmark`
- Snapshot: `GET /api/v1/discovery/coverage`

The benchmark runs the same query sample against each available provider and measures distinct URLs/domains, new candidates, contribution to the union and URLs unique to each engine.

## Local SearXNG

On Windows with Docker Desktop running:

1. Run `START_SEARXNG_WINDOWS.bat`.
2. It starts the official SearXNG container at `http://127.0.0.1:8888`.
3. It updates local `.env` with `SEARXNG_URL=http://127.0.0.1:8888`.
4. Restart `RUN_LOCAL_WINDOWS.bat` so Tender Intelligence reloads the environment.

Use `STOP_SEARXNG_WINDOWS.bat` to stop the local metasearch service.

## Important limitation

This architecture maximizes measurable coverage; it does not claim to search literally every page on the internet. Sites can require login, block automation, use CAPTCHA, hide data behind JavaScript, or prohibit automated access. Those states must be recorded and handled by source health/access policy rather than bypassed.
