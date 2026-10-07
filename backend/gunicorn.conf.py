"""Gunicorn settings used when no CLI flags override them (e.g. `gunicorn -c gunicorn.conf.py`)."""

import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = 4
timeout = 60          # AI mode waits on the LLM, bounded by AI_TIMEOUT_SECONDS
preload_app = True    # load spaCy once in the master, share memory with workers
accesslog = "-"
