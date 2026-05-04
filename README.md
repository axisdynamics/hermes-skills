# Hermes Operante Skills 🧠⚡

> Colección de skills forjadas por **Marco Torres Y.** — [Axis Dynamics](https://axisdynamics.cl)
> en colaboración con **Hermes VEX**. Optimización de contexto,
> automatización post-update, y más.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes](https://img.shields.io/badge/Hermes-v0.11.0%2B-blue)](https://github.com/NousResearch/hermes-agent)

---

## ¿Qué es esto?

Skills utilitarias para [Hermes Agent](https://github.com/NousResearch/hermes-agent)
que resuelven problemas reales del día a día operando agentes de IA. Cada skill
es independiente y se puede instalar por separado.

---

## Skills Disponibles

| Skill | Versión | Propósito | Una línea |
|-------|---------|-----------|-----------|
| [hermes-context-guardian](hermes-context-guardian/) | v1.1.0 | 🛡️ Bootstrap + post-update | Setup + supervivencia. Autosuficiente — no requiere pruning. |
| [hermes-context-pruning](hermes-context-pruning/) | v1.0.0 | ✂️ Referencia | Diagnóstico detallado + poda manual. Opcional — el guardian ya cubre todo. |

---

## Instalación

Cada skill se instala de forma independiente:

```bash
# Desde el repo (recomendado)
hermes skills install https://raw.githubusercontent.com/plaxius/hermes-skills/main/hermes-context-guardian/SKILL.md

# O clona todo y enlaza
git clone https://github.com/plaxius/hermes-skills.git
hermes skills install ./hermes-skills/hermes-context-guardian/SKILL.md
```

---

## Flujo Recomendado

```
┌──────────────────────────────────┐
│ 1. ./guardian.sh --bootstrap     │  Una sola vez. Crea el índice,
│    (first-time setup)            │  renombra AGENTS.md, configura todo.
└───────────────┬──────────────────┘
                │
                ▼
┌──────────────────────────────────┐
│ 2. ./guardian.sh                 │  Después de cada hermes update.
│    (post-update recurrente)      │  Sobrevive. Verifica. Repara.
└──────────────────────────────────┘
```

**El guardian es autosuficiente** — no requiere `hermes-context-pruning`.
El pruning queda como referencia para quienes quieran entender el diagnóstico
completo o personalizar su índice manualmente.

---

## ¿Por qué existen estas skills?

**El problema**: Hermes v0.11.0 tiene un mecanismo "Subdirectory context
discovered" que inyecta el `AGENTS.md` completo (~35KB / 8,700 tokens) al
contexto de cada sesión cuando cualquier herramienta lo toca — incluso con
`skip_context_files: true`.

**La solución**: Podar a un índice slim de ~470 tokens y renombrar el
archivo para evadir el detector. El guardian automatiza la supervivencia
frente a `hermes update`.

| Sin skills | Con skills |
|------------|------------|
| 8,700 tok por sesión | 470 tok por sesión |
| 94.6% más contexto | **94.6% ahorrado** |

---

## Contribuir

¿Tienes una skill que resuelve un dolor real operando Hermes? PRs bienvenidos.

Estructura de una skill en este repo:

```
hermes-skills/
├── mi-skill/
│   ├── SKILL.md         # El skill (formato Hermes, obligatorio)
│   ├── README.md        # Documentación humana
│   ├── install.sh       # Script de instalación (opcional)
│   └── ...              # Scripts auxiliares
└── README.md            # Este archivo
```

---

## Autores

Forjado por **Marco Torres Y.** — [Axis Dynamics](https://axisdynamics.cl)
en colaboración con **Hermes VEX**.

Parte del ecosistema Memovex / VEX / Hermes.

---

## Licencia

MIT — usa, modifica, comparte. Solo mantén la atribución.
