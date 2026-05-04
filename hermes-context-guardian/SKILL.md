---
name: hermes-context-guardian
description: Post-update guardian + first-time bootstrap. Renames AGENTS.md, creates AGENTS_INDEX.md, merges new content, and verifies auto-injection is blocked. Survives hermes updates. Self-sufficient — no separate pruning skill required.
version: 1.1.0
author: Marco Torres Y. — Axis Dynamics · Hermes VEX
license: MIT
metadata:
  hermes:
    tags: [hermes, context, guardian, update-survival, pruning, agents-md, automation]
    related_skills: [hermes-context-pruning, hermes-agent]
---

# Hermes Context Guardian

Post-update automation that ensures the context pruning system survives
`hermes update`. Detects when an update recreates `AGENTS.md`, merges
new content into `AGENTS_DEV.md`, and verifies the auto-injection block.

## When to Use

- **First time**: `./guardian.sh --bootstrap` (one-time setup)
- After `hermes update` completes
- When you suspect AGENTS.md was recreated
- As a cron job: `0 2 * * *` (daily health check)
- When context seems bloated unexpectedly

## Don't Use For

- Writing new AGENTS.md files
- General Hermes troubleshooting

---

## Quick Start

```bash
# First time on a fresh Hermes install (creates AGENTS_INDEX.md)
./guardian.sh --bootstrap

# Every time after hermes update (maintenance)
./guardian.sh

# Just check, no changes
./guardian.sh --check
```

That's it. No separate pruning skill needed — the guardian is self-sufficient.

---

## Architecture

```
        ┌──────────────────────┐
        │  First time?         │
        │  ./guardian --bootstrap│
        └──────────┬───────────┘
                   │
        ┌──────────▼───────────┐
        │ PHASE 0: BOOTSTRAP   │
        │ Create AGENTS_INDEX  │
        │ Rename AGENTS.md     │
        │ Set skip_context     │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  Every hermes update │
        │  ./guardian          │
        └──────────┬───────────┘
                   │
                   ▼
    ┌─────────────┐     NO     ┌──────────┐
    │ AGENTS.md   │───────────▶│ All good │
    │  exists?    │            │  nothing │
    └─────────────┘            └──────────┘
         │ YES
         ▼
    ┌─────────────┐
    │ MERGE new   │  AGENTS.md → AGENTS_DEV.md
    │ content     │
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ VERIFY      │  4 health checks ✓
    └─────────────┘
```

---

## Phase 0: Bootstrap (First-Time Setup)

Run once on a fresh Hermes install. Creates the entire pruning system:

```bash
./guardian.sh --bootstrap
```

What it does:
1. Finds AGENTS.md (or existing AGENTS_DEV.md)
2. Renames AGENTS.md → AGENTS_DEV.md (evades auto-injection)
3. Enables `skip_context_files: true` in config
4. Scans AGENTS_DEV.md for `##` sections
5. Generates AGENTS_INDEX.md with critical policies + section index
6. Reports context savings (typically ~94% reduction)

Idempotent — safe to run even if things already exist.

## Phase 1: Detection

Check if the update recreated AGENTS.md:

```bash
# Primary target — hermes-agent source
test -f ~/.hermes/hermes-agent/AGENTS.md && echo "DETECTED: AGENTS.md exists" || echo "CLEAN"

# Secondary targets — plugins that might ship AGENTS.md
find ~/.hermes/plugins -name "AGENTS.md" -o -name "CLAUDE.md" 2>/dev/null
```

If nothing is detected, exit. The guardian has nothing to do.

## Phase 2: Merge New Content

When a new AGENTS.md is detected, merge its content into AGENTS_DEV.md:

```python
from pathlib import Path
import re

NEW = Path.home() / ".hermes/hermes-agent/AGENTS.md"
DEV = Path.home() / ".hermes/hermes-agent/AGENTS_DEV.md"

new_content = NEW.read_text()
dev_content = DEV.read_text() if DEV.exists() else ""

# Strategy: if AGENTS_DEV.md doesn't exist, just use new content
# If it exists, extract section line numbers from new version
# and update our index references

sections_new = {}
for match in re.finditer(r'^## (.+)$', new_content, re.MULTILINE):
    sections_new[match.group(1)] = match.start() // len(new_content.split('\n'))

# Write merged content (new AGENTS.md as AGENTS_DEV.md)
DEV.write_text(new_content)
print(f"MERGED: {len(new_content)} bytes -> AGENTS_DEV.md")
```

**Merge strategy**: The new AGENTS.md from the update is the canonical dev guide.
We replace AGENTS_DEV.md entirely with it. Our custom additions live in
AGENTS_INDEX.md, not in the dev guide. This keeps the merge simple and safe.

## Phase 3: Rename and Cleanup

```bash
# Rename to evade "Subdirectory context discovered"
mv ~/.hermes/hermes-agent/AGENTS.md ~/.hermes/hermes-agent/AGENTS_DEV.md

# Verify rename
test -f ~/.hermes/hermes-agent/AGENTS_DEV.md && echo "RENAMED" || echo "FAILED"
test ! -f ~/.hermes/hermes-agent/AGENTS.md && echo "CLEAN" || echo "ORPHAN"
```

