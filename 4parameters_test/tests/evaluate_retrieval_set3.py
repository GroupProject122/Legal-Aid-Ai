"""Run the app's retrieval evaluation on Set 3 (right law) -- a redirect, not a copy.

The real evaluator stays at backend/evaluate_retrieval.py (the backend's tests import it, and it
uses the app's own search code). This file only points it at Set 3 and saves the results here:

    python evaluate_retrieval_set3.py

Reads   ../externaltestset/set3/right_law.json
Writes  results/set3_retrieval.json and results/set3_retrieval.md
        (never the committed baseline in backend/eval/)

Retrieval runs on the local search model and index only -- no Gemini calls, so it uses none of
the API quota and gives the same result every time. It does not need the backend server running.

It must run with the Python that has the backend's libraries (FAISS, sentence-transformers). If
you start it from this folder's .venv (which does not have them), it automatically switches to
the Python that .venv was created from.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1] / "backend"
EVALUATOR = BACKEND / "evaluate_retrieval.py"
SET3 = HERE.parent / "externaltestset" / "set3" / "right_law.json"
RESULTS = HERE / "results"


def backend_python() -> str:
    """This interpreter if it has the backend's search libraries, else the base Python this
    virtual environment was made from (where the backend's libraries are installed)."""
    if all(importlib.util.find_spec(name) for name in ("faiss", "sentence_transformers")):
        return sys.executable
    base = getattr(sys, "_base_executable", None)
    if base and Path(base).exists() and Path(base).resolve() != Path(sys.executable).resolve():
        return base
    sys.exit("Could not find a Python with the backend's libraries (faiss, sentence-transformers). "
             "Run this with the Python you use for the backend, e.g.  C:\\Python313\\python.exe evaluate_retrieval_set3.py")


def pct(value) -> str:
    return "  -  " if value is None else f"{value * 100:5.1f}%"


def short_name(source_file: str) -> str:
    name = (source_file or "?").split("/")[-1].removesuffix(".pdf")
    return name[:26]


def print_table(json_path: Path) -> None:
    """Print a per-question table and the headline numbers, for showing in the terminal."""
    import json

    report = json.loads(json_path.read_text(encoding="utf-8"))
    rows = report["query_results"]
    overall = report["overall_metrics"]
    line = "=" * 100
    print("\n" + line)
    print("  SET 3 - RIGHT LAW (retrieval)   24 real situations from court / consumer commission / CIC decisions")
    print(line)
    print("  PER QUESTION   (Doc@1 = right document ranked first;  Sec@5 = right section in the top 5)")
    print(f"  {'id':<12}{'Doc@1':<7}{'Doc@5':<7}{'Sec@5':<7}top result found by the app")
    print("  " + "-" * 96)
    for case in rows:
        m = case["evaluation"]["metrics"]
        top = (case["results"]["reranked_top10"] or [{}])[0]
        mark = lambda ok: "yes" if ok else ("n/a" if ok is None else "NO")
        found = f"{short_name(top.get('source_file'))} s.{top.get('provision_number') or '-'}"
        print(f"  {case['id']:<12}{mark(m['document_hit_at_1']):<7}{mark(m['document_hit_at_5']):<7}"
              f"{mark(m['provision_hit_at_5']):<7}{found}")
    print("  " + "-" * 96)
    print("  BY AREA")
    print(f"  {'area':<34}{'Doc@1':>8}{'Doc@5':>8}{'Sec@5':>8}{'MRR':>7}")
    for area, m in report["domain_breakdown"].items():
        label = "rti / public authority" if area == "constitutional_public_authority" else area
        print(f"  {label:<34}{pct(m['document_hit_at_1']):>8}{pct(m['document_hit_at_5']):>8}"
              f"{pct(m['provision_hit_at_5']):>8}{m['mrr']:>7.3f}")
    print(f"  {'ALL (' + str(overall['query_count']) + ' questions)':<34}{pct(overall['document_hit_at_1']):>8}"
          f"{pct(overall['document_hit_at_5']):>8}{pct(overall['provision_hit_at_5']):>8}{overall['mrr']:>7.3f}")
    print(line)
    print("  OVERALL RATING   (rules of thumb for a small legal search system, not official cut-offs)")
    print(f"  {'Metric':<26}{'Result':>9}   {'Rating':<11}{'Bad':>9}{'Okay':>12}{'Good':>12}{'Very good':>11}")
    print("  " + "-" * 96)
    for label, key, cuts, as_pct in RANGES:
        value = overall[key]
        shown = pct(value) if as_pct else f"{value:.3f}"
        fmt = (lambda x: f"{x * 100:.0f}%") if as_pct else (lambda x: f"{x:.2f}")
        bad, okay, good = cuts
        print(f"  {label:<26}{shown:>9}   {rate(value, cuts):<11}{'< ' + fmt(bad):>9}"
              f"{fmt(bad) + '-' + fmt(okay):>12}{fmt(okay) + '-' + fmt(good):>12}{'> ' + fmt(good):>11}")
    print(line)
    print("  HOW TO READ: Doc = the app searched the right law (Act / rules / case). Sec = it also reached the")
    print("  section the decision actually applied. MRR 1.0 = right document always ranked first.")
    print(line)


# (label, key in overall_metrics, (bad below, okay below, good below), shown as %)
RANGES = [
    ("Right document ranked 1st", "document_hit_at_1", (0.50, 0.70, 0.85), True),
    ("Right document in top 5", "document_hit_at_5", (0.60, 0.80, 0.90), True),
    ("Right section in top 5", "provision_hit_at_5", (0.40, 0.60, 0.80), True),
    ("MRR (rank of right doc)", "mrr", (0.50, 0.70, 0.85), False),
]


def rate(value: float, cuts) -> str:
    bad, okay, good = cuts
    return "BAD" if value < bad else "OKAY" if value < okay else "GOOD" if value < good else "VERY GOOD"


def main() -> None:
    if not SET3.exists():
        sys.exit(f"Set 3 file not found: {SET3}")
    RESULTS.mkdir(exist_ok=True)
    json_path = RESULTS / "set3_retrieval.json"
    command = [
        backend_python(), str(EVALUATOR),
        "--queries", str(SET3),
        "--json-output", str(json_path),
        "--md-output", str(RESULTS / "set3_retrieval.md"),
        *sys.argv[1:],
    ]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    code = subprocess.run(command, cwd=BACKEND, env=env).returncode
    if code == 0 and json_path.exists():
        print_table(json_path)
    sys.exit(code)


if __name__ == "__main__":
    main()
