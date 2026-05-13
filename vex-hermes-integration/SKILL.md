---
name: vex-hermes-integration
description: Use when integrating another Hermes instance, Hermes-adjacent app, plugin, or external repository with a VEX-style Hermes message bus. Build safe outbound telemetry bridges, CLI status/publish commands, optional defensive task handoff, fake-server tests, and live smoke checks without expanding operational scope.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [vex, hermes, integration, message-bus, plugins, cli, safety]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, github-repo-management]
---

# VEX / Hermes Integration

## Overview

Use this skill to integrate another Hermes instance, Hermes plugin, CLI application, or external repository with a VEX-style Hermes message bus.

Core principle: VEX is a message bus and shared operational fabric, not a remote-control bypass. A safe integration publishes compact telemetry, receives bounded defensive-review tasks, and verifies connectivity through stable HTTP endpoints. It must never expand the host application's scope, bypass policy gates, enable external targets, run offensive actions, or execute remote instructions just because a peer asked.

Default to local, explicit, and fail-soft behavior. A local development VEX node normally uses a loopback URL such as:

```bash
<local-vex-url>
```

For multi-node tests, use routable placeholders in docs and committed templates:

```text
<this-node-vex-url>
<peer-vex-url>
```

Do not publish private LAN IPs, local usernames, machine-specific paths, secrets, or runtime state in public examples.

## When to Use

Use when the user asks to:

- Integrate another Hermes node with VEX or a VEX-like bus.
- Connect an app, repo, or plugin to Hermes/VEX.
- Add VEX telemetry to a CLI project.
- Publish run summaries, findings, reports, health, or status through `/publish`.
- Add optional VEX task handoff for defensive review or coordination.
- Make another agent visible in the constellation without granting unsafe autonomy.
- Replicate a safe app-to-VEX bridge in a new repository.

Do not use for:

- Updating the VEX plugin/runtime itself. Use the relevant Hermes plugin workflow from `hermes-agent`.
- Adding heavy LLM work inside HTTP request handlers.
- Peer-to-peer remote shell execution.
- Enabling destructive or external-target behavior.
- Publishing secrets, raw evidence bodies, tokens, full prompts, or private runtime state.

## Safe Integration Contract

Every integration should explicitly preserve these invariants:

1. Existing application policy gates remain authoritative.
2. VEX config cannot expand scope, targets, or permissions.
3. Defaults keep the bridge disabled unless the operator opts in.
4. VEX failure is fail-soft: the app logs a warning but the primary workflow continues.
5. Payloads are compact and sanitized.
6. Task handoff is opt-in and defensive by wording and metadata.
7. Tests use fake/in-process VEX servers by default.
8. Live smoke tests use synthetic or temporary artifacts only.

## Stable HTTP Surfaces

Use only these stable endpoints for most integrations:

```text
GET  /health       liveness and version
GET  /identity     node identity, role/hash/url/public keys
POST /publish      topic event publication
POST /task         optional fire-and-forget task handoff
GET  /tasks        optional inspection
GET  /network-map  optional mesh inspection if available
```

Minimum client behavior:

- Standard-library HTTP (`urllib.request`) is enough unless the project already uses `requests` or `httpx`.
- Set a short timeout, usually 3-5 seconds.
- JSON-decode defensively.
- Raise or return explicit errors for connection failures and invalid JSON.
- Do not retry indefinitely.

## Recommended Config Shape

Add a small config section with safe defaults:

```yaml
vex:
  enabled: false
  base_url: "<local-vex-url>"
  agent_name: "<app-or-agent-name>"
  reply_to: null
  timeout_s: 5.0
  publish_findings: true
  task_handoff_enabled: false
```

Validation rules:

- `base_url` and `reply_to`, if present, must start with `http://` or `https://`.
- Strip trailing slashes.
- Keep `task_handoff_enabled: false` by default.
- Do not let `vex.enabled` mutate unrelated safety config.

