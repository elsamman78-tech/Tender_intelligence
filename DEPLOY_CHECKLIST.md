# 24/7 Deployment Checklist

Use this checklist for the first online deployment.

## 1. Cloud VM

- Create a small Linux VM.
- Install Docker Engine, Docker Compose plugin and Git.
- Do not expose application port 8000 publicly.

## 2. Clone

```bash
git clone https://github.com/elsamman78-tech/Tender_intelligence.git
cd Tender_intelligence
cp .env.cloud.example .env
chmod +x scripts/*.sh
```

## 3. Review `.env`

Keep:

```env
ZERO_COST_MODE=true
DISCOVERY_ENABLED=true
AGENT_REACH_ENABLED=false
```

Do not commit the server `.env`.

## 4. Start app

```bash
./scripts/cloud_start.sh
```

Verify:

```bash
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
```

## 5. Cloudflare

- Create a Cloudflare Tunnel.
- Put the real tunnel token only in the server `.env`.
- Create a protected public hostname.
- Use Cloudflare Access authentication.
- Route the hostname to the app service through the tunnel.

Start tunnel mode:

```bash
./scripts/cloud_start_with_cloudflare.sh
```

## 6. Persistence

Confirm these host directories exist and survive container rebuilds:

```text
data/
data/uploads/
backups/
```

## 7. Backup

```bash
./scripts/backup.sh
```

Verify that a backup file is created and that old backups rotate.

## 8. Update

```bash
./scripts/update_from_github.sh
```

Re-run health checks after every update.

## 9. Acceptance test

Deployment is accepted only when all are true:

- GitHub CI is green.
- Docker container is healthy.
- `/api/v1/health` returns OK.
- Dashboard loads through the Cloudflare hostname.
- Discovery dashboard loads.
- The system remains online while the office PC is off.
- Database data remains after a container restart.
- No real secrets exist in GitHub.

## 10. Still required for production

Application RBAC, PostgreSQL, off-machine backups and stronger monitoring remain production-hardening items.
