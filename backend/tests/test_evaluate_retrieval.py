from __future__ import annotations

from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import evaluate_retrieval


class FakeRetrieved:
    def __init__(self):
        self.text = "Section 45 text about essential supply."
        self.source = "tenancy/delhi_rent_control_act_1958.pdf"
        self.document_title = "The Delhi Rent Control Act, 1958"
        self.page = 24
        self.score = 0.5
        self.rerank_score = 0.6
        self.section_number = "45"
        self.section_title = "Cutting off or withholding essential supply or service"
        self.rule_number = None
        self.rule_title = None


def result(**overrides):
    item = {
        "rank": 1,
        "domain": "tenancy",
        "document_title": "The Delhi Rent Control Act, 1958",
        "source_file": "tenancy/delhi_rent_control_act_1958.pdf",
        "provision_number": "45",
        "document_type": "statute",
    }
    item.update(overrides)
    return item


def query_case(**overrides):
    item = {
        "id": "tenancy_01",
        "query": "landlord cut electricity",
        "expected_domain": ["tenancy"],
        "expected_primary_documents": ["The Delhi Rent Control Act, 1958"],
        "expected_primary_sources": ["tenancy/delhi_rent_control_act_1958.pdf"],
        "expected_provision_numbers": ["45"],
    }
    item.update(overrides)
    return item


def test_expected_domain_hit_metric():
    case = query_case()
    evaluation = evaluate_retrieval.evaluate_single_domain(case, [result()])

    assert evaluation["metrics"]["domain_hit_at_1"] is True
    assert evaluation["metrics"]["domain_hit_at_3"] is True


def test_expected_document_hit_metric():
    case = query_case()
    evaluation = evaluate_retrieval.evaluate_single_domain(
        case,
        [
            result(domain="consumer", source_file="consumer/other.pdf", document_title="Other Document"),
            result(rank=2),
        ],
    )

    assert evaluation["metrics"]["document_hit_at_1"] is False
    assert evaluation["metrics"]["document_hit_at_3"] is True
    assert evaluation["metrics"]["document_hit_at_5"] is True


def test_provision_hit_metric():
    case = query_case()
    evaluation = evaluate_retrieval.evaluate_single_domain(
        case,
        [result(provision_number="7"), result(rank=2, provision_number="45")],
    )

    assert evaluation["metrics"]["provision_hit_at_5"] is True


def test_mrr_calculation():
    case = query_case()
    cases = [
        {
            **case,
            "evaluation": evaluate_retrieval.evaluate_single_domain(
                case,
                [result(source_file="wrong.pdf", document_title="Wrong Document"), result(rank=2)],
            ),
        }
    ]

    metrics = evaluate_retrieval.aggregate_metrics(cases)

    assert metrics["mrr"] == 0.5


def test_query_result_serialization():
    retrieved = FakeRetrieved()
    metadata = {
        "chunk_id": "tenancy_delhi_rent_control_act_1958__chunk_0045",
        "domain": "tenancy",
        "document_title": "The Delhi Rent Control Act, 1958",
        "structure_type": "section",
        "section_number": "45",
        "section_title": "Cutting off or withholding essential supply or service",
        "source_file": "tenancy/delhi_rent_control_act_1958.pdf",
        "retrieval_priority": "high",
        "authority_level": "primary",
        "document_type": "statute",
        "page": 24,
    }

    serialized = evaluate_retrieval.serialize_result(1, retrieved, metadata)

    assert serialized["chunk_id"] == "tenancy_delhi_rent_control_act_1958__chunk_0045"
    assert serialized["domain"] == "tenancy"
    assert serialized["provision_number"] == "45"
    assert serialized["snippet"].startswith("Section 45")
