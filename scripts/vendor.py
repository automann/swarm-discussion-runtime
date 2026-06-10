#!/usr/bin/env python3
"""Vendor the runtime into a host-adapter repo with a pinned-SHA manifest.

Usage:
    python3 scripts/vendor.py vendor --dest <adapter>/vendor/swarm-runtime
    python3 scripts/vendor.py verify --dest <adapter>/vendor/swarm-runtime

`vendor` copies the adapter-facing runtime bundle and writes
`vendor-manifest.json` recording the runtime git SHA and a sha256 per file.
`verify` re-hashes the destination against its manifest so drift or local
edits fail loudly. Adapters must treat the vendored tree as read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "vendor-manifest.json"
BUNDLE = (
    "runtime/swarm_rt.py",
    "runtime/swarm",
    "schemas",
    "profiles",
    "protocol",
    "runtime-contract.json",
    "fixtures/e2e/minimal-v2",
)
EXCLUDED_DIR_NAMES = {"__pycache__", ".DS_Store"}


def _bundle_files() -> list[Path]:
    files: list[Path] = []
    for entry in BUNDLE:
        path = REPO_ROOT / entry
        if path.is_file():
            files.append(path)
            continue
        if not path.is_dir():
            raise SystemExit(f"bundle entry missing in runtime repo: {entry}")
        for child in sorted(path.rglob("*")):
            if child.is_file() and not any(part in EXCLUDED_DIR_NAMES for part in child.parts):
                files.append(child)
    return files


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def cmd_vendor(dest: Path) -> dict:
    if dest.exists():
        shutil.rmtree(dest)
    files = {}
    for source in _bundle_files():
        relative = source.relative_to(REPO_ROOT)
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files[str(relative)] = _sha256(target)
    manifest = {
        "schemaVersion": 1,
        "kind": "swarm.vendor_manifest",
        "runtimeSha": _runtime_sha(),
        "fileCount": len(files),
        "files": files,
    }
    (dest / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {"ok": True, "dest": str(dest), "runtimeSha": manifest["runtimeSha"], "fileCount": len(files)}


def cmd_verify(dest: Path) -> dict:
    manifest_path = dest / MANIFEST_NAME
    if not manifest_path.exists():
        return {"ok": False, "errors": [f"missing {MANIFEST_NAME} in {dest}"]}
    manifest = json.loads(manifest_path.read_text())
    errors: list[str] = []
    for relative, expected in sorted(manifest.get("files", {}).items()):
        path = dest / relative
        if not path.exists():
            errors.append(f"missing vendored file: {relative}")
            continue
        actual = _sha256(path)
        if actual != expected:
            errors.append(f"vendored file drifted: {relative}")
    extras = [
        str(path.relative_to(dest))
        for path in sorted(dest.rglob("*"))
        if path.is_file()
        and path.name != MANIFEST_NAME
        and not any(part in EXCLUDED_DIR_NAMES for part in path.parts)
        and str(path.relative_to(dest)) not in manifest.get("files", {})
    ]
    for extra in extras:
        errors.append(f"unmanifested file in vendored tree: {extra}")
    return {
        "ok": not errors,
        "errors": errors,
        "runtimeSha": manifest.get("runtimeSha"),
        "fileCount": len(manifest.get("files", {})),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vendor", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("vendor", "verify"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args(argv)
    result = cmd_vendor(args.dest) if args.command == "vendor" else cmd_verify(args.dest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
