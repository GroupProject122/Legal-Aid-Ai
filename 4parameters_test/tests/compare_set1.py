"""Set 1: first run vs final run for ROUGE and BERTScore, with good / okay / bad ranges.

    python compare_set1.py

Reads the saved score files in results/ (no model loading, no Gemini calls, runs instantly):
    first run : results/set1_scores_no_rbi_before_windowed_index.json
    final run : results/set1_scores_no_rbi.json   (after the chunking change)
Both exclude the RBI banking questions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
FIRST = RESULTS / "set1_scores_no_rbi_before_windowed_index.json"
FINAL = RESULTS / "set1_scores_no_rbi.json"

# (label, key in the score file, bad below, okay below, good below) -- above the last is "very good".
# Rules of thumb for free-text answers against a reference; not official cut-offs.
METRICS = [
    ("ROUGE-1", "full_rouge1", 0.20, 0.35, 0.50),
    ("ROUGE-2", "full_rouge2", 0.07, 0.15, 0.25),
    ("ROUGE-L", "full_rougeL", 0.15, 0.30, 0.45),
    ("BERTScore F1", "full_bertscore_f1", 0.10, 0.30, 0.50),
    ("In short: ROUGE-L", "short_rougeL", 0.15, 0.30, 0.45),
    ("In short: BERTScore F1", "short_bertscore_f1", 0.10, 0.30, 0.50),
]


def rating(value: float, bad: float, okay: float, good: float) -> str:
    if value < bad:
        return "BAD"
    if value < okay:
        return "OKAY"
    if value < good:
        return "GOOD"
    return "VERY GOOD"


def load(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"Missing score file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("summary", data)["overall"]


def main() -> None:
    first, final = load(FIRST), load(FINAL)
    line = "=" * 118
    print(line)
    print("  SET 1 - OFFICIAL Q&A   ROUGE + BERTScore   first run vs final run (after chunking change), without RBI")
    print(line)
    print(f"  {'Metric':<24}{'First run':>10}{'Final run':>11}{'Change':>9}   {'Rating (first -> final)':<25}"
          f"{'Bad':>9}{'Okay':>13}{'Good':>13}{'Very good':>11}")
    print("  " + "-" * 114)
    for label, key, bad, okay, good in METRICS:
        a, b = first[key], final[key]
        print(f"  {label:<24}{a:>10.3f}{b:>11.3f}{b - a:>+9.3f}   {rating(a, bad, okay, good) + ' -> ' + rating(b, bad, okay, good):<25}"
              f"{'< ' + format(bad, '.2f'):>9}{format(bad, '.2f') + '-' + format(okay, '.2f'):>13}"
              f"{format(okay, '.2f') + '-' + format(good, '.2f'):>13}{'> ' + format(good, '.2f'):>11}")
    print("  " + "-" * 114)
    print(f"  {'Questions scored':<24}{first['n']:>10}{final['n']:>11}")
    print(f"  {'Right law used':<24}{first['retrieval_hit_rate'] * 100:>9.1f}%{final['retrieval_hit_rate'] * 100:>10.1f}%"
          f"{(final['retrieval_hit_rate'] - first['retrieval_hit_rate']) * 100:>+8.1f}%")
    print(f"  {'App asked to clarify':<24}{first['clarification_rate'] * 100:>9.1f}%{final['clarification_rate'] * 100:>10.1f}%"
          f"{(final['clarification_rate'] - first['clarification_rate']) * 100:>+8.1f}%")
    print(line)
    print("  HOW TO READ")
    print("  ROUGE      = share of the official answer's words (1), word pairs (2), longest word sequence (L)")
    print("               that also appear in the app's answer. 0 = nothing shared, 1 = identical.")
    print("  BERTScore  = similarity of meaning, rescaled: 0 = unrelated text, 1 = same meaning.")
    print("  In short   = only the app's one-line 'In short' summary, compared with the official answer.")
    print("  Ranges are common rules of thumb, not official cut-offs. The app's answers are much longer than")
    print("  the official ones, which pulls every score down even when the answer is correct.")
    print(line)


if __name__ == "__main__":
    main()
