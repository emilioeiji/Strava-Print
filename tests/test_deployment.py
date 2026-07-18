from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mariadb_settings_load_from_external_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / "strava-print.env"
    env_file.write_text(
        "\n".join(
            (
                "DJANGO_SECRET_KEY=test-production-key",
                "DB_NAME=strava_print",
                "DB_USER=studio",
                "DB_PASSWORD=secret",
                "DB_HOST=127.0.0.1",
                "DB_PORT=3306",
            )
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    for key in ("DATABASE_URL", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"):
        env.pop(key, None)
    env["DJANGO_ENV_FILE"] = str(env_file)

    script = """
import json
from strava_print_web.settings import DATABASES, SECRET_KEY
db = DATABASES["default"]
print(json.dumps({
    "secret": SECRET_KEY,
    "engine": db["ENGINE"],
    "name": db["NAME"],
    "user": db["USER"],
    "charset": db["OPTIONS"]["charset"],
    "strict": db["OPTIONS"]["init_command"],
    "isolation": db["OPTIONS"]["isolation_level"],
    "health_checks": db["CONN_HEALTH_CHECKS"],
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=True,
        text=True,
    )
    config = json.loads(result.stdout)

    assert config == {
        "secret": "test-production-key",
        "engine": "django.db.backends.mysql",
        "name": "strava_print",
        "user": "studio",
        "charset": "utf8mb4",
        "strict": "SET sql_mode='STRICT_TRANS_TABLES'",
        "isolation": "read committed",
        "health_checks": True,
    }


def test_apache_and_worker_examples_keep_private_media() -> None:
    apache = (ROOT / "deploy" / "apache-strava-print.conf.example").read_text(encoding="utf-8")
    worker = (ROOT / "deploy" / "strava-print-worker.service.example").read_text(encoding="utf-8")

    assert "WSGIDaemonProcess strava_print" in apache
    assert "WSGIApplicationGroup %{GLOBAL}" in apache
    assert "Alias /static/" in apache
    assert "Alias /media/" not in apache
    assert "EnvironmentFile=-/etc/strava-print.env" in worker
    assert "process_export_jobs" in worker
