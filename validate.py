#!/usr/bin/env python3
"""Dependency-free structural and semantic checks for the Dele-bench seed dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TASKS_PATH = ROOT / "data" / "v0.1" / "tasks.jsonl"
REFERENCES_PATH = ROOT / "data" / "v0.1" / "references.jsonl"
ORGANIZATIONS_DIR = ROOT / "organizations"
WORLDS_DIR = ROOT / "data" / "v0.1" / "worlds"

PUBLIC_FORBIDDEN_KEYS = {
    "required_capabilities",
    "required_state",
    "forbidden_state",
    "trace_constraints",
    "approval_outcomes",
    "expected_roles",
    "expected_route",
    "ground_truth",
}
TRACKS = {"workflow", "approval", "mixed", "resilience"}
NUMERIC_OPS = {"lt", "lte", "gt", "gte", "eq", "neq", "count"}
VALUE_REQUIRED_OPS = NUMERIC_OPS | {"contains"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected an object")
        records.append(value)
    return records


def index_unique(records: list[dict[str, Any]], key: str, source: Path) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        value = record.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{source}: every record needs a non-empty {key!r}")
        if value in indexed:
            raise ValueError(f"{source}: duplicate {key} {value!r}")
        indexed[value] = record
    return indexed


def load_organizations() -> dict[str, dict[str, Any]]:
    organizations: dict[str, dict[str, Any]] = {}
    for path in sorted(ORGANIZATIONS_DIR.glob("*.json")):
        organization = json.loads(path.read_text())
        organization_id = organization.get("id")
        if not isinstance(organization_id, str) or not organization_id:
            raise ValueError(f"{path}: missing organization id")
        if organization_id in organizations:
            raise ValueError(f"{path}: duplicate organization id {organization_id!r}")
        organizations[organization_id] = organization
    return organizations


def capability_roles(organization: dict[str, Any]) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for role in organization.get("roles", []):
        for capability in role.get("capabilities", []):
            mapping.setdefault(capability, set()).add(role["id"])
    return mapping


def routing_index(organization: dict[str, Any]) -> dict[tuple[str, str], set[str]]:
    edges: dict[tuple[str, str], set[str]] = {}
    for edge in organization.get("routing", {}).get("edges", []):
        key = (edge["from"], edge["to"])
        edges.setdefault(key, set()).update(edge.get("kinds", []))
    return edges


def policy_targets(organization: dict[str, Any]) -> set[str]:
    system_ids = {system["id"] for system in organization.get("systems", [])}
    tool_ids = {
        tool["id"]
        for system in organization.get("systems", [])
        for tool in system.get("tools", [])
    }
    return system_ids | tool_ids | {"all"}


def handoff_is_routable(
    organization: dict[str, Any],
    *,
    from_capability: str,
    to_capability: str,
    kind: str,
) -> bool:
    cap_roles = capability_roles(organization)
    from_roles = cap_roles.get(from_capability, set())
    to_roles = cap_roles.get(to_capability, set())
    if not from_roles or not to_roles:
        return False
    edges = routing_index(organization)
    for from_role in from_roles:
        for to_role in to_roles:
            if kind in edges.get((from_role, to_role), set()):
                return True
    return False


def validate_predicate(task_id: str, predicate: dict[str, Any], *, label: str) -> None:
    op = predicate.get("op")
    if op not in NUMERIC_OPS | {"exists", "absent", "contains"}:
        raise ValueError(f"{task_id}: {label} has unknown op {op!r}")
    if op in VALUE_REQUIRED_OPS and "value" not in predicate:
        raise ValueError(f"{task_id}: {label} op {op!r} requires value")
    if op in {"exists", "absent"} and "value" in predicate:
        raise ValueError(f"{task_id}: {label} op {op!r} must not carry value")


def validate_organization(organization: dict[str, Any]) -> set[str]:
    organization_id = organization["id"]
    roles = organization.get("roles")
    if not isinstance(roles, list) or len(roles) < 2:
        raise ValueError(f"{organization_id}: requires at least two roles")

    role_ids = {role.get("id") for role in roles}
    if None in role_ids or len(role_ids) != len(roles):
        raise ValueError(f"{organization_id}: role ids must be present and unique")

    capabilities: set[str] = set()
    tool_owners: dict[str, set[str]] = {}
    for role in roles:
        role_id = role["id"]
        role_capabilities = role.get("capabilities", [])
        if not role_capabilities:
            raise ValueError(f"{organization_id}/{role_id}: needs capabilities")
        capabilities.update(role_capabilities)
        reports_to = role.get("reports_to")
        if reports_to is not None and reports_to not in role_ids:
            raise ValueError(f"{organization_id}/{role_id}: unknown manager {reports_to!r}")
        for tool in role.get("tools", []):
            tool_owners.setdefault(tool, set()).add(role_id)

    system_tools = {
        tool["id"]
        for system in organization.get("systems", [])
        for tool in system.get("tools", [])
    }
    missing_tools = sorted(set(tool_owners) - system_tools)
    if missing_tools:
        raise ValueError(f"{organization_id}: role tools absent from systems: {missing_tools}")

    allowed_targets = policy_targets(organization)
    for policy in organization.get("policies", []):
        for target in policy.get("applies_to", []):
            if target not in allowed_targets:
                raise ValueError(
                    f"{organization_id}: policy {policy['id']} applies_to unknown target {target!r}"
                )

    for edge in organization.get("routing", {}).get("edges", []):
        if edge.get("from") not in role_ids or edge.get("to") not in role_ids:
            raise ValueError(f"{organization_id}: routing edge references an unknown role: {edge}")
    return capabilities


def validate() -> None:
    tasks = read_jsonl(TASKS_PATH)
    references = read_jsonl(REFERENCES_PATH)
    tasks_by_id = index_unique(tasks, "id", TASKS_PATH)
    references_by_id = index_unique(references, "task_id", REFERENCES_PATH)
    organizations = load_organizations()
    capabilities_by_organization = {
        organization_id: validate_organization(organization)
        for organization_id, organization in organizations.items()
    }

    if set(tasks_by_id) != set(references_by_id):
        missing_references = sorted(set(tasks_by_id) - set(references_by_id))
        missing_tasks = sorted(set(references_by_id) - set(tasks_by_id))
        raise ValueError(
            f"task/reference mismatch; missing references={missing_references}, "
            f"orphan references={missing_tasks}"
        )

    for task_id, task in tasks_by_id.items():
        leaked = PUBLIC_FORBIDDEN_KEYS.intersection(task)
        if leaked:
            raise ValueError(f"{task_id}: public task leaks private keys: {sorted(leaked)}")
        if task.get("track") not in TRACKS:
            raise ValueError(f"{task_id}: invalid track {task.get('track')!r}")
        organization_id = task.get("organization")
        if organization_id not in organizations:
            raise ValueError(f"{task_id}: unknown organization {organization_id!r}")
        organization = organizations[organization_id]
        role_ids = {role["id"] for role in organization["roles"]}
        cap_roles = capability_roles(organization)
        if task.get("entry_role") not in role_ids:
            raise ValueError(f"{task_id}: unknown entry role {task.get('entry_role')!r}")
        limits = task.get("limits", {})
        if any(not isinstance(limits.get(key), int) or limits[key] < 1 for key in (
            "max_events",
            "max_handoffs",
            "deadline_ticks",
        )):
            raise ValueError(f"{task_id}: limits must be positive integers")

        fixture = task.get("world_fixture")
        world_path = WORLDS_DIR / f"{fixture}.json"
        if not world_path.exists():
            raise ValueError(f"{task_id}: missing world fixture {world_path}")

        reference = references_by_id[task_id]
        required_capabilities = reference.get("required_capabilities", [])
        if len(required_capabilities) != len(set(required_capabilities)):
            raise ValueError(f"{task_id}: duplicate required_capabilities")
        if len(set(required_capabilities)) < 2:
            raise ValueError(f"{task_id}: must require at least two capabilities")
        unknown_capabilities = set(required_capabilities) - capabilities_by_organization[organization_id]
        if unknown_capabilities:
            raise ValueError(f"{task_id}: unknown capabilities {sorted(unknown_capabilities)}")

        participating_roles = {
            role
            for capability in required_capabilities
            for role in cap_roles.get(capability, set())
        }
        if len(participating_roles) < 2:
            raise ValueError(f"{task_id}: must require capabilities from at least two roles")

        for predicate in reference.get("required_state", []):
            validate_predicate(task_id, predicate, label="required_state")
        for predicate in reference.get("forbidden_state", []):
            validate_predicate(task_id, predicate, label="forbidden_state")
        if not reference.get("required_state"):
            raise ValueError(f"{task_id}: pristine-fail gate needs positive required state")

        trace = reference.get("trace_constraints", {})
        handoff_caps: set[str] = set()
        for handoff in trace.get("handoffs", []):
            from_cap = handoff["from_capability"]
            to_cap = handoff["to_capability"]
            kind = handoff["kind"]
            handoff_caps.update({from_cap, to_cap})
            if from_cap not in capabilities_by_organization[organization_id]:
                raise ValueError(f"{task_id}: handoff from unknown capability {from_cap!r}")
            if to_cap not in capabilities_by_organization[organization_id]:
                raise ValueError(f"{task_id}: handoff to unknown capability {to_cap!r}")
            if not handoff_is_routable(
                organization,
                from_capability=from_cap,
                to_capability=to_cap,
                kind=kind,
            ):
                raise ValueError(
                    f"{task_id}: unroutable handoff {from_cap} --{kind}--> {to_cap}"
                )
        missing_from_required = handoff_caps - set(required_capabilities)
        if missing_from_required:
            raise ValueError(
                f"{task_id}: handoff capabilities missing from required_capabilities: "
                f"{sorted(missing_from_required)}"
            )

        for outcome in reference.get("approval_outcomes", []):
            for citation in outcome.get("rule_citations", []):
                policy_ids = {policy["id"] for policy in organization.get("policies", [])}
                if citation not in policy_ids:
                    raise ValueError(f"{task_id}: unknown policy citation {citation!r}")

        closure = reference.get("closure", {})
        if closure.get("open_children") != 0:
            raise ValueError(f"{task_id}: accepted reference must not leave open children")
        trace_limit = trace.get("max_handoffs")
        if trace_limit is not None and trace_limit > limits["max_handoffs"]:
            raise ValueError(f"{task_id}: private handoff ceiling exceeds public limit")

    print(
        f"valid: {len(tasks)} tasks, {len(references)} references, "
        f"{len(organizations)} organization(s), "
        f"{len(list(WORLDS_DIR.glob('*.json')))} world fixture(s)"
    )


if __name__ == "__main__":
    try:
        validate()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
