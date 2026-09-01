from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
import rag


client = TestClient(main.app)


def classified_route(domain: str = "consumer") -> main.domain_router.RouteDecision:
    return main.domain_router.RouteDecision(
        status="classified",
        domains=[domain],
        primary_domain=domain,
        confidence="high",
        issue_summary="Mock supported legal issue.",
        needs_clarification=False,
    )


def test_health_endpoint_shape():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "knowledge_base_loaded" in data


def test_empty_question_rejected():
    response = client.post("/api/ask", json={"question": "   "})
    assert response.status_code == 400
    assert "Question is required" in response.json()["detail"]


def test_missing_vector_store_handling(monkeypatch):
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _question: classified_route())

    def missing_retrieve(_question: str):
        raise main.VectorStoreMissingError("Vector store is missing. Run `python ingest.py` inside backend first.")

    monkeypatch.setattr(main.rag, "retrieve", missing_retrieve)
    response = client.post("/api/ask", json={"question": "The seller refused a refund."})
    assert response.status_code == 503
    assert "Vector store is missing" in response.json()["detail"]


def test_configuration_error_returns_json(monkeypatch):
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _question: classified_route())

    def configuration_error(*_args, **_kwargs):
        raise main.ConfigurationError("Gemini API key is not configured.")

    monkeypatch.setattr(main, "answer_grounded_from_context", configuration_error)
    response = client.post("/api/ask", json={"question": "The seller refused a refund."})
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Gemini API key is not configured."}


def test_response_json_shape(monkeypatch):
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _question: classified_route())

    def fake_grounded(*_args, **_kwargs):
        return {
            "answer": {
                "issue_summary": "Mock summary",
                "possible_rights": ["Mock right"],
                "next_steps": ["Mock step"],
                "possible_legal_position": ["Mock right"],
                "suggested_next_steps": ["Mock step"],
            },
            "sources": [{"document": "Consumer Protection Act, 2019", "page": 1, "section": None, "excerpt": "Mock excerpt"}],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is legal information, not professional legal advice.",
        }

    monkeypatch.setattr(main, "answer_grounded_from_context", fake_grounded)
    response = client.post("/api/ask", json={"question": "Can I ask for refund for defective goods?"})
    assert response.status_code == 200
    data = response.json()
    assert set(data) >= {"answer", "sources", "confidence", "insufficient_context", "disclaimer"}
    assert set(data["answer"]) >= {"issue_summary", "possible_rights", "next_steps"}


def test_off_topic_question_uses_safe_fallback(monkeypatch):
    def out_of_scope(_question: str):
        return main.domain_router.RouteDecision(
            status="out_of_scope",
            domains=[],
            primary_domain=None,
            confidence="high",
            issue_summary="Clearly not a legal-information issue.",
            needs_clarification=False,
        )

    monkeypatch.setattr(main.domain_router, "route_issue", out_of_scope)
    response = client.post("/api/ask", json={"question": "Write Python code for bubble sort."})
    assert response.status_code == 200
    data = response.json()
    assert data["insufficient_context"] is True
    assert data["sources"] == []
    assert "legal-information" in data["answer"]["issue_summary"]


def test_response_normalization_removes_markdown_numbering_disclaimer_and_svg():
    parsed = {
        "answer": {
            "issue_summary": "**Possible consumer dispute** svg",
            "possible_rights": [
                "**May request repair**",
                "This is legal information, not professional legal advice.",
                "**May request repair**",
                "svg",
            ],
            "next_steps": [
                "1. **Keep the invoice**",
                "Step 2: Send a written request",
                "This is legal information, not professional legal advice.",
            ],
        },
        "confidence": "medium",
        "insufficient_context": False,
    }
    chunk = rag.RetrievedChunk(
        text="defect means any fault imperfection or shortcoming in quality",
        source="consumer_protection_act_2019.pdf",
        document_title="Consumer Protection Act, 2019",
        page=6,
        score=0.52,
    )

    normalized = rag.normalize_rag_response(parsed, [chunk])

    assert normalized["answer"]["issue_summary"] == "Possible consumer dispute"
    assert normalized["answer"]["possible_rights"] == ["May request repair"]
    assert normalized["answer"]["next_steps"] == ["Keep the invoice", "Send a written request"]
    assert normalized["disclaimer"] == "This is legal information, not professional legal advice."


