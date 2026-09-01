from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import grounded_answer
import rag


def chunk(chunk_id="c1", domain="consumer"):
    return rag.RetrievedChunk(
        chunk_id=chunk_id,
        text="The District Commission may direct replacement of goods or return of price where supported by the Act.",
        source="consumer/consumer_protection_act_2019.pdf",
        document_title="Consumer Protection Act, 2019",
        page=10,
        page_start=10,
        page_end=10,
        score=0.8,
        domain=domain,
        section_number="39",
        section_title="Findings of District Commission",
    )


def test_grounded_prompt_separates_user_facts_and_legal_material():
    prompt = grounded_answer.build_grounded_prompt(
        original_message="seller refused refund",
        normalized_case_summary="User says seller refused refund for defective product.",
        domains=["consumer"],
        chunks=[chunk()],
    )

    assert "USER FACTS:" in prompt
    assert "RETRIEVED LEGAL MATERIAL:" in prompt
    assert "Never treat user facts as law" in prompt


def test_unknown_chunk_ids_are_removed():
    output = grounded_answer.normalize_grounded_output(
        {
            "issue_summary": "Neutral summary.",
            "what_this_may_involve": [],
            "possible_legal_position": ["A provision may be relevant."],
            "suggested_next_steps": [],
            "evidence_to_preserve": [],
            "where_to_approach": [],
            "limitations": [],
            "source_chunk_ids": ["missing", "c1"],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is general legal information.",
        },
        [chunk()],
    )

    assert output["source_chunk_ids"] == ["c1"]
    assert output["_invalid_source_ids"] == ["missing"]
    assert output["sources"][0]["chunk_id"] == "c1"


def test_structured_output_validation_and_mapping():
    output = grounded_answer.normalize_grounded_output(
        {
            "issue_summary": "**User reports** a defective product.",
            "what_this_may_involve": ["1. Consumer dispute"],
            "possible_legal_position": ["**Replacement may be relevant**"],
            "suggested_next_steps": ["Step 1: Keep invoice"],
            "evidence_to_preserve": ["If available, preserve chats"],
            "where_to_approach": ["District Commission if supported"],
            "limitations": ["Facts are incomplete"],
            "source_chunk_ids": ["c1"],
            "confidence": "high",
            "insufficient_context": False,
            "disclaimer": "This is general legal information.",
        },
        [chunk()],
    )

    assert output["answer"]["issue_summary"] == "User reports a defective product."
    assert output["answer"]["suggested_next_steps"] == ["Keep invoice"]
    assert output["sources"][0]["provision"].startswith("Section 39")


def test_insufficient_issue_can_return_insufficient_context():
    output = grounded_answer.normalize_grounded_output(
        {
            "issue_summary": "Not enough legal material.",
            "what_this_may_involve": [],
            "possible_legal_position": [],
            "suggested_next_steps": [],
            "evidence_to_preserve": [],
            "where_to_approach": [],
            "limitations": ["Retrieved material does not answer this."],
            "source_chunk_ids": [],
            "confidence": "high",
            "insufficient_context": True,
            "disclaimer": "This is general legal information.",
        },
        [chunk()],
    )

    assert output["insufficient_context"] is True
    assert output["confidence"] != "high"


def test_no_retrieved_law_returns_no_fabricated_answer():
    output = grounded_answer.insufficient_response("No retrieved law.")

    assert output["sources"] == []
    assert output["insufficient_context"] is True


def test_obvious_unsupported_source_gap_returns_insufficient_without_fabrication():
    output = grounded_answer.generate_grounded_answer(
        original_message="income tax notice ka reply kaise doon",
        normalized_case_summary="income tax notice",
        domains=["constitutional_public_authority"],
        chunks=[chunk()],
    )

    assert output["insufficient_context"] is True
    assert output["sources"] == []
    assert "Income Tax Act" not in json.dumps(output["answer"])


def test_multi_domain_source_mapping():
    cyber = chunk("c2", "cyber")
    cyber.source = "cyber/information_technology_act_2000.pdf"
    cyber.document_title = "Information Technology Act, 2000"
    cyber.section_number = "66"
    output = grounded_answer.normalize_grounded_output(
        {
            "issue_summary": "Possible seller and cyber issue.",
            "what_this_may_involve": [],
            "possible_legal_position": [],
            "suggested_next_steps": [],
            "evidence_to_preserve": [],
            "where_to_approach": [],
            "limitations": [],
            "source_chunk_ids": ["c1", "c2"],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is general legal information.",
        },
        [chunk(), cyber],
    )

    assert {source["chunk_id"] for source in output["sources"]} == {"c1", "c2"}


def test_neutral_issue_summary_is_preserved():
    output = grounded_answer.normalize_grounded_output(
        {
            "issue_summary": "You report that your landlord stopped electricity supply.",
            "what_this_may_involve": [],
            "possible_legal_position": [],
            "suggested_next_steps": [],
            "evidence_to_preserve": [],
            "where_to_approach": [],
            "limitations": [],
            "source_chunk_ids": ["c1"],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is general legal information.",
        },
        [chunk()],
    )

    assert "illegally" not in output["answer"]["issue_summary"].lower()
