from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
import source_text
from config import DOCUMENTS_DIR

client = TestClient(main.app)


def test_repeated_search_heading_is_dropped():
    text = (
        "Manual Section 5.1.4.1 — To report a complaint, you may keep following information ready\n"
        "5.1.4.1 To report a complaint, you may keep following information ready before registering\n"
        "your complaint:"
    )
    readable = source_text.readable_source_text(text)

    assert not readable.startswith("Manual Section")
    assert readable.startswith("5.1.4.1 To report a complaint")


def test_heading_after_chapter_line_is_dropped_but_chapter_kept():
    text = "CHAPTER IV\nSection 35 — Manner in which complaint shall be made\n35. Manner in which complaint shall be made .—\n(1) A complaint may be filed."
    lines = source_text.readable_source_text(text).split("\n")

    assert lines[0] == "CHAPTER IV"
    assert not any(line.startswith("Section 35 —") for line in lines)


def test_wrapped_lines_are_rejoined_and_list_items_kept():
    text = (
        "To report a complaint, you may keep following information ready before registering\n"
        "your complaint:\n"
        "i. If you found a fake profile on a messaging platform such as\n"
        "WhatsApp, Hike etc.:\n"
        "a. Take the screenshot of the profile"
    )
    lines = source_text.readable_source_text(text).split("\n")

    assert lines == [
        "To report a complaint, you may keep following information ready before registering your complaint:",
        "i. If you found a fake profile on a messaging platform such as WhatsApp, Hike etc.:",
        "a. Take the screenshot of the profile",
    ]


def test_run_together_subsections_are_split():
    text = "45. Cutting off essential supply. (1)No landlord shall cut off supply.(2)If a landlord contravenes, the tenant may apply."
    lines = source_text.readable_source_text(text).split("\n")

    assert lines[1].startswith("(1)No landlord")
    assert lines[2].startswith("(2)If a landlord")


def test_page_header_and_footer_removed():
    text = "a. Save the page as evidence\nUSER MANUAL FOR NATIONAL CYBERCRIME REPORTING PORTAL\nPage 22 of 91\nNote1: Preserve the original evidence."
    readable = source_text.readable_source_text(text)

    assert "Page 22 of 91" not in readable
    assert "USER MANUAL FOR" not in readable
    assert "Note1: Preserve" in readable


def test_case_law_good_law_note_is_kept():
    text = "S.P. Gupta v. Union of India, 1982 AIR 149\nNOTE: This decision is partial good law -- some holdings overruled.\n1. These writ petitions raise issues."

    assert "NOTE: This decision is partial good law" in source_text.readable_source_text(text)


def first_active_pdf() -> str:
    manifest = json.loads((DOCUMENTS_DIR / "corpus_manifest.json").read_text(encoding="utf-8"))
    return next(
        item["source_file"]
        for item in manifest["documents"]
        if item.get("source_file", "").endswith(".pdf")
        and not item["source_file"].startswith("archive/")
        and (DOCUMENTS_DIR / item["source_file"]).exists()
    )


def test_corpus_pdf_is_served_inline():
    response = client.get("/api/corpus/file", params={"source": first_active_pdf()})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")


def test_corpus_pdf_endpoint_refuses_paths_outside_manifest():
    for source in ("../config.py", "..\\.env", "../legal_aid.db", "archive/bharatiya_nagarik_suraksha_sanhita_2023.pdf", "corpus_manifest.json", ""):
        assert client.get("/api/corpus/file", params={"source": source}).status_code == 404
