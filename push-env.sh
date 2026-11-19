#!/usr/bin/env bash
# Copy the values from .env.local (made by `uv run login.py`) to Vercel production and redeploy.
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env.local ] || { echo "Run 'uv run login.py' first."; exit 1; }

while IFS='=' read -r key value; do
  [ -z "$key" ] && continue
  value="${value%\"}"; value="${value#\"}"
  npx -y vercel@latest env rm "$key" --environment production --yes >/dev/null 2>&1 || true
  printf '%s' "$value" | npx -y vercel@latest env add "$key" --environment production --sensitive >/dev/null 2>&1
  echo "set $key"
done < .env.local

npx -y vercel@latest deploy --prod --yes >/dev/null
key=$(grep '^ROBI_KEY=' .env.local | cut -d= -f2- | tr -d '"')
echo
echo "Done. Open this once on the phone:"
echo "  https://robi-lime.vercel.app/#k=$key"
