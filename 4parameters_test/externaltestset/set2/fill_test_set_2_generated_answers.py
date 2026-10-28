import json
import shutil
import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
DEFAULT_FILE = Path(__file__).resolve().parent / "test_set_2_evaluation.json"


def answer_to_text(body: dict) -> str:
    """Turn the structured /api/ask response into text for evaluation metrics."""
    answer = body.get("answer")

    if isinstance(answer, str):
        return answer.strip()

    if not isinstance(answer, dict):
        clarification = body.get("clarification")
        if isinstance(clarification, dict):
            return json.dumps(clarification, ensure_ascii=False)
        return ""

    parts = []

    issue_summary = answer.get("issue_summary")
    if isinstance(issue_summary, str) and issue_summary.strip():
        parts.append(issue_summary.strip())

    rights = answer.get("possible_rights")
    if isinstance(rights, list) and rights:
        cleaned = [str(x).strip() for x in rights if str(x).strip()]
        if cleaned:
            parts.append("Possible rights:\n" + "\n".join(f"- {x}" for x in cleaned))

    next_steps = answer.get("next_steps")
    if isinstance(next_steps, list) and next_steps:
        cleaned = [str(x).strip() for x in next_steps if str(x).strip()]
        if cleaned:
            parts.append("Next steps:\n" + "\n".join(f"- {x}" for x in cleaned))

    return "\n\n".join(parts).strip()


def main() -> None:
    eval_file = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_FILE

    if not eval_file.exists():
        print(f"ERROR: Evaluation file not found:\n{eval_file}")
        print("\nPut this script in the same set2 folder as test_set_2_evaluation.json,")
        print("or run: python fill_test_set_2_generated_answers.py <full_path_to_json>")
        sys.exit(1)

    # Make a backup before changing the evaluation file.
    backup_file = eval_file.with_suffix(".backup.json")
    if not backup_file.exists():
        shutil.copy2(eval_file, backup_file)
        print(f"Backup created: {backup_file}")

    with eval_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cases = data.get("cases")
    if not isinstance(cases, list):
        print("ERROR: Expected the JSON to contain a top-level 'cases' list.")
        sys.exit(1)

    # Use a normal HTTP client without logging in.
    # /api/ask supports guest questions, and guest turns are not saved.
    session = requests.Session()

    print(f"\nFound {len(cases)} evaluation cases.")
    print(f"Backend: {BASE_URL}")
    print("Starting automatic generation...\n")

    success = 0
    errors = 0

    for i, case in enumerate(cases, start=1):
        case_id = case.get("id", f"case_{i}")
        question = str(case.get("question", "")).strip()

        if not question:
            print(f"[{i}/{len(cases)}] {case_id}: SKIPPED (empty question)")
            errors += 1
            continue

        # IMPORTANT:
        # Do NOT send case_id or conversation/state IDs.
        # This makes every evaluation query an independent guest request.
        payload = {
            "question": question,
            "document_ids": []
        }

        try:
            response = session.post(
                f"{BASE_URL}/api/ask",
                json=payload,
                timeout=180
            )

            if response.status_code == 200:
                body = response.json()
                generated = answer_to_text(body)

                case["generated_answer"] = generated

                success += 1
                preview = generated.replace("\n", " ")[:120]
                print(f"[{i}/{len(cases)}] {case_id}: OK")
                print(f"    {preview}")

            else:
                errors += 1
                try:
                    detail = response.json()
                except ValueError:
                    detail = response.text

                print(f"[{i}/{len(cases)}] {case_id}: ERROR {response.status_code}")
                print(f"    {detail}")

                # Keep the generated_answer empty when the API did not produce
                # a genuine answer.
                case["generated_answer"] = ""

            # Save after every case so progress is not lost.
            with eval_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Small pause between requests.
            time.sleep(0.5)

        except requests.RequestException as exc:
            errors += 1
            case["generated_answer"] = ""
            print(f"[{i}/{len(cases)}] {case_id}: REQUEST ERROR")
            print(f"    {exc}")

            with eval_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("Finished.")
    print(f"Successful responses: {success}")
    print(f"Errors/skipped:        {errors}")
    print(f"Updated file:          {eval_file}")
    print(f"Backup file:           {backup_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
