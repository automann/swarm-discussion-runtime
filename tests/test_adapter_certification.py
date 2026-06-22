"""Pin the vendoring contract and adapter certification kit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "scripts" / "vendor.py"
CERTIFY = ROOT / "conformance" / "certify_adapter.py"
FIXTURE = ROOT / "fixtures" / "e2e" / "minimal-v2"


def run_json(*args: str) -> tuple[dict, int]:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return json.loads(completed.stdout), completed.returncode


def vendor_to(dest: Path) -> dict:
    payload, returncode = run_json(str(VENDOR), "vendor", "--dest", str(dest))
    assert returncode == 0, payload
    return payload


def test_vendor_produces_pinned_manifest_and_runnable_bundle(tmp_path: Path) -> None:
    dest = tmp_path / "vendor" / "swarm-runtime"
    result = vendor_to(dest)

    manifest = json.loads((dest / "vendor-manifest.json").read_text())
    assert manifest["kind"] == "swarm.vendor_manifest"
    assert manifest["fileCount"] == result["fileCount"] > 0
    assert manifest["runtimeSha"]
    for required in (
        "runtime/swarm_rt.py",
        "runtime/swarm/wal.py",
        "runtime-contract.json",
        "protocol/PROTOCOL.md",
        "protocol/templates/context-generator.md",
        "schemas/evidence.schema.json",
        "profiles/expert-basic.json",
        "fixtures/e2e/minimal-v2/manifest.json",
    ):
        assert required in manifest["files"], required

    health = subprocess.run(
        [sys.executable, str(dest / "runtime" / "swarm_rt.py"), "health"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert health.returncode == 0, health.stderr


def test_vendor_verify_detects_drift_and_unmanifested_files(tmp_path: Path) -> None:
    dest = tmp_path / "vendor" / "swarm-runtime"
    vendor_to(dest)

    payload, returncode = run_json(str(VENDOR), "verify", "--dest", str(dest))
    assert returncode == 0 and payload["ok"] is True

    with (dest / "runtime" / "swarm" / "wal.py").open("a") as handle:
        handle.write("# local edit\n")
    (dest / "runtime" / "swarm" / "rogue.py").write_text("pass\n")

    payload, returncode = run_json(str(VENDOR), "verify", "--dest", str(dest))
    assert returncode == 1 and payload["ok"] is False
    joined = " ".join(payload["errors"])
    assert "drifted" in joined
    assert "unmanifested" in joined


def test_certify_adapter_passes_on_complete_fixture_with_vendored_runtime(tmp_path: Path) -> None:
    dest = tmp_path / "vendor" / "swarm-runtime"
    vendor_to(dest)

    payload, returncode = run_json(
        str(CERTIFY),
        "--discussion",
        str(FIXTURE),
        "--vendored",
        str(dest),
        "--runtime",
        str(dest / "runtime" / "swarm_rt.py"),
    )

    assert returncode == 0, payload
    assert payload["certified"] is True
    names = [check["name"] for check in payload["checks"]]
    assert names == [
        "runtime-contract",
        "vendor-manifest",
        "adapter-smoke",
        "validate-loop",
        "validate-discussion",
    ]


def test_certify_adapter_fails_on_broken_discussion(tmp_path: Path) -> None:
    import shutil

    discussion = tmp_path / "broken"
    shutil.copytree(FIXTURE, discussion)
    (discussion / "transport" / "r001" / "response" / "collect-result.json").write_text("{}")

    payload, returncode = run_json(str(CERTIFY), "--discussion", str(discussion))

    assert returncode == 1
    assert payload["certified"] is False
    failed = {check["name"] for check in payload["checks"] if not check["passed"]}
    assert "adapter-smoke" in failed


def test_certify_require_stress_inert_on_no_policy_fixture() -> None:
    # minimal-v2 declares no stressPolicy -> off -> --require-stress is inert and threads
    # through certify without breaking certification (plan 009 step 5).
    payload, returncode = run_json(str(CERTIFY), "--discussion", str(FIXTURE), "--require-stress")
    assert returncode == 0, payload
    assert payload["certified"] is True
    assert payload["requireStress"] is True


def test_certify_require_stress_fails_when_policy_unsatisfied(tmp_path: Path) -> None:
    import shutil

    discussion = tmp_path / "stressreq"
    shutil.copytree(FIXTURE, discussion)
    manifest = json.loads((discussion / "manifest.json").read_text())
    manifest["stressPolicy"] = "required"  # minimal-v2 ran no stress pass
    (discussion / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    # regenerate trace/evidence so the manifest byte change doesn't trip the stale check
    rt = str(ROOT / "runtime" / "swarm_rt.py")
    for command in ("trace", "evidence"):
        run_json(rt, command, "--dir", str(discussion), "--output", str(discussion / "artifacts" / f"{command}.json"))

    base, base_rc = run_json(str(CERTIFY), "--discussion", str(discussion))
    assert base_rc == 0 and base["certified"] is True, base  # gate inert without the flag

    payload, returncode = run_json(str(CERTIFY), "--discussion", str(discussion), "--require-stress")
    assert returncode == 1 and payload["certified"] is False
    assert payload["requireStress"] is True
    loop = next(check for check in payload["checks"] if check["name"] == "validate-loop")
    assert any(error["code"] == "stress_required_not_triggered" for error in loop["errors"])
