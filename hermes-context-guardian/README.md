# Hermes Context Guardian 🛡️

> **Post-update survival skill for Hermes Agent context pruning.**
> Survives `hermes update` — detects recreated AGENTS.md, merges content,
> renames to evade auto-injection, and verifies the pruning system.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes](https://img.shields.io/badge/Hermes-v0.11.0%2B-blue)](https://github.com/NousResearch/hermes-agent)

---

## The Problem

Hermes Agent v0.11.0 introduced a mechanism called **"Subdirectory context
discovered"** that auto-injects the full `AGENTS.md` (~35KB / 8,700 tokens)
into your session context whenever any tool touches the file — even with
`skip_context_files: true` in your config.

This defeats context pruning setups that rely on slim index files
(`AGENTS_INDEX.md`) and on-demand access to the full development guide.

**Worse**: every `hermes update` may recreate the original `AGENTS.md`,
re-enabling the auto-injection and silently bloating your context.

---

## The Solution

**Hermes Context Guardian** is a skill + standalone script that:

1. **Detects** when `hermes update` recreates `AGENTS.md`
2. **Merges** new content into `AGENTS_DEV.md` (keeping you up to date)
3. **Renames** `AGENTS.md → AGENTS_DEV.md` (evading auto-injection)
4. **Updates** your `AGENTS_INDEX.md` line offsets
5. **Verifies** the pruning system is intact

The guardian is **idempotent** — safe to run any time, even when nothing
has changed.

---

## Quick Install

```bash
# Clone the repo
git clone https://github.com/plaxius/hermes-skills.git
cd hermes-skills/hermes-context-guardian

# First time: bootstrap the pruning system
./guardian.sh --bootstrap

# Done. Now run this after every hermes update:
./guardian.sh
```

### Or install as a Hermes skill

```bash
hermes skills install https://raw.githubusercontent.com/plaxius/hermes-skills/main/hermes-context-guardian/SKILL.md
```

Then in a Hermes session:
```
/skill hermes-context-guardian
```

---

## Two Modes, One Tool

| Mode | Command | When |
|------|---------|------|
| **Bootstrap** | `./guardian.sh --bootstrap` | Once, on fresh Hermes install |
| **Maintenance** | `./guardian.sh` | After every `hermes update` |
| **Audit** | `./guardian.sh --check` | Anytime, read-only |

The guardian is **self-sufficient**. It creates the index, renames the file,
and verifies everything. No separate pruning skill required.

### Cron Job (auto-pilot)

```bash
# Daily health check at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /path/to/guardian.sh >> ~/.hermes/logs/guardian.log 2>&1") | crontab -
```

---

## How It Works

```
First time:
  ./guardian.sh --bootstrap
  → Creates AGENTS_INDEX.md from AGENTS_DEV.md sections
  → Sets skip_context_files: true
  → Renames AGENTS.md → AGENTS_DEV.md (evades injection)

Every update:
  ./guardian.sh
  → Detects if hermes update recreated AGENTS.md
  → Merges new content → AGENTS_DEV.md
  → Deletes AGENTS.md (keeps injection blocked)
  → Verifies 4 health checks pass
```

---

## Context Savings

The numbers that matter:

| Scenario | Context Load | Tokens | Delta |
|----------|-------------|--------|-------|
| No pruning (AGENTS.md loads every session) | 35 KB | ~8,700 tok | — |
| With `skip_context_files` only | 35 KB | ~8,700 tok | 0% (auto-injection bypasses it) |
| **With Guardian active** | **3.9 KB** | **~470 tok** | **94.6% reduction** |

**Per session**: 8,230 tokens saved. That's ~$0.02-$0.08/session on paid
providers, or several extra tool-calling turns on free-tier models with
small context windows (DeepSeek 8K, Gemini Flash, etc.).

**Per update cycle**: Without the guardian, a single `hermes update` silently
restores the bloat. With it, the pruning survives indefinitely.

```
Before:  [████████████████████████████████████████] 8,700 tok (bloated)
After:   [██] 470 tok (lean)
         ─────────────────────────────────────
                  94.6% context saved
```

## Prerequisites

- **Hermes Agent v0.11.0+** (the version that introduced the bug)
- `skip_context_files: true` in `~/.hermes/config.yaml`
- An `AGENTS_INDEX.md` file in your home directory (see
  [hermes-context-pruning](https://github.com/plaxius/hermes-context-pruning)
  for setup)

---

## What Gets Modified

| File | Action |
|------|--------|
| `~/.hermes/hermes-agent/AGENTS.md` | DELETED (renamed to AGENTS_DEV.md) |
| `~/.hermes/hermes-agent/AGENTS_DEV.md` | CREATED/UPDATED with latest content |
| `~/AGENTS_INDEX.md` | UPDATED (line offsets, version, header) |
| `~/.hermes/config.yaml` | READ ONLY (verifies skip_context_files) |

**Nothing else is touched.** The guardian is surgical.

---

## Manual Run

```bash
# Full check with output
./guardian.sh

# Example output:
# === GUARDIAN v1.0.0 ===
# ✓ skip_context_files: true
# ✓ AGENTS.md does not exist (clean)
# ✓ AGENTS_DEV.md: 36047 bytes (healthy)
# ✓ No auto-injection
# === ALL CHECKS PASSED ===
```

If AGENTS.md is detected:
```bash
# === GUARDIAN v1.0.0 ===
# ⚠ AGENTS.md DETECTED — merging into AGENTS_DEV.md
# MERGED: 36047 bytes
# RENAMED: AGENTS.md → AGENTS_DEV.md
# New section offsets:
# 16:## Project Structure
# 78:## AIAgent Class
# ...
# === GUARDIAN: Update AGENTS_INDEX.md offsets ===
```

---

## Ecosystem

This skill is part of the Hermes context pruning ecosystem:

| Skill | Purpose | When |
|-------|---------|------|
| `hermes-context-pruning` | Initial context audit + pruning setup | One-time setup |
| **`hermes-context-guardian`** | **Post-update survival** | **After every `hermes update`** |

The pruning skill creates the slim index. The guardian keeps it alive.

---

## Background: The Bug

In Hermes v0.11.0, accessing an `AGENTS.md` file via any tool (`ls`, `cat`,
`file`, etc.) triggers a "Subdirectory context discovered" mechanism that
injects the full file content into the session context. This is separate
from `skip_context_files` (which only controls session-start loading).

The injection:
- Adds ~35KB / 8,700 tokens per trigger
- Can happen multiple times per session
- Has no documented config option to disable

**Renaming `AGENTS.md → AGENTS_DEV.md` evades the detector** — it only
matches exact filenames (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`).

Diagnosed and fixed by Marco Torres Y. — Axis Dynamics · Hermes VEX, May 2026.

---

## License

MIT — do whatever you want, just keep the attribution.

---

## Author

Created by **Marco Torres Y.** — [Axis Dynamics](https://axisdynamics.cl)
in collaboration with **Hermes VEX**.

Part of the Memovex / VEX ecosystem.
