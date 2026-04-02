"""
Gunicorn config. Load .env so PORT and app secrets are available.

Run from service root:
  gunicorn -c gunicorn.conf.py wsgi:app

Or override bind/workers:
  GUNICORN_BIND=0.0.0.0:8080 GUNICORN_WORKERS=4 gunicorn -c gunicorn.conf.py wsgi:app
"""
import multiprocessing
import os

from dotenv import load_dotenv

load_dotenv()

_port = os.environ.get("PORT", "8000")
bind = os.environ.get("GUNICORN_BIND", f"0.0.0.0:{_port}")
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "1"))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "0"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "0"))

accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

preload_app = os.environ.get("GUNICORN_PRELOAD", "").lower() in (
    "1",
    "true",
    "yes",
)

if workers <= 0:
    workers = max(1, min(multiprocessing.cpu_count() + 1, 4))

# WSGI entry is wsgi:app (module:variable)
