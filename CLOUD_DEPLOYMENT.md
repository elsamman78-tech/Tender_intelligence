# Cloud deployment (zero-cost oriented)

This project is prepared for a small Linux VM running Docker. The intended first deployment is a free/Always-Free VM when available, with Cloudflare Tunnel in front of the app.

## Architecture

Browser/mobile -> Cloudflare Access/Tunnel -> Linux VM -> Docker -> FastAPI + Discovery + SQLite

The application port is bound to `127.0.0.1:8000` on the VM, so it is not directly exposed to the public internet.

## Server requirements

- Linux (Ubuntu 22.04/24.04 or Oracle Linux)
- Docker Engine + Docker Compose plugin
- Git
- outbound internet access

## First deployment

```bash
git clone https://github.com/elsamman78-tech/Tender_intelligence.git
cd Tender_intelligence
cp .env.cloud.example .env
chmod +x scripts/*.sh
./scripts/cloud_start.sh
```

Check:

```bash
docker compose ps
curl http://127.0.0.1:8000/api/v1/health
```

## Cloudflare Tunnel

Create a Tunnel in Cloudflare Zero Trust and copy its tunnel token. Put the token only in the server `.env` file:

```env
CLOUDFLARE_TUNNEL_TOKEN=YOUR_REAL_TOKEN
```

Then run:

```bash
./scripts/cloud_start_with_cloudflare.sh
```

Point the Cloudflare public hostname to:

`http://tender-intelligence:8000`

when cloudflared runs in the same Compose project, or use the local service route recommended by the Tunnel dashboard.

## Important security notes

- Never commit `.env` or the Cloudflare token.
- Put Cloudflare Access authentication in front of the hostname until application-level RBAC is implemented.
- Do not expose port 8000 publicly in the VM firewall.
- SQLite is acceptable for cloud testing; PostgreSQL is the target for multi-user production.

## Backups

```bash
./scripts/backup.sh
```

Backups are retained locally for 30 days by the current script. Off-machine backup is still pending.
