# Hermes VEX Skills 🧠⚡

> A collection of skills forged by **Marco Torres Y.** — [Axis Dynamics](https://axisdynamics.cl)
> in collaboration with **Hermes VEX**. Context optimization, post-update
> automation, and more.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes](https://img.shields.io/badge/Hermes-v0.11.0%2B-blue)](https://github.com/NousResearch/hermes-agent)

---

## What is this?

Utility skills for [Hermes Agent](https://github.com/NousResearch/hermes-agent)
that solve real day-to-day problems when operating AI agents. Each skill is
independent and can be installed separately.

---

## Available Skills

| Skill | Version | Purpose | TL;DR |
|-------|---------|---------|-------|
| [hermes-context-guardian](hermes-context-guardian/) | v1.1.0 | 🛡️ Bootstrap + post-update | Self-sufficient setup & survival. No pruning skill required. |
| [hermes-context-pruning](hermes-context-pruning/) | v1.0.0 | ✂️ Reference | Detailed audit + manual prune. Optional — guardian handles it all. |
| [AI-Cyber-Range](AI-Cyber-Range/) | v1.1.0 | 🌌 AI Cyber Range → VEX | Recreate the safe `axisdynamics/ai_cyber_range_project` bridge: VEX telemetry, CLI status/publish, defensive handoff, tests, and verification. |

---

## Installation

Each skill installs independently:

```bash
# From the repo (recommended)
hermes skills install https://raw.githubusercontent.com/axisdynamics/hermes-skills/main/hermes-context-guardian/SKILL.md

# Or clone everything and link
git clone https://github.com/axisdynamics/hermes-skills.git
hermes skills install ./hermes-skills/hermes-context-guardian/SKILL.md
```

---

## Recommended Flow

```
┌──────────────────────────────────┐
│ 1. ./guardian.sh --bootstrap     │  Once. Creates the index,
│    (first-time setup)            │  renames AGENTS.md, configures everything.
└───────────────┬──────────────────┘
                │
                ▼
┌──────────────────────────────────┐
│ 2. ./guardian.sh                 │  After every hermes update.
│    (recurring post-update)       │  Survives. Verifies. Repairs.
└──────────────────────────────────┘
```

**The guardian is self-sufficient** — it doesn't need `hermes-context-pruning`.
Pruning remains as a reference for those who want to understand the full
diagnostic or customize their index manually.

---

## Why These Skills Exist

**The problem**: Hermes v0.11.0 has a "Subdirectory context discovered"
mechanism that injects the full `AGENTS.md` (~35KB / 8,700 tokens) into
every session's context whenever any tool touches the file — even with
`skip_context_files: true`.

**The solution**: Prune to a slim index of ~470 tokens and rename the
file to evade the detector. The guardian automates survival across
`hermes update` cycles.

| Without skills | With skills |
|----------------|-------------|
| 8,700 tok per session | 470 tok per session |
| 94.6% more context | **94.6% saved** |

---

## Contributing

Got a skill that solves a real pain point operating Hermes? PRs welcome.

Skill structure in this repo:

```
hermes-skills/
├── my-skill/
│   ├── SKILL.md         # The skill (Hermes format, required)
│   ├── README.md        # Human-readable docs
│   ├── install.sh       # Install script (optional)
│   └── ...              # Helper scripts
└── README.md            # This file
```

---

## Authors

Forged by **Marco Torres Y.** — [Axis Dynamics](https://axisdynamics.cl)
in collaboration with **Hermes VEX**.

Part of the Memovex / VEX / Hermes ecosystem.

---

## License

MIT — use it, modify it, share it. Just keep the attribution.
