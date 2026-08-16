#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --build
