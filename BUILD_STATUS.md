# BUILD STATUS — Tender Intelligence Zero Cost V2 Discovery

## Implemented in this build
- Preserves V1 tender analyzer, manual URL/text/PDF ingestion, rules, business-day urgency, scoring, BID/NO-BID/HOLD, Ollama optional adapter.
- Source Intelligence models: sources, channels, scans, health, trust, priority, lifecycle, cost class.
- Initial verified public seed library (10 sources) covering World Bank, UNGM, AfDB, IsDB, ADB, Saudi Etimad, Bangladesh e-GP, UAE federal procurement, Dubai eSupply, Libya NOC.
- Query Intelligence models and 18 initial Arabic/English/French discovery queries.
- Generic HTML/RSS/Sitemap scanner.
- Free public open-search provider (DuckDuckGo HTML; experimental/replaceable) plus optional local SearXNG.
- Agent-Reach/upstream adapter that respects Agent-Reach's current architecture; it is optional and never a core dependency.
- New-domain/source candidate creation and source profiling.
- Opportunity candidate classification, deduplication and validation.
- Automatic promotion of validated consulting procurement opportunities into the existing V1 analyzer.
- File discovery/indexing for PDF/DOC/DOCX/XLS/XLSX/CSV/ZIP links; digital PDFs can be read during candidate validation.
- Zero-cost cost-policy block for PAID/UNKNOWN sources in automated scanning.
- Local interval scheduler using Python standard library only; first automatic discovery begins about one minute after startup, then follows configured intervals.
- Discovery, Sources, Source Detail and provider-health UI.
- Manual full-cycle button and RUN_DISCOVERY_NOW.bat.
- Additive SQLite migration helper for upgrading from V1 schema.
- 12 automated tests passing.

## Important limits / not yet implemented
- The initial 10-source library is a bootstrap seed, NOT complete coverage of all government/private/news/social sources.
- Live internet discovery could not be executed from the build container because outbound network access is unavailable there; network logic is unit-tested and current source URLs were independently verified during build.
- No production-grade custom connector yet for complex JS portals; generic scanner is Phase-1 foundation.
- Open search via DuckDuckGo HTML is public/zero-key but may be throttled or change; SearXNG/other providers remain replaceable fallbacks.
- Agent-Reach itself does not currently expose one universal search command; its adapter can execute a configured zero-cost upstream command when available.
- DOCX/XLSX/ZIP parsing is indexed but not fully parsed yet.
- OCR/scanned PDFs, newspapers, news intelligence, social-media discovery, early signals/project watch, change/addendum tracking are Phase 2.
- Full Source Graph, organizations/clients/projects/funders relationships, missed-opportunity audit and query-learning optimization are not complete yet.
- Company projects/experts/registrations, eligibility gap engine, Bid Readiness, RBAC, full audit log and proposal workspace are later phases.
