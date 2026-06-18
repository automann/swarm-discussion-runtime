# Codex Review Runtime Fix Handoff - 2026-06-19

## 背景和 repo 关系

目标 repo: `/Users/syfq/dev/harness/swarm-discussion-runtime`

相关 Codex repo: `/Users/syfq/dev/harness/swarm-discussion-codex`

父线程在 `swarm-discussion-codex` commit `7d72fcd` 的 Claude review 后做了诊断。需要交给 runtime repo 处理的问题属于 runtime source of truth，不应在 Codex vendored copy 里直接修。

关系边界：

- `swarm-discussion-runtime` 是 host-agnostic runtime source of truth。
- `swarm-discussion-codex` vendored 了 runtime 到 `vendor/swarm-runtime`。
- Codex vendored copy 当前通过 runtime repo 的 `scripts/vendor.py verify` 校验，说明 vendored tree 没有本地漂移；问题应先在 runtime repo 修，再由 Codex repo 重新 vendor。
- 只读确认时 runtime repo 当前有未提交修改：`M docs/CODEX-ADAPTER-HANDOFF.md`。请不要无意覆盖用户已有改动。

## 建议技能 / 工作方式

- 使用诊断优先的流程：先复现、定位 source-of-truth，再修复并补 regression tests。
- 保持 runtime repo 为唯一修复源头；Codex vendored copy 只能通过 re-vendor 同步。
- 修复完成前后都记录命令输出，尤其是新增 regression test 的失败/通过行为。

## Runtime 侧问题 1: fixture artifacts 不一致但 gate 仍通过

观察到 runtime repo 和 Codex vendored copy 中同一 fixture 都存在不一致。

Runtime 文件：

- `/Users/syfq/dev/harness/swarm-discussion-runtime/fixtures/e2e/minimal-v2/artifacts/trace.json`
- `/Users/syfq/dev/harness/swarm-discussion-runtime/fixtures/e2e/minimal-v2/artifacts/evidence.json`

Codex vendored copy 对应文件：

- `/Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime/fixtures/e2e/minimal-v2/artifacts/trace.json`
- `/Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime/fixtures/e2e/minimal-v2/artifacts/evidence.json`

存盘值：

- `trace.json`: `.artifacts.totalBytes == 22714`
- `evidence.json`: `.artifacts.totalBytes == 22916`
- `evidence.json`: `.metrics.artifactTotalBytes == 22916`

但 runtime 的 gate 仍通过：

- `adapter-smoke` 通过
- `validate-loop` 通过
- vendored copy 内同样通过

额外只读确认：当前重新调用 `build_trace()` / `build_evidence()` 时，按当前目录文件重新计算出的 total bytes 是 `23051`。这说明 `artifacts.totalBytes` 很可能把 `artifacts/trace.json` 和 `artifacts/evidence.json` 这些自引用/互引用 projection 文件也纳入了字节总量，导致生成顺序或已有静态文件大小会改变总和。

当前 validation 只检查 evidence 的形状和必需 key，没有重算并比对静态 `trace.json` / `evidence.json` 的稳定内容或一致字段。

相关代码入口：

- `runtime/swarm/audit.py`
  - `_artifact_paths()`
  - `_artifact_total_bytes()`
  - `build_trace()`
  - `build_evidence()`
- `runtime/swarm/loop.py`
  - `validate_minimal_loop()`
  - 当前只检查静态 `artifacts/evidence.json` 的 kind 和 required keys
- `runtime/swarm/smoke.py`
  - `adapter_smoke()` 调 `build_trace()` / `build_evidence()` / `validate_minimal_loop()`，但未暴露该不一致

## Runtime 侧问题 2: command surface drift

`runtime/swarm/__init__.py` 的 `planned_commands()` 包含 `persona-plan`。

但当前 CLI parser 和 runtime contract 不包含实际 `persona-plan` 命令：

- `runtime/swarm_rt.py build_parser()` 没有 `sub.add_parser("persona-plan", ...)`
- `runtime-contract.json.commands` 没有 `persona-plan`
- `python3 runtime/swarm_rt.py persona-plan --help` 返回 invalid choice
- `runtime/swarm/contract.py validate_runtime_contract()` 只检查 contract 里的 command 是否在 planned surface 中，不检查 planned surface 是否全部由 parser/contract 覆盖，所以 drift 没有失败