## Event Topic Design

Use product/domain-namespaced topics:

```text
axis/<product>/runs
axis/<product>/findings
axis/<product>/gaps
axis/<product>/health
vex/agents/<agent-id>/status
```

Good event payloads include:

- schema version, e.g. `axis.cyber_range.run.v1`
- stable IDs: `run_id`, `finding_id`, `task_id`
- status and timestamps
- counts and percentages
- severity and detection status
- SHA-256 hashes or artifact IDs
- short defensive summary

Avoid:

- raw evidence bodies
- secrets/API keys/tokens
- full prompts or model traces
- local absolute paths in public docs
- private IP topology in public examples
- customer data

## Minimal Python Client Template

Use or adapt this when a repo does not already have a VEX client:

```python
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VexBridgeConfig:
    enabled: bool = False
    base_url: str = "<local-vex-url>"
    agent_name: str = "my-app"
    reply_to: str | None = None
    timeout_s: float = 5.0
    publish_findings: bool = True
    task_handoff_enabled: bool = False


class VexBridgeError(RuntimeError):
    pass


class VexClient:
    def __init__(self, base_url: str = "<local-vex-url>", timeout_s: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def get_json(self, path: str) -> dict[str, Any]:
        req = urllib.request.Request(self.base_url + path, method="GET")
        return self._open_json(req)

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "vex-bridge/1.0"},
        )
        return self._open_json(req)

    def _open_json(self, req: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw) if raw.strip() else {"status": resp.status}
                return data if isinstance(data, dict) else {"data": data}
        except (urllib.error.URLError, TimeoutError) as exc:
            raise VexBridgeError(f"VEX request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise VexBridgeError(f"VEX returned invalid JSON: {exc}") from exc

    def health(self) -> dict[str, Any]:
        return self.get_json("/health")

    def identity(self) -> dict[str, Any]:
        return self.get_json("/identity")

    def publish(
        self,
        topic: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
        source: str = "my-app",
        ttl_sec: int = 3600,
    ) -> dict[str, Any]:
        return self.post_json("/publish", {
            "topic": topic,
            "event_id": event_id or f"my-app-{int(time.time() * 1000)}",
            "from": source,
            "type": event_type,
            "payload": payload,
            "ttl_sec": ttl_sec,
        })

    def task(
        self,
        task_id: str,
        task_type: str,
        description: str,
        *,
        source: str = "my-app",
        reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "task_id": task_id,
            "type": task_type,
            "description": description,
            "from": source,
            "metadata": metadata or {},
        }
        if reply_to:
            payload["reply_to"] = reply_to.rstrip("/")
        return self.post_json("/task", payload)
```

## CLI Commands to Add

When the target has a CLI, add two commands if practical:

```bash
<app> vex status --base-url <local-vex-url>
<app> vex publish-latest --base-url <local-vex-url>
```

`vex status` should:

1. Call `/health`.
2. Call `/identity`.
3. Print base URL, status, version, agent, advertised URL, role/hash if present.
4. Exit non-zero on unavailable VEX.

`vex publish-latest` should:

1. Load the latest local artifact/run/report.
2. Build sanitized payloads.
3. Publish summary to `<namespace>/runs`.
4. Optionally publish findings to `<namespace>/findings`.
5. Handle “no run found” cleanly.
6. Optionally support `--no-findings` for smoke tests.

## Automatic Publish Hook

If the application has a run pipeline, add a fail-soft hook after reports/artifacts are written:

```python
def publish_to_vex_if_enabled(cfg, run_summary, findings, logger, out_dir):
    vex_cfg = getattr(cfg, "vex", None)
    if not vex_cfg or not vex_cfg.enabled:
        return
    try:
        client = VexClient(vex_cfg.base_url, vex_cfg.timeout_s)
        result = publish_run_to_vex(client, vex_cfg, run_summary, findings)
        (out_dir / "vex_publish.json").write_text(json.dumps(result, indent=2))
        logger.info("vex_publish", "Published run telemetry to VEX")
    except Exception as exc:
        logger.warning("vex_publish_failed", f"VEX publish failed: {exc}")
```

