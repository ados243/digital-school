"""Démarre Digital School dans le conteneur Coolify."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

for folder in ("media", "private_media", "staticfiles"):
    (ROOT / folder).mkdir(parents=True, exist_ok=True)


def run(args: list[str]) -> None:
    subprocess.check_call(args)


run([sys.executable, "manage.py", "migrate", "--noinput"])
run([sys.executable, "manage.py", "collectstatic", "--noinput"])

port = os.environ.get("PORT", "8000")
workers = os.environ.get("GUNICORN_WORKERS", "3")
timeout = os.environ.get("GUNICORN_TIMEOUT", "120")

os.execvp(
    "gunicorn",
    [
        "gunicorn",
        "ds.wsgi:application",
        "--bind",
        f"0.0.0.0:{port}",
        "--workers",
        workers,
        "--timeout",
        timeout,
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
    ],
)