def test_clear_cyber_signal_detection():
    signals = rag.detect_domain_signals("cyber fraud online payment")

    assert signals["scores"]["cyber"] > signals["scores"]["consumer"]
    assert "cyber" in signals["primary_domains"]


def test_clear_consumer_signal_detection():
    signals = rag.detect_domain_signals("defective product seller refusing refund")

    assert signals["scores"]["consumer"] > signals["scores"]["cyber"]
    assert "consumer" in signals["primary_domains"]


def test_clear_tenancy_signal_detection():
    signals = rag.detect_domain_signals("landlord cut electricity essential supply")

    assert signals["scores"]["tenancy"] > signals["scores"]["consumer"]
    assert "tenancy" in signals["primary_domains"]


def test_clear_constitutional_signal_detection():
    signals = rag.detect_domain_signals("article 14 right to equality")

    assert signals["scores"]["constitutional_public_authority"] > signals["scores"]["consumer"]
    assert "constitutional_public_authority" in signals["primary_domains"]


def test_generic_online_payment_does_not_force_consumer_expansion():
    signals = rag.detect_domain_signals("online payment")

    assert signals["scores"]["consumer"] < rag.DOMAIN_SIGNAL_THRESHOLD
    assert signals["primary_domains"] == []
    assert rag.retrieval_query("online payment") == "online payment"


def test_cyber_cues_outweigh_generic_payment_language():
    query = "cyber fraud online payment"
    signals = rag.detect_domain_signals(query)

    assert signals["scores"]["cyber"] > signals["scores"]["consumer"]
    assert rag.retrieval_query(query) == query


def test_multi_domain_query_can_retain_multiple_primary_domains():
    signals = rag.detect_domain_signals("Instagram seller took payment and blocked me after refund request")

    assert "consumer" in signals["primary_domains"]
    assert "cyber" in signals["primary_domains"]


def test_domain_boost_changes_ranking_without_hard_filtering():
    consumer_chunk = rag.RetrievedChunk(
        text="consumer product payment refund",
        source="consumer/consumer_protection_act_2019.pdf",
        document_title="The Consumer Protection Act, 2019",
        page=1,
        score=0.55,
        domain="consumer",
    )
    cyber_chunk = rag.RetrievedChunk(
        text="cyber fraud online payment unauthorized transaction",
        source="cyber/information_technology_act_2000.pdf",
        document_title="The Information Technology Act, 2000",
        page=1,
        score=0.50,
        domain="cyber",
    )

    selected = rag.select_relevant_chunks(
        [consumer_chunk, cyber_chunk],
        question="cyber fraud online payment",
        top_k=2,
    )

    assert selected[0].domain == "cyber"
    assert {chunk.domain for chunk in selected} == {"cyber", "consumer"}


def test_high_priority_source_gets_modest_boost():
    high = rag.RetrievedChunk(
        text="identity theft unauthorized access account",
        source="cyber/information_technology_act_2000.pdf",
        document_title="The Information Technology Act, 2000",
        page=1,
        score=0.5,
        domain="cyber",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )
    low = rag.RetrievedChunk(
        text="identity theft unauthorized access account",
        source="cyber/supporting.pdf",
        document_title="Supporting Cyber Material",
        page=1,
        score=0.5,
        domain="cyber",
        retrieval_priority="low",
        authority_level="primary",
        status="active",
        document_type="statute",
    )

    assert rag.source_role_boost("identity theft using my personal details", high) > rag.source_role_boost(
        "identity theft using my personal details",
        low,
    )


