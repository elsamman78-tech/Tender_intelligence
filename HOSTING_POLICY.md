# Hosting policy

## Core zero-cost rule

Tender Intelligence must remain runnable locally without any mandatory paid API, paid proxy, paid OCR, paid search provider, paid cloud service, credit-card dependency, or vendor-specific free tier.

## 24/7 cloud hosting

A machine that remains online while the office PC is off is infrastructure outside the local-first core. Current verified provider conditions must be checked before deployment.

### Oracle Cloud Always Free — OPTIONAL

Oracle currently documents Always Free compute resources, but its Free Tier signup normally requires a mobile phone number and credit/debit card for verification. Therefore Oracle hosting is **not a mandatory core dependency** and is not compliant with a strict no-card hosting requirement. Use it only if the owner explicitly accepts card verification while staying inside resources marked Always Free eligible.

### Cloudflare Tunnel / Access — OPTIONAL edge layer

Cloudflare Tunnel is available on all plans and can securely expose an origin using outbound-only connections. Cloudflare Zero Trust Free is currently $0 for teams under 50 users, but current onboarding documentation says payment details are still required when creating the Zero Trust organization. Therefore Access must remain optional and must not be treated as a no-card dependency.

## If no-card remains absolute

Keep the application local-first. Remote access can be provided only while a user-controlled machine/server is online, unless a future verified provider offers suitable 24/7 compute without card verification. Do not silently switch to paid hosting or a card-required free tier.
