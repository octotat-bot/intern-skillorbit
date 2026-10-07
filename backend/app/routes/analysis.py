"""Analysis route.

GET /api/resumes/<id>/analysis?role=<role_id>&mode=rules|ai
"""

from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("analysis", __name__, url_prefix="/api")


@bp.get("/resumes/<int:resume_id>/analysis")
def get_analysis(resume_id: int):
    """Return the full deterministic analysis for a resume and role. (Phase 3)"""
    return jsonify({"error": "not_implemented", "message": "Analysis arrives in Phase 3."}), 501
