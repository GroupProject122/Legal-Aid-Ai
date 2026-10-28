"""Evaluate Legal Aid AI on Set 1 (official Q&A) with ROUGE and BERTScore.

Two steps (run from 4parameters_test/tests with the test environment on):

    python evaluate_set1.py answer   # ask the running app all 50 questions, save its answers
    python evaluate_set1.py score    # score the saved answers, write the report
    python evaluate_set1.py          # both
    python evaluate_set1.py score --no-rbi   # score without the RBI (banking) questions

Step 1 needs the backend running on http://127.0.0.1:8000 (start it from backend/ with
`python -m uvicorn main:app --host 127.0.0.1 --port 8000`). It is resumable: questions already
answered are skipped, so an interrupted run continues where it stopped. Delete
results/set1_answers.json to start again from scratch.

How each question is asked. The official question is sent exactly as written. Official FAQs
assume a context (e.g. "mediation" in a consumer dispute) that a real user would give when the
app asks, so if the app asks a clarifying question, one short context reply is sent -- the
same thing a user would type. If the app then asks for details of a specific case, a second
reply says it is a general question about the law. How often clarification was needed is
reported as its own metric.

What is scored. The app's answer is compared with the official answer:
  - "full answer": everything the app shows as its answer (In short, what this may involve,
    legal position, next steps, where to approach, evidence) -- the headline score;
  - "short answer": only the "In short" paragraph.
ROUGE-1/2/L F1 (word overlap) and BERTScore F1 (meaning overlap, roberta-large, rescaled with
baseline so unrelated text lands near 0). Also: did the app retrieve at least one of the
documents the team expected (expected_sources)?
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(HERE / "models"))

SET_FILE = HERE.parent / "externaltestset" / "set 1" / "official_qa.json"
RESULTS = HERE / "results"
ANSWERS = RESULTS / "set1_answers.json"
SCORES = RESULTS / "set1_scores.json"
REPORT = RESULTS / "set1_report.md"
API = os.environ.get("LEGAL_AID_API", "http://127.0.0.1:8000")

# The one-line context a user would give if the app asks what the question is about.
CONTEXT_REPLY = {
    "consumer law": "This is about a consumer complaint before a consumer commission under the Consumer Protection Act.",
    "cybercrime reporting": "This is about reporting a cyber crime on the National Cyber Crime Reporting Portal.",
    "banking ombudsman (RBI)": "This is about a complaint against my bank to the RBI Ombudsman.",
    "right to information": "This is about an RTI application to a government public authority.",
    "free legal aid": "This is about getting free legal aid from a legal services authority.",
}
GENERAL_REPLY = ("It is a general question about what the law says, not about a specific product, "
                 "transaction or incident of mine.")
ANSWER_FIELDS = ["issue_summary", "what_this_may_involve", "possible_legal_position",
                 "suggested_next_steps", "where_to_approach", "evidence_to_preserve"]


def post(payload: dict, attempts: int = 3) -> dict:
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(f"{API}/api/ask", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=240) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == attempts:
                raise
            print(f"    request failed ({exc}); retrying in {10 * attempt}s")
            time.sleep(10 * attempt)
    raise RuntimeError("unreachable")


def ask(case: dict) -> dict:
    started = time.perf_counter()
    response = post({"question": case["question"]})
    clarifications = []
    for round_number in range(2):
        clarification = response.get("clarification") or {}
        if not (clarification.get("needed") and clarification.get("state_id")):
            break
        # First reply: the area of law. Second reply (if the app then asks for case details):
        # that this is a general question about the law -- what a real user would say.
        reply = CONTEXT_REPLY.get(case.get("topic"), "This is about the legal question above.") if round_number == 0 else GENERAL_REPLY
        clarifications.append({"app_asked": clarification.get("question"), "reply": reply})
        response = post({"question": reply, "clarification_state_id": clarification["state_id"]})
    answer = response.get("answer") or {}
    still_clarifying = bool((response.get("clarification") or {}).get("needed"))
    # An answer with no text is a failed call, not an answer -- it is what the app returns when
    # Gemini is unavailable (e.g. the free-tier daily quota is used up). Marked "empty_answer"
    # so it is retried on the next run instead of being scored.
    empty = not still_clarifying and not (answer.get("issue_summary") or "").strip()
    return {
        "id": case["id"],
        "status": "clarification_unresolved" if still_clarifying else ("empty_answer" if empty else "answered"),
        "clarifications": clarifications,
        "answer": answer,
        "sources": [source.get("document") or source.get("document_title") for source in response.get("sources", [])],
        "routing": (response.get("routing") or {}).get("domains"),
        "insufficient_context": response.get("insufficient_context"),
        "seconds": round(time.perf_counter() - started, 1),
    }


def run_answers(cases: list[dict]) -> None:
    RESULTS.mkdir(exist_ok=True)
    saved = json.loads(ANSWERS.read_text(encoding="utf-8")) if ANSWERS.exists() else {}
    try:
        health = json.loads(urllib.request.urlopen(f"{API}/api/health", timeout=10).read())
    except OSError:
        sys.exit(f"The backend is not reachable at {API}. Start it first (see the top of this file).")
    if not health.get("knowledge_base_loaded"):
        sys.exit("The backend is running but its knowledge base is not loaded.")
    todo = [case for case in cases if saved.get(case["id"], {}).get("status") != "answered"]
    rule = "-" * 96
    print(f"\n{'=' * 96}\n  LEGAL AID AI  |  SET 1: asking the app  |  {len(todo)} to ask"
          f" ({len(cases) - len(todo)} already answered)\n{'=' * 96}")
    empty_streak = 0
    for number, case in enumerate(todo, 1):
        print(f"\n[{number}/{len(todo)}] {case['id']}  ({case['topic']})")
        print(f"  Q       : {case['question']}")
        try:
            saved[case["id"]] = ask(case)
        except Exception as exc:  # noqa: BLE001 -- keep going; the item is retried next run
            print(f"  FAILED  : {exc}")
            saved[case["id"]] = {"id": case["id"], "status": "error", "error": str(exc)}
        item = saved[case["id"]]
        if item.get("status") != "error":
            for turn in item["clarifications"]:
                print(f"  App asked: {turn['app_asked']}")
                print(f"  We said : {turn['reply']}")
            short = (item["answer"].get("issue_summary") or "").strip()
            print(f"  Answer  : {short[:230] + ('...' if len(short) > 230 else '')}")
            laws = list(dict.fromkeys(item["sources"]))
            print(f"  Law used: {'; '.join(laws[:2]) if laws else 'none'}" + (f" (+{len(laws) - 2} more)" if len(laws) > 2 else ""))
            print(f"  Outcome : {OUTCOME_LABEL[outcome(item)]}  |  {item['seconds']}s")
        print(rule)
        ANSWERS.write_text(json.dumps(saved, indent=2, ensure_ascii=False), encoding="utf-8")
        empty_streak = empty_streak + 1 if item.get("status") == "empty_answer" else 0
        if empty_streak >= 3:
            print("\nSTOPPED: 3 empty answers in a row. The app's Gemini calls are failing -- most likely the")
            print("daily free-tier quota is used up (it resets at midnight Pacific time). Answers so far are")
            print("saved; run this again later and it continues from where it stopped.")
            return
        time.sleep(2)  # stay well inside the Gemini rate limit


OUTCOME_LABEL = {
    "grounded_answer": "Answered from the law (with sources)",
    "insufficient": "Said the material was insufficient",
    "clarification_unresolved": "Still asking for clarification",
    "empty_answer": "EMPTY ANSWER (app failed, e.g. Gemini quota) - not scored",
}


OUTCOME_SHORT = {
    "grounded_answer": "answered",
    "insufficient": "insufficient",
    "clarification_unresolved": "no answer (clarifying)",
    "empty_answer": "EMPTY (failed)",
}


def outcome(item: dict) -> str:
    if item["status"] == "empty_answer":
        return "empty_answer"
    if item["status"] == "clarification_unresolved":
        return "clarification_unresolved"
    if item.get("insufficient_context") or not item.get("sources"):
        return "insufficient"
    return "grounded_answer"


def answer_text(answer: dict, fields: list[str]) -> str:
    parts = []
    for field in fields:
        value = answer.get(field)
        if isinstance(value, list):
            parts.extend(str(item) for item in value if item)
        elif value:
            parts.append(str(value))
    return " ".join(parts).strip()


def run_scores(cases: list[dict], label: str = "", suffix: str = "") -> None:
    """Score the saved answers for `cases`. `label` names the run in the output (e.g. "without
    RBI questions"); `suffix` keeps its files separate (set1_scores{suffix}.json, ...)."""
    from bert_score import BERTScorer
    from rouge_score import rouge_scorer

    scores_file = RESULTS / f"set1_scores{suffix}.json"
    report_file = RESULTS / f"set1_report{suffix}.md"

    saved = json.loads(ANSWERS.read_text(encoding="utf-8"))
    usable = [case for case in cases if saved.get(case["id"], {}).get("status") in {"answered", "clarification_unresolved"}]
    missing = [case["id"] for case in cases if case not in usable]
    references = [case["reference_answer"] for case in usable]
    full = [answer_text(saved[case["id"]]["answer"], ANSWER_FIELDS) or "(no answer)" for case in usable]
    short = [answer_text(saved[case["id"]]["answer"], ["issue_summary"]) or "(no answer)" for case in usable]

    rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    print("Loading BERTScore model ...")
    scorer = BERTScorer(lang="en", rescale_with_baseline=True)
    _p, _r, bert_full = scorer.score(full, references)
    _p, _r, bert_short = scorer.score(short, references)

    rows = []
    for index, case in enumerate(usable):
        item = saved[case["id"]]
        r_full = rouge.score(references[index], full[index])
        r_short = rouge.score(references[index], short[index])
        rows.append({
            "id": case["id"],
            "domain": case["domain"],
            "topic": case["topic"],
            "status": item["status"],
            "needed_clarification": bool(item["clarifications"]),
            "outcome": outcome(item),
            "retrieved_expected_source": any(source in item["sources"] for source in case["expected_sources"]),
            "full": {"rouge1": r_full["rouge1"].fmeasure, "rouge2": r_full["rouge2"].fmeasure,
                     "rougeL": r_full["rougeL"].fmeasure, "bertscore_f1": float(bert_full[index])},
            "short": {"rouge1": r_short["rouge1"].fmeasure, "rouge2": r_short["rouge2"].fmeasure,
                      "rougeL": r_short["rougeL"].fmeasure, "bertscore_f1": float(bert_short[index])},
            "question": case["question"],
            "app_short_answer": short[index],
        })

    def summarise(items: list[dict]) -> dict:
        return {
            "n": len(items),
            **{f"full_{m}": round(mean(i["full"][m] for i in items), 3) for m in ("rouge1", "rouge2", "rougeL", "bertscore_f1")},
            **{f"short_{m}": round(mean(i["short"][m] for i in items), 3) for m in ("rougeL", "bertscore_f1")},
            "retrieval_hit_rate": round(mean(i["retrieved_expected_source"] for i in items), 3),
            "clarification_rate": round(mean(i["needed_clarification"] for i in items), 3),
        }

    by_topic = defaultdict(list)
    for row in rows:
        by_topic[row["topic"]].append(row)
    seconds = sorted(saved[case["id"]].get("seconds", 0) for case in usable)
    outcomes = defaultdict(list)
    for row in rows:
        outcomes[row["outcome"]].append(row)
    summary = {
        "run": {
            "questions": len(cases),
            "scored": len(rows),
            "total_minutes": round(sum(seconds) / 60, 1),
            "median_seconds_per_question": seconds[len(seconds) // 2] if seconds else None,
            "outcomes": {name: {**summarise(items), "ids": [i["id"] for i in items]}
                         for name, items in sorted(outcomes.items(), key=lambda pair: list(OUTCOME_LABEL).index(pair[0]))},
        },
        "overall": summarise(rows),
        "by_topic": {topic: summarise(items) for topic, items in by_topic.items()},
        "not_scored": missing,
        "bertscore_model": scorer.model_type,
        "bertscore_rescaled_with_baseline": True,
    }
    summary["label"] = label or "all questions"
    scores_file.write_text(json.dumps({"summary": summary, "items": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    report_file.write_text(markdown_report(summary, rows), encoding="utf-8")
    print_results({**summary, "rows": rows}, missing, scores_file, report_file)


def print_results(summary: dict, missing: list[str], scores_file: Path, report_file: Path) -> None:
    o, run = summary["overall"], summary["run"]
    line, thin = "=" * 96, "-" * 96
    print(f"\n{line}")
    print(f"  LEGAL AID AI  |  SET 1: OFFICIAL Q&A  |  ROUGE + BERTScore  |  {summary['label'].upper()}")
    print(line)
    print(f"  Questions scored : {run['scored']} of {run['questions']}" + (f"   (not scored: {', '.join(missing)})" if missing else ""))
    print(f"  Time asking app  : {run['total_minutes']} min in total, median {run['median_seconds_per_question']}s per question")
    print(f"  BERTScore model  : {summary['bertscore_model']}, rescaled (0 = unrelated, 1 = identical meaning)")
    print(thin)
    print("  HEADLINE (app's full answer vs the official answer)")
    print(f"     ROUGE-1  {o['full_rouge1']:<7} ROUGE-2  {o['full_rouge2']:<7} ROUGE-L  {o['full_rougeL']:<7} "
          f"BERTScore F1  {o['full_bertscore_f1']}")
    print(f"     'In short' paragraph only:  ROUGE-L {o['short_rougeL']}   BERTScore F1 {o['short_bertscore_f1']}")
    print(f"     Right law retrieved: {o['retrieval_hit_rate']:.0%}     Needed a clarifying question: {o['clarification_rate']:.0%}")
    print(thin)
    print("  WHAT THE APP DID                              Questions   BERTScore   ROUGE-L")
    for name, info in run["outcomes"].items():
        print(f"     {OUTCOME_LABEL[name]:42} {info['n']:>6}   {info['full_bertscore_f1']:>9}   {info['full_rougeL']:>7}")
    print(thin)
    print(f"  BY TOPIC              {'n':>3}  {'ROUGE-1':>8} {'ROUGE-2':>8} {'ROUGE-L':>8} {'BERTScore':>10} "
          f"{'Right law':>10} {'Clarified':>10}")
    for topic, s in summary["by_topic"].items():
        print(f"     {topic[:18]:18} {s['n']:>3}  {s['full_rouge1']:>8} {s['full_rouge2']:>8} {s['full_rougeL']:>8} "
              f"{s['full_bertscore_f1']:>10} {s['retrieval_hit_rate']:>10.0%} {s['clarification_rate']:>10.0%}")
    print(f"     {'OVERALL':18} {o['n']:>3}  {o['full_rouge1']:>8} {o['full_rouge2']:>8} {o['full_rougeL']:>8} "
          f"{o['full_bertscore_f1']:>10} {o['retrieval_hit_rate']:>10.0%} {o['clarification_rate']:>10.0%}")
    print(thin)
    print("  PER QUESTION                                   BERTScore  ROUGE-L  Right law  Outcome")
    for row in summary.get("rows", []):
        print(f"     {row['id']:13} {row['question'][:30]:30} {row['full']['bertscore_f1']:>9.3f} {row['full']['rougeL']:>8.3f}"
              f"  {'yes' if row['retrieved_expected_source'] else 'no':>9}  {OUTCOME_SHORT[row['outcome']]}")
    print(thin)
    print("  HOW TO READ: ROUGE = shared words (0-1). BERTScore = shared meaning; for scale, a correct paraphrase")
    print("  scored 0.58 in the installation check. Both reward matching wording, so long, cautious answers")
    print("  score lower even when correct.")
    print(f"  Saved: results/{scores_file.name}, results/{report_file.name}")
    print(line)


def markdown_report(summary: dict, rows: list[dict]) -> str:
    o = summary["overall"]
    lines = [
        "# Set 1 (official Q&A): results", "",
        f"{o['n']} questions scored. BERTScore: `{summary['bertscore_model']}`, rescaled with baseline "
        "(unrelated text scores near 0; identical meaning near 1). Scores compare the app's **full answer** with the "
        "official answer unless marked *short* (the \"In short\" paragraph only).", "",
        f"**Run:** {summary['run']['scored']} of {summary['run']['questions']} questions scored · "
        f"{summary['run']['total_minutes']} min asking the app · median "
        f"{summary['run']['median_seconds_per_question']}s per question.", "",
        "## What the app did", "",
        "| Outcome | Questions | BERTScore F1 | ROUGE-L | *short* BERTScore |", "|---|---|---|---|---|",
        *[f"| {OUTCOME_LABEL[name]} | {info['n']} | {info['full_bertscore_f1']} | {info['full_rougeL']} | "
          f"{info['short_bertscore_f1']} |" for name, info in summary["run"]["outcomes"].items()],
        "", "## Scores", "",
        "| | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore F1 | *short* ROUGE-L | *short* BERTScore | Right law retrieved | Needed clarification |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, s in [("**Overall**", o)] + list(summary["by_topic"].items()):
        lines.append(f"| {label} (n={s['n']}) | {s['full_rouge1']} | {s['full_rouge2']} | {s['full_rougeL']} | "
                     f"{s['full_bertscore_f1']} | {s['short_rougeL']} | {s['short_bertscore_f1']} | "
                     f"{s['retrieval_hit_rate']:.0%} | {s['clarification_rate']:.0%} |")
    lines += ["", "## Per question", "", "| ID | ROUGE-L | BERTScore | Right law | Clarified | Question |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| `{r['id']}` | {r['full']['rougeL']:.3f} | {r['full']['bertscore_f1']:.3f} | "
                     f"{'yes' if r['retrieved_expected_source'] else 'no'} | {'yes' if r['needed_clarification'] else 'no'} | "
                     f"{r['question'].replace('|', '/')} |")
    if summary["not_scored"]:
        lines += ["", f"Not scored (no answer): {', '.join(summary['not_scored'])}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    cases = json.loads(SET_FILE.read_text(encoding="utf-8"))["cases"]
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    step = args[0] if args else "all"
    label, suffix = "", ""
    if "--no-rbi" in sys.argv:
        # Leave out the RBI Integrated Ombudsman (banking) questions: the scheme in the dataset is
        # the 2021 version and is stored without its clause structure (see the README).
        cases = [case for case in cases if not case["id"].startswith("banking")]
        label, suffix = "without RBI questions", "_no_rbi"
    if step in {"answer", "all"}:
        run_answers(cases)
    if step in {"score", "all"}:
        run_scores(cases, label, suffix)


if __name__ == "__main__":
    main()
