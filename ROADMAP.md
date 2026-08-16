# Tender Intelligence Roadmap

This repository is the main development baseline for the Tender Intelligence & Bid Decision System.

## Completed baseline — V2 Discovery + Cloud Ready

- V1 analyzer preserved.
- Engineering-consultancy scope rules and blacklist rules.
- Business-day urgency logic.
- Opportunity score out of 100.
- Source Intelligence database.
- Known-source monitoring.
- Open discovery provider abstraction.
- Arabic / English / French query seeds.
- Candidate validation and deduplication.
- Automatic promotion into the analyzer.
- PDF parsing for digital PDFs.
- Procurement document link discovery.
- Source health and discovery dashboard.
- Local scheduler.
- Zero-cost firewall.
- Docker/Linux deployment files.
- Cloudflare Tunnel-ready compose configuration.
- Automated Python tests and Docker smoke CI.

## Phase 2 — Discovery depth

1. Expand the source library by country, sector and organization.
2. Add procurement-plan, GPN, prequalification and early-project signal tracking.
3. Add tender/addendum/deadline change detection with version history.
4. Add richer document parsing for DOCX/XLSX/CSV/ZIP.
5. Add OCR path for scanned PDFs and newspaper notices.
6. Add news and public social-signal ingestion as leads that must be verified against official sources.
7. Add source graph and organization/project relationships.
8. Add query yield metrics, vocabulary learning and negative-noise learning.
9. Add missed-opportunity audit and source latency metrics.

## Phase 3 — Bid Readiness

1. Company capability database: projects, experts, offices, registrations, certifications and clients.
2. Eligibility matching: MATCHED / PARTIAL / UNKNOWN / NOT_MATCHED.
3. Bid Readiness Score separate from Opportunity Score.
4. Partner/JV database and local-partner gap detection.
5. Required-document checklist and compliance gaps.

## Phase 4 — Bid Workspace

1. BID workspace per opportunity.
2. Proposal preparation assistant.
3. Technical/commercial requirement checklist.
4. Clarification/addendum tracking.
5. Internal responsibility and deadline tracking.
6. Reusable project and expert references.

## Production hardening

- Application authentication/RBAC.
- PostgreSQL migration for multi-user production.
- Off-machine encrypted backups.
- Observability and alerting.
- Deployment rollback strategy.
- Secure secrets management.
- Source-specific connectors for complex high-value portals.

## Non-negotiable policies

- `ZERO_COST_MODE=true` remains the default.
- Paid or unknown-cost providers may not become mandatory core dependencies.
- No aggressive CAPTCHA bypass or paywall circumvention.
- Official tender documents and addenda take precedence over secondary sources.
- External tools remain replaceable adapters, not core dependencies.
