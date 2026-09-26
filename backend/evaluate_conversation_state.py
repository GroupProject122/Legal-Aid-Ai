from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import conversation_state
from config import BASE_DIR

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASE_PATH = EVAL_DIR / "conversation_state_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "conversation_state_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "conversation_state_evaluation.md"


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("cases", [])


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


# What the user actually experiences for each turn type. Since additional facts and corrections
# are re-answered with the updated case (not merely acknowledged), confusing any two labels in
# the same group is harmless; crossing groups is not -- "reset" wipes the conversation's context
# and "bypass" gives no answer at all.
RESPONSE_ACTION = {
    "follow_up_question": "answer_with_context",
    "additional_fact": "answer_with_context",
    "correction": "answer_with_context",
    "clarification_reply": "answer_with_context",
    "new_issue": "reset",
    "acknowledgement": "bypass",
    "small_talk": "bypass",
}


def classify(case_message: str, state: conversation_state.ActiveCaseState, mode: str) -> conversation_state.TurnClassification:
    if mode == "live":
        return conversation_state.classify_turn(case_message, state, use_memory=False, record_corrections=False)
    return conversation_state.deterministic_turn_classification(case_message, state)


def evaluate_case(case: dict[str, Any], mode: str = "rules") -> dict[str, Any]:
    state = conversation_state.create_state(
        domains=case.get("domains", []),
        primary_domain=(case.get("domains") or [None])[0],
        case_summary=case.get("initial_summary", ""),
        known_facts=case.get("known_facts", []),
        confirmed_document_context_id=case.get("confirmed_document_context_id"),
    )
    classification = classify(case["message"], state, mode)
    acceptable = case.get("acceptable_turn_types") or [case.get("expected_turn_type")]
    turn_type_correct = classification.turn_type in acceptable
    expected_action = RESPONSE_ACTION.get(case.get("expected_turn_type"))
    predicted_action = RESPONSE_ACTION.get(classification.turn_type)
    acceptable_actions = {RESPONSE_ACTION.get(item) for item in acceptable}
    if classification.turn_type in {"additional_fact", "correction", "follow_up_question", "clarification_reply"}:
        conversation_state.apply_turn_to_state(state, case["message"], classification)
    if classification.turn_type == "new_issue":
        facts_text = case["message"].lower()
        combined = case["message"]
    else:
        combined = conversation_state.pipeline_message(case["message"], state)
        facts_text = " ".join([state.case_summary, *state.known_facts, combined]).lower()
    must_preserve = all(item.lower() in facts_text for item in case.get("must_preserve", []))
    must_not_preserve = all(item.lower() not in facts_text for item in case.get("must_not_preserve", []))
    bypass_correct = True
    if case.get("should_bypass_pipeline"):
        bypass_correct = classification.turn_type in {"small_talk", "acknowledgement"}
    document_context_correct = True
    if case.get("expected_document_context_preserved"):
        document_context_correct = bool(state.confirmed_document_context_id)
    correct = all(
        [
            turn_type_correct,
            must_preserve,
            must_not_preserve,
            bypass_correct,
            document_context_correct,
        ]
    )
    conversation_state.clear_state(state.conversation_state_id)
    return {
        "case_id": case["case_id"],
        "message": case["message"],
        "expected_turn_type": case.get("expected_turn_type"),
        "predicted_turn_type": classification.turn_type,
        "provider": classification.provider,
        "turn_type_correct": turn_type_correct,
        "expected_action": expected_action,
        "predicted_action": predicted_action,
        "action_correct": predicted_action in acceptable_actions,
        "swallowed": predicted_action == "bypass" and "bypass" not in acceptable_actions,
        "wrongly_reset": predicted_action == "reset" and "reset" not in acceptable_actions,
        "missed_reset": expected_action == "reset" and predicted_action != "reset",
        "must_preserve_correct": must_preserve,
        "must_not_preserve_correct": must_not_preserve,
        "bypass_correct": bypass_correct,
        "document_context_correct": document_context_correct,
        "correct": correct,
        "case_summary": state.case_summary,
        "known_facts": state.known_facts,
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    follow_up_cases = [item for item in results if item["expected_turn_type"] == "follow_up_question"]
    new_issue_cases = [item for item in results if item["expected_turn_type"] == "new_issue"]
    additional_fact_cases = [item for item in results if item["expected_turn_type"] == "additional_fact"]
    correction_cases = [item for item in results if item["expected_turn_type"] == "correction"]
    bypass_cases = [item for item in results if item["expected_turn_type"] in {"small_talk", "acknowledgement"}]
    return {
        "case_count": total,
        "overall_accuracy": pct(sum(item["correct"] for item in results), total),
        "turn_type_accuracy": pct(sum(item["turn_type_correct"] for item in results), total),
        "response_action_accuracy": pct(sum(item["action_correct"] for item in results), total),
        "swallowed_rate": pct(sum(item["swallowed"] for item in results), total),
        "wrong_reset_rate": pct(sum(item["wrongly_reset"] for item in results), total),
        "missed_reset_rate": subset_rate(new_issue_cases, "missed_reset"),
        "gemini_decided_rate": pct(sum(item["provider"] == "gemini" for item in results), total),
        "follow_up_classification_accuracy": subset_rate(follow_up_cases, "turn_type_correct"),
        "new_issue_detection_accuracy": subset_rate(new_issue_cases, "turn_type_correct"),
        "additional_fact_preservation_accuracy": subset_rate(additional_fact_cases, "must_preserve_correct"),
        "correction_accuracy": subset_rate(correction_cases, "correct"),
        "small_talk_bypass_rate": subset_rate(bypass_cases, "bypass_correct"),
        "previous_fact_preservation_rate": pct(sum(item["must_preserve_correct"] for item in results), total),
        "unrelated_fact_contamination_rate": pct(sum(not item["must_not_preserve_correct"] for item in results), total),
        "document_context_preservation_rate": pct(sum(item["document_context_correct"] for item in results), total),
        "failed_cases": [item["case_id"] for item in results if not item["correct"]],
    }


def subset_rate(items: list[dict[str, Any]], key: str) -> float:
    return pct(sum(bool(item[key]) for item in items), len(items))


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Conversation State Evaluation",
        "",
        "## Overall Results",
        f"- Mode: {report['evaluation_config']['mode']}",
        f"- Cases: {metrics['case_count']}",
        f"- Overall accuracy: {percent(metrics['overall_accuracy'])}",
        f"- Turn-type accuracy: {percent(metrics['turn_type_accuracy'])}",
        f"- Response-action accuracy (right kind of response): {percent(metrics['response_action_accuracy'])}",
        f"- Swallowed (needed an answer, got an acknowledgement): {percent(metrics['swallowed_rate'])}",
        f"- Wrongly reset (context wiped on a same-case message): {percent(metrics['wrong_reset_rate'])}",
        f"- Missed reset (new issue kept old context): {percent(metrics['missed_reset_rate'])}",
        f"- Decided by Gemini: {percent(metrics['gemini_decided_rate'])}",
        f"- Follow-up classification accuracy: {percent(metrics['follow_up_classification_accuracy'])}",
        f"- New-issue detection accuracy: {percent(metrics['new_issue_detection_accuracy'])}",
        f"- Additional-fact preservation accuracy: {percent(metrics['additional_fact_preservation_accuracy'])}",
        f"- Correction accuracy: {percent(metrics['correction_accuracy'])}",
        f"- Small-talk bypass rate: {percent(metrics['small_talk_bypass_rate'])}",
        f"- Previous-fact preservation rate: {percent(metrics['previous_fact_preservation_rate'])}",
        f"- Unrelated-fact contamination rate: {percent(metrics['unrelated_fact_contamination_rate'])}",
        f"- Document-context preservation rate: {percent(metrics['document_context_preservation_rate'])}",
        "",
        "## Case Results",
    ]
    for item in report["results"]:
        status = "PASS" if item["correct"] else "REVIEW"
        lines.append(
            f"- `{item['case_id']}`: {status}; expected `{item['expected_turn_type']}`, predicted `{item['predicted_turn_type']}`"
        )
    lines.extend(["", "## Recommendation"])
    if metrics["failed_cases"]:
        lines.append("- Review targeted follow-up handling for failed cases.")
    else:
        lines.append("- Conversational state is ready for manual follow-up testing.")
    return "\n".join(lines)


