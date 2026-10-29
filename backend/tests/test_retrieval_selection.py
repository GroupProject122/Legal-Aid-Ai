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


# LegalRAG.production_candidates() (2026-10-29, e2e cyber_001/cyber_010): manuals that match the
# phrasing closely filled the whole raw-similarity pool (12 of 12, 35 of 40), so the statute was
# never fetched. Down-weighted manuals must not count towards candidate_k.
def stub_engine(ranked: list[RetrievedChunk]):
    import rag

    engine = rag.LegalRAG.__new__(rag.LegalRAG)
    engine.chunks = [None] * 1000
    engine.retrieve_candidates = lambda question, candidate_k=None: [c for c in ranked][:candidate_k]
    return engine


def manuals_then_statute() -> list[RetrievedChunk]:
    manuals = [chunk(MANUAL, 0.70 - i * 0.01, f"Portal step {i}: report fraud online.", chunk_id=f"m{i}") for i in range(12)]
    statute = chunk(IT_ACT, 0.51, "66D. Punishment for cheating by personation by using computer resource.", section_number="66D", chunk_id="i66d")
    return [*manuals, statute]


def test_down_weighted_manuals_do_not_take_candidate_pool_slots(monkeypatch):
    import rag

    monkeypatch.setattr(rag, "production_candidate_k", lambda question, top_k=rag.TOP_K: 12)
    question = "General inquiry regarding online payment fraud through cyber means."
    engine = stub_engine(manuals_then_statute())

    pool = engine.production_candidates(question)
    assert "i66d" in [c.chunk_id for c in pool]
    assert sum(1 for c in pool if c.source.endswith("manual_latest.pdf")) == 12  # kept, not dropped

    selected = select_relevant_chunks(pool, question)
    assert selected[0].source == "cyber/information_technology_act_2000.pdf"


def test_pool_is_unchanged_for_procedural_questions(monkeypatch):
    import rag

    monkeypatch.setattr(rag, "production_candidate_k", lambda question, top_k=rag.TOP_K: 12)
    question = "how do I report payment fraud on the cybercrime portal"
    pool = stub_engine(manuals_then_statute()).production_candidates(question)
    assert [c.chunk_id for c in pool] == [f"m{i}" for i in range(12)]  # manuals count normally here


# is_procedural_query() (2026-10-29, e2e multi_003): substring matching made "User reports that
# their account was hacked" (the rewritten summary narrating the user) and "profile" look like
# "how do I report / file" questions, so the manuals were not down-weighted.
import pytest

from rag import is_procedural_query


@pytest.mark.parametrize(
    "question",
    [
        "how do I report a hacked account",
        "online cybercrime kaise report karu",
        "where can I file a consumer complaint",
        "consumer complaint kahan file karu",
        "Inquiry regarding the limitation period for filing a consumer complaint.",
        "I want to register a complaint on the portal",
    ],
)
def test_real_procedural_questions_are_procedural(question):
    assert is_procedural_query(question) is True


@pytest.mark.parametrize(
    "question",
    [
        "User reports that their online marketplace account was hacked resulting in loss of money.",
        "The tenant is reporting an issue where the landlord is disconnecting the electricity supply.",
        "my instagram profile was hacked",
    ],
)
def test_narration_and_partial_words_are_not_procedural(question):
    assert is_procedural_query(question) is False


def test_manual_is_down_weighted_for_a_narrated_substantive_summary():
    question = "User reports that their online marketplace account was hacked resulting in loss of money."
    assert is_down_weighted_manual(question, candidates()[0]) is True


# Set 1 rti_02 (2026-10-29): "What is the Time Period for Supply of Information?" had no domain
# keyword, so retrieval used a 12-candidate pool and missed RTI s.7 although the router had
# classified the question; and for "How long does the public authority have to supply
# information?" s.7 ranked below ss.25 and 4. Two general fixes below.
import rag  # noqa: E402

RTI = dict(source="constitutional_public_authority/right_to_information_act_2005.pdf", document_title="The Right to Information Act, 2005",
           authority_level="primary", document_type="statute", retrieval_priority="high", status="active")


