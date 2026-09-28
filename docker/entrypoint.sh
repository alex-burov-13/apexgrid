#!/usr/bin/env sh
set -eu

python manage.py migrate --noinput
python manage.py seed_demo
python manage.py collectstatic --noinput

exec "$@"
