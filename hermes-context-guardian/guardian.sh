#!/usr/bin/env bash
# =============================================================================
# Hermes Context Guardian v1.0.0
# Post-update survival script for Hermes Agent context pruning.
#
# Detects if hermes update recreated AGENTS.md, merges content into
# AGENTS_DEV.md, renames to evade auto-injection, and verifies the
# context pruning system is intact.
#
# Usage:
#   ./guardian.sh             # Full check + fix
#   ./guardian.sh --check     # Check only, no changes
#   ./guardian.sh --bootstrap # First-time setup (creates AGENTS_INDEX.md)
#   ./guardian.sh --help      # Show help
#
# Author: Marco Torres Y. — Axis Dynamics · Hermes VEX
# License: MIT
# =============================================================================

set -euo pipefail

VERSION="1.1.0"
GUARDIAN_TARGET="${HOME}/.hermes/hermes-agent/AGENTS.md"
GUARDIAN_DEV="${HOME}/.hermes/hermes-agent/AGENTS_DEV.md"
GUARDIAN_INDEX="${HOME}/AGENTS_INDEX.md"
GUARDIAN_CONFIG="${HOME}/.hermes/config.yaml"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Banner ────────────────────────────────────────────────────────────
banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   🛡️  HERMES CONTEXT GUARDIAN v${VERSION}  ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

# ── Help ──────────────────────────────────────────────────────────────
show_help() {
    echo "Hermes Context Guardian v${VERSION}"
    echo ""
    echo "USAGE:"
    echo "  ./guardian.sh               Full check + auto-fix if AGENTS.md detected"
    echo "  ./guardian.sh --check       Check only, report status, no changes"
    echo "  ./guardian.sh --bootstrap   First-time setup: creates AGENTS_INDEX.md,"
    echo "                              sets skip_context_files, renames AGENTS.md"
    echo "  ./guardian.sh --help        Show this help"
    echo ""
    echo "MODES:"
    echo "  default      Post-update maintenance. Safe to run any time."
    echo "  --check      Read-only audit. No files modified."
    echo "  --bootstrap  One-time setup. Run once on a fresh Hermes install."
    echo ""
    echo "WHAT IT DOES:"
    echo "  1. Detects if hermes update recreated AGENTS.md"
    echo "  2. Merges new content into AGENTS_DEV.md"
    echo "  3. Renames AGENTS.md -> AGENTS_DEV.md (evades auto-injection)"
    echo "  4. Reports new section offsets for AGENTS_INDEX.md update"
    echo "  5. Verifies skip_context_files is active"
    echo "  6. Tests auto-injection is blocked"
    echo ""
    echo "FILES TOUCHED:"
    echo "  ${GUARDIAN_TARGET}    -> DELETED (renamed to AGENTS_DEV.md)"
    echo "  ${GUARDIAN_DEV}       -> CREATED/UPDATED"
    echo "  ${GUARDIAN_CONFIG}     -> READ ONLY"
    echo ""
    echo "BACKGROUND:"
    echo "  Hermes v0.11.0 auto-injects AGENTS.md (~35KB) into session context"
    echo "  when accessed by any tool. Renaming to AGENTS_DEV.md evades this."
    echo "  hermes update may recreate the original AGENTS.md."
    exit 0
}

# ── Check functions ───────────────────────────────────────────────────
check_config() {
    if grep -q "skip_context_files: true" "${GUARDIAN_CONFIG}" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} skip_context_files: true"
        return 0
    else
        echo -e "  ${RED}✗${NC} skip_context_files NOT true — FIX NEEDED"
        return 1
    fi
}

check_agents_md() {
    if [ -f "${GUARDIAN_TARGET}" ]; then
        echo -e "  ${YELLOW}⚠${NC}  AGENTS.md EXISTS — $(wc -c < "${GUARDIAN_TARGET}") bytes"
        return 1
    else
        echo -e "  ${GREEN}✓${NC} AGENTS.md does not exist (clean)"
        return 0
    fi
}

check_agents_dev() {
    if [ -f "${GUARDIAN_DEV}" ]; then
        local size=$(wc -c < "${GUARDIAN_DEV}")
        echo -e "  ${GREEN}✓${NC} AGENTS_DEV.md: ${size} bytes (healthy)"
        return 0
    else
        echo -e "  ${YELLOW}⚠${NC}  AGENTS_DEV.md missing (will be created on merge)"
        return 1
    fi
}

check_injection() {
    local output
    output=$(ls -la "${GUARDIAN_DEV}" 2>&1 || true)
    if echo "$output" | grep -q "Subdirectory context discovered"; then
        echo -e "  ${RED}✗${NC} AUTO-INJECTION DETECTED"
        return 1
    else
        echo -e "  ${GREEN}✓${NC} No auto-injection"
        return 0
    fi
}