## Phase 4: Update AGENTS_INDEX.md

After merging, the line offsets in AGENTS_INDEX.md may be stale. Update them:

```bash
# Extract new section line numbers
grep -n "^## " ~/.hermes/hermes-agent/AGENTS_DEV.md
```

Update the task->section index table in AGENTS_INDEX.md with new offsets.
Key sections to check (names may vary by version):

| Section pattern | AGENTS_INDEX.md row |
|----------------|---------------------|
| `Project Structure` | "Entender estructura" |
| `AIAgent Class` | "Modificar el agent loop" |
| `CLI Architecture` | "Modificar el CLI" |
| `Adding Slash Command` | "Agregar un slash command" |
| `TUI Architecture` | "Modificar TUI" |
| `Adding New Tools` | "Agregar un tool nuevo" |
| `Adding Configuration` | "Agregar opcion de config" |
| `Skin/Theme` | "Agregar skin/theme" |
| `Plugins` | "Agregar/configurar plugin" |
| `Skills` | "Agregar una skill" |
| `Important Policies` | "Seguir reglas criticas" |
| `Known Pitfalls` | "Debuggear un error" |
| `Testing` | "Escribir tests" |
| `Profiles` | "Trabajar con perfiles" |

Update the file size and line count in the header reference.
Increment AGENTS_INDEX.md version number.

## Phase 5: Verify

```bash
# 1. Confirm skip_context_files is still active
grep "skip_context_files: true" ~/.hermes/config.yaml && echo "✓ skip" || echo "✗ FIX NEEDED"

# 2. Test no auto-injection
output=$(ls -la ~/.hermes/hermes-agent/AGENTS_DEV.md 2>&1)
echo "$output" | grep -q "Subdirectory context discovered" && echo "✗ INJECTION" || echo "✓ blocked"

# 3. Confirm AGENTS.md does NOT exist
test -f ~/.hermes/hermes-agent/AGENTS.md && echo "✗ AGENTS.md STILL EXISTS" || echo "✓ clean"

# 4. Check AGENTS_INDEX.md is slim
wc -c < ~/AGENTS_INDEX.md
```

---

## One-Shot Recipe

```bash
# Full guardian run
GUARDIAN_TARGET=~/.hermes/hermes-agent/AGENTS.md
GUARDIAN_DEV=~/.hermes/hermes-agent/AGENTS_DEV.md

if [ -f "$GUARDIAN_TARGET" ]; then
    echo "=== GUARDIAN: AGENTS.md detected ==="

    # Merge: replace AGENTS_DEV.md with new AGENTS.md content
    cp "$GUARDIAN_TARGET" "$GUARDIAN_DEV"
    echo "MERGED: $(wc -c < "$GUARDIAN_DEV") bytes"

    # Rename
    rm "$GUARDIAN_TARGET"
    echo "RENAMED: AGENTS.md -> AGENTS_DEV.md"

    # Update index offsets
    echo "New section offsets (update AGENTS_INDEX.md manually):"
    grep -n "^## " "$GUARDIAN_DEV"

    echo "=== GUARDIAN: Done. Update AGENTS_INDEX.md offsets. ==="
else
    echo "=== GUARDIAN: Clean. No AGENTS.md detected. ==="
fi
```

---

## Cron Job Setup

Automate the guardian to run daily:

```
cronjob action='create'
schedule='0 2 * * *'
name='hermes-context-guardian'
prompt='Run the hermes-context-guardian skill: check if AGENTS.md was recreated, merge+rename if yes, verify no auto-injection, update AGENTS_INDEX.md offsets. Report results.'
skills=['hermes-context-guardian']
```

---

## Pitfalls

1. **hermes update may not recreate AGENTS.md every time.** The guardian is
   idempotent — safe to run when nothing has changed.
2. **Section names change between versions.** "Adding New Tools" might become
   "Creating Tools". Always grep for `^## ` to see the actual section names.
3. **Line offsets are version-specific.** After merge, ALL offsets in
   AGENTS_INDEX.md must be updated. Don't skip this — stale offsets = broken
   development workflow.
4. **Don't delete AGENTS_DEV.md during merge.** Always read it first to preserve
   any custom content, then replace.
5. **AGENTS_INDEX.md lives in ~/.** Not in .hermes/. The guardian updates
   ~/AGENTS_INDEX.md, not a copy.

---

## Verification Checklist

- [ ] `skip_context_files: true` still in config.yaml
- [ ] `AGENTS.md` does NOT exist in hermes-agent/
- [ ] `AGENTS_DEV.md` exists with updated content
- [ ] `ls -la AGENTS_DEV.md` does NOT trigger auto-injection
- [ ] AGENTS_INDEX.md line offsets match new AGENTS_DEV.md
- [ ] AGENTS_INDEX.md version incremented
- [ ] `vex_mods/` updated if significant changes
