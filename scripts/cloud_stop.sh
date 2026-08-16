#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml down 2>/dev/null || docker compose down