Do not call VEX before the application's own policy/safety checks have completed.

## Defensive Task Handoff Pattern

Task handoff must be opt-in. Good task type names:

```text
defensive_gap_review
report_review
detection_suggestion
documentation_review
integration_review
```

Good task description template:

```text
Defensive review requested for <app> finding/gap: run=<run_id>, id=<id>, severity=<severity>.
Suggest detections, controls, and validation steps only. Do not run offensive actions.
```

Include metadata:

```json
{
  "run_id": "RUN-123",
  "finding_id": "F-001",
  "safety": "defensive-review-only"
}
```

Never hand off:

- shell commands to run,
- exploit steps,
- credentials,
- customer secrets,
- prompts that ask a peer to bypass policy.

## Unit Test Pattern with Fake VEX

Use an in-process HTTP server so tests do not touch the live mesh:

```python
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class FakeVexHandler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "conscious", "version": "test"})
        elif self.path == "/identity":
            self._json(200, {"agent": "fake-vex", "hash": "FAKE"})
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self):
        raw_len = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(raw_len) or b"{}")
        self.server.received.append((self.path, payload))
        if self.path == "/publish":
            self._json(200, {"published": True, "event_id": payload.get("event_id"), "topic": payload.get("topic")})
        elif self.path == "/task":
            self._json(202, {"accepted": True, "task_id": payload.get("task_id")})
        else:
            self._json(404, {"error": "not_found"})

    def log_message(self, *_args):
        return


@pytest.fixture
def fake_vex():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeVexHandler)
    srv.received = []
    srv.base_url = f"http://127.0.0.1:{srv.server_address[1]}"
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=2)
```

Test cases to include:

- defaults keep VEX disabled;
- URL validation rejects invalid schemes;
- status calls `/health` and `/identity`;
- publish emits summary event;
- optional findings publish can be disabled;
- payload excludes raw evidence/secrets;
- task handoff returns empty when disabled;
- enabled handoff uses defensive wording;
- network failures are surfaced/logged without breaking primary workflow.

## Live Verification

After unit tests pass, verify against the local VEX node:

```bash
python -m py_compile <bridge_module>.py <cli_module>.py <test_file>.py
python -m pytest <targeted_tests> -q
python -m pytest tests/ -q

<app> vex status --base-url <local-vex-url>
```

If the app supports publish-latest, create a synthetic temp project/run rather than using production data:

```bash
TMP=/tmp/<app>-vex-smoke
mkdir -p "$TMP/artifacts/runs/RUN-SMOKE"
printf '{"run_id":"RUN-SMOKE","status":"success","findings_count":0}' > "$TMP/artifacts/runs/RUN-SMOKE/summary.json"
printf '[]' > "$TMP/artifacts/runs/RUN-SMOKE/findings.json"
<app> vex publish-latest --base-url <local-vex-url> --project-root "$TMP" --no-findings
```

Then optionally inspect local VEX events if the implementation exposes event queries:

```bash
python3 -m json.tool < /path/to/exported-vex-events.json
```

## Integrating Another Hermes Node

For another Hermes instance rather than an app repo:

1. Confirm Hermes is installed and healthy:
   ```bash
   hermes doctor
   hermes config path
   hermes plugins list
   ```
2. Install/enable the VEX Constellation plugin under that node's `$HERMES_HOME/plugins/vex-constellation` using the plugin workflow in `hermes-agent`.
3. Ensure the node advertises a routable URL if peers need callbacks:
   ```ini
   Environment=VEX_PUBLIC_URL=<this-node-vex-url>
   Environment=VEX_LOCAL_URL=<this-node-vex-url>
   ```
