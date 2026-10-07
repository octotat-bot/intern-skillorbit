"""Flask application factory.

Wires CORS, JSON error handlers, the SQLite database, and the API blueprints.
Keeping construction in a factory makes the app importable by tests and by the
gunicorn entrypoint without side effects at import time.
"""

from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS

from app import config
from app.db import init_db
from app.errors import register_error_handlers


def create_app() -> Flask:
    """Build and configure the Flask app.

    Returns:
        A configured :class:`flask.Flask` instance with blueprints, CORS,
        JSON error handlers, and an initialised database.
    """
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_REQUEST_BYTES
    # Keep insertion order: sections are in document order and score parameters
    # in their defined order. Flask sorts JSON keys alphabetically by default.
    app.json.sort_keys = False

    # Expose Content-Disposition so the cross-origin frontend can read report filenames.
    CORS(app, origins=config.CORS_ORIGINS, expose_headers=["Content-Disposition"])

    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    init_db()

    from app.routes.analysis import bp as analysis_bp
    from app.routes.roles import bp as roles_bp
    from app.routes.upload import bp as upload_bp

    app.register_blueprint(upload_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(analysis_bp)

    register_error_handlers(app)

    @app.get("/api/health")
    def health():
        """Liveness probe."""
        return jsonify({"status": "ok"}), 200

    return app
