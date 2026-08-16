#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  cp .env.cloud.example .env
fi
if ! grep -Eq '^CLOUDFLARE_TUNNEL_TOKEN=.+$' .env; then
  echo "CLOUDFLARE_TUNNEL_TOKEN is missing in .env"
  exit 1
fi
mkdir -p data/uploads backups
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --build
