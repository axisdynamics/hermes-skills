---
name: vex-autoupdate
description: Constellation-wide auto-update. Each agent checks configured GitHub repos on every start, pulls updates, and re-installs. No bash, no cron, no human. Designed for multi-agent constellations.
version: 1.0.0
author: Marco Torres Y. — Axis Dynamics · Hermes VEX
license: MIT
metadata:
  hermes:
    tags: [vex, autoupdate, constellation, git, deploy, sync, auto-update]
    related_skills: [vex-constellation, vex-crystallization]
---

# VEX Auto-Update 🌐

> **Each agent updates itself. No bash scripts. No central orchestration.**

---

## How It Works

Every time an agent starts (via `run_constellation.py`, `/constellation start`, or `_start_server()`), it should:

1. Read `$VEX_AUTOUPDATE_REPOS` — comma-separated GitHub HTTPS URLs
2. For each URL, infer the local path: `$HOME/Documentos/GITHUB/<repo-name>`
3. `git fetch <url>` — if that fails, fallback to `git fetch origin`
4. `git merge --ff-only origin/main`
5. If new commits, run `install.sh` for relevant plugins
6. Log via `_log_activity("autoupdate", ...)`

---

## Configuration

```bash
export VEX_AUTOUPDATE_REPOS=\
"https://github.com/axisdynamics/hermes-tools.git,\
https://github.com/axisdynamics/hermes-skills.git"
```

Or in systemd service:

```ini
Environment=VEX_AUTOUPDATE_REPOS=\
  https://github.com/axisdynamics/hermes-tools.git,\
  https://github.com/axisdynamics/hermes-skills.git
```

---

## Reference Implementation

```python
import os, subprocess
from pathlib import Path

def autoupdate_repos():
    repos = os.environ.get("VEX_AUTOUPDATE_REPOS", "")
    if not repos:
        return "No repos configured. Set VEX_AUTOUPDATE_REPOS."

    git_home = str(Path.home() / "Documentos" / "GITHUB")
    results = []

    for entry in repos.split(","):
        entry = entry.strip()
        if not entry:
            continue

        # Infer repo name from URL
        repo_name = entry.rstrip("/").rsplit("/", 1)[-1].replace(".git", "")
        git_dir = os.path.join(git_home, repo_name)

        if not os.path.isdir(git_dir):
            results.append(f"⚠  {repo_name}: no local repo at {git_dir}")
            results.append(f"   Clone: git clone {entry} {git_dir}")
            continue

        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"],
                               capture_output=True, text=True, timeout=10, cwd=git_dir)
            before = r.stdout.strip()

            # Try fetching directly from the env var URL,
            # fallback to origin remote
            r = subprocess.run(["git", "fetch", entry],
                               capture_output=True, text=True, timeout=15, cwd=git_dir)
            if r.returncode != 0:
                r = subprocess.run(["git", "fetch", "origin"],
                                   capture_output=True, text=True, timeout=15, cwd=git_dir)
                if r.returncode != 0:
                    results.append(f"⚠  {repo_name}: fetch failed: {r.stderr.strip()[:80]}")
                    continue

            r = subprocess.run(["git", "merge", "--ff-only", "origin/main"],
                               capture_output=True, text=True, timeout=15, cwd=git_dir)
            if r.returncode != 0:
                results.append(f"⚠  {repo_name}: merge conflict — {r.stderr.strip()[:80]}")
                continue

            r = subprocess.run(["git", "rev-parse", "HEAD"],
                               capture_output=True, text=True, timeout=10, cwd=git_dir)
            after = r.stdout.strip()

            if before != after:
                log = subprocess.run(["git", "log", "--oneline", f"{before[:8]}..{after[:8]}"],
                                     capture_output=True, text=True, timeout=5, cwd=git_dir)
                n = len(log.stdout.strip().splitlines()) if log.stdout.strip() else 0
                results.append(f"✓  {repo_name}: {before[:8]}..{after[:8]} ({n} commits)")

                # Re-install plugins if tools repo updated
                for plugin in ["sustrato", "vex-constellation"]:
                    installer = os.path.join(git_dir, plugin, "install.sh")
                    if os.path.isfile(installer):
                        subprocess.run(["bash", installer],
                                       capture_output=True, timeout=30,
                                       cwd=os.path.join(git_dir, plugin))
                        results.append(f"   → {plugin}: re-installed")
            else:
                results.append(f"✓  {repo_name}: up to date")

        except subprocess.TimeoutExpired:
            results.append(f"⚠  {repo_name}: timeout")
        except Exception as e:
            results.append(f"⚠  {repo_name}: {str(e)[:80]}")

    return "\n".join(results)
```

---

## For Constellation Agents

If your agent implements the VEX Constellation protocol, wire this into:

- `_start_server()` — run autoupdate in a background thread after server starts
- `/constellation autoupdate` — slash command for manual trigger
- `_on_session_start` hook — optional check at session start

---

## No Dependencies

Only requires `git` and `bash` (always present in development environments).
Public GitHub repos over HTTPS — no API keys for read access.
