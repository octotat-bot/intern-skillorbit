"""Analysis routes.

GET /api/resumes/<id>/analysis?role=<role_id>&mode=rules|ai   analysis JSON
GET /api/resumes/<id>/report?role=<role_id>&mode=rules|ai     the same analysis as a PDF report
"""

from __future__ import annotations

import io
import re
from typing import Any

from flask import Blueprint, jsonify, request, send_file

from app.db import get_resume
from app.errors import ApiError
from app.services.analysis import VALID_MODES, build_analysis
from app.services.report import render_report_pdf
from app.services.roles import load_catalog

bp = Blueprint("analysis", __name__, url_prefix="/api")


def _analysis_for_request(resume_id: int) -> dict[str, Any]:
    """Validate role/mode query parameters, load the resume and build its analysis."""
    role_id = request.args.get("role", "").strip()
    mode = request.args.get("mode", "rules").strip().lower() or "rules"
    roles = list(load_catalog().roles)
    if not role_id:
        raise ApiError(400, "missing_role", f"Pass ?role=<id>. Valid roles: {', '.join(roles)}.")
    if role_id not in roles:
        raise ApiError(400, "unknown_role", f"Unknown role '{role_id}'. Valid roles: {', '.join(roles)}.")
    if mode not in VALID_MODES:
        raise ApiError(400, "invalid_mode", f"mode must be one of: {', '.join(VALID_MODES)}.")
    record = get_resume(resume_id)
    if record is None:
        raise ApiError(404, "resume_not_found", f"No resume with id {resume_id}.")
    return build_analysis(record, role_id, mode)


@bp.get("/resumes/<int:resume_id>/analysis")
def get_analysis(resume_id: int):
    """Return the full analysis for a stored resume and a target role.

    Query parameters:
        role: required role id (see GET /api/roles).
        mode: ``rules`` (default) or ``ai``.
    """
    return jsonify(_analysis_for_request(resume_id))


@bp.get("/resumes/<int:resume_id>/report")
def download_report(resume_id: int):
    """Return the analysis as a downloadable PDF report (same parameters as /analysis)."""
    analysis = _analysis_for_request(resume_id)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", analysis["filename"].rsplit(".", 1)[0]).strip("_") or "resume"
    return send_file(
        io.BytesIO(render_report_pdf(analysis)),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{stem}-{analysis['role']['id']}-report.pdf",
    )