需要收敛 source-of-truth，或新增 drift check，确保 planned/parser/contract 三者不会再次偏离。

## 复现命令

### Runtime repo 里复现 fixture totalBytes 不一致

```bash
cd /Users/syfq/dev/harness/swarm-discussion-runtime

jq '{trace_totalBytes:.artifacts.totalBytes}' \
  fixtures/e2e/minimal-v2/artifacts/trace.json

jq '{evidence_totalBytes:.artifacts.totalBytes, metrics_artifactTotalBytes:.metrics.artifactTotalBytes}' \
  fixtures/e2e/minimal-v2/artifacts/evidence.json
```

预期观察：

```json
{"trace_totalBytes": 22714}
{"evidence_totalBytes": 22916, "metrics_artifactTotalBytes": 22916}
```

### Runtime repo 里确认 gate 仍绿

```bash
cd /Users/syfq/dev/harness/swarm-discussion-runtime

PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py runtime-contract --full
PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py adapter-smoke --dir fixtures/e2e/minimal-v2
PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py validate-loop fixtures/e2e/minimal-v2
```

只读诊断时三条均返回 `ok: true`。

### Runtime repo 里复现当前重算值不等于存盘值

```bash
cd /Users/syfq/dev/harness/swarm-discussion-runtime

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=runtime python3 - <<'PY'
from pathlib import Path
from swarm.audit import build_trace, build_evidence

p = Path("fixtures/e2e/minimal-v2")
trace = build_trace(p)
evidence = build_evidence(p)
print({
    "computed_trace_totalBytes": trace["artifacts"]["totalBytes"],
    "computed_evidence_totalBytes": evidence["artifacts"]["totalBytes"],
    "computed_metric_artifactTotalBytes": evidence["metrics"]["artifactTotalBytes"],
})
PY
```

只读诊断时输出为 `23051`。

### Codex vendored copy 里观察同一问题

```bash
cd /Users/syfq/dev/harness/swarm-discussion-codex

jq '{trace_totalBytes:.artifacts.totalBytes}' \
  vendor/swarm-runtime/fixtures/e2e/minimal-v2/artifacts/trace.json

jq '{evidence_totalBytes:.artifacts.totalBytes, metrics_artifactTotalBytes:.metrics.artifactTotalBytes}' \
  vendor/swarm-runtime/fixtures/e2e/minimal-v2/artifacts/evidence.json
```

也观察到 `22714` vs `22916`。

可从 vendored runtime 根目录运行：

```bash
cd /Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime

PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py adapter-smoke --dir fixtures/e2e/minimal-v2
PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py validate-loop fixtures/e2e/minimal-v2
```

只读诊断时两条也均返回 `ok: true`。

### 查看 command surface drift

```bash
cd /Users/syfq/dev/harness/swarm-discussion-runtime

PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py planned-commands
PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py persona-plan --help

jq -r '.commands | keys[]' runtime-contract.json

rg -n "planned_commands|persona-plan|runtime-contract|adapter-smoke|validate-loop|add_parser|REQUIRED_PLUGIN_COMMANDS" \
  runtime/swarm/__init__.py runtime/swarm_rt.py runtime/swarm/contract.py runtime-contract.json tests
```

只读诊断时：

- `planned-commands` 输出包含 `persona-plan`
- `persona-plan --help` 失败：invalid choice
- `runtime-contract.json.commands` 不含 `persona-plan`

### Vendor 校验现状

从 runtime repo 运行：

```bash
cd /Users/syfq/dev/harness/swarm-discussion-runtime

PYTHONDONTWRITEBYTECODE=1 python3 scripts/vendor.py verify \
  --dest /Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime
```

只读诊断时返回：

```json
{"ok": true, "fileCount": 54, "runtimeSha": "7b02561fb245a99ca91f9744fa287bd4487260f1"}
```

## 修复建议

优先在 `/Users/syfq/dev/harness/swarm-discussion-runtime` 修，不要直接改 `/Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime`。

### 1. 修正 artifact total bytes 的 source-of-truth

选择一种稳定定义，例如：

