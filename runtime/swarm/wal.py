"""Write-ahead-log helpers for round state."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from swarm.validation import ALLOWED_RELATIONS, validate_round_record

MESSAGE_ID = re.compile(r"^r(\d+)-msg-(\d{3})$")


def _issue(code: str, path: str, message: str, value: Any = None) -> dict[str, Any]:
    issue = {"code": code, "path": path, "message": message}
    if value is not None:
        issue["value"] = value
    return issue


def _round_paths(discussion_dir: Path, round_id: int) -> dict[str, Path]:
    rounds_dir = discussion_dir / "rounds"
    stem = f"{round_id:03d}"
    return {
        "rounds": rounds_dir,
        "partial": rounds_dir / f"{stem}.json.partial",
        "final": rounds_dir / f"{stem}.json",
        "tmp": rounds_dir / f"{stem}.json.tmp",
        "progress": discussion_dir / "progress.md",
        "events": discussion_dir / "events.jsonl",
    }


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _event_seq(events_path: Path) -> int:
    if not events_path.exists():
        return 1
    return sum(1 for line in events_path.read_text().splitlines() if line.strip()) + 1


def append_event(discussion_dir: Path, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    discussion_dir.mkdir(parents=True, exist_ok=True)
    events_path = discussion_dir / "events.jsonl"
    event = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seq": _event_seq(events_path),
        "type": event_type,
        "data": data,
    }
    with events_path.open("a") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def _load_state(discussion_dir: Path, round_id: int) -> tuple[dict[str, Any] | None, str | None]:
    paths = _round_paths(discussion_dir, round_id)
    if paths["partial"].exists():
        return _read_json(paths["partial"]), "partial"
    if paths["final"].exists():
        return _read_json(paths["final"]), "final"
    return None, None


def _empty_state(round_id: int, phase: str) -> dict[str, Any]:
    return {
        "roundId": round_id,
        "round": round_id,
        "phase": phase,
        "messages": [],
        "argumentGraph": [],
        "positionShifts": [],
        "personaContextLog": {},
    }


def _seqs_from_state(state: dict[str, Any], round_id: int) -> set[int]:
    seqs: set[int] = set()
    for message in state.get("messages") or []:
        if not isinstance(message, dict):
            continue
        match = MESSAGE_ID.match(str(message.get("id") or ""))
        if match and int(match.group(1)) == round_id:
            seqs.add(int(match.group(2)))
    return seqs


def _seqs_on_disk(discussion_dir: Path, round_id: int) -> set[int]:
    paths = _round_paths(discussion_dir, round_id)
    seqs: set[int] = set()
    for path in (paths["partial"], paths["final"]):
        if path.exists():
            seqs.update(_seqs_from_state(_read_json(path), round_id))
    return seqs


def max_seq(discussion_dir: Path, round_id: int) -> int:
    seqs = _seqs_on_disk(discussion_dir, round_id)
    return max(seqs) if seqs else 0


def next_message_id(discussion_dir: Path, round_id: int) -> str:
    return f"r{round_id}-msg-{max_seq(discussion_dir, round_id) + 1:03d}"


def _max_message_id(discussion_dir: Path, round_id: int) -> str | None:
    seq = max_seq(discussion_dir, round_id)
    return f"r{round_id}-msg-{seq:03d}" if seq else None


def _validate_message_payload(
    state: dict[str, Any], message: dict[str, Any], round_id: int
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if "id" in message:
        errors.append(_issue("message_id_must_be_minted", "message.id", "append-message mints message ids"))
    sender = message.get("from")
    if not isinstance(sender, str) or not sender.strip():
        errors.append(_issue("invalid_sender", "message.from", "message sender must be a non-empty string"))
    kind = message.get("type")
    if not isinstance(kind, str) or not kind.strip():
        errors.append(_issue("invalid_message_type", "message.type", "message type must be a non-empty string"))
    if "content" not in message:
        errors.append(_issue("missing_content", "message.content", "message content is required"))

    present = {
        item.get("id")
        for item in state.get("messages", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    references = message.get("references", [])
    if references is None:
        references = []
    if not isinstance(references, list):
        errors.append(_issue("invalid_references", "message.references", "references must be a list"))
        return errors
    for index, ref in enumerate(references):
        path = f"message.references[{index}]"
        if not isinstance(ref, dict):
            errors.append(_issue("invalid_reference", path, "reference must be an object"))
            continue
        relation = ref.get("relation")
        if relation not in ALLOWED_RELATIONS:
            errors.append(
                _issue(
                    "invalid_relation",
                    f"{path}.relation",
                    "relation must be one of counters, extends, questions, supports",
                    relation,
                )
            )
        target_id = ref.get("targetId")
        if target_id not in present:
            errors.append(
                _issue(
                    "unresolved_reference",
                    f"{path}.targetId",
                    "reference target is not in WAL state",
                    target_id,
                )
            )
        match = MESSAGE_ID.match(str(target_id or ""))
        if match and int(match.group(1)) != round_id:
            errors.append(
                _issue(
                    "cross_round_reference",
                    f"{path}.targetId",
                    "append-message references must stay in round",
                    target_id,
                )
            )
    return errors


def checkpoint(discussion_dir: Path, round_id: int, phase: str, state: dict[str, Any]) -> dict[str, Any]:
    paths = _round_paths(discussion_dir, round_id)
    payload = dict(state)
    payload["roundId"] = int(payload.get("roundId", round_id))
    payload["round"] = int(round_id)
    payload["phase"] = phase
    paths["rounds"].mkdir(parents=True, exist_ok=True)

    with paths["tmp"].open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(paths["tmp"], paths["partial"])
    _fsync_dir(paths["rounds"])

    message_ids = [
        message.get("id")
        for message in payload.get("messages", [])
        if isinstance(message, dict) and isinstance(message.get("id"), str)
    ]
    if message_ids:
        progress_seen = paths["progress"].read_text() if paths["progress"].exists() else ""
        with paths["progress"].open("a") as progress:
            for message_id in message_ids:
                if message_id not in progress_seen:
                    progress.write(f"{message_id} emitted\n")
            progress.flush()
            os.fsync(progress.fileno())

    event = append_event(
        discussion_dir,
        "checkpoint_written",
        {
            "round": round_id,
            "phase": phase,
            "messageCount": len(payload.get("messages", []) or []),
            "path": str(paths["partial"]),
        },
    )
    return {
        "ok": True,
        "errors": [],
        "round": round_id,
        "phase": phase,
        "path": str(paths["partial"]),
        "event": event,
    }


def append_message(
    discussion_dir: Path, round_id: int, phase: str, message: dict[str, Any]
) -> dict[str, Any]:
    state, source = _load_state(discussion_dir, round_id)
    if source == "final":
        return {
            "ok": False,
            "errors": [_issue("round_finalized", "round", "cannot append to a finalized round", round_id)],
        }
    if state is None:
        state = _empty_state(round_id, phase)
    if not isinstance(message, dict):
        return {
            "ok": False,
            "errors": [_issue("invalid_message", "message", "message must be a JSON object")],
        }

    errors = _validate_message_payload(state, message, round_id)
    if errors:
        return {"ok": False, "errors": errors}

    minted_id = next_message_id(discussion_dir, round_id)
    new_message = dict(message)
    new_message["id"] = minted_id
    new_message.setdefault("references", [])
    state.setdefault("messages", []).append(new_message)
    graph = state.setdefault("argumentGraph", [])
    for ref in new_message.get("references", []):
        graph.append({"from": minted_id, "to": ref["targetId"], "relation": ref["relation"]})

    checkpoint_result = checkpoint(discussion_dir, round_id, phase, state)
    event = append_event(
        discussion_dir,
        "message_appended",
        {"round": round_id, "phase": phase, "messageId": minted_id, "from": new_message.get("from")},
    )
    return {
        "ok": True,
        "errors": [],
        "message": new_message,
        "checkpoint": checkpoint_result,
        "event": event,
    }


def finalize_round(discussion_dir: Path, round_id: int, final_state: dict[str, Any]) -> dict[str, Any]:
    validation = validate_round_record(final_state)
    if not validation["ok"]:
        return {"ok": False, "errors": validation["errors"], "warnings": validation["warnings"]}

    checkpoint_result = checkpoint(discussion_dir, round_id, "complete", final_state)
    paths = _round_paths(discussion_dir, round_id)
    if not paths["partial"].exists():
        return {
            "ok": False,
            "errors": [_issue("missing_partial", str(paths["partial"]), "final checkpoint did not produce partial")],
        }
    os.replace(paths["partial"], paths["final"])
    _fsync_dir(paths["rounds"])
    event = append_event(
        discussion_dir,
        "round_finalized",
        {
            "round": round_id,
            "messageCount": len(final_state.get("messages", []) or []),
            "path": str(paths["final"]),
        },
    )
    return {
        "ok": True,
        "errors": [],
        "warnings": validation["warnings"],
        "round": round_id,
        "path": str(paths["final"]),
        "checkpoint": checkpoint_result,
        "event": event,
    }


def _highest_round(paths: list[Path], suffix: str) -> int | None:
    rounds = []
    for path in paths:
        name = path.name.removesuffix(suffix)
        if name.isdigit():
            rounds.append(int(name))
    return max(rounds) if rounds else None


def resume_plan(discussion_dir: Path) -> dict[str, Any]:
    rounds_dir = discussion_dir / "rounds"
    if not rounds_dir.exists():
        return {"ok": True, "source": "none", "nextAction": "start_round", "round": None}

    partial_round = _highest_round(list(rounds_dir.glob("*.json.partial")), ".json.partial")
    final_round = _highest_round(list(rounds_dir.glob("*.json")), ".json")
    candidates = [item for item in (partial_round, final_round) if item is not None]
    if not candidates:
        return {"ok": True, "source": "none", "nextAction": "start_round", "round": None}

    top = max(candidates)
    paths = _round_paths(discussion_dir, top)
    if paths["partial"].exists():
        state = _read_json(paths["partial"])
        source = "partial"
        phase = state.get("phase")
        action = "resume_round"
        state_path = paths["partial"]
    else:
        state = _read_json(paths["final"])
        source = "final"
        phase = "complete"
        action = "start_next_round"
        state_path = paths["final"]

    return {
        "ok": True,
        "source": source,
        "round": top,
        "phase": phase,
        "maxId": _max_message_id(discussion_dir, top),
        "nextMessageId": next_message_id(discussion_dir, top),
        "statePath": str(state_path),
        "messageCount": len(state.get("messages", []) or []),
        "nextAction": action,
    }
