"""Review the follow-up turn corrections recorded by turn_memory.

Each record is a follow-up message where the keyword rules guessed one turn type and Gemini
decided another. Approving a record lets the app reuse its label directly for near-identical
messages (no Gemini call); rejecting it stops it being shown to Gemini as an example.

    python review_turn_corrections.py                      # interactive review of pending records
    python review_turn_corrections.py list [--status all]  # print records
    python review_turn_corrections.py approve 12 [--label follow_up_question] [--note "..."]
    python review_turn_corrections.py reject 12 [--note "..."]
    python review_turn_corrections.py delete 12
    python review_turn_corrections.py stats
    python review_turn_corrections.py export               # approved -> eval test cases
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import turn_memory
from config import BASE_DIR

EXPORT_PATH = BASE_DIR / "eval" / "conversation_state_cases_learned.json"
LABEL_KEYS = {
    "q": "follow_up_question",
    "f": "additional_fact",
    "c": "correction",
    "n": "new_issue",
    "a": "acknowledgement",
    "s": "small_talk",
}


def show(record: dict) -> None:
    print(
        f"#{record['id']}  [{record['status']}]  seen {record['seen_count']}x  domains={record['domains'] or '-'}\n"
        f"   message : {record['message']}\n"
        f"   rules   : {record['rule_label']}\n"
        f"   gemini  : {record['model_label']}   ({record['reason'] or 'no reason given'})\n"
        f"   current : {record['final_label']} -> {record['response_action']}"
    )


def interactive() -> None:
    pending = turn_memory.list_corrections("pending")
    if not pending:
        print("No pending corrections.")
        return
    print(f"{len(pending)} pending. Keys: [y] approve Gemini's label, [q/f/c/n/a/s] approve with that label, "
          "[r] reject, [d] delete, [enter] skip, [x] stop.")
    for record in pending:
        print()
        show(record)
        choice = input("   decision> ").strip().lower()
        if choice == "x":
            break
        if choice == "y":
            turn_memory.review(record["id"], "approved")
        elif choice in LABEL_KEYS:
            turn_memory.review(record["id"], "approved", label=LABEL_KEYS[choice])
        elif choice == "r":
            turn_memory.review(record["id"], "rejected")
        elif choice == "d":
            turn_memory.delete(record["id"])


def export() -> None:
    approved = turn_memory.list_corrections("approved")
    cases = [
        {
            "case_id": f"learned_{record['id']:04d}",
            "initial_summary": f"Ongoing {record['domains'] or 'legal'} consultation.",
            "domains": [item for item in (record["domains"] or "").split(",") if item],
            "known_facts": [],
            "message": record["message"],
            "expected_turn_type": record["final_label"],
            **({"should_bypass_pipeline": True} if record["final_label"] in {"acknowledgement", "small_talk"} else {}),
            "note": f"learned from use: rules said {record['rule_label']}",
        }
        for record in approved
    ]
    EXPORT_PATH.write_text(json.dumps({
        "description": "Approved turn corrections learned from real use (review_turn_corrections.py export).",
        "cases": cases,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {EXPORT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Review recorded follow-up turn corrections.")
    sub = parser.add_subparsers(dest="command")
    listing = sub.add_parser("list")
    listing.add_argument("--status", default="pending", choices=["pending", "approved", "rejected", "all"])
    for name in ("approve", "reject"):
        command = sub.add_parser(name)
        command.add_argument("id", type=int)
        command.add_argument("--note")
        if name == "approve":
            command.add_argument("--label", choices=sorted(turn_memory.TURN_TYPES))
    sub.add_parser("delete").add_argument("id", type=int)
    sub.add_parser("stats")
    sub.add_parser("export")
    args = parser.parse_args()

    if args.command is None:
        interactive()
    elif args.command == "list":
        records = turn_memory.list_corrections(None if args.status == "all" else args.status)
        for record in records:
            show(record)
        print(f"{len(records)} record(s).")
    elif args.command in {"approve", "reject"}:
        ok = turn_memory.review(
            args.id,
            "approved" if args.command == "approve" else "rejected",
            label=getattr(args, "label", None),
            note=args.note,
        )
        print("Done." if ok else f"No record #{args.id}.")
    elif args.command == "delete":
        print("Deleted." if turn_memory.delete(args.id) else f"No record #{args.id}.")
    elif args.command == "stats":
        print(json.dumps(turn_memory.stats(), indent=2))
    elif args.command == "export":
        export()


if __name__ == "__main__":
    main()
