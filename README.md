# Tender Intelligence Zero Cost V2 — Discovery + Cloud Ready

Local-first and cloud-ready Tender Intelligence & Bid Decision System for engineering consultancy opportunities.

## Current implemented core

- Existing V1 analyzer preserved.
- Source Intelligence models and seed registry.
- Known-source HTML/RSS/Sitemap scanning.
- Open-search provider abstraction with zero-cost routing.
- Discovery candidates, validation, deduplication and automatic promotion into the analyzer.
- File discovery for procurement documents.
- Source health and Discovery dashboard.
- Local background scheduler.
- Zero-cost policy blocking paid/unknown providers from core execution.
- Docker/Linux deployment files for a 24/7 cloud test server.
- Cloudflare Tunnel-ready configuration without committing secrets.

## Local Windows

Use `INSTALL.bat` then `START.bat`.

## Linux / Cloud

```bash
cp .env.cloud.example .env
chmod +x scripts/*.sh
./scripts/cloud_start.sh
```

For Cloudflare Tunnel, add a real `CLOUDFLARE_TUNNEL_TOKEN` only to the server `.env`, then:

```bash
./scripts/cloud_start_with_cloudflare.sh
```

See `CLOUD_DEPLOYMENT.md`.

## Health

- App: `http://127.0.0.1:8000`
- API health: `/api/v1/health`
- Discovery: `/discovery`
- Sources: `/sources`

## Security

The repository contains no production secrets. `.env`, runtime databases, uploads and backups are excluded from Git. Until application RBAC is implemented, protect any public hostname with Cloudflare Access.

## Status

This is not the final product. OCR, news/social early signals, change detection, company capability matching, Bid Readiness and full production auth/RBAC remain pending.
