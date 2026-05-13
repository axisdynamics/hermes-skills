---
name: vex-hermes-integration
description: Use when integrating axisdynamics/ai_cyber_range_project with Hermes/VEX. Recreates the safe local bridge that adds a stdlib VEX client, CyberRangeConfig.vex settings, CLI commands, post-run telemetry publishing, defensive task handoff, tests, docs, and verification without expanding cyber-range scope or external targets.
version: 1.1.0
author: Marco Torres Y. / AxisDynamics + Hermes VEX
license: MIT
metadata:
  hermes:
    tags: [axisdynamics, ai-cyber-range, vex, hermes, cyber-range, defensive-security, telemetry]
    related_skills: [hermes-agent, github-repo-management, hermes-agent-skill-authoring]
---

# AI Cyber Range → Hermes/VEX Integration

## Overview

This skill captures the exact workflow used to integrate `axisdynamics/ai_cyber_range_project` with the local Hermes/VEX framework.

The integration is intentionally defensive and safe-by-default. VEX is used only as a signed/handled message bus for run telemetry, compact findings, and optional defensive-review handoff. It must never become a remote-control channel, never authorize new targets, never change `allow_external_targets`, and never bypass the cyber range policy gates.

Use this when you need to recreate, audit, port, or finish the VEX bridge in:

```text
https://github.com/axisdynamics/ai_cyber_range_project
```

The proven local implementation added:

```text
src/cyber_range/agents/vex.py
src/cyber_range/config/schema.py        # VexConfig + CyberRangeConfig.vex
src/cyber_range/cli/main.py             # cyber-range vex status / publish-latest + post-run hook
examples/local.yaml                     # disabled-by-default vex: block
README.md                               # operator docs
tests/unit/test_vex_bridge.py           # fake VEX server tests
tasks/todo.md                           # verification log
```

## When to Use

Use this skill when the user asks to:

- Integrate `axisdynamics/ai_cyber_range_project` with Hermes/VEX.
- Recreate the local bridge in a fresh clone of the cyber range repo.
- Add `cyber-range vex status` and `cyber-range vex publish-latest`.
- Publish cyber range run summaries/findings to VEX topics.
- Add optional defensive VEX task handoff for persistent gaps.
- Verify that the integration stays local, safe, and non-offensive.
- Convert the local working patch into GitHub-ready code/docs/tests.

Do not use this skill to:

- Enable external targets.
- Relax or remove blocked techniques.
- Send raw evidence bodies over VEX.
- Run offensive actions from a VEX task.
- Modify live VEX runtime files unless explicitly requested.

## Safety Contract

Before editing code, state and preserve these invariants:

1. `engagement.allow_external_targets` remains false unless an authorized operator changes it outside this integration.
2. `PolicyEnforcer.check_scenario()` and existing policy gates remain the authority before simulation.
3. Destructive techniques remain blocked.
4. VEX bridge defaults to disabled.
5. VEX failures do not fail the primary cyber range run.
6. VEX publishes compact summaries and findings only, not raw evidence.
7. Optional VEX `/task` handoff is defensive-review-only and disabled by default.
8. Unit tests use a fake local HTTP server, not the live mesh.

## Repository Setup

Preferred local path for this user's GitHub projects:

```text
~/Documentos/Github/ai_cyber_range_project
```

If the repo is not present, obtain it from the official AxisDynamics GitHub repository using your normal reviewed clone workflow, then enter the project directory. If pytest/dev tooling is missing globally, create a local virtualenv and install the project dev extras using the repository's normal Python packaging workflow.

Use the venv commands for validation:

```bash
.venv/bin/python -m pytest tests/unit/ -q
.venv/bin/cyber-range validate-config --config examples/local.yaml
```

## Implementation Map

### 1. Add the VEX bridge module

Create:

```text
src/cyber_range/agents/vex.py
```

Required responsibilities:

- Define constants:
  - `DEFAULT_AGENT_NAME = "ai-cyber-range"`
  - `RUN_TOPIC = "axis/cyber-range/runs"`
  - `FINDINGS_TOPIC = "axis/cyber-range/findings"`
  - `GAPS_TOPIC = "axis/cyber-range/gaps"`
- Define `VexBridgeConfig` with safe defaults:
  - `enabled=False`
  - `agent_name="ai-cyber-range"`
  - `reply_to=None`
  - `timeout_s=5.0`
  - `publish_findings=True`
  - `task_handoff_enabled=False`