def evaluate(path: Path, mode: str = "rules") -> dict[str, Any]:
    """mode="rules" scores the keyword rules alone with no network calls (the fallback used when
    Gemini is unavailable). mode="live" scores the production path -- rules as a hint, Gemini
    deciding -- with the correction memory switched off so results are reproducible."""
    previous_key = conversation_state.GEMINI_API_KEY
    if mode == "rules":
        conversation_state.GEMINI_API_KEY = ""
    try:
        cases = load_cases(path)
        results = [evaluate_case(case, mode) for case in cases]
    finally:
        conversation_state.GEMINI_API_KEY = previous_key
    return {
        "evaluation_config": {
            "case_file": path.as_posix(),
            "mode": mode,
            "live_gemini_calls": sum(item["provider"] == "gemini" for item in results),
        },
        "metrics": aggregate(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate compact active conversation state.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--mode", choices=["rules", "live"], default="rules")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()
    report = evaluate(args.cases, args.mode)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        "Conversation state evaluation complete: "
        f"{report['metrics']['case_count']} cases; "
        f"mode={args.mode}; "
        f"overall_accuracy={percent(report['metrics']['overall_accuracy'])}; "
        f"response_action_accuracy={percent(report['metrics']['response_action_accuracy'])}; "
        f"swallowed={percent(report['metrics']['swallowed_rate'])}; "
        f"wrong_reset={percent(report['metrics']['wrong_reset_rate'])}; "
        f"small_talk_bypass={percent(report['metrics']['small_talk_bypass_rate'])}"
    )


if __name__ == "__main__":
    main()
