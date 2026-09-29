"""Check that ROUGE and BERTScore are installed and working, on a few sample answer pairs.

Run from 4parameters_test/tests with the test environment switched on (see README.md):

    python check_metrics.py

The first run downloads BERTScore's model (~1.4 GB) into ./models, so it takes a while;
later runs reuse it. Results are saved to ./results/metrics_check.json.

The samples include one deliberate trap -- "may claim" vs "may not claim" -- to show the
known weakness of both metrics: near-identical wording scores high even when the legal
meaning is reversed. This is why the evaluation also uses AlignScore and a hand review.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Keep BERTScore's downloaded model inside this folder instead of the user-wide cache.
# Must be set before bert_score / transformers are imported.
os.environ.setdefault("HF_HOME", str(HERE / "models"))

from bert_score import BERTScorer  # noqa: E402
from rouge_score import rouge_scorer  # noqa: E402

RESULTS_DIR = HERE / "results"

# (label, app answer, reference answer)
SAMPLES = [
    (
        "same meaning, similar words",
        "You can file a consumer complaint online through the e-Daakhil portal.",
        "Yes, a consumer complaint can be filed online using the e-Daakhil portal.",
    ),
    (
        "same meaning, different words",
        "Public authorities must give you the information within 30 days of your request.",
        "Information shall be provided within thirty days of receipt of the RTI application.",
    ),
    (
        "unrelated answer",
        "Report the fraud on the National Cybercrime Reporting Portal or call 1930.",
        "Information shall be provided within thirty days of receipt of the RTI application.",
    ),
    (
        "TRAP: meaning reversed, wording almost identical",
        "You may not claim a refund for the defective product.",
        "You may claim a refund for the defective product.",
    ),
]


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    candidates = [answer for _label, answer, _ref in SAMPLES]
    references = [reference for _label, _answer, reference in SAMPLES]

    rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge_results = [rouge.score(reference, candidate) for candidate, reference in zip(candidates, references)]

    print("Loading BERTScore model (first run downloads ~1.4 GB into ./models) ...")
    started = time.perf_counter()
    # Default English model (roberta-large). rescale_with_baseline spreads scores out so that
    # unrelated text lands near 0 instead of ~0.8, which makes them easier to read.
    scorer = BERTScorer(lang="en", rescale_with_baseline=True)
    precision, recall, f1 = scorer.score(candidates, references)
    seconds = round(time.perf_counter() - started, 1)

    rows = []
    for index, (label, candidate, reference) in enumerate(SAMPLES):
        rows.append(
            {
                "sample": label,
                "app_answer": candidate,
                "reference_answer": reference,
                "rouge1_f": round(rouge_results[index]["rouge1"].fmeasure, 3),
                "rouge2_f": round(rouge_results[index]["rouge2"].fmeasure, 3),
                "rougeL_f": round(rouge_results[index]["rougeL"].fmeasure, 3),
                "bertscore_precision": round(float(precision[index]), 3),
                "bertscore_recall": round(float(recall[index]), 3),
                "bertscore_f1": round(float(f1[index]), 3),
            }
        )

    report = {
        "purpose": "Installation check for ROUGE and BERTScore on sample answer pairs.",
        "bertscore_model": scorer.model_type,
        "bertscore_rescaled_with_baseline": True,
        "bertscore_seconds": seconds,
        "results": rows,
    }
    output = RESULTS_DIR / "metrics_check.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nBERTScore model: {scorer.model_type} ({seconds}s)\n")
    print(f"{'sample':50} {'ROUGE-L':>8} {'BERTScore F1':>13}")
    for row in rows:
        print(f"{row['sample']:50} {row['rougeL_f']:>8} {row['bertscore_f1']:>13}")
    print(f"\nSaved to {output}")


if __name__ == "__main__":
    main()