- Define `VexClient` using stdlib `urllib.request` only.
- Support only these HTTP surfaces:
  - `GET /health`
  - `GET /identity`
  - `POST /publish`
  - optional `POST /task`
- Add functions to build compact payloads:
  - `summarize_run_for_vex(...)`
  - `finding_event_payload(...)`
  - `publish_run_to_vex(...)`
  - `handoff_gap_tasks(...)`
- Ensure no method can execute shell commands or expand scanning scope.

Payload rules:

- Include run id, status, profile, counts, timestamps, and artifact references.
- Include finding id/title/severity/status and compact summaries.
- Avoid raw evidence bodies, secrets, long stack traces, local private topology, and full prompts.

### 2. Add VexConfig to the project schema

Edit:

```text
src/cyber_range/config/schema.py
```

Add a Pydantic model near the other config models:

```python
class VexConfig(BaseModel):
    """Optional VEX Constellation bridge settings.

    Disabled by default so cyber-range runs remain offline/deterministic unless
    an operator explicitly opts in. VEX is treated as a message bus only.
    """

    enabled: bool = Field(default=False)
    base_url: str = Field(default="<local-vex-url>")
    agent_name: str = Field(default="ai-cyber-range")
    reply_to: str | None = Field(default=None)
    timeout_s: float = Field(default=5.0, ge=0.1, le=60.0)
    publish_findings: bool = Field(default=True)
    task_handoff_enabled: bool = Field(default=False)

    @field_validator("base_url", "reply_to")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("VEX URLs must start with http:// or https://")
        return v.rstrip("/")
```

Then add this field to `CyberRangeConfig`:

```python
vex: VexConfig = Field(default_factory=VexConfig)
```

Use the real local VEX URL only in private/local config. Public skills and README examples should use `<local-vex-url>` placeholders.

### 3. Add CLI commands

Edit:

```text
src/cyber_range/cli/main.py
```

Add a `vex` group:

```python
@cli.group("vex")
def vex_group():
    """Hermes/VEX message-bus integration helpers."""
```

Add status command:

```bash
cyber-range vex status --base-url <local-vex-url>
```

Behavior:

1. Instantiate `VexClient(base_url)`.
2. Call `/health` and `/identity`.
3. Print JSON or a Rich table/panel with status, version, agent/hash/url.
4. Exit non-zero on connection/JSON failures.

Add publish-latest command:

```bash
cyber-range vex publish-latest --base-url <local-vex-url> [--project-root <repo>] [--no-findings]
```

Behavior:

1. Locate latest `artifacts/runs/<run-id>/summary.json`.
2. Load optional `findings.json`.
3. Publish run summary to `axis/cyber-range/runs`.
4. Publish findings to `axis/cyber-range/findings` unless disabled.
5. Handle missing artifacts cleanly with a clear error.

### 4. Add the post-run hook

In both supported run flows, after reports/artifacts are written and before the logger closes, call a fail-soft helper:

```python
_publish_to_vex_if_enabled(cfg, run_summary, findings, logger, out_dir)
```

Helper rules:

- Return immediately if `cfg.vex.enabled` is false.
- Convert `cfg.vex` into `VexBridgeConfig`.
- Publish summary/findings with `publish_run_to_vex(...)`.
- Write `vex_publish.json` beside the run output if useful.
- Catch exceptions and log a warning, not a fatal error.

### 5. Add disabled-by-default config example

Edit:

```text
examples/local.yaml
```

Add:

```yaml
# Optional Hermes/VEX integration. Disabled by default: VEX is a message bus
# only and never authorizes external targets or remote execution.
vex:
  enabled: false
  base_url: "<local-vex-url>"
  agent_name: "ai-cyber-range"
  publish_findings: true
  task_handoff_enabled: false
```

For the actual private/local repo, `<local-vex-url>` can be replaced with the running local VEX node. Do not put private LAN IPs in public docs.

### 6. Add unit tests with fake VEX

Create:

```text
tests/unit/test_vex_bridge.py
```

Use `ThreadingHTTPServer` with a local handler that implements:

```text
GET  /health
GET  /identity
POST /publish
POST /task
```

Minimum tests:

- `CyberRangeConfig().vex.enabled is False`.
- `CyberRangeConfig().engagement.allow_external_targets is False`.
- explicit VEX settings strip trailing slash.
- invalid URL schemes fail validation.
- status client calls health/identity.
- run publish sends a `RUN_TOPIC` event.
- findings publish can be disabled.
- handoff returns no tasks when disabled.
- enabled handoff uses task type `defensive_gap_review`.
- task description includes “Do not run offensive actions”.

