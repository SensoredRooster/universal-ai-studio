"""Architect/Inspector orchestration for Universal AI Studio.

The Architect plans only against capabilities that are actually present.
The Inspector validates structured plans and completed artifacts without
performing side-effecting production work itself.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from .capabilities import CapabilityRegistry, build_default_registry
from .pipelines import load_pipeline_catalog, load_pipeline_manifest


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
ARCHITECT_MODEL = os.getenv("PLANNER_MODEL", "qwen2.5-coder:7b-instruct")
INSPECTOR_MODEL = os.getenv("INSPECTOR_MODEL", "deepseek-coder:6.7b-instruct")


def _ollama_json(model: str, system: str, prompt: str, timeout: int = 180) -> dict[str, Any]:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    raw = response.json().get("response", "").strip()
    if not raw:
        raise RuntimeError(f"{model} returned an empty response")
    return json.loads(raw)


def _capability_state(report: dict[str, Any], capability: str) -> str:
    bucket = report.get("capabilities", {}).get(capability, {})
    if bucket.get("available"):
        return "available"
    if bucket.get("degraded"):
        return "degraded"
    return "unavailable"


def score_pipeline(
    pipeline: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    required = pipeline.get("required_capabilities", [])
    optional = pipeline.get("optional_capabilities", [])
    required_states = {cap: _capability_state(report, cap) for cap in required}
    optional_states = {cap: _capability_state(report, cap) for cap in optional}

    missing = [cap for cap, state in required_states.items() if state == "unavailable"]
    degraded = [cap for cap, state in required_states.items() if state == "degraded"]
    available_optional = [cap for cap, state in optional_states.items() if state == "available"]

    score = 100 - (100 * len(missing)) - (15 * len(degraded)) + (3 * len(available_optional))
    return {
        **pipeline,
        "executable": not missing,
        "score": max(0, score),
        "missing_required": missing,
        "degraded_required": degraded,
        "available_optional": available_optional,
    }


def ranked_pipelines(registry: CapabilityRegistry | None = None) -> list[dict[str, Any]]:
    registry = registry or build_default_registry()
    report = registry.report()
    ranked = [score_pipeline(item, report) for item in load_pipeline_catalog()]
    ranked.sort(key=lambda item: (item["executable"], item["score"]), reverse=True)
    return ranked


def architect_system_prompt(registry: CapabilityRegistry | None = None) -> str:
    registry = registry or build_default_registry()
    report = registry.report()
    compact_tools = [
        {
            "name": item["name"],
            "capability": item["capability"],
            "status": item["status"],
            "provider": item["provider"],
            "runtime": item["runtime"],
            "detail": item["status_detail"],
        }
        for item in report["tools"]
    ]
    pipelines = ranked_pipelines(registry)
    return (
        "You are The Architect in Universal AI Studio. You design executable plans, not wish lists. "
        "Use only capabilities that the supplied machine support envelope reports as available or degraded. "
        "If a required capability is unavailable, say so and select a real fallback when one exists. "
        "Choose an existing production pipeline when the request is production work. "
        "Never claim a tool ran merely because it exists in the catalog. "
        "Keep normal chat useful when the user is not asking for production work.\n\n"
        f"LIVE TOOL ENVELOPE:\n{json.dumps(compact_tools, indent=2)}\n\n"
        f"PIPELINE CATALOG:\n{json.dumps(pipelines, indent=2)}"
    )


def inspector_system_prompt(registry: CapabilityRegistry | None = None) -> str:
    registry = registry or build_default_registry()
    report = registry.report()
    return (
        "You are The Inspector in Universal AI Studio. Your job is independent verification and QA. "
        "Check whether plans are executable, required capabilities are truly available, claimed artifacts "
        "actually exist in supplied evidence, approval gates are respected, and outputs meet stated success "
        "criteria. Never approve unsupported claims. Return specific failures and concrete fixes. "
        "Do not pretend to have inspected media or files that were not supplied.\n\n"
        f"LIVE CAPABILITY SUMMARY:\n{json.dumps(report['summary'], indent=2)}\n"
        f"CAPABILITY GROUPS:\n{json.dumps(report['capabilities'], indent=2)}"
    )


def create_production_plan(
    request_text: str,
    registry: CapabilityRegistry | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    registry = registry or build_default_registry()
    ranked = ranked_pipelines(registry)
    executable = [item for item in ranked if item["executable"]]
    if not executable:
        return {
            "ok": False,
            "request": request_text,
            "error": "No production pipeline currently has all required capabilities.",
            "pipeline_candidates": ranked,
        }

    system = architect_system_prompt(registry)
    prompt = (
        "Create a structured production plan for this request:\n"
        f"{request_text}\n\n"
        "Return JSON with keys: pipeline_id, rationale, stages, tools, fallbacks, approval_gates, "
        "risks, and ready_to_execute. pipeline_id must be one of these executable IDs: "
        f"{[item['id'] for item in executable]}. "
        "Each stage should name its expected artifact/output. Do not invent capabilities."
    )
    plan = _ollama_json(model or ARCHITECT_MODEL, system, prompt)
    selected_id = plan.get("pipeline_id")
    allowed = {item["id"] for item in executable}
    if selected_id not in allowed:
        selected_id = executable[0]["id"]
        plan["pipeline_id"] = selected_id
        plan["planner_correction"] = "Model selected an unavailable/unknown pipeline; registry chose the best executable pipeline."

    manifest = load_pipeline_manifest(selected_id)
    return {
        "ok": True,
        "request": request_text,
        "plan": plan,
        "pipeline": manifest,
        "pipeline_candidates": ranked,
    }


def inspect_plan(
    plan_payload: dict[str, Any],
    registry: CapabilityRegistry | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    registry = registry or build_default_registry()
    pipeline_id = (
        plan_payload.get("pipeline_id")
        or plan_payload.get("plan", {}).get("pipeline_id")
    )
    if not pipeline_id:
        return {"ok": False, "approved": False, "errors": ["pipeline_id is missing"]}

    try:
        manifest = load_pipeline_manifest(pipeline_id)
    except (FileNotFoundError, ValueError) as exc:
        return {"ok": False, "approved": False, "errors": [str(exc)]}

    report = registry.report()
    scored = score_pipeline(
        {
            "id": manifest["id"],
            "name": manifest.get("name", manifest["id"]),
            "description": manifest.get("description", ""),
            "required_capabilities": manifest.get("required_capabilities", []),
            "optional_capabilities": manifest.get("optional_capabilities", []),
            "stage_count": len(manifest["stages"]),
        },
        report,
    )
    deterministic_errors = []
    if not scored["executable"]:
        deterministic_errors.append(
            "Missing required capabilities: " + ", ".join(scored["missing_required"])
        )

    system = inspector_system_prompt(registry)
    prompt = (
        "Inspect this proposed production plan against the manifest and live support envelope. "
        "Return JSON with keys: approved (boolean), errors (array), warnings (array), "
        "checks (array of objects with name/status/detail), and recommended_changes (array).\n\n"
        f"PLAN:\n{json.dumps(plan_payload, indent=2)}\n\n"
        f"MANIFEST:\n{json.dumps(manifest, indent=2)}\n\n"
        f"DETERMINISTIC PRECHECK:\n{json.dumps(scored, indent=2)}"
    )
    review = _ollama_json(model or INSPECTOR_MODEL, system, prompt)
    errors = list(deterministic_errors)
    errors.extend(review.get("errors") or [])
    approved = bool(review.get("approved")) and not errors

    return {
        "ok": True,
        "approved": approved,
        "errors": errors,
        "warnings": review.get("warnings") or [],
        "checks": review.get("checks") or [],
        "recommended_changes": review.get("recommended_changes") or [],
        "pipeline": manifest,
        "capability_precheck": scored,
    }
