#!/usr/bin/env sh
set -eu

compose="docker compose"
base_url="${APEXGRID_SMOKE_URL:-http://127.0.0.1:8000}"
smoke_dir="$(mktemp -d)"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-apexgrid-smoke-test-key-never-use-in-production-2026}"

cleanup() {
  $compose down --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$smoke_dir"
}
trap cleanup EXIT INT TERM

$compose config >/dev/null
$compose build
$compose up -d

attempt=0
until curl -fsS "$base_url/health/" >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 40 ]; then
    $compose ps
    $compose logs --tail=120 web
    exit 1
  fi
  sleep 1
done

curl -fsS "$base_url/health/" -o "$smoke_dir/health.json"
curl -fsS "$base_url/" -o "$smoke_dir/home.html"
curl -fsS "$base_url/calendar/" -o "$smoke_dir/calendar.html"
curl -fsS "$base_url/grand-prix/2026/16/" -o "$smoke_dir/grand-prix.html"
grep -q '"status": "ok"' "$smoke_dir/health.json"
grep -q 'APEXGRID' "$smoke_dir/home.html"
grep -q 'Календарь сезона' "$smoke_dir/calendar.html"
grep -q 'data-track-blueprint' "$smoke_dir/grand-prix.html"

$compose ps
$compose logs --no-color web | tail -n 20
echo "ApexGrid Docker smoke: OK"
