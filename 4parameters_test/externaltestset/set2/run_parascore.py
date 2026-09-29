import json
import statistics
from pathlib import Path

from parascore import ParaScorer

INPUT_FILE = Path("set2_evaluation.json")
OUTPUT_FILE = Path("parascore_results.json")


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_FILE.resolve()}. "
            "Run this script from the set2 folder."
        )

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cases = data.get("cases", [])
    usable = [
        c for c in cases
        if str(c.get("reference_answer", "")).strip()
        and str(c.get("generated_answer", "")).strip()
    ]

    if not usable:
        raise ValueError(
            "No cases contain both reference_answer and generated_answer."
        )

    sources = [c["reference_answer"] for c in usable]
    candidates = [c["generated_answer"] for c in usable]

    print(f"Cases in file: {len(cases)}")
    print(f"Cases scored:  {len(usable)}")
    print("\nLoading ParaScore model...")

    scorer = ParaScorer(
        lang="en",
        model_type="bert-base-uncased",
    )

    print("Calculating ParaScore...")

    # ParaScore's free_score returns three tensors:
    # adjusted Precision, adjusted Recall, adjusted F-score.
    # For a single scalar per case, use the adjusted F-score (index 2).
    score_outputs = scorer.free_score(
        candidates,
        sources,
        batch_size=16
    )

    f_scores = score_outputs[2].detach().cpu().tolist()

    if len(f_scores) != len(usable):
        raise RuntimeError(
            f"Expected {len(usable)} scores but received {len(f_scores)}."
        )

    results = []
    for case, score in zip(usable, f_scores):
        results.append({
            "id": case["id"],
            "domain": case["domain"],
            "parascore_f1": float(score),
        })

    overall = statistics.mean(r["parascore_f1"] for r in results)

    domain_scores = {}
    for domain in sorted({r["domain"] for r in results}):
        vals = [
            r["parascore_f1"]
            for r in results
            if r["domain"] == domain
        ]
        domain_scores[domain] = {
            "n": len(vals),
            "mean_parascore_f1": statistics.mean(vals)
        }

    output = {
        "metric": "ParaScore reference-free",
        "model": "bert-base-uncased",
        "cases_in_file": len(cases),
        "cases_scored": len(results),
        "score_used": "adjusted F-score",
        "overall_mean_parascore_f1": overall,
        "domain_means": domain_scores,
        "results": results,
        "note": (
            "ParaScore is a paraphrase-quality/semantic similarity metric. "
            "For Legal Aid AI it is supplementary and should not be interpreted "
            "as a direct legal-correctness or factual-grounding score."
        )
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"Overall mean ParaScore F1: {overall:.4f}")
    print("=" * 60)

    for domain, info in domain_scores.items():
        print(
            f"{domain}: n={info['n']}, "
            f"mean={info['mean_parascore_f1']:.4f}"
        )

    print(f"\nSaved results to: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