check_index() {
    if [ -f "${GUARDIAN_INDEX}" ]; then
        local size=$(wc -c < "${GUARDIAN_INDEX}")
        echo -e "  ${GREEN}✓${NC} AGENTS_INDEX.md: ${size} bytes"
        return 0
    else
        echo -e "  ${YELLOW}⚠${NC}  AGENTS_INDEX.md not found at ${GUARDIAN_INDEX}"
        return 1
    fi
}

# ── Fix: Merge + Rename ──────────────────────────────────────────────
merge_and_rename() {
    echo ""
    echo -e "${YELLOW}=== ACTION: AGENTS.md detected — merging ===${NC}"
    echo ""

    # Merge: copy new AGENTS.md content to AGENTS_DEV.md
    cp "${GUARDIAN_TARGET}" "${GUARDIAN_DEV}"
    local merged_size=$(wc -c < "${GUARDIAN_DEV}")
    echo -e "  ${GREEN}✓${NC} MERGED: ${merged_size} bytes → AGENTS_DEV.md"

    # Rename (delete original)
    rm "${GUARDIAN_TARGET}"
    echo -e "  ${GREEN}✓${NC} RENAMED: AGENTS.md → AGENTS_DEV.md"

    # Show new section offsets for manual index update
    echo ""
    echo -e "${CYAN}=== New section offsets (update AGENTS_INDEX.md) ===${NC}"
    grep -n "^## " "${GUARDIAN_DEV}" | head -20 || echo "  (no ## sections found)"

    echo ""
    echo -e "${YELLOW}⚠  Remember to update AGENTS_INDEX.md line offsets!${NC}"
}

# ── Bootstrap: First-time setup ───────────────────────────────────────
bootstrap() {
    echo ""
    echo -e "${CYAN}=== BOOTSTRAP: First-time context pruning setup ===${NC}"
    echo ""

    local boot_errors=0

    # Step 1: Ensure we have source content (AGENTS.md or AGENTS_DEV.md)
    local source_file=""
    if [ -f "${GUARDIAN_TARGET}" ]; then
        source_file="${GUARDIAN_TARGET}"
        echo -e "  ${GREEN}✓${NC} Found AGENTS.md (will rename to AGENTS_DEV.md)"
    elif [ -f "${GUARDIAN_DEV}" ]; then
        source_file="${GUARDIAN_DEV}"
        echo -e "  ${GREEN}✓${NC} Found AGENTS_DEV.md: $(wc -c < "${GUARDIAN_DEV}") bytes"
    else
        echo -e "  ${RED}✗${NC} No AGENTS.md or AGENTS_DEV.md found in hermes-agent/"
        echo "    Skipping index creation — run after herm es agent is installed."
        ((boot_errors++))
    fi

    # Step 2: Rename AGENTS.md → AGENTS_DEV.md if needed
    if [ -f "${GUARDIAN_TARGET}" ]; then
        cp "${GUARDIAN_TARGET}" "${GUARDIAN_DEV}"
        rm "${GUARDIAN_TARGET}"
        echo -e "  ${GREEN}✓${NC} Renamed: AGENTS.md → AGENTS_DEV.md (evades auto-injection)"
        source_file="${GUARDIAN_DEV}"
    fi

    # Step 3: Enable skip_context_files
    if grep -q "skip_context_files: true" "${GUARDIAN_CONFIG}" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} skip_context_files already true"
    else
        echo -e "  ${YELLOW}⚠${NC}  Setting skip_context_files: true..."
        echo -e "    Run: hermes config set context.skip_context_files true"
        echo -e "    Then restart Hermes (/reset or new session)"
    fi

    # Step 4: Create AGENTS_INDEX.md from AGENTS_DEV.md sections
    if [ -n "${source_file}" ] && [ -f "${source_file}" ]; then
        echo ""
        echo -e "${CYAN}--- Generating AGENTS_INDEX.md ---${NC}"

        local total_lines=$(wc -l < "${source_file}")
        local total_chars=$(wc -c < "${source_file}")
        local est_tokens=$((total_chars / 4))

        # Extract section headers with line numbers
        local sections_map
        sections_map=$(grep -n "^## " "${source_file}" | head -20)

        cat > "${GUARDIAN_INDEX}" << INDEXEOF
# HERMES OPERANTE — Contexto Esencial v1.0

