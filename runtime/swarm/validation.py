"""Runtime validation helpers for discussion artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ALLOWED_RELATIONS = {"supports", "counters", "extends", "questions"}
MESSAGE_ID = re.compile(r"^r(\d+)-msg-(\d{3})$")
COMPLETED_STATUSES = {"completed", "complete", "done"}


def _issue(code: str, path: str, message: str, value: Any = None) -> dict[str, Any]:
    issue = {"code": code, "path": path, "message": message}
    if value is not None:
        issue["value"] = value
    return issue


def _load_json(path: Path, errors: list[dict[str, Any]], label: str) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        errors.append(_issue("missing_file", label, f"missing file: {path}"))
    except json.JSONDecodeError as exc:
        errors.append(_issue("invalid_json", label, f"invalid JSON: {exc}"))
    return None


def validate_round_record(round_record: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    required = (
        "roundId",
        "topic",
        "mode",
        "timestamp",
        "messages",
        "argumentGraph",
        "positionShifts",
        "synthesis",
        "metadata",
    )
    for field in required:
        if field not in round_record:
            errors.append(_issue("missing_field", field, f"missing field: {field}"))

    round_id = round_record.get("roundId")
    if not isinstance(round_id, int):
        errors.append(_issue("invalid_round_id", "roundId", "roundId must be an integer", round_id))

    messages = round_record.get("messages") or []
    if not isinstance(messages, list):
        errors.append(_issue("invalid_messages", "messages", "messages must be a list"))
        messages = []

    message_ids: list[str] = []
    seqs: list[int] = []
    for index, message in enumerate(messages):
        path = f"messages[{index}]"
        if not isinstance(message, dict):
            errors.append(_issue("invalid_message", path, "message must be an object"))
            continue

        message_id = message.get("id")
        if not isinstance(message_id, str):
            errors.append(_issue("invalid_message_id", f"{path}.id", "message id must be a string", message_id))
            continue

        message_ids.append(message_id)
        match = MESSAGE_ID.match(message_id)
        if not match:
            errors.append(_issue("invalid_message_id", f"{path}.id", "message id violates rN-msg-NNN grammar", message_id))
            continue

        if isinstance(round_id, int) and int(match.group(1)) != round_id:
            errors.append(
                _issue(
                    "message_round_mismatch",
                    f"{path}.id",
                    "message id round does not match roundId",
                    message_id,
                )
            )
        seqs.append(int(match.group(2)))

    if len(message_ids) != len(set(message_ids)):
        errors.append(_issue("duplicate_message_id", "messages", "message ids must be unique"))
    expected_seqs = list(range(1, len(messages) + 1))
    if sorted(seqs) != expected_seqs:
        errors.append(
            _issue(
                "message_id_gap",
                "messages",
                f"message ids must be gapless 1..{len(messages)}",
                sorted(seqs),
            )
        )

    present = set(message_ids)
    argument_graph = round_record.get("argumentGraph") or []
    if not isinstance(argument_graph, list):
        errors.append(_issue("invalid_argument_graph", "argumentGraph", "argumentGraph must be a list"))
        argument_graph = []

    for index, edge in enumerate(argument_graph):
        path = f"argumentGraph[{index}]"
        if not isinstance(edge, dict):
            errors.append(_issue("invalid_edge", path, "argumentGraph edge must be an object"))
            continue
        relation = edge.get("relation")
        if relation not in ALLOWED_RELATIONS:
            errors.append(
                _issue(
                    "invalid_relation",
                    f"{path}.relation",
                    "relation must be one of counters, extends, questions, supports",
                    relation,
                )
            )
        for key in ("from", "to"):
            if edge.get(key) not in present:
                errors.append(
                    _issue(
                        "unresolved_edge",
                        f"{path}.{key}",
                        "argumentGraph endpoint must resolve to a present message id",
                        edge.get(key),
                    )
                )

    for message_index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        references = message.get("references") or []
        path = f"messages[{message_index}].references"
        if not isinstance(references, list):
            errors.append(_issue("invalid_references", path, "references must be a list"))
            continue
        for ref_index, ref in enumerate(references):
            ref_path = f"{path}[{ref_index}]"
            if not isinstance(ref, dict):
                errors.append(_issue("invalid_reference", ref_path, "reference must be an object"))
                continue
            relation = ref.get("relation")
            if relation not in ALLOWED_RELATIONS:
                errors.append(
                    _issue(
                        "invalid_relation",
                        f"{ref_path}.relation",
                        "relation must be one of counters, extends, questions, supports",
                        relation,
                    )
                )
            if ref.get("targetId") not in present:
                errors.append(
                    _issue(
                        "unresolved_reference",
                        f"{ref_path}.targetId",
                        "reference target must resolve to a present message id",
                        ref.get("targetId"),
                    )
                )

    if not round_record.get("synthesis"):
        errors.append(_issue("missing_synthesis", "synthesis", "committed round must include synthesis"))

    metadata = round_record.get("metadata") or {}
    if not isinstance(metadata, dict):
        errors.append(_issue("invalid_metadata", "metadata", "metadata must be an object"))
        metadata = {}

    if metadata.get("messageCount") != len(messages):
        errors.append(
            _issue(
                "metadata_mismatch",
                "metadata.messageCount",
                "metadata.messageCount must equal len(messages)",
                metadata.get("messageCount"),
            )
        )
    if metadata.get("referenceCount") != len(argument_graph):
        errors.append(
            _issue(
                "metadata_mismatch",
                "metadata.referenceCount",
                "metadata.referenceCount must equal len(argumentGraph)",
                metadata.get("referenceCount"),
            )
        )
    participants = metadata.get("participants")
    distinct_senders = {message.get("from") for message in messages if isinstance(message, dict)}
    if set(participants or []) != distinct_senders:
        errors.append(
            _issue(
                "metadata_mismatch",
                "metadata.participants",
                "metadata.participants must equal distinct message senders",
                participants,
            )
        )

    context_log = round_record.get("personaContextLog")
    if context_log:
        for shift_index, shift in enumerate(round_record.get("positionShifts") or []):
            if not isinstance(shift, dict):
                continue
            trigger = shift.get("trigger")
            trigger_ids = trigger if isinstance(trigger, list) else ([trigger] if trigger else [])
            expert = shift.get("expert")
            visibility = context_log.get(expert, {}) if isinstance(context_log, dict) else {}
            for trigger_id in trigger_ids:
                if not isinstance(visibility, dict) or visibility.get(trigger_id) != "full":
                    errors.append(
                        _issue(
                            "shift_trigger_not_visible",
                            f"positionShifts[{shift_index}].trigger",
                            "position shift trigger must have been visible in full",
                            trigger_id,
                        )
                    )
    else:
        warnings.append(
            _issue(
                "missing_persona_context_log",
                "personaContextLog",
                "shift provenance skipped because personaContextLog is absent",
            )
        )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "messageCount": len(messages),
            "argumentEdgeCount": len(argument_graph),
            "relationEnum": sorted(ALLOWED_RELATIONS),
        },
    }


def validate_round_file(path: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    data = _load_json(path, errors, str(path))
    if errors:
        return {"ok": False, "errors": errors, "warnings": [], "summary": {}}
    if not isinstance(data, dict):
        return {
            "ok": False,
            "errors": [_issue("invalid_round", str(path), "round file must contain a JSON object")],
            "warnings": [],
            "summary": {},
        }
    result = validate_round_record(data)
    result["path"] = str(path)
    return result


def validate_discussion_dir(path: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not path.exists():
        return {
            "ok": False,
            "errors": [_issue("missing_directory", str(path), "discussion directory does not exist")],
            "warnings": [],
            "summary": {},
        }
    if not path.is_dir():
        return {
            "ok": False,
            "errors": [_issue("invalid_directory", str(path), "discussion path is not a directory")],
            "warnings": [],
            "summary": {},
        }

    manifest = _load_json(path / "manifest.json", errors, "manifest.json")
    if manifest is not None and not isinstance(manifest, dict):
        errors.append(_issue("invalid_manifest", "manifest.json", "manifest must be a JSON object"))
        manifest = {}

    summary_path = path / "context" / "summary.md"
    if not summary_path.exists():
        errors.append(_issue("missing_summary", "context/summary.md", "context summary is required"))
    elif not summary_path.read_text().strip():
        errors.append(_issue("empty_summary", "context/summary.md", "context summary must be non-empty"))

    rounds_dir = path / "rounds"
    round_files = sorted(rounds_dir.glob("[0-9][0-9][0-9].json")) if rounds_dir.exists() else []
    partial_files = sorted(rounds_dir.glob("*.json.partial")) if rounds_dir.exists() else []
    if not round_files:
        errors.append(_issue("missing_rounds", "rounds", "at least one committed round is required"))

    round_results = []
    for round_file in round_files:
        round_result = validate_round_file(round_file)
        round_results.append(round_result)
        for issue in round_result["errors"]:
            nested = dict(issue)
            nested["path"] = f"{round_file.relative_to(path)}:{issue['path']}"
            errors.append(nested)
        warnings.extend(round_result["warnings"])

    status = manifest.get("status") if isinstance(manifest, dict) else None
    if status in COMPLETED_STATUSES:
        if partial_files:
            errors.append(
                _issue(
                    "stale_partial",
                    "rounds",
                    "completed discussions must not leave partial round files",
                    [str(p.relative_to(path)) for p in partial_files],
                )
            )

        tmp_dir = path / "tmp"
        if tmp_dir.exists() and any(tmp_dir.iterdir()):
            errors.append(_issue("leftover_tmp", "tmp", "completed discussions must not leave tmp files"))

        synthesis = path / "artifacts" / "synthesis.md"
        if not synthesis.exists():
            errors.append(
                _issue("missing_artifact", "artifacts/synthesis.md", "completed discussion requires synthesis.md")
            )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "discussionId": manifest.get("id") if isinstance(manifest, dict) else None,
            "status": status,
            "roundCount": len(round_files),
            "validatedRounds": sum(1 for result in round_results if result["ok"]),
        },
    }