def test_primary_authority_gets_modest_boost():
    primary = rag.RetrievedChunk(
        text="unauthorized access computer account",
        source="cyber/information_technology_act_2000.pdf",
        document_title="The Information Technology Act, 2000",
        page=1,
        score=0.5,
        domain="cyber",
        retrieval_priority="medium",
        authority_level="primary",
        status="active",
        document_type="statute",
    )
    guide = rag.RetrievedChunk(
        text="unauthorized access computer account",
        source="cyber/manual.pdf",
        document_title="Cybercrime Portal Manual",
        page=1,
        score=0.5,
        domain="cyber",
        retrieval_priority="medium",
        authority_level="procedural_guide",
        status="reference_only",
        document_type="procedural_user_guide",
    )

    assert rag.source_role_boost("identity theft using my personal details", primary) > rag.source_role_boost(
        "identity theft using my personal details",
        guide,
    )


def test_supporting_only_source_is_not_hard_filtered():
    primary = rag.RetrievedChunk(
        text="landlord tenant eviction premises",
        source="tenancy/delhi_rent_control_act_1958.pdf",
        document_title="The Delhi Rent Control Act, 1958",
        page=1,
        score=0.5,
        domain="tenancy",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )
    supporting = rag.RetrievedChunk(
        text="landlord tenant lease agreement property",
        source="tenancy/transfer_of_property_act_1882.pdf",
        document_title="The Transfer of Property Act, 1882",
        page=1,
        score=0.49,
        domain="tenancy",
        retrieval_priority="medium",
        authority_level="primary",
        status="supporting_only",
        document_type="supporting_property_law",
    )

    selected = rag.select_relevant_chunks([supporting, primary], "landlord tenant dispute", top_k=2)

    assert {chunk.status for chunk in selected} == {"active", "supporting_only"}


def test_procedural_guide_can_still_rank_first_for_procedural_query():
    manual = rag.RetrievedChunk(
        text="report online cybercrime portal submit complaint",
        source="cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf",
        document_title="Cybercrime Portal Manual",
        page=1,
        score=0.56,
        domain="cyber",
        retrieval_priority="low",
        authority_level="procedural_guide",
        status="reference_only",
        document_type="procedural_user_guide",
    )
    act = rag.RetrievedChunk(
        text="unauthorized access identity theft computer resource",
        source="cyber/information_technology_act_2000.pdf",
        document_title="The Information Technology Act, 2000",
        page=1,
        score=0.5,
        domain="cyber",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )

    selected = rag.select_relevant_chunks([act, manual], "how do I report online cybercrime", top_k=2)

    assert selected[0].document_type == "procedural_user_guide"


def test_strong_semantic_relevance_can_outweigh_authority_preference():
    primary = rag.RetrievedChunk(
        text="general computer resource intermediary",
        source="cyber/information_technology_act_2000.pdf",
        document_title="The Information Technology Act, 2000",
        page=1,
        score=0.45,
        domain="cyber",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )
    guide = rag.RetrievedChunk(
        text="report online cybercrime portal complaint step submit",
        source="cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf",
        document_title="Cybercrime Portal Manual",
        page=1,
        score=0.62,
        domain="cyber",
        retrieval_priority="low",
        authority_level="procedural_guide",
        status="reference_only",
        document_type="procedural_user_guide",
    )

    selected = rag.select_relevant_chunks([primary, guide], "how do I report online cybercrime", top_k=2)

    assert selected[0].document_type == "procedural_user_guide"