- `_artifact_total_bytes()` 排除 `artifacts/trace.json` 和 `artifacts/evidence.json` 这类 audit projection 自身。
- 或改成只统计非派生输入 artifact。
- 或引入明确的 stable artifact manifest / digest 语义，避免自引用 total。

修复目标：trace/evidence 生成结果不再依赖已有 trace/evidence 文件大小。随后重新生成/更新 `fixtures/e2e/minimal-v2/artifacts/trace.json` 和 `evidence.json`，让两者一致。

### 2. 加 regression test

`validate-loop` 应能发现静态 `trace.json` / `evidence.json` 与 runtime 重建结果的不一致。至少要比对关键稳定字段：

- `artifacts.totalBytes`
- `metrics.artifactTotalBytes`
- `discussion`
- `outcome`
- `trace.health`
- `trace.nextAction`

新测试应覆盖当前这种 `trace.totalBytes != evidence.totalBytes` 但 gate 误通过的情况。

现有测试缺口：

- `tests/test_phase4_trace_evidence.py` 只断言 `artifactTotalBytes > 0`，不够。
- `tests/test_e2e_minimal_loop.py` 可以补 fixture 静态 artifact 一致性测试。

### 3. 收敛 command source-of-truth

可选路径：

- 实现/声明 `persona-plan` 并加入 parser + contract + tests。
- 或从 `planned_commands()` 移除 `persona-plan`，如果它不是当前稳定/计划命令。

更重要的是新增 drift check：planned commands、argparse parser choices、`runtime-contract.json.commands` 至少要有明确规则。

建议在 `tests/test_runtime_contract.py` 或 `tests/test_skeleton_contract.py` 增加检查，防止 planned 里出现 parser 不支持的命令，或 contract stable commands 与 parser 脱节。

### 4. 修完 runtime 后再 re-vendor

修复完成后，再让 Codex repo 重新 vendor：

```bash
cd /Users/syfq/dev/harness/swarm-discussion-runtime

PYTHONDONTWRITEBYTECODE=1 python3 scripts/vendor.py vendor \
  --dest /Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime

PYTHONDONTWRITEBYTECODE=1 python3 scripts/vendor.py verify \
  --dest /Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime
```

不要在 vendored copy 内手工修 fixture。

## Acceptance commands

建议 Claude Code 修复后至少报告以下命令和结果：

```bash
cd /Users/syfq/dev/harness/swarm-discussion-runtime

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest
PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py runtime-contract --full
PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py adapter-smoke --dir fixtures/e2e/minimal-v2
PYTHONDONTWRITEBYTECODE=1 python3 runtime/swarm_rt.py validate-loop fixtures/e2e/minimal-v2
```

如果同步到 Codex vendored copy：

```bash
cd /Users/syfq/dev/harness/swarm-discussion-runtime

PYTHONDONTWRITEBYTECODE=1 python3 scripts/vendor.py vendor \
  --dest /Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime

PYTHONDONTWRITEBYTECODE=1 python3 scripts/vendor.py verify \
  --dest /Users/syfq/dev/harness/swarm-discussion-codex/vendor/swarm-runtime
```

还需要显式报告新增的 drift/consistency regression test 名称，以及它们在修复前会失败、修复后会通过的行为。

## 边界

不要处理这些问题，它们属于 `swarm-discussion-codex` row 1 hotfix，不属于本 runtime handoff：

- Codex wrapper explicit runtime fallback
- top-level traceback
- hostDiagnostics

不要编辑 Claude adapter 或 Codex adapter 文件。runtime 侧只处理 host-agnostic runtime、fixture、contract、validation、tests，以及必要的 vendor script/contract source-of-truth。

## 给 Claude Code 的请求

请在 `/Users/syfq/dev/harness/swarm-discussion-runtime` 中诊断并修复上述两个 runtime 问题：

1. `minimal-v2` fixture 的 `trace.json` / `evidence.json` artifact total bytes 不一致，但 `adapter-smoke` / `validate-loop` 未捕获。
2. `planned_commands()`、CLI parser、`runtime-contract.json` 的 command surface drift，尤其是 `persona-plan`。

请完成修复、添加 regression tests、运行 acceptance commands，并在回复中报告：

- changed files
- 关键实现选择
- 新增/修改的测试
- 实际运行过的 commands 和结果
- 是否需要 Codex repo re-vendor，以及 re-vendor 后的 verify 结果
