from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import grounded_answer
import ipc_bns
import rag
from rag import RetrievedChunk


def bns_chunk(section: str) -> RetrievedChunk:
    return RetrievedChunk(
        text=f"BNS section {section}",
        source=ipc_bns.BNS_SOURCE_FILE,
        document_title="The Bharatiya Nyaya Sanhita, 2023",
        page=1,
        score=0.4,
        section_number=section,
        status="supporting_only",
    )


def test_retrieval_query_adds_the_mapped_bns_section():
    query = rag.retrieval_query("My FIR is under 420 IPC")
    assert "Bharatiya Nyaya Sanhita Section 318" in query
    assert rag.retrieval_query("my landlord will not return my deposit").count("Bharatiya Nyaya Sanhita") == 0


def test_mapped_bns_section_outranks_the_supporting_only_penalty():
    question = "threatened online, case under IPC 506"
    assert rag.ipc_mapped_section_boost(question, bns_chunk("351")) > rag.SUPPORTING_ONLY_PENALTY
    assert rag.ipc_mapped_section_boost(question, bns_chunk("318")) == 0.0
    assert rag.ipc_mapped_section_boost("threatened online", bns_chunk("351")) == 0.0


def test_grounded_prompt_includes_mapping_block_only_when_given():
    chunk = bns_chunk("318")
    with_block = grounded_answer.build_grounded_prompt("q", "s", ["cyber"], [chunk], None, "- IPC 420 → BNS 318(4).")
    without_block = grounded_answer.build_grounded_prompt("q", "s", ["cyber"], [chunk])
    assert "IPC TO BNS MAPPING" in with_block and "- IPC 420 → BNS 318(4)." in with_block
    assert "IPC TO BNS MAPPING (from" not in without_block


def test_bns_section_chunks_returns_unindexed_sections():
    chunks = rag.bns_section_chunks({"103"})
    assert chunks and all(chunk.section_number == "103" for chunk in chunks)
    assert chunks[0].source == ipc_bns.BNS_SOURCE_FILE


def test_lookup_question_is_answered_from_the_map_without_routing(monkeypatch):
    import main
    from fastapi.testclient import TestClient

    def fail_routing(*_args, **_kwargs):
        raise AssertionError("a section lookup must not reach the router")

    monkeypatch.setattr(main.domain_router, "route_issue", fail_routing)
    response = TestClient(main.app).post("/api/ask", json={"question": "what is IPC 302 now?"})
    assert response.status_code == 200
    body = response.json()
    assert "IPC 302 (Punishment for murder) is now BNS 103(1)" in body["answer"]["issue_summary"]
    assert body["ipc_bns_mapping"]["sections"][0]["bns_sections"] == ["103(1)"]
    assert body["sources"] and body["sources"][0]["source_file"] == ipc_bns.BNS_SOURCE_FILE
    assert main.IPC_LOOKUP_LIMITATION in body["answer"]["limitations"]


def test_lookup_reply_qualifies_mappings_that_are_our_reading():
    import main

    summary = main.ipc_lookup_response("IPC 143 now?")["answer"]["issue_summary"]
    assert "our reading of the BNS text; the government table does not list it" in summary


def test_out_of_scope_reply_still_carries_the_mapping():
    import domain_router
    import main

    route = domain_router.RouteDecision(
        status="unsupported", domains=[], primary_domain=None, confidence="high",
        issue_summary=None, needs_clarification=False,
    )
    response = main.router_minimal_response(route, "my brother was arrested under 302 IPC, what should we do")
    assert response["ipc_bns_mapping"]["sections"][0]["ipc_section"] == "302"
    assert "ipc_bns_mapping" not in main.router_minimal_response(route, "my brother was arrested")
