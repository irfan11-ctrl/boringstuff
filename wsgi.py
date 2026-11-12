"""WSGI entry point for a production deployment.

Configure BORINGSTUFF_ENV, BORINGSTUFF_SECRET_KEY, and
BORINGSTUFF_ALLOWED_HOSTS before importing this module.
"""
import os

from app import create_app


if os.environ.get("BORINGSTUFF_ENV", "").strip().lower() not in {"production", "prod"}:
    raise RuntimeError("Set BORINGSTUFF_ENV=production before using the WSGI entry point.")
if not os.environ.get("BORINGSTUFF_SECRET_KEY", "").strip():
    raise RuntimeError("Set BORINGSTUFF_SECRET_KEY before starting the production server.")
if not os.environ.get("BORINGSTUFF_ALLOWED_HOSTS", "").strip():
    raise RuntimeError("Set BORINGSTUFF_ALLOWED_HOSTS to the public hostname(s).")

app = create_app()
