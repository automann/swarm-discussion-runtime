#!/usr/bin/env python3
"""Certify a host adapter against the runtime integration gates.

Usage:
    python3 conformance/certify_adapter.py \
        --discussion <adapter-produced discussion dir> \
        [--vendored <adapter vendor dir with vendor-manifest.json>] \
        [--runtime <path to swarm_rt.py>]

Certification checks, in order:
  1. runtime-contract validates (the runtime the adapter ships is contract-true)
  2. vendor manifest verifies, when --vendored is given (no drift, no local edits)
  3. adapter-smoke passes on the discussion dir (host-step thinness, transport
     replay, trace/evidence/capability summaries)
  4. validate-loop passes on the discussion dir (complete artifact loop,
     schema-conformant evidence)
  5. validate-discussion passes (directory-level artifact hygiene)

The discussion dir must be a REAL discussion driven on the host through the
adapter, not the bundled minimal-v2 fixture; the fixture proves the runtime,
certification proves the adapter. Emits a JSON verdict; exit 0 only when every
check passes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = REPO_ROOT / "runtime" / "swarm_rt.py"
VENDOR_SCRIPT = REPO_ROOT / "scripts" / "vendor.py"


def _run_json(command: list[str]) -> tuple[dict, int]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "errors": [{"code": "non_json_output", "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]}]}
    return payload, completed.returncode


def certify(discussion: Path, runtime: Path, vendored: Path | None, require_projection: bool = False) -> dict:
    checks: list[dict] = []

    def record(name: str, payload: dict, returncode: int) -> bool:
        passed = returncode == 0 and bool(payload.get("ok"))
        checks.append(
            {
                "name": name,
                "passed": passed,
                "errors": payload.get("errors", []) if not passed else [],
            }
        )
        return passed

    contract, code = _run_json([sys.executable, str(runtime), "runtime-contract"])
    record("runtime-contract", contract, code)

    if vendored is not None:
        verify, code = _run_json([sys.executable, str(VENDOR_SCRIPT), "verify", "--dest", str(vendored)])
        verify_errors = verify.get("errors", [])
        checks.append(
            {
                "name": "vendor-manifest",
                "passed": code == 0 and bool(verify.get("ok")),
                "errors": verify_errors if verify_errors else [],
                "runtimeSha": verify.get("runtimeSha"),
            }
        )

    smoke, code = _run_json([sys.executable, str(runtime), "adapter-smoke", "--dir", str(discussion)])
    record("adapter-smoke", smoke, code)

    loop_command = [sys.executable, str(runtime), "validate-loop", str(discussion)]
    if require_projection:
        loop_command.append("--require-projection")
    loop, code = _run_json(loop_command)
    record("validate-loop", loop, code)

    validation, code = _run_json([sys.executable, str(runtime), "validate-discussion", str(discussion)])
    record("validate-discussion", validation, code)

    certified = all(check["passed"] for check in checks)
    return {
        "ok": certified,
        "certified": certified,
        "discussionDir": str(discussion),
        "runtime": str(runtime),
        "requireProjection": require_projection,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="certify-adapter", description=__doc__)
    parser.add_argument("--discussion", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--vendored", type=Path)
    parser.add_argument(
        "--require-projection",
        action="store_true",
        help="v0.3.0 release mode: require a projected discussion with consistent provenance (ADR 0001 D4)",
    )
    args = parser.parse_args(argv)
    result = certify(args.discussion, args.runtime, args.vendored, require_projection=args.require_projection)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
