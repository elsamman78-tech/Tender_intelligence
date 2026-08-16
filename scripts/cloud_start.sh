#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  cp .env.cloud.example .env
  echo "Created .env from .env.cloud.example. Review it before production use."
fi
mkdir -p data/uploads backups
docker compose up -d --build
printf '\nTender Intelligence started locally on http://127.0.0.1:8000\n'
printf 'Health: docker compose ps\n'
