# Security Policy

## Current deployment model

Tender Intelligence is intended to run behind Cloudflare Access/Tunnel on a private or tightly controlled hostname. The application does not yet provide full production-grade RBAC.

## Secrets

Never commit any of the following:

- `.env`
- Cloudflare Tunnel tokens
- SMTP passwords or API keys
- production database credentials
- browser cookies/session exports
- portal credentials
- private tender documents not intended for public release

The repository intentionally tracks only `.env.example` and `.env.cloud.example`.

## Network exposure

- Keep application port `8000` bound to `127.0.0.1` on the host.
- Do not open port `8000` to the public internet.
- Put Cloudflare Access authentication in front of the public hostname until application RBAC is implemented.
- Use HTTPS at the Cloudflare edge.

## Zero-cost policy

The core system must not silently enable paid APIs, paid proxies, paid OCR or subscription tender feeds. Any future paid integration must be optional and explicitly approved.

## Responsible collection

Do not bypass paywalls, CAPTCHAs or access controls aggressively. Respect source terms, rate limits and public-access boundaries.

## Reporting a security issue

Do not post real credentials, tokens or sensitive tender documents in a public GitHub issue. Rotate any credential immediately if it is accidentally exposed.
