"""select_relevant_chunks(): the admission window must not be anchored by a down-weighted
procedural manual on a substantive question (2026-10-28). Scores are the ones measured on the
rebuilt, windowed index for "someone hacked my social media account"."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag import RetrievedChunk, is_down_weighted_manual, select_relevant_chunks

MANUAL = dict(
    source="cyber/cybercrime_portal_citizen_manual_latest.pdf",
    document_title="National Cyber Crime Reporting Portal - Citizen User Manual",
    authority_level="procedural_guide",
    document_type="procedural_user_guide",
    retrieval_priority="low",
    status="reference_only",
)
IT_ACT = dict(
    source="cyber/information_technology_act_2000.pdf",
    document_title="The Information Technology Act, 2000",
    authority_level="primary",
    document_type="statute",
    retrieval_priority="high",
    status="active",
)


def chunk(meta: dict, score: float, text: str, **extra) -> RetrievedChunk:
    return RetrievedChunk(text=text, page=1, score=score, domain="cyber", **meta, **extra)


def candidates() -> list[RetrievedChunk]:
    return [
        chunk(MANUAL, 0.667, "If your social media account is hacked, report it on the portal under Hacking.", chunk_id="m1"),
        chunk(MANUAL, 0.531, "Steps to file a complaint on the cybercrime portal and track its status.", chunk_id="m2"),
        chunk(IT_ACT, 0.319, "66C. Punishment for identity theft. Whoever fraudulently makes use of the password...", section_number="66C", chunk_id="i66c"),
        chunk(IT_ACT, 0.308, "43. Penalty and compensation for damage to computer, computer system, etc.", section_number="42", chunk_id="i42"),
    ]


def test_statutes_are_admitted_when_a_manual_scores_far_higher_on_a_substantive_question():
    selected = select_relevant_chunks(candidates(), "someone hacked my social media account")
    sources = [c.source for c in selected]
    assert "cyber/information_technology_act_2000.pdf" in sources
    assert "cyber/cybercrime_portal_citizen_manual_latest.pdf" in sources  # down-weighted, not removed


def test_manual_still_anchors_procedural_questions():
    question = "how do I report a hacked account on the cybercrime portal"
    assert not is_down_weighted_manual(question, candidates()[0])
    selected = select_relevant_chunks(candidates(), question)
    assert selected[0].source == "cyber/cybercrime_portal_citizen_manual_latest.pdf"


def test_only_manuals_retrieved_still_returns_them():
    only_manuals = [c for c in candidates() if c.source.endswith("manual_latest.pdf")]
    selected = select_relevant_chunks(only_manuals, "someone hacked my social media account")
    assert selected