def rti_chunk(section, score, text):
    return RetrievedChunk(text=text, page=1, score=score, domain="constitutional_public_authority", section_number=section,
                          chunk_id=f"rti{section}", **RTI)


def test_router_domains_are_used_only_inside_retrieve_and_only_without_keyword_signals():
    question = "What is the Time Period for Supply of Information?"
    assert rag.detect_domain_signals(question)["primary_domains"] == []
    token = rag._ROUTED_DOMAINS.set(("constitutional_public_authority",))
    try:
        assert rag.detect_domain_signals(question)["primary_domains"] == ["constitutional_public_authority"]
        assert rag.production_candidate_k(question) == 40  # was the 12-candidate fallback
        # keyword signals still win when the question has any
        assert rag.detect_domain_signals("my instagram account was hacked")["primary_domains"] == ["cyber"]
    finally:
        rag._ROUTED_DOMAINS.reset(token)
    assert rag.production_candidate_k(question) == 12


def test_retrieve_sets_and_clears_the_router_domains(monkeypatch):
    seen = []
    engine = rag.LegalRAG.__new__(rag.LegalRAG)
    engine.chunks = [None] * 100

    def candidates(question, top_k=rag.TOP_K):
        seen.append(rag._ROUTED_DOMAINS.get())
        return []

    engine.production_candidates = candidates
    engine.retrieve("What is the Time Period for Supply of Information?", domains=["constitutional_public_authority"])
    assert seen == [("constitutional_public_authority",)]
    assert rag._ROUTED_DOMAINS.get() == ()


def test_time_limit_questions_favour_provisions_that_state_a_period():
    with_period = rti_chunk("7", 0.60, "7. Disposal of request.--(1) ... as expeditiously as possible, and in any case within thirty days of the receipt of the request ... within forty-eight hours")
    without = rti_chunk("25", 0.65, "25. Monitoring and reporting.--(1) The Central Information Commission shall, as soon as practicable after the end of each year, prepare a report")
    for question in ("How long does the public authority have to supply information?", "What is the time limit for filing the complaint?",
                     "within how many days must they reply"):
        assert rag.query_intent_boost(question, with_period) == rag.TIME_LIMIT_BOOST
        assert rag.query_intent_boost(question, without) == 0.0
    assert rag.query_intent_boost("Who is a public information officer?", with_period) == 0.0


def test_section_7_is_selected_for_the_time_limit_question():
    question = "How long does the public authority have to supply information?"
    pool = [
        rti_chunk("25", 0.651, "25. Monitoring and reporting. The Commission shall prepare a report on the implementation of the provisions of this Act."),
        rti_chunk("4", 0.595, "4. Obligations of public authorities. Every public authority shall maintain all its records duly catalogued and indexed."),
        rti_chunk("7", 0.601, "7. Disposal of request. Within thirty days of the receipt of the request, provide the information; where it concerns life or liberty, within forty-eight hours."),
    ]
    # Before the fix s.7 reranked below s.4 (and s.25), so the two-per-document cap left it out.
    s25, s4, s7 = pool
    assert rag.final_rerank_score(question, s7) > rag.final_rerank_score(question, s4)
    assert "7" in [c.section_number for c in select_relevant_chunks(pool, question)]


def test_main_passes_the_router_domains_to_retrieval(monkeypatch):
    import fact_sufficiency
    import main

    calls = []
    monkeypatch.setattr(main.rag, "retrieve", lambda query, domains=None: calls.append(domains) or [])
    context = fact_sufficiency.CaseContext(state_id="x", original_message="What is the Time Period for Supply of Information?",
                                           domains=["constitutional_public_authority"], issue_summary=None)
    result = fact_sufficiency.FactSufficiencyResult("sufficient", [], False, None, None, "What is the Time Period for Supply of Information?")
    main.answer_grounded_from_context(original_message=context.original_message, context=context, fact_result=result)
    assert calls == [["constitutional_public_authority"]]
