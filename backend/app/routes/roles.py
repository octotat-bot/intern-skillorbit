"""Roles route: GET /api/roles. Serves the target-role catalogue."""

from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("roles", __name__, url_prefix="/api")


@bp.get("/roles")
def list_roles():
    """Return the list of target roles. (Phase 2)"""
    return jsonify({"error": "not_implemented", "message": "Roles arrive in Phase 2."}), 501