def test_domain_aware_behavior_remains_intact_with_source_role_boosts():
    consumer_chunk = rag.RetrievedChunk(
        text="consumer product payment refund",
        source="consumer/consumer_protection_act_2019.pdf",
        document_title="The Consumer Protection Act, 2019",
        page=1,
        score=0.55,
        domain="consumer",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )
    cyber_chunk = rag.RetrievedChunk(
        text="cyber fraud online payment unauthorized transaction",
        source="cyber/information_technology_act_2000.pdf",
        document_title="The Information Technology Act, 2000",
        page=1,
        score=0.50,
        domain="cyber",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )

    selected = rag.select_relevant_chunks([consumer_chunk, cyber_chunk], "cyber fraud online payment", top_k=2)

    assert selected[0].domain == "cyber"


def test_cross_domain_retrieval_remains_possible_with_source_role_boosts():
    consumer_chunk = rag.RetrievedChunk(
        text="instagram seller payment refund order blocked me",
        source="consumer/ecommerce_rules_2020.pdf",
        document_title="The Consumer Protection (E-Commerce) Rules, 2020",
        page=1,
        score=0.53,
        domain="consumer",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="rules",
    )
    cyber_chunk = rag.RetrievedChunk(
        text="instagram account online scam blocked me cyber complaint",
        source="cyber/information_technology_act_2000.pdf",
        document_title="The Information Technology Act, 2000",
        page=1,
        score=0.52,
        domain="cyber",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )

    selected = rag.select_relevant_chunks(
        [consumer_chunk, cyber_chunk],
        "Instagram seller took payment and blocked me",
        top_k=2,
    )

    assert {chunk.domain for chunk in selected} == {"consumer", "cyber"}


def test_rti_intent_detection():
    signals = rag.detect_public_authority_intents("RTI application ka reply nahi mila")

    assert signals["scores"]["rti"] >= rag.PUBLIC_AUTHORITY_INTENT_THRESHOLD
    assert "rti" in signals["primary_intents"]


def test_rti_cue_does_not_match_inside_advertisement():
    domain_signals = rag.detect_domain_signals("misleading advertisement caused me loss")
    intent_signals = rag.detect_public_authority_intents("misleading advertisement caused me loss")

    assert domain_signals["scores"]["constitutional_public_authority"] == 0.0
    assert intent_signals["scores"]["rti"] == 0.0


def test_fundamental_rights_intent_detection():
    signals = rag.detect_public_authority_intents("article 14 right to equality")

    assert signals["scores"]["fundamental_rights"] >= rag.PUBLIC_AUTHORITY_INTENT_THRESHOLD
    assert "fundamental_rights" in signals["primary_intents"]


def test_legal_aid_intent_detection():
    signals = rag.detect_public_authority_intents("can I get a free lawyer through legal aid")

    assert signals["scores"]["legal_aid"] >= rag.PUBLIC_AUTHORITY_INTENT_THRESHOLD
    assert "legal_aid" in signals["primary_intents"]


def test_human_rights_intent_detection():
    signals = rag.detect_public_authority_intents("human rights complaint against public authority")

    assert signals["scores"]["human_rights"] >= rag.PUBLIC_AUTHORITY_INTENT_THRESHOLD
    assert "human_rights" in signals["primary_intents"]


def test_contempt_intent_detection():
    signals = rag.detect_public_authority_intents("court order was deliberately disobeyed")

    assert signals["scores"]["contempt"] >= rag.PUBLIC_AUTHORITY_INTENT_THRESHOLD
    assert "contempt" in signals["primary_intents"]


def test_multi_intent_public_authority_query_retains_multiple_signals():
    signals = rag.detect_public_authority_intents("article 21 human rights complaint against public authority")

    assert "fundamental_rights" in signals["primary_intents"] or "fundamental_rights" in signals["secondary_intents"]
    assert "human_rights" in signals["primary_intents"] or "human_rights" in signals["secondary_intents"]


