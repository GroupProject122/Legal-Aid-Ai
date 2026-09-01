from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rag


def chunk(chunk_id: str, domain: str, title: str, section: str, section_title: str, score: float) -> rag.RetrievedChunk:
    return rag.RetrievedChunk(
        chunk_id=chunk_id,
        text=f"{section_title} legal text",
        source=f"{domain}/{title.lower().replace(' ', '_')}.pdf",
        document_title=title,
        page=1,
        score=score,
        rerank_score=0.0,
        domain=domain,
        retrieval_priority="high",
        authority_level="primary",
        status="active",
        document_type="statute",
        section_number=section,
        section_title=section_title,
    )


def test_consumer_refund_query_no_longer_expands_to_product_liability():
    query = rag.retrieval_query("The seller is refusing to refund a defective product.")

    assert "consumer complaint remedy" in query
    assert "product liability" not in query.lower()


def test_product_liability_query_still_gets_product_liability_expansion():
    query = rag.retrieval_query("The phone exploded and injured me because it was defective.")

    assert "product liability" in query.lower()


def test_no_harm_defective_refund_query_suppresses_product_liability():
    question = "I bought a defective laptop online. It stopped working within two days. No one was injured."
    query = rag.retrieval_query(question)
    product_liability = chunk("pl83", "consumer", "The Consumer Protection Act, 2019", "83", "Product liability action", 0.55)
    remedy = chunk("s39", "consumer", "The Consumer Protection Act, 2019", "39", "Findings of District Commission", 0.5)

    assert "product liability" not in query.lower()
    assert rag.should_suppress_product_liability_for_query(question)
    assert rag.final_rerank_score(question, remedy) > rag.final_rerank_score(question, product_liability)


def test_credential_misuse_query_expands_toward_section_66c():
    query = rag.retrieval_query("Someone used my personal details to access my online account without permission.")

    assert "Section 66C" in query
    assert rag.is_credential_misuse_query(query)


def test_credential_misuse_boost_prefers_identity_theft_section():
    query = "Someone used my personal details to access my online account without permission."
    section_66c = chunk("c66c", "cyber", "The Information Technology Act, 2000", "66C", "Punishment for identity theft", 0.45)
    section_72 = chunk("c72", "cyber", "The Information Technology Act, 2000", "72", "Penalty for breach of confidentiality and privacy", 0.45)

    assert rag.final_rerank_score(query, section_66c) > rag.final_rerank_score(query, section_72)


def test_multi_domain_balancing_can_promote_secondary_domain_without_filtering():
    query = "Instagram seller took payment and blocked me"
    ranked = [
        chunk("consumer1", "consumer", "The Consumer Protection Act, 2019", "39", "Findings of District Commission", 0.8),
        chunk("consumer2", "consumer", "The Consumer Protection Act, 2019", "86", "Liability of product sellers", 0.78),
        chunk("consumer3", "consumer", "The Consumer Protection Act, 2019", "83", "Product liability action", 0.76),
        chunk("cyber1", "cyber", "The Information Technology Act, 2000", "66C", "Punishment for identity theft", 0.74),
    ]
    for item in ranked:
        item.rerank_score = rag.final_rerank_score(query, item)
    balanced = rag.balance_multi_domain_candidates(query, ranked)

    assert any(item.domain == "cyber" for item in balanced[:4])
    assert any(item.domain == "consumer" for item in balanced[:4])


def test_multi_domain_selection_replaces_duplicate_domain_to_keep_both_domains():
    query = "Instagram seller took payment and blocked me"
    selected = [
        chunk("cyber1", "cyber", "Cyber Manual", "", "Report cybercrime", 0.7),
        chunk("cyber2", "cyber", "Cyber Manual", "", "Track complaint", 0.69),
        chunk("cyber3", "cyber", "The Information Technology Act, 2000", "66C", "Punishment for identity theft", 0.68),
        chunk("cyber4", "cyber", "Cyber Manual", "", "Portal steps", 0.67),
    ]
    consumer = chunk("consumer1", "consumer", "The Consumer Protection Act, 2019", "39", "Findings of District Commission", 0.66)
    ranked = selected + [consumer]
    for item in ranked:
        item.rerank_score = rag.final_rerank_score(query, item)

    balanced = rag.ensure_multi_domain_selection(query, selected, ranked, threshold=0.2)

    assert any(item.domain == "consumer" for item in balanced)
    assert any(item.domain == "cyber" for item in balanced)


def test_rti_no_response_prioritizes_section_19_over_complaint_and_penalty():
    query = "I filed an RTI application but did not receive any reply. What can I do next?"
    section_19 = chunk("rti19", "constitutional_public_authority", "The Right to Information Act, 2005", "19", "Appeal", 0.45)
    section_18 = chunk("rti18", "constitutional_public_authority", "The Right to Information Act, 2005", "18", "Powers and functions of Information Commissions", 0.45)
    section_20 = chunk("rti20", "constitutional_public_authority", "The Right to Information Act, 2005", "20", "Penalties", 0.45)

    assert rag.final_rerank_score(query, section_19) > rag.final_rerank_score(query, section_18)
    assert rag.final_rerank_score(query, section_19) > rag.final_rerank_score(query, section_20)
