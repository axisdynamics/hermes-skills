---
name: hermes-context-pruning
description: Use when Hermes Agent or Claude Code is slow, timing out, or hitting context limits — audit AGENTS.md / CLAUDE.md context files, classify sections by criticality, create a slim AGENTS_INDEX.md, and document the reduction.
version: 1.0.0
author: Marco Torres Y. — Axis Dynamics · Hermes VEX
license: MIT
metadata:
  hermes:
    tags: [hermes, context, optimization, pruning, performance, timeout, agents-md]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, hermes-context-guardian]
---

# Hermes Context Pruning

When Hermes Agent (or Claude Code) responses are slow (2min+), hitting timeouts ("⚠️ No response from provider for 180s"), or showing "Response truncated" — the root cause is often context bloat from AGENTS.md / CLAUDE.md files loaded into every session.

This skill provides a systematic methodology for auditing, classifying, pruning, and documenting context file reduction.

## When to Use

- Hermes responses take >60 seconds consistently
- Provider timeouts: "peer closed connection without sending complete message body"
- "Response truncated due to output length limit"
- User asks to "optimize context", "reduce tokens", "podar AGENTS.md"
- After installing large plugins or adding extensive AGENTS.md files
- DeepSeek or other 8K-context models are hitting their limit

## Don't Use For

- General Hermes troubleshooting (use `hermes-agent` skill)
- Writing new SKILL.md files (use `hermes-agent-skill-authoring`)
- One-off slow responses (check `hermes doctor` first)

---

## Methodology

### Phase 1: Audit

Identify all AGENTS.md / CLAUDE.md files loaded into context:

```bash
find . -name "AGENTS.md" -o -name "CLAUDE.md" -o -name "GEMINI.md" 2>/dev/null
find ~/.hermes/plugins -name "AGENTS.md" -o -name "CLAUDE.md" 2>/dev/null
find ~/.hermes/hermes-agent -name "AGENTS.md" 2>/dev/null
```

Count tokens for each file (rough estimate: chars ÷ 4):

```bash
for f in $(find . ~/.hermes -name "AGENTS.md" -o -name "CLAUDE.md" 2>/dev/null); do
    chars=$(wc -c < "$f")
    echo "$(printf '%5d' $((chars/4))) tok | $chars chars | $f"
done
```

### Phase 1b: Test Auto-Injection (v0.11.0+)

Hermes v0.11.0+ has a separate "Subdirectory context discovered" mechanism
that auto-injects AGENTS.md content when accessed during a tool call — this
bypasses `skip_context_files`. Test if your AGENTS.md triggers it:

```bash
# If output includes more than file stats, auto-injection is active:
ls -la ~/.hermes/hermes-agent/AGENTS.md
```

If auto-injection is detected, rename to evade the detector:
```bash
mv ~/.hermes/hermes-agent/AGENTS.md ~/.hermes/hermes-agent/AGENTS_DEV.md
```

Update AGENTS_INDEX.md references. Re-test after every `hermes update`.

### Phase 2: Classify

Read the largest AGENTS.md and classify every `##` section:

```python
import re
from pathlib import Path

text = Path("AGENTS.md").read_text()
sections = re.split(r'\n(?=## )', text)

for section in sections:
    title = section.split('\n')[0][:80]
    chars = len(section)
    est_tokens = chars // 4
    pct = (chars / len(text)) * 100
    print(f"{pct:5.1f}% | ~{est_tokens:4d} tok | {title}")
```

Assign each section a classification:

| Tag | Meaning | Action |
|-----|---------|--------|
| 🔴 CRÍTICO | Operationally essential | Keep in slim index |
| 🔧 DEV | Only needed when modifying agent source | Drop, reference path |
| 📖 REF | Reference, consultable on demand | Drop, reference path |
| 🗑️ COSMÉTICO | Never used operationally | Drop |
| ⚡ MIXTO | Partially useful | Extract key points only |

### Phase 3: Prune

**Step 1:** Enable context file skipping:

```bash
hermes config set context.skip_context_files true
```

This prevents Hermes from auto-loading AGENTS.md/CLAUDE.md from the filesystem. Takes effect on next session.