## Documentation Updates

Update the cyber range `README.md` with:

- A short “Hermes/VEX integration” section.
- Safe activation block.
- New CLI commands.
- Safety boundaries.

Activation example for private/local operation:

```yaml
vex:
  enabled: true
  base_url: "<local-vex-url>"
  agent_name: "ai-cyber-range"
  publish_findings: true
  task_handoff_enabled: false
```

Operator commands:

```bash
cyber-range vex status --base-url <local-vex-url>
cyber-range vex publish-latest --base-url <local-vex-url>
cyber-range run --mode agent --config examples/local.yaml
```

Safety docs must say:

- VEX is a message bus only.
- VEX does not authorize targets.
- VEX does not execute remote commands.
- Raw evidence bodies are not published.
- Task handoff is disabled by default and defensive if enabled.

## Verification Commands

Run from the cyber range repo:

```bash
.venv/bin/python -m py_compile \
  src/cyber_range/agents/vex.py \
  src/cyber_range/config/schema.py \
  src/cyber_range/cli/main.py \
  tests/unit/test_vex_bridge.py

.venv/bin/python -m pytest tests/unit/ -q
.venv/bin/cyber-range validate-config --config examples/local.yaml
.venv/bin/cyber-range run --config examples/local.yaml --dry-run
.venv/bin/python -m ruff check src/cyber_range/agents/vex.py tests/unit/test_vex_bridge.py
```

If a local VEX node is running, smoke-test status:

```bash
.venv/bin/cyber-range vex status --base-url <local-vex-url>
```

For publish smoke, use synthetic temp artifacts only:

```bash
TMP=/tmp/ai-cyber-range-vex-smoke
mkdir -p "$TMP/artifacts/runs/RUN-SMOKE"
printf '{"run_id":"RUN-SMOKE","status":"success","findings_count":0}' > "$TMP/artifacts/runs/RUN-SMOKE/summary.json"
printf '[]' > "$TMP/artifacts/runs/RUN-SMOKE/findings.json"
.venv/bin/cyber-range vex publish-latest \
  --base-url <local-vex-url> \
  --project-root "$TMP" \
  --no-findings
```

Expected smoke result:

- `published: true`
- event id similar to `cyber-range-run-RUN-SMOKE`
- topic `axis/cyber-range/runs`

## Known Good Local Verification Results

The original local integration was verified with:

```text
py_compile: OK
pytest tests/unit/ -q: 122 passed
cyber-range validate-config --config examples/local.yaml: OK
cyber-range run --config examples/local.yaml --dry-run: OK
cyber-range vex status against local VEX v1.5.0: OK
cyber-range vex publish-latest with /tmp/ai-cyber-range-vex-smoke: OK
ruff check on new VEX bridge/test files: OK
```

## GitHub Promotion Checklist

Before pushing the cyber range integration or this skill to GitHub:

- [ ] `git diff --check` passes.
- [ ] No pasted tokens, API keys, or credentials.
- [ ] No private LAN IPs or local user paths in public docs.
- [ ] No raw evidence bodies in examples.
- [ ] VEX defaults are disabled.
- [ ] `allow_external_targets` remains untouched.
- [ ] Unit tests use fake VEX server.
- [ ] Live smoke uses synthetic temp artifacts only.
- [ ] Commit message is clear, e.g. `feat: add safe VEX bridge`.

## Common Pitfalls

1. **Publishing the generic bridge skill instead of this cyber range skill.** This skill is specifically for `axisdynamics/ai_cyber_range_project` and should mention the cyber range files, commands, topics, and verification results.

2. **Letting VEX mutate scope.** The bridge publishes telemetry; it does not approve external targets or bypass policy.

3. **Failing the run because VEX is down.** VEX publication is best-effort and should log warnings only.

4. **Sending raw evidence.** Keep raw artifacts local; publish compact summaries and hashes/IDs only.

5. **Using live VEX in unit tests.** Use a fake in-process HTTP server for deterministic tests.

6. **Forgetting the no-artifacts path.** `publish-latest` should clearly report that no `artifacts/runs` directory exists rather than crashing unclearly.

7. **Forgetting fresh installs.** If this skill was just pushed to a standalone skill repo, install it from the raw GitHub URL in a fresh Hermes session before relying on automatic skill loading.

## Install This Skill

From AxisDynamics skills repo:

```bash
hermes skills install https://raw.githubusercontent.com/axisdynamics/hermes-skills/main/vex-hermes-integration/SKILL.md
```
