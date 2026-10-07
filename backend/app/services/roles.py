"""Role catalogue: loads and validates ``data/roles.json``.

The catalogue is read once per process and validated eagerly, so a typo in an
alias or weight fails fast at startup instead of silently skewing scores.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app import config


class RoleCatalogError(ValueError):
    """roles.json is structurally invalid."""


class UnknownRoleError(KeyError):
    """The requested role id does not exist."""


@dataclass(frozen=True)
class Requirement:
    """A weighted must-have, satisfied when any skill in ``any_of`` is present."""

    label: str
    weight: float
    any_of: tuple[str, ...]


@dataclass(frozen=True)
class Role:
    """A target job role."""

    id: str
    name: str
    description: str
    must_have: tuple[Requirement, ...]
    nice_to_have: tuple[str, ...]
    aliases: dict[str, str]

    def skills(self) -> set[str]:
        """Every canonical skill this role mentions."""
        required = {skill for req in self.must_have for skill in req.any_of}
        return required | set(self.nice_to_have)


@dataclass(frozen=True)
class RoleCatalog:
    """All roles plus the shared vocabulary used by the skill matcher."""

    roles: dict[str, Role]
    common_aliases: dict[str, str]
    case_sensitive_terms: dict[str, str]
    extra_skills: frozenset[str]
    display_names: dict[str, str]

    def vocabulary(self) -> set[str]:
        """Every canonical skill known to the system."""
        return set(self.extra_skills).union(*(role.skills() for role in self.roles.values()))

    def aliases(self) -> dict[str, str]:
        """Common aliases merged with every role's aliases (validated conflict-free)."""
        merged = dict(self.common_aliases)
        for role in self.roles.values():
            merged.update(role.aliases)
        return merged

    def display(self, skill: str) -> str:
        """UI label for a canonical skill."""
        return self.display_names.get(skill) or skill[:1].upper() + skill[1:]


def _parse_requirement(raw: dict[str, Any], role_id: str) -> Requirement:
    any_of = tuple(s.lower() for s in raw.get("any_of", []))
    weight = raw.get("weight", 0)
    if not any_of:
        raise RoleCatalogError(f"{role_id}: requirement '{raw.get('label')}' has empty any_of")
    if not isinstance(weight, (int, float)) or weight <= 0:
        raise RoleCatalogError(f"{role_id}: requirement '{raw.get('label')}' needs a positive weight")
    return Requirement(label=raw["label"], weight=float(weight), any_of=any_of)


def _parse_role(raw: dict[str, Any]) -> Role:
    role_id = raw["id"]
    if not raw.get("must_have"):
        raise RoleCatalogError(f"{role_id}: must_have is empty")
    return Role(
        id=role_id,
        name=raw["name"],
        description=raw["description"],
        must_have=tuple(_parse_requirement(r, role_id) for r in raw["must_have"]),
        nice_to_have=tuple(s.lower() for s in raw.get("nice_to_have", [])),
        aliases={k.lower(): v.lower() for k, v in raw.get("aliases", {}).items()},
    )


def _validate(catalog: RoleCatalog) -> None:
    """Check alias targets exist and no alias maps to two different skills."""
    known = catalog.vocabulary()
    seen: dict[str, str] = dict(catalog.common_aliases)
    for role in catalog.roles.values():
        for alias, target in role.aliases.items():
            if seen.get(alias, target) != target:
                raise RoleCatalogError(f"Alias '{alias}' maps to both '{seen[alias]}' and '{target}'")
            seen[alias] = target
    for alias, target in {**seen, **catalog.case_sensitive_terms}.items():
        if target not in known:
            raise RoleCatalogError(f"Alias '{alias}' points to unknown skill '{target}'")


def parse_catalog(data: dict[str, Any]) -> RoleCatalog:
    """Build and validate a catalogue from decoded roles.json content.

    Raises:
        RoleCatalogError: On duplicate ids, bad weights, or broken aliases.
    """
    try:
        roles = [_parse_role(r) for r in data["roles"]]
    except KeyError as exc:
        raise RoleCatalogError(f"Missing field: {exc}") from exc
    ids = [role.id for role in roles]
    if len(ids) != len(set(ids)):
        raise RoleCatalogError("Duplicate role ids")
    catalog = RoleCatalog(
        roles={role.id: role for role in roles},
        common_aliases={k.lower(): v.lower() for k, v in data.get("common_aliases", {}).items()},
        case_sensitive_terms={k: v.lower() for k, v in data.get("case_sensitive_terms", {}).items()},
        extra_skills=frozenset(s.lower() for s in data.get("extra_skills", [])),
        display_names={k.lower(): v for k, v in data.get("display_names", {}).items()},
    )
    _validate(catalog)
    return catalog


@lru_cache(maxsize=1)
def load_catalog(path: Path = config.ROLES_FILE) -> RoleCatalog:
    """Load the role catalogue from disk (cached)."""
    return parse_catalog(json.loads(path.read_text(encoding="utf-8")))


def get_role(role_id: str) -> Role:
    """Return a role by id.

    Raises:
        UnknownRoleError: If no role has this id.
    """
    roles = load_catalog().roles
    if role_id not in roles:
        raise UnknownRoleError(role_id)
    return roles[role_id]