4. Verify services:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart vex-constellation.service vex-autoresponder.service
   systemctl --user status vex-constellation.service vex-autoresponder.service --no-pager
   python3 - <<'PY'
   import json, urllib.request
   for path in ("/health", "/identity"):
       with urllib.request.urlopen("<local-vex-url>" + path, timeout=5) as r:
           print(json.dumps(json.load(r), indent=2))
   PY
   ```
5. Verify listener is LAN-reachable when needed:
   ```bash
   ss -ltnp | grep ':8390'
   ```
   A wildcard listener is LAN-reachable; a loopback-only listener is local-only.
6. Send a smoke task with a routable `reply_to`, not loopback, when testing across machines.
7. Query `/network-map` on each reachable peer and count real participants by routable URL plus identity hash.

## Secret and Public-Repo Scan

Before committing integration docs/code, scan touched files:

```bash
git diff --check
python3 - <<'PY'
from pathlib import Path
import re
patterns = [
    r"common GitHub token prefixes",
    r"OpenAI-style secret-key prefixes",
    r"/home/[A-Za-z0-9_-]+",
    r"192\\.168\\.",
    r"10\\.",
    r"172\\.(1[6-9]|2[0-9]|3[0-1])\\.",
]
paths = ["README.md", "docs", "examples", "src", "tests", "skills"]
for root in paths:
    p = Path(root)
    files = [p] if p.is_file() else list(p.rglob("*")) if p.exists() else []
    for f in files:
        if not f.is_file() or f.suffix in {".png", ".jpg", ".gif", ".zip"}:
            continue
        text = f.read_text(errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(re.search(pat, line) for pat in patterns[2:]):
                print(f"{f}:{line_no}:{line[:160]}")
PY
```

Also scan manually for token-like strings using the repository's preferred secret-scanning tool. Private IP examples can be acceptable in local/private notes, but public READMEs and templates should use placeholders.

## Common Pitfalls

1. **Letting VEX become an authorization layer.** VEX is a bus. It does not approve scope, targets, or destructive actions.

2. **Blocking primary workflows on VEX.** VEX publication should happen after the main output is saved and should fail-soft.

3. **Testing against live VEX only.** Always add fake-server tests. Live mesh tests are smoke checks, not unit tests.

4. **Using loopback for remote callbacks.** `reply_to=<local-vex-url>` points the peer back to itself. Use a routable URL across machines.

5. **Publishing raw evidence.** Send IDs, hashes, and summaries. Keep raw files local unless there is an explicit secure transport design.

6. **Docs leaking local machine details.** Replace LAN IPs, `/home/<user>`, and service-specific paths with placeholders in public docs.

7. **Judging worker success from `/task/<id>` only.** Some receivers keep inbound status as `received` while worker status is visible in merged `/tasks` or JSONL outbox logs.

8. **Forgetting fresh sessions.** Hermes tool, plugin, and skill changes may require `/reset`, a new Hermes session, or service restart to load.

## Verification Checklist

- [ ] Existing application safety model is unchanged.
- [ ] `vex.enabled` defaults to false.
- [ ] URL fields are validated and stripped of trailing slash.
- [ ] Client covers `/health`, `/identity`, `/publish`, and optional `/task`.
- [ ] Publish payloads are compact and sanitized.
- [ ] Optional task handoff is disabled by default and defensive in wording.
- [ ] CLI has `vex status` and, where practical, `vex publish-latest`.
- [ ] Unit tests use a fake VEX server.
- [ ] Targeted tests pass.
- [ ] Full relevant suite passes or unrelated failures are documented.
- [ ] Live `vex status` smoke passes against `<local-vex-url>`.
- [ ] Optional live publish smoke uses synthetic/temp artifacts.
- [ ] Docs avoid public leakage of private IPs, local usernames, tokens, and raw runtime state.
- [ ] `git status --short` and `git diff --stat` reviewed.
