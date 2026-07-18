#!/usr/bin/env sh
set -eu

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