**Step 2:** Create a slim `AGENTS_INDEX.md` containing ONLY:

- 🔴 Critical policies (prompt caching, role alternation, config safety)
- ⚡ Quick reference (frequent commands, key paths)
- 🔌 Your custom plugins (paths, hooks, skills registered)
- 🧠 Pointer to full AGENTS.md for development work

Target: **~500 tokens** (down from 8,000-10,000+).

Template:

```markdown
# AGENT OPERANTE — Contexto Esencial vX.0

> Slim context file. Full AGENTS.md at <path>. Critical policies extracted.

## 🔴 Políticas Críticas (NO TOCAR)
<extract from Important Policies + Known Pitfalls sections>
- Prompt caching rules
- Role alternation rules
- Config safety rules

## ⚡ Referencia Rápida
| Necesidad | Comando / Ruta |
<frequent commands and paths>

## 🔌 Plugins (creados por nosotros)
<your custom plugins with paths and hooks>

## 🧠 Desarrollo (bajo demanda)
Full AGENTS.md: `<path>` (<size>, ~<tokens> tok)
Access via: search_files, skill_view, or read_file
```

### Phase 4: Document

Create a `vex_mods/hermes-poda.md` (or similar) documenting:

```markdown
# Hermes Context Pruning — Documentación Completa
## 1. Diagnóstico Original
## 2. Auditoría Completa (table of every file + section)
## 3. Análisis de Degradación (what we lose, mitigations, scenario matrix)
## 4. Solución Implementada (config + slim index + metrics)
## 5. Rollback Instructions
## 6. Lecciones Aprendidas
```

---

## Decision Framework

When deciding to prune, ask:

1. **Are we MODIFYING the agent's source code?** If yes, keep full AGENTS.md accessible. If no, prune.
2. **What % of AGENTS.md is development docs?** Typically 60-80%. All of it can be dropped for operational use.
3. **Do we have other sources of truth?** Skills (`hermes-agent`), `hermes doctor`, logs — these cover troubleshooting.
4. **Can critical policies fit in 300 tokens?** Yes — they're short constraint rules.

**Safe to prune when:** Using Hermes operationally (not developing it), plugins already built, troubleshooting covered by skills.

**Don't prune when:** Actively contributing PRs to hermes-agent, writing tests, modifying core CLI.

---

### Phase 2b: Build a Task→Section Index

After classifying sections, build a **development task index** that maps common modification tasks to exact line offsets in the full AGENTS.md. This enables surgical reads without loading 8,000+ tokens.

```bash
# Map AGENTS.md section headers to line numbers
grep -n "^## \|^# \|^### " .hermes/hermes-agent/AGENTS.md
```

Create a table in AGENTS_INDEX.md:

```markdown
## 🧠 Desarrollo — Índice de Tareas → Secciones AGENTS.md

| Si necesitas... | Lee esto | Líneas | Archivos a tocar |
|---|---|---|---|
| **Agregar un tool nuevo** | §7 Adding New Tools | 258-296 | `tools/tu_tool.py` + `toolsets.py` |
| **Agregar un slash command** | §5.3 Adding Slash Command | 159-191 | `hermes_cli/commands.py` + `cli.py` |
| **Modificar el CLI** | §5 CLI Architecture | 138-191 | `cli.py`, `hermes_cli/` |
| **Agregar/configurar plugin** | §10 Plugins | 434-493 | `~/.hermes/plugins/<name>/` |
| ... | ... | ... | ... |

### Acceso rápido por línea:
read_file(".hermes/hermes-agent/AGENTS.md", offset=258, limit=38)
```

This achieves **96-98% token reduction per development query** — loading only the specific section needed (~150-350 tok) vs the full file (~8,767 tok). Without this index, you either skip all context (losing development guidance) or load everything (bloating context). With it, you get surgical access.

### Phase 3 template — updated to include task index:

```markdown
# AGENT OPERANTE — Contexto Esencial vX.0

> Slim context file. Full AGENTS.md at <path>.
> Critical policies extracted. Dev sections accessible via offset reads.

## 🔴 Políticas Críticas (NO TOCAR)
<extract from Important Policies + Known Pitfalls>

## ⚡ Referencia Rápida
| Necesidad | Comando / Ruta |
<frequent commands and key paths>

## 🔌 Plugins (creados por nosotros)
<custom plugins with paths, hooks, skills>

## 🧠 Desarrollo — Índice de Tareas → Secciones AGENTS.md
> AGENTS.md completo: `<path>` (<size>, ~<tokens> tok, <lines> líneas)
> Leer bajo demanda: `read_file("<path>", offset=L, limit=N)`

| Si necesitas... | Lee esto | Líneas | Archivos a tocar |
|---|---|---|---|
| **Agregar un tool nuevo** | §7 Adding New Tools | L-L | `tools/` + `toolsets.py` |
| **Agregar un slash command** | §5.3 | L-L | `hermes_cli/commands.py` |
| ... (map all 10-15 common tasks) | ... | ... | ... |
```

---

## Common Pitfalls

1. **AGENTS_INDEX.md too sparse.** v2.4 was just section names (731 bytes, zero actionable content). Include actual critical policies, not just pointers to them.
2. **No task→section index.** Without precise line offsets for each development task, you either skip all context (losing guidance) or load everything (bloating). Map every common modification task to exact line ranges.
3. **Forgetting subdirectory AGENTS.md files.** `.hermes/hermes-agent/AGENTS.md` and `.hermes/plugins/<name>/AGENTS.md` load when you `cd` into those dirs. `skip_context_files` blocks them all.
4. **Not verifying with a real session.** After pruning, run `hermes chat -q "¿Quién soy?"` to verify core identity and memory still work.
5. **Pruning before understanding what's critical.** Always run the classification script (Phase 2) before deleting anything.
5. **Deleting the full AGENTS.md.** Never delete it — keep it accessible via path reference with exact offsets for surgical reads.
6. **"Subdirectory context discovered" bypass (v0.11.0).** Hermes v0.11.0 has a separate mechanism that auto-injects AGENTS.md/CLAUDE.md/GEMINI.md when accessed during a session — even with `skip_context_files: true`. Rename the file (e.g., `AGENTS_DEV.md`) to evade detection. Verify after each `hermes update` as it may recreate the original filename.
7. **Not testing after Hermes updates.** Updates can restore AGENTS.md, change context loading behavior, or add new detection mechanisms. Always run `ls -la` on the renamed file to confirm it doesn't trigger injection.

---

## Verification Checklist

- [ ] `hermes config set context.skip_context_files true` applied
- [ ] AGENTS_INDEX.md ≤ 2,500 chars (~600 tokens)
- [ ] Critical policies (prompt caching, role alternation) preserved
- [ ] Quick reference table contains frequently used commands
- [ ] Custom plugins documented with paths
- [ ] Full AGENTS.md renamed to AGENTS_DEV.md (v0.11.0+ auto-injection evasion)
- [ ] `ls -la` on renamed file does NOT trigger auto-injection
- [ ] `vex_mods/hermes-poda.md` created with full audit trail
- [ ] Test session: identity preserved, memory works, no timeouts
- [ ] Rollback path documented

---

## One-Shot Recipe

```bash
# 1. Audit
find . ~/.hermes -name "AGENTS.md" -o -name "CLAUDE.md" | xargs wc -c

# 2. Apply pruning
hermes config set context.skip_context_files true

# 3. Create slim index (use write_file)
# Template above → target ~500 tokens

# 4. Document (use write_file to vex_mods/hermes-poda.md)
# Full audit trail template above

# 5. Verify
hermes chat -q "¿Quién eres y qué recuerdas de mí?" --quiet
```

---

## Real-World Results (DeepSeek v4, Apr 2026)

| Métrica | Antes | Después |
|---|---|---|
| AGENTS.md tokens in context | ~8,767 | ~558 |
| Total context files | 3 (42 KB) | 1 (2.2 KB) |
| Reducción | — | 94% |
| Response time | 2min 30s → timeout | <30s |
| Identity preserved | ✓ | ✓ |
| Memory (Memovex) | ✓ | ✓ |
| Plugin functionality | ✓ | ✓ |
