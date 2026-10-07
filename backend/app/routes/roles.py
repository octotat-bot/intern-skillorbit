"""Roles route: GET /api/roles. Serves the target-role catalogue."""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.services.roles import load_catalog

bp = Blueprint("roles", __name__, url_prefix="/api")


@bp.get("/roles")
def list_roles():
    """Return every target role with its requirements, in catalogue order.

    Returns:
        ``{"roles": [{id, name, description, must_have[], nice_to_have[]}]}``.
    """
    catalog = load_catalog()
    roles = [
        {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "must_have": [
                {"label": req.label, "weight": req.weight,
                 "alternatives": [catalog.display(s) for s in req.any_of]}
                for req in role.must_have
            ],
            "nice_to_have": [catalog.display(s) for s in role.nice_to_have],
        }
        for role in catalog.roles.values()
    ]
    return jsonify({"roles": roles})
