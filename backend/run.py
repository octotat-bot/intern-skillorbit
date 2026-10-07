"""Development entrypoint for the Resume Analyzer backend.

Usage:
    python run.py                 # Flask dev server on $PORT (default 5000)
Production runs gunicorn against ``app:create_app()``.
"""

from __future__ import annotations

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