def test_public_authority_intent_prefers_expected_document_family():
    constitution = rag.RetrievedChunk(
        text="fundamental rights equality article 14 state action",
        source="constitutional_public_authority/constitution_of_india.pdf",
        document_title="The Constitution of India",
        page=1,
        score=0.5,
        domain="constitutional_public_authority",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="constitution",
    )
    rti = rag.RetrievedChunk(
        text="information request public authority records",
        source="constitutional_public_authority/right_to_information_act_2005.pdf",
        document_title="The Right to Information Act, 2005",
        page=1,
        score=0.5,
        domain="constitutional_public_authority",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )

    selected = rag.select_relevant_chunks([constitution, rti], "public authority refused to give information", top_k=2)

    assert selected[0].source == "constitutional_public_authority/right_to_information_act_2005.pdf"


def test_equality_query_uses_article_14_specific_expansion():
    expanded = rag.retrieval_query("right to equality")

    assert "article 14 equality before law" in expanded
    assert "article 21 protection of life" not in expanded


def test_strong_semantic_relevance_can_outweigh_public_authority_intent_preference():
    constitution = rag.RetrievedChunk(
        text="general equality state action",
        source="constitutional_public_authority/constitution_of_india.pdf",
        document_title="The Constitution of India",
        page=1,
        score=0.5,
        domain="constitutional_public_authority",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="constitution",
    )
    human_rights = rag.RetrievedChunk(
        text="human rights complaint public authority rights violation commission",
        source="constitutional_public_authority/protection_of_human_rights_act_1993.pdf",
        document_title="The Protection of Human Rights Act, 1993",
        page=1,
        score=0.64,
        domain="constitutional_public_authority",
        retrieval_priority="medium",
        authority_level="primary",
        status="active",
        document_type="statute",
    )

    selected = rag.select_relevant_chunks(
        [constitution, human_rights],
        "article 21 human rights complaint against public authority",
        top_k=2,
    )

    assert selected[0].source == "constitutional_public_authority/protection_of_human_rights_act_1993.pdf"


def test_public_authority_intent_does_not_affect_non_constitutional_domains():
    consumer = rag.RetrievedChunk(
        text="rti refund defective product seller",
        source="consumer/consumer_protection_act_2019.pdf",
        document_title="The Consumer Protection Act, 2019",
        page=1,
        score=0.5,
        domain="consumer",
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
    )

    assert rag.public_authority_intent_boost("RTI application issue", consumer) == 0.0


def test_reranking_prefers_substantive_act_chunk_over_duplicate_rule_chunk():
    act_chunk = rag.RetrievedChunk(
        text="Section 39 Findings of District Commission replace the goods return to the complainant the price defect",
        source="consumer_protection_act_2019.pdf",
        document_title="Consumer Protection Act, 2019",
        page=22,
        score=0.48,
        section_number="39",
        section_title="Findings of District Commission",
    )
    rule_chunk = rag.RetrievedChunk(
        text="Rule 39 replace the goods return to the complainant the price defect",
        source="consumer_protection_general_rules_2020.pdf",
        document_title="Consumer Protection (General) Rules, 2020",
        page=22,
        score=0.5,
        rule_number="39",
    )

    selected = rag.select_relevant_chunks(
        [rule_chunk, act_chunk],
        question="The seller is refusing to refund a defective product.",
        top_k=2,
    )

    assert selected[0].document_title == "Consumer Protection Act, 2019"
    assert len(selected) == 1


def test_real_retrieval_returns_substantive_act_sources_for_defective_product():
    if not (Path(__file__).resolve().parents[1] / "vectorstore" / "metadata.json").exists():
        pytest.skip("Vector store has not been built.")

    rag.rag.load()
    chunks = rag.rag.retrieve("The seller is refusing to refund a defective product.")
    sections = {
        chunk.section_number
        for chunk in chunks
        if chunk.source == "consumer/consumer_protection_act_2019.pdf"
    }

    assert {"39", "83"} & sections
    assert any(chunk.source == "consumer/consumer_protection_act_2019.pdf" for chunk in chunks)
    assert len({(chunk.document_title, chunk.section_number, chunk.rule_number) for chunk in chunks}) == len(chunks)
