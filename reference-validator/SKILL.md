---
name: reference-validator
description: "Use when verifying academic paper references are real, correctly cited, and contextually relevant. Verifies references against Semantic Scholar, arXiv, and CrossRef APIs — detects fabricated citations, incorrect metadata, and off-topic references."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, papers, validation, references, academic, integrity]
    related_skills: [arxiv, ocr-and-documents]
---

# Reference Validator

Verifies that every reference in an academic paper actually exists, is correctly cited, and belongs in context. Detects "hallucinated references" (AI-generated papers that don't exist), metadata mismatches, and references that have nothing to do with what the citing paper claims.

## Overview

When reviewing a paper — whether your own before submission, a peer's for review, or an AI-generated survey — the reference list is often the weakest link. This skill uses three independent scholarly APIs (Semantic Scholar, arXiv, CrossRef) to cross-validate each reference, then optionally assesses whether the cited paper is contextually relevant to the citing paper's topic.

**What it checks:**
- **Existence**: Does the reference exist in scholarly databases? (S2 + arXiv + CrossRef)
- **Accuracy**: Do title, authors, and year match between citation and source?
- **Relevance** (--deep): Does the cited paper's abstract and field of study align with the citing paper?

**Output**: Terminal report with ✓ verified / ⚠ uncertain / ✗ not found / ⚡ context mismatch + optional JSON export.

## When to Use

- Reviewing a paper before submission — catch missing/broken references
- Peer review — flag suspicious or fabricated citations
- Vetting AI-generated papers or literature reviews — LLMs hallucinate references
- Literature survey quality check — are all cited sources real and relevant?
- Due diligence on any academic manuscript

**Don't use for:**
- Papers without DOIs or arXiv IDs (the tool needs a starting identifier)
- Checking citation formatting style (APA/MLA/etc) — this validates existence, not style
- Papers where you need 100% coverage (APIs are rate-limited, large ref lists take time)

## Quick Start

```bash
# Basic verification (first 30 references)
python3 scripts/validate_references.py --arxiv 1706.03762

# With contextual relevance analysis
python3 scripts/validate_references.py --arxiv 1706.03762 --deep

# Via DOI
python3 scripts/validate_references.py --doi 10.1038/nature14539

# Limit to first 10 references, export JSON
python3 scripts/validate_references.py --arxiv 2402.03300 --max 10 --output report.json
```

No API keys required. Works offline after the initial API calls. Rate-limited to respect scholarly APIs (~1 ref/sec).

## Output Interpretation

| Symbol | Status | Meaning |
|--------|--------|---------|
| ✓ | verified | Found in ≥1 database with high confidence match (score > 0.9) |
| ⚠ | uncertain | Found but metadata mismatch (score 0.7-0.9) — wrong year? typo in title? |
| ✗ | not_found | Not found in any database — likely fabricated or badly malformed |
| ⚡ | context_mismatch | Paper exists but abstract/fields don't align with citing paper (--deep only) |

**Salud bibliográfica** = (verified + uncertain) / total × 100. Below 70% is a red flag.

## How It Works

### Phase 1: Fetch Paper Metadata
- Queries Semantic Scholar by arXiv ID or DOI to get: title, authors, year, abstract, fields of study, reference count.

### Phase 2: Fetch Reference List
- Semantic Scholar `/references` endpoint returns all papers cited by the target paper, including titles, authors, years, abstracts, and external IDs.

### Phase 3: Multi-Source Verification
For each reference, queries three APIs in parallel:

| Source | What it provides | Best for |
|--------|-----------------|----------|
| Semantic Scholar | Title search → paper metadata, citations | CS/AI/ML papers, citation counts |
| arXiv API | Title search → arXiv ID, categories | CS, math, physics preprints |
| CrossRef | Title + author → DOI, publisher | Published journal papers, DOIs |

A reference is "verified" if found in ≥1 source with fuzzy title match > 0.7 and reasonable year/author overlap.

### Phase 4: Contextual Relevance (--deep)
Compares the citing paper's fields of study and abstract keywords against each reference:
- **Fields of study overlap** (40% weight): e.g., if paper is "cs.CL" and ref is "cs.CV" → low overlap
- **Abstract keyword intersection** (35% weight): extracts significant words, counts shared terms
- **Citation count** (15% weight): 0-citation papers are flagged as potential preprints or low quality
- **Title similarity** (10% weight): penalizes completely unrelated titles

Score < 0.15 triggers ⚡ context_mismatch status.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Healthy: all references verified or within acceptable range |
| 1 | Error: paper not found or API failure |
| 2 | Suspicious: >30% of references not found |
| 3 | Context issues: at least one context_mismatch detected (--deep) |

## Integration with Hermes Agent

Load the skill and run validation directly:

```
/skill reference-validator

# Then in conversation:
Valida las referencias del paper arXiv:2402.03300 con --deep
```

The script lives at `~/.hermes/skills/research/reference-validator/scripts/validate_references.py`.

## Common Pitfalls

1. **Rate limiting**: Semantic Scholar allows 1 req/sec without API key. Large reference lists (50+) will take 1-2 minutes. Use `--max` to limit checks during quick reviews.

2. **arXiv IDs with version suffixes**: Use `1706.03762` not `1706.03762v7`. The script strips version suffixes automatically.

3. **Papers without Semantic Scholar coverage**: Very new papers (< 1 week old), obscure journals, or non-English papers may not appear in S2. A ✗ result doesn't always mean fabrication — check manually.

4. **Title mismatches due to special characters**: LaTeX math, Unicode, or formatting differences can reduce fuzzy match scores. The script handles common cases but edge cases exist.

5. **Contextual relevance is heuristic**: A ⚡ doesn't mean the reference is wrong — it means the automated analysis couldn't confirm relevance. Always review context_mismatch cases manually.

6. **--deep mode is API-heavy**: Each reference requires additional abstract fetching. Use sparingly on papers with >30 references.

7. **The script uses urllib (stdlib), not requests**: If you're extending it, avoid importing requests — keep it zero-dependency.

## Known Limitations & Test Data

See `references/session-test-20260512.md` for a real test run on "Attention Is All You Need" — includes 3 documented false negatives from S2 coverage gaps (ICLR 2016-2017 papers) and mitigation strategies.

## Verification Checklist

- [ ] Script is executable: `python3 scripts/validate_references.py --arxiv 1706.03762`
- [ ] Returns structured report with verified/uncertain/not_found counts
- [ ] `--deep` flag adds relevance scores and context_mismatch detection
- [ ] `--output report.json` writes valid JSON
- [ ] Exit codes: 0 on success, 1 on error, 2 on >30% not_found, 3 on context_mismatch
- [ ] Works with both `--arxiv` and `--doi` inputs
- [ ] Handles papers with 0 references gracefully
- [ ] Handles API errors without crashing (retries with backoff)
