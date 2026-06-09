"""Trace and evidence builders for discussion artifact directories."""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from swarm.validation import validate_discussion_dir, validate_round_file
from swarm.wal import resume_plan

SCHEMA_VERSION = 1
TRACE_KIND = "swarm.discussion_trace"
EVIDENCE_KIND = "swarm.discussion_evidence"


def _issue(code: str, path: str, message: str, value: Any = None) -> dict[str, Any]:
    issue = {"code": code, "path": path, "message": message}
    if value is not None:
        issue["value"] = value
    return issue


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[Any | None, dict[str, Any] | None]:
    try:
        return json.loads(path.read_text()), None
    except FileNotFoundError:
        return None, _issue("missing_file", str(path), f"missing file: {path}")
    except json.JSONDecodeError as exc:
        return None, _issue("invalid_json", str(path), f"invalid JSON: {exc}")


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not path.exists():
        return events, errors
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(_issue("invalid_jsonl", f"{path}:{line_number}", f"invalid JSONL: {exc}"))
            continue
        if isinstance(event, dict):
            events.append(event)
        else:
            errors.append(_issue("invalid_event", f"{path}:{line_number}", "event must be a JSON object"))
    return events, errors


def _manifest_summary(discussion_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest, error = _load_json(discussion_dir / "manifest.json")
    if error:
        return {}, [error]
    if not isinstance(manifest, dict):
        return {}, [_issue("invalid_manifest", "manifest.json", "manifest must be a JSON object")]
    return manifest, []


def _round_summary(discussion_dir: Path) -> dict[str, Any]:
    rounds_dir = discussion_dir / "rounds"
    final_paths = sorted(rounds_dir.glob("[0-9][0-9][0-9].json")) if rounds_dir.exists() else []
    partial_paths = sorted(rounds_dir.glob("*.json.partial")) if rounds_dir.exists() else []
    rounds: list[dict[str, Any]] = []
    for path in final_paths:
        payload, error = _load_json(path)
        if isinstance(payload, dict):
            validation = validate_round_file(path)
            rounds.append(
                {
                    "round": payload.get("roundId") or int(path.name.split(".")[0]),
                    "source": "final",
                    "path": str(path),
                    "messageCount": len(payload.get("messages", []) or []),
                    "validationOk": validation["ok"],
                }
            )
        elif error:
            rounds.append({"source": "final", "path": str(path), "error": error})
    for path in partial_paths:
        payload, error = _load_json(path)
        if isinstance(payload, dict):
            rounds.append(
                {
                    "round": payload.get("roundId") or payload.get("round") or int(path.name.split(".")[0]),
                    "source": "partial",
                    "path": str(path),
                    "phase": payload.get("phase"),
                    "messageCount": len(payload.get("messages", []) or []),
                }
            )
        elif error:
            rounds.append({"source": "partial", "path": str(path), "error": error})
    return {
        "finalCount": len(final_paths),
        "partialCount": len(partial_paths),
        "rounds": sorted(rounds, key=lambda item: (int(item.get("round") or 0), item.get("source", ""))),
    }


def _prompt_summary(discussion_dir: Path) -> dict[str, Any]:
    prompt_paths = sorted((discussion_dir / "prompts").glob("**/prompt-build.json"))
    phases: Counter[str] = Counter()
    personas: Counter[str] = Counter()
    visibility: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []
    artifacts: list[str] = []
    for path in prompt_paths:
        payload, error = _load_json(path)
        artifacts.append(str(path))
        if error:
            errors.append(error)
            continue
        if not isinstance(payload, dict):
            errors.append(_issue("invalid_prompt_artifact", str(path), "prompt-build artifact must be an object"))
            continue
        phases[str(payload.get("phase") or "unknown")] += 1
        persona = payload.get("persona")
        if isinstance(persona, dict):
            personas[str(persona.get("id") or persona.get("name") or "unknown")] += 1
        for value in (payload.get("visibility") or {}).values():
            visibility[str(value)] += 1
    return {
        "count": len(prompt_paths),
        "promptBuildCount": len(prompt_paths),
        "phases": dict(sorted(phases.items())),
        "personas": dict(sorted(personas.items())),
        "visibility": dict(sorted(visibility.items())),
        "errors": errors,
        "paths": artifacts,
    }


def _transport_summary(discussion_dir: Path) -> dict[str, Any]:
    transport_root = discussion_dir / "transport"
    spawn_paths = sorted(transport_root.glob("**/spawn-order.json"))
    wait_paths = sorted(transport_root.glob("**/wait-batches.jsonl"))
    collect_paths = sorted(transport_root.glob("**/collect-result.json"))
    errors: list[dict[str, Any]] = []
    collect_results: list[dict[str, Any]] = []

    wait_batch_count = 0
    for path in wait_paths:
        batches, batch_errors = _load_jsonl(path)
        wait_batch_count += len(batches)
        errors.extend(batch_errors)

    for path in collect_paths:
        payload, error = _load_json(path)
        if error:
            errors.append(error)
            continue
        if not isinstance(payload, dict):
            errors.append(_issue("invalid_collect_result", str(path), "collect result must be an object"))
            continue
        collect_results.append(
            {
                "path": str(path),
                "ok": bool(payload.get("ok")),
                "complete": bool(payload.get("complete")),
                "timedOut": bool(payload.get("timedOut") or payload.get("timed_out")),
                "missingAgentIds": payload.get("missingAgentIds") or [],
                "errorCount": len(payload.get("errors") or []),
                "resultCount": len(payload.get("results") or []),
            }
        )

    complete = all(item["complete"] and item["ok"] and not item["timedOut"] for item in collect_results)
    complete = complete if collect_results else False
    return {
        "spawnOrderCount": len(spawn_paths),
        "waitBatchCount": wait_batch_count,
        "collectResultCount": len(collect_results),
        "complete": complete,
        "collectResults": collect_results,
        "errors": errors,
        "paths": [str(path) for path in [*spawn_paths, *wait_paths, *collect_paths]],
    }


def _events_summary(discussion_dir: Path) -> dict[str, Any]:
    events, errors = _load_jsonl(discussion_dir / "events.jsonl")
    counts = Counter(event.get("type", "unknown") for event in events)
    return {"count": len(events), "counts": dict(sorted(counts.items())), "last": events[-1] if events else None, "errors": errors}


def _quality_summary(discussion_dir: Path) -> dict[str, Any]:
    round_files = sorted((discussion_dir / "rounds").glob("[0-9][0-9][0-9].json"))
    synthesis_present = (discussion_dir / "artifacts" / "synthesis.md").exists()
    latest_synthesis: dict[str, Any] = {}
    if round_files:
        payload, _error = _load_json(round_files[-1])
        if isinstance(payload, dict) and isinstance(payload.get("synthesis"), dict):
            latest_synthesis = payload["synthesis"]
    quality_score = latest_synthesis.get("qualityScore")
    recommendation = latest_synthesis.get("recommendation")
    return {
        "synthesisPresent": synthesis_present or bool(latest_synthesis),
        "qualityScore": quality_score,
        "recommendation": recommendation,
    }


def _artifact_paths(discussion_dir: Path) -> list[str]:
    if not discussion_dir.exists():
        return []
    ignored_parts = {"tmp"}
    paths = []
    for path in sorted(discussion_dir.rglob("*")):
        if path.is_file() and not any(part in ignored_parts for part in path.relative_to(discussion_dir).parts):
            paths.append(str(path))
    return paths


def _next_action(
    validation: dict[str, Any],
    transport: dict[str, Any],
    resume: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if not validation.get("ok", False):
        return {
            "kind": "inspect_validation",
            "command": "swarm-rt validate-discussion --dir <discussion-dir>",
            "reason": "discussion validation failed",
        }

    incomplete_collect = next(
        (
            item
            for item in transport.get("collectResults", [])
            if not item.get("complete") or not item.get("ok") or item.get("timedOut")
        ),
        None,
    )
    if incomplete_collect:
        return {
            "kind": "poll_remaining",
            "command": "swarm-rt collect-merge ...",
            "reason": "transport collect result is incomplete",
            "missingAgentIds": incomplete_collect.get("missingAgentIds", []),
        }

    if resume.get("source") == "partial":
        return {
            "kind": "resume_round",
            "command": "swarm-rt resume-plan --dir <discussion-dir>",
            "reason": "partial round is the current WAL state",
            "round": resume.get("round"),
            "phase": resume.get("phase"),
        }

    status = manifest.get("status")
    if status in {"completed", "complete", "done"} and resume.get("source") == "final":
        return {"kind": "none", "command": None, "reason": "discussion completed"}
    if resume.get("source") == "none":
        return {"kind": "start_round", "command": "swarm-rt append-message ...", "reason": "no round state exists"}
    return {"kind": "inspect_artifacts", "command": "swarm-rt trace --dir <discussion-dir>", "reason": "manual inspection needed"}


def _health(validation: dict[str, Any], transport: dict[str, Any], resume: dict[str, Any], next_action: dict[str, Any]) -> str:
    if not validation.get("ok", False):
        return "off-track"
    if next_action.get("kind") in {"poll_remaining", "resume_round", "start_round", "inspect_artifacts"}:
        return "at-risk"
    if transport.get("errors") or resume.get("source") == "partial":
        return "at-risk"
    return "on-track"


def _relax_validation_for_partial(validation: dict[str, Any], resume: dict[str, Any]) -> dict[str, Any]:
    if resume.get("source") != "partial":
        return validation

    errors = validation.get("errors", []) or []
    missing_rounds = [error for error in errors if error.get("code") == "missing_rounds"]
    remaining = [error for error in errors if error.get("code") != "missing_rounds"]
    if not missing_rounds:
        return validation

    relaxed = dict(validation)
    relaxed["errors"] = remaining
    relaxed["warnings"] = [
        *validation.get("warnings", []),
        *[
            {
                **error,
                "message": "committed round is absent because the current WAL source is partial",
            }
            for error in missing_rounds
        ],
    ]
    relaxed["ok"] = not remaining
    return relaxed


def build_trace(discussion_dir: Path) -> dict[str, Any]:
    if not discussion_dir.exists():
        return {
            "ok": False,
            "kind": TRACE_KIND,
            "errors": [_issue("missing_directory", str(discussion_dir), "discussion directory does not exist")],
        }
    if not discussion_dir.is_dir():
        return {
            "ok": False,
            "kind": TRACE_KIND,
            "errors": [_issue("invalid_directory", str(discussion_dir), "discussion path is not a directory")],
        }

    manifest, manifest_errors = _manifest_summary(discussion_dir)
    validation = validate_discussion_dir(discussion_dir)
    if manifest_errors:
        validation = dict(validation)
        validation["ok"] = False
        validation["errors"] = [*validation.get("errors", []), *manifest_errors]

    resume = resume_plan(discussion_dir)
    validation = _relax_validation_for_partial(validation, resume)
    prompts = _prompt_summary(discussion_dir)
    transport = _transport_summary(discussion_dir)
    events = _events_summary(discussion_dir)
    rounds = _round_summary(discussion_dir)
    quality = _quality_summary(discussion_dir)
    next_action = _next_action(validation, transport, resume, manifest)
    return {
        "ok": True,
        "kind": TRACE_KIND,
        "discussionDir": str(discussion_dir),
        "discussion": {
            "id": manifest.get("id"),
            "title": manifest.get("title"),
            "mode": manifest.get("mode"),
            "status": manifest.get("status"),
            "schemaVersion": manifest.get("schemaVersion"),
        },
        "health": _health(validation, transport, resume, next_action),
        "validation": validation,
        "resume": resume,
        "rounds": rounds,
        "prompts": prompts,
        "transport": transport,
        "quality": quality,
        "events": events,
        "artifacts": {"root": str(discussion_dir), "paths": _artifact_paths(discussion_dir)},
        "nextAction": next_action,
    }


def _outcome(trace: dict[str, Any]) -> dict[str, Any]:
    action = trace.get("nextAction", {})
    status = trace.get("discussion", {}).get("status")
    if action.get("kind") == "none":
        return {"result": "completed", "determinedBy": "discussion", "reason": "discussion completed", "nextAction": action}
    if action.get("kind") == "inspect_validation":
        return {"result": "failed", "determinedBy": "validation", "reason": "validation failed", "nextAction": action}
    if action.get("kind") == "poll_remaining":
        return {"result": "incomplete", "determinedBy": "transport", "reason": "transport incomplete", "nextAction": action}
    if action.get("kind") == "resume_round":
        return {"result": "incomplete", "determinedBy": "wal", "reason": "partial round present", "nextAction": action}
    return {"result": status or "unknown", "determinedBy": "trace", "reason": action.get("reason"), "nextAction": action}


def _metrics(trace: dict[str, Any]) -> dict[str, Any]:
    artifacts = trace.get("artifacts", {}).get("paths", [])
    rounds = trace.get("rounds", {})
    return {
        "artifactCount": len(artifacts),
        "promptBuildCount": trace.get("prompts", {}).get("count", 0),
        "collectResultCount": trace.get("transport", {}).get("collectResultCount", 0),
        "finalRoundCount": rounds.get("finalCount", 0),
        "partialRoundCount": rounds.get("partialCount", 0),
        "eventCount": trace.get("events", {}).get("count", 0),
        "validationErrorCount": len(trace.get("validation", {}).get("errors", []) or []),
    }


def build_evidence(discussion_dir: Path) -> dict[str, Any]:
    trace = build_trace(discussion_dir)
    if not trace.get("ok"):
        return {
            "schemaVersion": SCHEMA_VERSION,
            "kind": EVIDENCE_KIND,
            "generatedAt": _now_iso(),
            "ok": False,
            "errors": trace.get("errors", []),
        }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": EVIDENCE_KIND,
        "generatedAt": _now_iso(),
        "ok": True,
        "discussion": trace["discussion"],
        "outcome": _outcome(trace),
        "metrics": _metrics(trace),
        "validation": {
            "ok": trace["validation"].get("ok"),
            "errorCount": len(trace["validation"].get("errors", []) or []),
            "warningCount": len(trace["validation"].get("warnings", []) or []),
            "summary": trace["validation"].get("summary", {}),
        },
        "transport": {
            "complete": trace["transport"].get("complete"),
            "spawnOrderCount": trace["transport"].get("spawnOrderCount"),
            "waitBatchCount": trace["transport"].get("waitBatchCount"),
            "collectResultCount": trace["transport"].get("collectResultCount"),
            "collectResults": trace["transport"].get("collectResults", []),
        },
        "prompts": {
            "promptBuildCount": trace["prompts"].get("count"),
            "phases": trace["prompts"].get("phases", {}),
            "personas": trace["prompts"].get("personas", {}),
            "visibility": trace["prompts"].get("visibility", {}),
        },
        "wal": {
            "resume": trace["resume"],
            "rounds": trace["rounds"],
            "events": {
                "count": trace["events"].get("count"),
                "counts": trace["events"].get("counts", {}),
                "lastType": (trace["events"].get("last") or {}).get("type"),
            },
        },
        "quality": trace["quality"],
        "trace": {
            "health": trace["health"],
            "nextAction": trace["nextAction"],
        },
        "artifacts": trace["artifacts"],
        "rawHostLogs": {
            "required": False,
            "present": bool(list(discussion_dir.glob("host-logs/**/*"))) if discussion_dir.exists() else False,
            "paths": [str(path) for path in sorted(discussion_dir.glob("host-logs/**/*")) if path.is_file()],
        },
    }
