from __future__ import annotations

import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import audit_ingestion


def chunk_record(**overrides):
    record = {
        "chunk_id": "consumer_test__chunk_0001",
        "text": "Section 1\n1. Short title.— This Act may be called the Test Act.",
        "source_file": "consumer/test.pdf",
        "document_title": "The Test Act, 2026",
        "short_title": "Test Act",
        "domain": "consumer",
        "jurisdiction": "India",
        "document_type": "statute",
        "status": "active",
        "authority_level": "primary",
        "year": 2026,
        "retrieval_priority": "high",
        "cross_domain_relevance": [],
        "structure_type": "section",
        "section_number": "1",
        "section_title": "Short title",
        "article_number": None,
        "article_title": None,
        "rule_number": None,
        "rule_title": None,
        "regulation_number": None,
        "regulation_title": None,
        "guideline_number": None,
        "guideline_title": None,
        "provision_number": "1",
        "provision_title": "Short title",
        "chapter": None,
        "part": None,
        "page": 1,
        "page_start": 1,
        "page_end": 1,
        "provision_chunk_index": 1,
        "provision_chunk_count": 1,
    }
    record.update(overrides)
    return record


def manifest():
    return {
        "consumer/test.pdf": {
            "source_file": "consumer/test.pdf",
            "domain": "consumer",
            "jurisdiction": "India",
            "document_title": "The Test Act, 2026",
            "document_type": "statute",
            "status": "active",
            "authority_level": "primary",
            "year": 2026,
            "retrieval_priority": "high",
        }
    }


def test_empty_chunk_detection():
    records = [chunk_record(text="")]

    issues = audit_ingestion.validate_basic_records(records)

    assert any(issue["type"] == "missing_text" for issue in issues)


def test_duplicate_chunk_id_detection():
    records = [chunk_record(), chunk_record(text="different text")]

    issues = audit_ingestion.validate_basic_records(records)

    assert any(issue["type"] == "duplicate_chunk_id" for issue in issues)


def test_invalid_page_range_detection():
    records = [chunk_record(page_start=3, page_end=2)]

    issues = audit_ingestion.validate_basic_records(records)

    assert any(issue["type"] == "invalid_page_range" for issue in issues)


def test_missing_provision_number_for_section():
    records = [chunk_record(section_number=None, provision_number=None)]

    issues = audit_ingestion.validate_provision_metadata(records)

    assert any(issue["type"] == "missing_provision_number" for issue in issues)


def test_child_chunk_sequence_validation():
    records = [
        chunk_record(chunk_id="consumer_test__chunk_0001", provision_chunk_index=1, provision_chunk_count=3),
        chunk_record(chunk_id="consumer_test__chunk_0002", provision_chunk_index=3, provision_chunk_count=3),
    ]

    issues = audit_ingestion.child_chunk_issues(records)

    assert any(issue["type"] == "invalid_child_chunk_sequence" for issue in issues)


def test_fallback_percentage_calculation():
    records = [
        chunk_record(chunk_id="consumer_test__chunk_0001", structure_type="section"),
        chunk_record(chunk_id="consumer_test__chunk_0002", structure_type="fallback"),
    ]

    stats = audit_ingestion.fallback_statistics(records)

    assert stats["total_fallback_chunks"] == 1
    assert stats["by_document_ranked"][0]["fallback_percentage"] == 50.0


def test_manifest_mismatch_detection():
    records = [chunk_record(domain="cyber")]

    issues = audit_ingestion.manifest_consistency(records, manifest())

    assert any(issue["type"] == "manifest_metadata_mismatch" and issue["field"] == "domain" for issue in issues)


def test_run_audit_writes_reports(tmp_path):
    chunks_path = tmp_path / "legal_chunks.jsonl"
    manifest_path = tmp_path / "corpus_manifest.json"
    json_path = tmp_path / "ingestion_audit.json"
    md_path = tmp_path / "ingestion_audit.md"
    chunks_path.write_text(json.dumps(chunk_record()) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps({"documents": list(manifest().values())}), encoding="utf-8")

    audit = audit_ingestion.run_audit(chunks_path, manifest_path, json_path, md_path)

    assert audit["audit_summary"]["total_chunks_checked"] == 1
    assert json_path.exists()
    assert md_path.exists()
