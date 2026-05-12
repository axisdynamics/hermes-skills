#!/usr/bin/env python3
"""
Reference Validator — verifies academic paper references are real, correct,
and contextually relevant to the citing paper.

Uses: Semantic Scholar API (primary), arXiv API (secondary), CrossRef API (DOI verification)
No API keys required. Stdlib-only + urllib. Respects rate limits.

Usage:
  python3 validate_references.py --arxiv 1706.03762
  python3 validate_references.py --arxiv 1706.03762 --deep        # full abstract comparison
  python3 validate_references.py --arxiv 1706.03762 --max 20      # check first 20 refs
  python3 validate_references.py --doi 10.1038/nature14539
  python3 validate_references.py --arxiv 1706.03762 --output report.json
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from collections import Counter

# ─── API Endpoints ───────────────────────────────────────────────
S2_API = "https://api.semanticscholar.org/graph/v1"
ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"

# Rate limiting: Semantic Scholar = 1 req/s, arXiv = 1 req/3s, CrossRef = polite
S2_DELAY = 1.1
ARXIV_DELAY = 3.5
CROSSREF_DELAY = 0.5

# ─── HTTP Helpers ────────────────────────────────────────────────
def _fetch(url, headers=None, retries=3):
    """GET a URL, return parsed JSON or raw text. Retries on transient errors."""
    req = urllib.request.Request(url, headers=headers or {})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                content_type = resp.headers.get("Content-Type", "")
                if "json" in content_type:
                    return json.loads(raw)
                return raw
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # Not found is a valid result
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None
        except (urllib.error.URLError, OSError):
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None


def _similarity(a, b):
    """Fuzzy string similarity 0-1."""
    if not a or not b:
        return 0.0
    a = a.lower().strip()
    b = b.lower().strip()
    return SequenceMatcher(None, a, b).ratio()


def _extract_keywords(text, top_n=10):
    """Extract significant lowercase words from text, filtering stopwords."""
    if not text:
        return set()
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "both", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "just", "that", "this", "these", "those", "which",
        "and", "but", "or", "if", "while", "although", "because", "unless",
        "until", "about", "also", "thus", "however", "therefore", "using",
        "based", "proposed", "show", "used", "new", "one", "two", "first",
        "well", "yet", "still", "via", "et", "al"
    }
    words = text.lower().split()
    filtered = [w.strip(".,;:()[]{}'\"!?-") for w in words
                if w.strip(".,;:()[]{}'\"!?-") not in stopwords
                and len(w.strip(".,;:()[]{}'\"!?-")) > 2]
    counter = Counter(filtered)
    return {w for w, _ in counter.most_common(top_n)}


# ─── Paper Fetching ──────────────────────────────────────────────
def get_paper_by_arxiv(arxiv_id):
    """Get paper metadata from Semantic Scholar by arXiv ID."""
    clean_id = arxiv_id.strip()
    fields = "title,authors,year,abstract,citationCount,referenceCount,fieldsOfStudy,externalIds,publicationVenue"
    url = f"{S2_API}/paper/arXiv:{clean_id}?fields={fields}"
    time.sleep(S2_DELAY)
    return _fetch(url)


def get_paper_by_doi(doi):
    """Get paper metadata from Semantic Scholar by DOI."""
    clean_doi = doi.strip()
    fields = "title,authors,year,abstract,citationCount,referenceCount,fieldsOfStudy,externalIds"
    url = f"{S2_API}/paper/DOI:{urllib.parse.quote(clean_doi, safe='')}?fields={fields}"
    time.sleep(S2_DELAY)
    return _fetch(url)


def get_references(paper_id, limit=50):
    """Get the list of references for a paper from Semantic Scholar.
    paper_id can be 'arXiv:XXXX.XXXXX' or 'DOI:...'."""
    clean = paper_id.strip()
    fields = "title,authors,year,citationCount,externalIds,abstract,fieldsOfStudy,publicationVenue"
    refs = []
    offset = 0
    batch = min(limit, 500)

    while len(refs) < limit:
        url = f"{S2_API}/paper/{urllib.parse.quote(clean, safe='')}/references"
        url += f"?fields={fields}&limit={batch}&offset={offset}"
        time.sleep(S2_DELAY)
        data = _fetch(url)
        if not data or "data" not in data:
            break
        for item in data["data"]:
            if "citedPaper" in item:
                refs.append(item["citedPaper"])
            if len(refs) >= limit:
                break
        if len(data.get("data", [])) < batch:
            break
        offset += batch
    return refs


# ─── Verification ────────────────────────────────────────────────
def verify_arxiv(title, authors, year):
    """Search arXiv for a paper by title. Return best match or None."""
    query = urllib.parse.quote(title[:200].strip())
    url = f"{ARXIV_API}?search_query=ti:{query}&max_results=5"
    time.sleep(ARXIV_DELAY)
    raw = _fetch(url)
    if not raw:
        return None

    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None

    best = None
    best_score = 0
    for entry in root.findall("a:entry", ns):
        e_title = entry.find("a:title", ns)
        e_published = entry.find("a:published", ns)
        e_id = entry.find("a:id", ns)

        e_title_str = e_title.text.strip().replace("\n", " ") if e_title is not None else ""
        e_year = int(e_published.text[:4]) if e_published is not None else 0
        e_arxiv_id = e_id.text.strip().split("/abs/")[-1] if e_id is not None else ""

        title_sim = _similarity(title, e_title_str)
        year_match = 1.0 if year and e_year and abs(int(year) - e_year) <= 1 else 0.5
        score = 0.7 * title_sim + 0.3 * year_match

        if score > best_score and title_sim > 0.6:
            best_score = score
            best = {
                "arxiv_id": e_arxiv_id,
                "title": e_title_str,
                "year": e_year,
                "score": round(score, 3),
                "url": f"https://arxiv.org/abs/{e_arxiv_id}"
            }
    return best


def verify_semantic_scholar(title, authors=None):
    """Search Semantic Scholar by title. Return best match or None."""
    query = urllib.parse.quote(title[:200].strip())
    fields = "title,authors,year,citationCount,externalIds,fieldsOfStudy"
    url = f"{S2_API}/paper/search?query={query}&limit=3&fields={fields}"
    time.sleep(S2_DELAY)
    data = _fetch(url)
    if not data or "data" not in data:
        return None

    best = None
    best_score = 0
    for paper in data["data"]:
        p_title = paper.get("title", "")
        title_sim = _similarity(title, p_title)

        # Author similarity
        author_sim = 0.5
        if authors:
            expected_authors = {a.get("name", "").lower().split()[-1] for a in authors if a.get("name")}
            found_authors = {a.get("name", "").lower().split()[-1] for a in paper.get("authors", [])}
            if expected_authors and found_authors:
                overlap = expected_authors & found_authors
                author_sim = len(overlap) / max(len(expected_authors), 1)

        score = 0.6 * title_sim + 0.4 * author_sim
        if score > best_score and title_sim > 0.6:
            best_score = score
            doi = (paper.get("externalIds") or {}).get("DOI", "")
            arxiv_id = (paper.get("externalIds") or {}).get("ArXiv", "")
            best = {
                "paper_id": paper.get("paperId"),
                "title": p_title,
                "year": paper.get("year"),
                "citation_count": paper.get("citationCount", 0),
                "doi": doi,
                "arxiv_id": arxiv_id,
                "fields_of_study": paper.get("fieldsOfStudy", []),
                "score": round(score, 3)
            }
    return best


def verify_crossref(title, authors=None, year=None):
    """Verify paper exists in CrossRef by title + author. Returns DOI if found."""
    query = urllib.parse.quote(title[:200].strip())
    url = f"{CROSSREF_API}?query.title={query}&rows=3"
    if authors:
        author_str = " ".join(a.get("name", "") for a in authors[:2])
        url += f"&query.author={urllib.parse.quote(author_str[:100])}"
    time.sleep(CROSSREF_DELAY)
    data = _fetch(url)
    if not data or "message" not in data or "items" not in data["message"]:
        return None

    best = None
    best_score = 0
    for item in data["message"]["items"]:
        item_title = item.get("title", [""])[0] if item.get("title") else ""
        title_sim = _similarity(title, item_title)
        item_year = item.get("published-print", {}).get("date-parts", [[0]])[0][0]
        year_match = 1.0 if year and item_year and abs(int(year) - item_year) <= 1 else 0.5
        score = 0.7 * title_sim + 0.3 * year_match
        if score > best_score and title_sim > 0.6:
            best_score = score
            best = {
                "doi": item.get("DOI"),
                "title": item_title,
                "year": item_year,
                "publisher": item.get("publisher", ""),
                "score": round(score, 3)
            }
    return best


# ─── Contextual Relevance ────────────────────────────────────────
def evaluate_relevance(paper_context, ref_data, ref_abstract=None):
    """
    Evaluate whether a reference is contextually relevant to the citing paper.
    Compares fields of study and keyword overlap between abstracts.

    Returns: (relevance_score, explanation)
      - 0.0-1.0 score
      - explanation string
    """
    score = 0.0
    reasons = []

    # 1. Fields of Study overlap
    paper_fields = set(paper_context.get("fieldsOfStudy") or [])
    paper_field_lower = {f.lower() for f in paper_fields}
    ref_fields = set(ref_data.get("fieldsOfStudy") or ref_data.get("fields_of_study") or [])
    ref_field_lower = {f.lower() for f in ref_fields}

    if paper_field_lower and ref_field_lower:
        overlap = paper_field_lower & ref_field_lower
        field_score = len(overlap) / max(len(paper_field_lower), 1)
        score += 0.4 * field_score
        if field_score > 0:
            reasons.append(f"campos compartidos: {', '.join(overlap)}")
        else:
            reasons.append(f"sin campos compartidos (paper: {paper_fields}, ref: {ref_fields})")

    # 2. Abstract keyword overlap
    paper_abstract = paper_context.get("abstract", "")
    if paper_abstract and ref_abstract:
        paper_kw = _extract_keywords(paper_abstract)
        ref_kw = _extract_keywords(ref_abstract)
        if paper_kw and ref_kw:
            overlap = paper_kw & ref_kw
            kw_score = len(overlap) / max(len(paper_kw), 0.5)
            score += 0.35 * kw_score
            if kw_score > 0.1:
                reasons.append(f"keywords compartidos ({len(overlap)}): {', '.join(sorted(overlap)[:8])}")
            else:
                reasons.append("sin keywords compartidos entre abstracts")

    # 3. Citation count (papers with 0 citations might be preprints or low quality)
    citations = ref_data.get("citationCount", ref_data.get("citation_count", 0))
    if citations is None:
        citations = 0
    if citations == 0:
        reasons.append("0 citas — posible preprint oscuro o paper marginal")
        score += 0.1  # slight penalty but not decisive
    elif citations > 50:
        score += 0.15
        reasons.append(f"paper establecido ({citations} citas)")
    else:
        score += 0.08

    return min(score, 1.0), "; ".join(reasons) if reasons else "sin datos para evaluar"


# ─── Main Validation Pipeline ────────────────────────────────────
def validate_paper(arxiv_id=None, doi=None, max_refs=30, deep=False):
    """Main entry point. Returns a structured report dict."""
    report = {
        "paper": {},
        "references_checked": 0,
        "verified": 0,
        "uncertain": 0,
        "not_found": 0,
        "context_mismatch": 0,
        "results": []
    }

    # 1. Get primary paper metadata
    if arxiv_id:
        clean = arxiv_id.strip()
        paper_id = f"arXiv:{clean}"
        paper = get_paper_by_arxiv(clean)
    elif doi:
        clean = doi.strip()
        paper_id = f"DOI:{clean}"
        paper = get_paper_by_doi(clean)
    else:
        return {"error": "Must provide --arxiv or --doi"}

    if not paper:
        return {"error": f"Paper not found: {paper_id}"}

    report["paper"] = {
        "title": paper.get("title", ""),
        "authors": [a.get("name", "") for a in paper.get("authors", [])],
        "year": paper.get("year"),
        "citation_count": paper.get("citationCount", 0),
        "reference_count": paper.get("referenceCount", 0),
        "fields_of_study": paper.get("fieldsOfStudy", []),
        "abstract": paper.get("abstract", "")[:500] if paper.get("abstract") else "",
        "id": paper_id
    }

    print(f"\n📄 Paper: {paper.get('title', 'N/A')}")
    print(f"   Autores: {', '.join(report['paper']['authors'][:5])}")
    print(f"   Año: {paper.get('year')} | Citas: {paper.get('citationCount')}")
    print(f"   Referencias totales: {paper.get('referenceCount')}")
    print(f"\n🔍 Verificando referencias (máx {max_refs})...\n")

    # 2. Get references
    refs = get_references(paper_id, limit=max_refs)
    report["references_checked"] = len(refs)

    # 3. Verify each reference
    for i, ref in enumerate(refs):
        ref_title = ref.get("title", "")
        ref_authors = ref.get("authors", [])
        ref_year = ref.get("year")
        ref_abstract = ref.get("abstract", "")
        ref_doi = (ref.get("externalIds") or {}).get("DOI", "")
        ref_arxiv = (ref.get("externalIds") or {}).get("ArXiv", "")

        if not ref_title:
            print(f"  [{i+1}] ⚠ SKIP — sin título\n")
            report["not_found"] += 1
            continue

        print(f"  [{i+1}] {ref_title[:100]}...")
        sys.stdout.flush()

        result = {
            "index": i + 1,
            "cited_title": ref_title,
            "cited_authors": [a.get("name", "") for a in ref_authors],
            "cited_year": ref_year,
            "cited_doi": ref_doi,
            "cited_arxiv": ref_arxiv,
            "status": "unknown",
            "evidence": {},
            "relevance": None,
            "relevance_explanation": ""
        }

        # Multi-source verification
        found_any = False
        best_evidence = None
        best_score = 0

        # A. Check Semantic Scholar by title
        s2_result = verify_semantic_scholar(ref_title, ref_authors)
        if s2_result and s2_result["score"] > 0.7:
            found_any = True
            result["evidence"]["semantic_scholar"] = s2_result
            if s2_result["score"] > best_score:
                best_score = s2_result["score"]
                best_evidence = s2_result

        # B. Check arXiv
        arxiv_result = verify_arxiv(ref_title, ref_authors, ref_year)
        if arxiv_result and arxiv_result["score"] > 0.7:
            found_any = True
            result["evidence"]["arxiv"] = arxiv_result
            if arxiv_result["score"] > best_score:
                best_score = arxiv_result["score"]
                best_evidence = arxiv_result

        # C. Check CrossRef if we have author/year
        if ref_authors:
            crossref_result = verify_crossref(ref_title, ref_authors, ref_year)
            if crossref_result and crossref_result["score"] > 0.7:
                found_any = True
                result["evidence"]["crossref"] = crossref_result
                if crossref_result["score"] > best_score:
                    best_score = crossref_result["score"]
                    best_evidence = crossref_result

        # Determine status
        if found_any:
            if best_score > 0.9:
                result["status"] = "verified"
                report["verified"] += 1
                symbol = "✓"
            else:
                result["status"] = "uncertain"
                report["uncertain"] += 1
                symbol = "⚠"
        else:
            result["status"] = "not_found"
            report["not_found"] += 1
            symbol = "✗"

        # Contextual relevance (if deep mode and reference found)
        if deep and (found_any or ref_abstract):
            rel_score, rel_expl = evaluate_relevance(report["paper"], ref, ref_abstract)
            result["relevance"] = round(rel_score, 3)
            result["relevance_explanation"] = rel_expl

            if rel_score < 0.15 and found_any:
                result["status"] = "context_mismatch"
                report["context_mismatch"] += 1
                if symbol == "✓":
                    report["verified"] -= 1
                elif symbol == "⚠":
                    report["uncertain"] -= 1
                symbol = "⚡"

        # Print inline
        status_line = f"     {symbol} {result['status'].upper()}"
        if best_evidence:
            ev_title = best_evidence.get("title", "")[:80]
            status_line += f" → {ev_title}"
        if result["relevance"] is not None:
            status_line += f" (relevancia: {result['relevance']:.2f})"
        print(status_line)
        sys.stdout.flush()

        report["results"].append(result)

    # Summary
    print(f"\n{'═' * 60}")
    print(f"📊 RESUMEN:")
    print(f"   ✓ Verificadas:    {report['verified']}")
    print(f"   ⚠ Inciertas:      {report['uncertain']}")
    print(f"   ✗ No encontradas: {report['not_found']}")
    if deep:
        print(f"   ⚡ Fuera de contexto: {report['context_mismatch']}")
    print(f"   Total revisadas:  {report['references_checked']}")
    if report['references_checked'] > 0:
        health = (report['verified'] + report['uncertain']) / report['references_checked'] * 100
        print(f"   Salud bibliográfica: {health:.0f}%")
    print(f"{'═' * 60}\n")

    return report


# ─── CLI ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Reference Validator — verifica referencias de papers académicos"
    )
    parser.add_argument("--arxiv", help="arXiv ID (ej: 1706.03762)")
    parser.add_argument("--doi", help="DOI (ej: 10.1038/nature14539)")
    parser.add_argument("--max", type=int, default=30, help="Máx referencias a verificar (default: 30)")
    parser.add_argument("--deep", action="store_true", help="Evaluar relevancia contextual (más lento)")
    parser.add_argument("--output", help="Guardar reporte JSON en archivo")
    args = parser.parse_args()

    if not args.arxiv and not args.doi:
        parser.error("Debes especificar --arxiv o --doi")

    report = validate_paper(
        arxiv_id=args.arxiv,
        doi=args.doi,
        max_refs=args.max,
        deep=args.deep
    )

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"📁 Reporte guardado en: {args.output}")

    # Exit code reflects health
    if "error" in report:
        sys.exit(1)
    elif report["not_found"] > report["references_checked"] * 0.3:
        sys.exit(2)  # >30% not found = suspicious paper
    elif report.get("context_mismatch", 0) > 0:
        sys.exit(3)  # context mismatches detected
    sys.exit(0)


if __name__ == "__main__":
    main()