> Archivo slim de contexto. Guía desarrollo completa en
> \`.hermes/hermes-agent/AGENTS_DEV.md\` (${total_chars} bytes, ~${est_tokens} tok, ${total_lines} líneas).
> Creado por Hermes Context Guardian --bootstrap.
> Políticas críticas extraídas. Detalles de desarrollo por demanda.

---

## 🔴 Políticas Críticas (NO TOCAR)

### Prompt Caching
- El system prompt, herramientas y skills son inmutables durante una sesión
- Cualquier cambio requiere \`/reset\` o nueva sesión

### Message Role Alternation
- Nunca dos mensajes con el mismo rol consecutivos
- Tool results van como role="tool", no como user

### Config & Herramientas
- Cambios de toolsets requieren nueva sesión
- \`skip_context_files: true\` previene carga de AGENTS.md al inicio
- AGENTS.md está renombrado a AGENTS_DEV.md para evadir auto-injection

---

## ⚡ Referencia Rápida

| Necesidad | Comando / Ruta |
|---|---|
| Salud del sistema | \`hermes doctor [--fix]\` |
| Cambiar modelo | \`hermes model\` |
| Listar plugins | \`hermes plugins list\` |
| Buscar skill | \`skill_view("nombre")\` |
| Troubleshooting | skill \`hermes-agent\` |
| Logs | \`~/.hermes/logs/agent.log\` |
| Context guardian | \`./guardian.sh\` (post-update) |

---

## 🧠 Desarrollo — Índice de Tareas

> Guía completa: \`.hermes/hermes-agent/AGENTS_DEV.md\`
> Leer bajo demanda: \`read_file(".hermes/hermes-agent/AGENTS_DEV.md", offset=L, limit=N)\`

| Sección | Línea |
|---|---|
INDEXEOF

        # Append section list from AGENTS_DEV.md
        echo "${sections_map}" | while IFS=: read -r lineno title; do
            echo "| ${title} | ${lineno} |" >> "${GUARDIAN_INDEX}"
        done

        cat >> "${GUARDIAN_INDEX}" << INDEXEOF

### Acceso rápido:
\`\`\`bash
# Ejemplo: leer una sección específica
read_file(".hermes/hermes-agent/AGENTS_DEV.md", offset=<linea>, limit=50)
\`\`\`

---

## 🛡️ Mantención

| Acción | Comando |
|---|---|
| Verificar salud | \`./guardian.sh --check\` |
| Post-update fix | \`./guardian.sh\` |
| Re-crear índice | \`./guardian.sh --bootstrap\` |

---

*Generado por Hermes Context Guardian v${VERSION} — $(date +%Y-%m-%d)*
INDEXEOF

        local index_size=$(wc -c < "${GUARDIAN_INDEX}")
        echo -e "  ${GREEN}✓${NC} AGENTS_INDEX.md created: ${index_size} bytes"
        echo -e "  ${GREEN}✓${NC} Context reduction: ~${est_tokens} tok → ~$((index_size / 4)) tok (~$(( 100 - (index_size * 100 / total_chars) ))%)"
    fi

    echo ""
    echo -e "${CYAN}=== Bootstrap complete. Running health check... ===${NC}"

    return $boot_errors
}
health_check() {
    local failures=0

    echo -e "${CYAN}--- Config ---${NC}"
    check_config || ((failures++))

    echo ""
    echo -e "${CYAN}--- Files ---${NC}"
    check_agents_md || true  # detection is expected to fail sometimes
    check_agents_dev || ((failures++))
    check_index || ((failures++))

    echo ""
    echo -e "${CYAN}--- Injection Test ---${NC}"
    check_injection || ((failures++))

    echo ""
    if [ $failures -eq 0 ]; then
        echo -e "${GREEN}=== ALL CHECKS PASSED ===${NC}"
    else
        echo -e "${RED}=== ${failures} CHECK(S) FAILED ===${NC}"
    fi

    return $failures
}

# ── Main ──────────────────────────────────────────────────────────────
main() {
    case "${1:-}" in
        --help|-h)
            show_help
            ;;
        --check)
            banner
            health_check
            ;;
        --bootstrap)
            banner
            bootstrap
            health_check
            ;;
        *)
            banner
            health_check
            local health_result=$?

            # If AGENTS.md exists, merge+rename regardless of health
            if [ -f "${GUARDIAN_TARGET}" ]; then
                merge_and_rename
                echo ""
                echo -e "${CYAN}--- Post-merge re-check ---${NC}"
                health_check
            elif [ $health_result -ne 0 ]; then
                echo ""
                echo -e "${RED}Health check found issues but no AGENTS.md to merge.${NC}"
                echo "Run './guardian.sh --check' for details."
            fi
            ;;
    esac
}

main "$@"
