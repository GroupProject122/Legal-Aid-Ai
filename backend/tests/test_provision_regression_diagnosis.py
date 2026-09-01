from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import diagnose_provision_regression as diagnosis


def test_first_matching_rank_finds_expected_provision():
    results = [
        {"rank": 1, "provision_number": "13"},
        {"rank": 2, "provision_number": "14"},
    ]

    assert diagnosis.first_matching_rank(results, {"14"}) == 2


def test_hit_at_5_only_counts_first_five():
    results = [{"rank": rank, "provision_number": str(rank)} for rank in range(1, 8)]

    assert diagnosis.hit_at_5(results, {"5"}) is True
    assert diagnosis.hit_at_5(results, {"6"}) is False


def test_candidate_presence_reports_raw_rank():
    result_group = {
        "raw_candidates_top10": [
            {"rank": 1, "provision_number": "18"},
            {"rank": 2, "provision_number": "19"},
        ]
    }

    assert diagnosis.candidate_presence(result_group, {"19"}) == {
        "present_in_raw_top10": True,
        "raw_rank": 2,
    }


def test_candidate_generation_issue_classification():
    query_case = {
        "expected_primary_documents": ["The Constitution of India"],
        "expected_primary_sources": ["constitutional_public_authority/constitution_of_india.pdf"],
    }
    before = {"results": {"reranked_top10": [{"rank": 1, "provision_number": "14"}]}}
    after = {
        "results": {
            "raw_candidates_top10": [{"rank": 1, "provision_number": "21"}],
            "reranked_top10": [{"rank": 1, "provision_number": "21"}],
        }
    }

    root = diagnosis.classify_regression(query_case, before, after, {"14"})

    assert root["category"] == "D. Candidate-generation issue"


def test_compact_result_includes_score_breakdown():
    result = {
        "rank": 1,
        "document_title": "The Constitution of India",
        "domain": "constitutional_public_authority",
        "structure_type": "article",
        "provision_number": "14",
        "provision_title": "Equality before law",
        "similarity_score": 0.5,
        "rerank_score": 0.8,
        "source_file": "constitutional_public_authority/constitution_of_india.pdf",
        "domain_debug": {
            "domain_boost": 0.08,
            "priority_boost": 0.045,
            "authority_boost": 0.035,
            "supporting_status_boost": 0.0,
            "source_role_boost": 0.08,
            "public_authority_chunk_intent": "fundamental_rights",
            "public_authority_intent_boost": 0.06,
        },
    }

    compact = diagnosis.compact_result(result)

    assert compact["domain_adjustment"] == 0.08
    assert compact["source_role_adjustment"] == 0.08
    assert compact["public_authority_intent"] == "fundamental_rights"
    assert compact["public_authority_intent_adjustment"] == 0.06
