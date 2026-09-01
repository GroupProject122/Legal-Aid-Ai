from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ingest


class FakePage:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self) -> str:
        return self._text


class FakeReader:
    def __init__(self, _path: str):
        self.pages = [
            FakePage("1. Short title.— This test legal document applies to consumer issues.")
        ]


def manifest_entry(**overrides):
    entry = {
        "source_file": "consumer/test_document.pdf",
        "document_title": "The Test Legal Document, 2026",
        "short_title": "Test Legal Document",
        "domain": "consumer",
        "document_type": "statute",
        "jurisdiction": "India",
        "status": "active",
        "authority_level": "primary",
        "year": 2026,
        "cross_domain_relevance": ["cyber"],
        "retrieval_priority": "high",
    }
    entry.update(overrides)
    return entry


def write_manifest(tmp_path: Path, documents: list[dict]):
    manifest_path = tmp_path / "corpus_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "supported_domains": ["consumer", "cyber", "tenancy", "constitutional_public_authority"],
                "documents": documents,
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def patch_reader(monkeypatch, page_texts: list[str]):
    class CustomFakeReader:
        def __init__(self, _path: str):
            self.pages = [FakePage(text) for text in page_texts]

    monkeypatch.setattr(ingest, "PdfReader", CustomFakeReader)


def parsed_metadata_fixture() -> dict:
    chunk = {
        "chunk_id": "consumer_test_document__chunk_0001",
        "text": "Section 1\n1. Short title.— This test legal document applies to consumer issues.",
        "domain": "consumer",
        "jurisdiction": "India",
        "document_title": "The Test Legal Document, 2026",
        "short_title": "Test Legal Document",
        "document_type": "statute",
        "status": "active",
        "authority_level": "primary",
        "year": 2026,
        "source_file": "consumer/test_document.pdf",
        "retrieval_priority": "high",
        "cross_domain_relevance": ["cyber"],
        "structure_type": "section",
        "section_number": "1",
        "section_title": "Short title",
        "article_number": None,
        "article_title": None,
        "rule_number": None,
        "rule_title": None,
        "regulation_number": None,
        "regulation_title": None,
        "chapter": None,
        "part": None,
        "page": 1,
        "page_start": 1,
        "page_end": 1,
        "provision_chunk_index": 1,
        "provision_chunk_count": 1,
        "source": "consumer/test_document.pdf",
        "chunk": 1,
        "parser_family": "statute",
    }
    return {
        "chunking_strategy": "test",
        "chunk_size": 1000,
        "chunk_overlap": 160,
        "document_count": 1,
        "chunk_count": 1,
        "structure_aware_chunk_count": 1,
        "fallback_chunk_count": 0,
        "structure_aware_percentage": 100.0,
        "fallback_percentage": 0.0,
        "parsed_documents": [
            {
                "source_file": "consumer/test_document.pdf",
                "document_title": "The Test Legal Document, 2026",
                "document_type": "statute",
                "domain": "consumer",
                "status": "active",
                "parser_family": "statute",
                "chunk_count": 1,
                "structure_aware_chunk_count": 1,
                "fallback_chunk_count": 0,
                "chunks_by_structure_type": {"section": 1},
            }
        ],
        "skipped_documents": [
            {"source_file": "archive/old.pdf", "reason": "archived document"},
            {"source_file": "tenancy/delhi_rent_act_1995.pdf", "reason": "manual_verification_required"},
        ],
        "chunks_per_domain": {"consumer": 1},
        "chunks_per_document_type": {"statute": 1},
        "chunks_by_structure_type": {"section": 1},
        "chunks": [chunk],
    }


def test_section_detection(monkeypatch, tmp_path):
    pdf_path = tmp_path / "consumer" / "test_act.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    patch_reader(
        monkeypatch,
        ["14. Protection of consumer.— The consumer may file a complaint.\n15. Powers of authority.— The authority may inquire."],
    )
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)

    chunks = ingest.parse_statute_document(pdf_path, manifest_entry(source_file="consumer/test_act.pdf"))

    assert [chunk["section_number"] for chunk in chunks] == ["14", "15"]
    assert chunks[0]["structure_type"] == "section"
    assert chunks[0]["section_title"] == "Protection of consumer"


def test_article_detection(monkeypatch, tmp_path):
    pdf_path = tmp_path / "constitutional_public_authority" / "constitution.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    patch_reader(monkeypatch, ["PART III\n14. Equality before law.— The State shall not deny equality before the law."])
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)

    chunks = ingest.parse_constitution_document(
        pdf_path,
        manifest_entry(
            source_file="constitutional_public_authority/constitution.pdf",
            document_type="constitution",
            domain="constitutional_public_authority",
        ),
    )

    assert chunks[0]["structure_type"] == "article"
    assert chunks[0]["article_number"] == "14"
    assert chunks[0]["article_title"] == "Equality before law"
    assert chunks[0]["part"] == "PART III"


def test_rule_detection(monkeypatch, tmp_path):
    pdf_path = tmp_path / "consumer" / "test_rules.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    patch_reader(monkeypatch, ["3. Duties of seller.— A seller shall provide information."])
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)

    chunks = ingest.parse_rules_document(
        pdf_path,
        manifest_entry(source_file="consumer/test_rules.pdf", document_type="rules"),
    )

    assert chunks[0]["structure_type"] == "rule"
    assert chunks[0]["rule_number"] == "3"
    assert chunks[0]["rule_title"] == "Duties of seller"


def test_gazette_page_furniture_is_removed():
    text = "\n".join(
        [
            "2 THE GAZETTE OF INDIA : EXTRAORDINARY [PART II—SEC. 3(i)]",
            "EXTRAORDINARY",
            "PUBLISHED BY AUTHORITY",
            "MINISTRY OF CONSUMER AFFAIRS, FOOD AND PUBLIC DISTRIBUTION",
            "NOTIFICATION",
            "1. Short title and commencement. — These rules may be called the Test Rules.",
            "Uploaded by Dte. of Printing at Government of India Press",
        ]
    )

    cleaned = ingest.remove_gazette_page_furniture(text)

    assert "THE GAZETTE OF INDIA" not in cleaned
    assert "PUBLISHED BY AUTHORITY" not in cleaned
    assert "Uploaded by Dte." not in cleaned
    assert "MINISTRY OF CONSUMER AFFAIRS" in cleaned
    assert "1. Short title and commencement" in cleaned


def test_bilingual_gazette_front_matter_is_trimmed_but_english_notification_remains():
    pages = [
        (1, "असाधारण\nहिंदी सूचना पाठ\n"),
        (
            2,
            "हिंदी नियम पाठ\nMINISTRY OF CONSUMER AFFAIRS, FOOD AND PUBLIC DISTRIBUTION\n"
            "NOTIFICATION\nNew Delhi\n1. Short title and commencement. — These rules apply.",
        ),
    ]

    trimmed = ingest.trim_bilingual_gazette_front_matter(pages, "rules")

    assert trimmed[0][0] == 2
    assert trimmed[0][1].startswith("MINISTRY OF CONSUMER AFFAIRS")
    assert "हिंदी" not in trimmed[0][1]
    assert "1. Short title and commencement" in trimmed[0][1]


def test_bilingual_gazette_guideline_authority_marker_is_trimmed():
    pages = [
        (1, "असाधारण\nहिंदी दिशानिर्देश पाठ\n"),
        (
            2,
            "हिंदी पाठ\nCENTRAL CONSUMER PROTECTION AUTHORITY\n"
            "NOTIFICATION\n1. Short title and commencement. — These guidelines apply.",
        ),
    ]

    trimmed = ingest.trim_bilingual_gazette_front_matter(pages, "guidelines")

    assert trimmed[0][0] == 2
    assert trimmed[0][1].startswith("CENTRAL CONSUMER PROTECTION AUTHORITY")
    assert "हिंदी" not in trimmed[0][1]
    assert "1. Short title and commencement" in trimmed[0][1]


def test_non_gazette_parser_does_not_trim_bilingual_text():
    pages = [(1, "हिंदी पाठ\nMINISTRY OF TEST\nNOTIFICATION\n1. Short title.— Text.")]

    assert ingest.trim_bilingual_gazette_front_matter(pages, "statute") == pages


def test_regulation_detection(monkeypatch, tmp_path):
    pdf_path = tmp_path / "consumer" / "test_regulations.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    patch_reader(monkeypatch, ["4. Filing procedure.— The registry shall receive complaints."])
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)

    chunks = ingest.parse_regulations_document(
        pdf_path,
        manifest_entry(source_file="consumer/test_regulations.pdf", document_type="regulations"),
    )

    assert chunks[0]["structure_type"] == "regulation"
    assert chunks[0]["regulation_number"] == "4"
    assert chunks[0]["regulation_title"] == "Filing procedure"


def test_body_text_reference_does_not_create_false_section_boundary(monkeypatch, tmp_path):
    pdf_path = tmp_path / "consumer" / "test_act.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    patch_reader(
        monkeypatch,
        ["1. First provision.— A remedy under section 14 of the Act may be discussed here.\nThis body continues without a new provision."],
    )
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)

    chunks = ingest.parse_statute_document(pdf_path, manifest_entry(source_file="consumer/test_act.pdf"))

    assert len(chunks) == 1
    assert chunks[0]["section_number"] == "1"
    assert "section 14" in chunks[0]["text"]


def test_amendment_footnote_does_not_create_false_article_boundary(monkeypatch, tmp_path):
    pdf_path = tmp_path / "constitutional_public_authority" / "constitution.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    patch_reader(
        monkeypatch,
        [
            "PREAMBLE\nWE, THE PEOPLE OF INDIA.\n2. Subs. by the Constitution amendment for earlier words.",
            "17. Abolition of Untouchability.— Untouchability is abolished.",
        ],
    )
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)

    chunks = ingest.parse_constitution_document(
        pdf_path,
        manifest_entry(
            source_file="constitutional_public_authority/constitution.pdf",
            document_type="constitution",
            domain="constitutional_public_authority",
        ),
    )

    assert "2" not in {chunk.get("article_number") for chunk in chunks}
    assert any(chunk.get("structure_type") == "preamble" for chunk in chunks)
    assert any(chunk.get("article_number") == "17" for chunk in chunks)


def test_long_provision_child_chunks_retain_provision_metadata(monkeypatch, tmp_path):
    pdf_path = tmp_path / "consumer" / "test_act.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    long_text = "14. Long provision.— " + ("This provision has detailed text. " * 80)
    patch_reader(monkeypatch, [long_text])
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(ingest, "STRUCTURED_CHILD_CHUNK_SIZE", 260)
    monkeypatch.setattr(ingest, "STRUCTURED_CHILD_CHUNK_OVERLAP", 40)

    chunks = ingest.parse_statute_document(pdf_path, manifest_entry(source_file="consumer/test_act.pdf"))

    assert len(chunks) > 1
    assert {chunk["section_number"] for chunk in chunks} == {"14"}
    assert {chunk["section_title"] for chunk in chunks} == {"Long provision"}
    assert [chunk["provision_chunk_index"] for chunk in chunks] == list(range(1, len(chunks) + 1))
    assert {chunk["provision_chunk_count"] for chunk in chunks} == {len(chunks)}


def test_contents_page_does_not_create_fake_provisions(monkeypatch, tmp_path):
    pdf_path = tmp_path / "consumer" / "test_act.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    patch_reader(
        monkeypatch,
        [
            "THE TEST ACT\nARRANGEMENT OF SECTIONS\n14. Protection listed only.\n15. Another listed only.",
            "14. Protection of consumer.— This is the actual provision text.",
        ],
    )
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)

    chunks = ingest.parse_statute_document(pdf_path, manifest_entry(source_file="consumer/test_act.pdf"))

    assert len(chunks) == 1
    assert chunks[0]["section_number"] == "14"
    assert "listed only" not in chunks[0]["text"]


def test_fallback_still_works_when_structure_is_not_detected(monkeypatch, tmp_path):
    pdf_path = tmp_path / "cyber" / "manual.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    patch_reader(monkeypatch, ["This page explains how a user can report a cybercrime complaint online."])
    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)

    chunks = ingest.parse_manual_document(
        pdf_path,
        manifest_entry(source_file="cyber/manual.pdf", document_type="procedural_user_guide", domain="cyber"),
    )

    assert len(chunks) == 1
    assert chunks[0]["structure_type"] == "fallback"
    assert chunks[0]["domain"] == "cyber"


def test_manifest_metadata_is_attached_to_chunks(monkeypatch, tmp_path):
    pdf_path = tmp_path / "consumer" / "test_document.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")

    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(ingest, "PdfReader", FakeReader)

    chunks = ingest.parse_statute_document(pdf_path, manifest_entry())

    assert chunks[0]["chunk_id"] == "consumer_test_document__chunk_0001"
    assert chunks[0]["source"] == "consumer/test_document.pdf"
    assert chunks[0]["source_file"] == "consumer/test_document.pdf"
    assert chunks[0]["document_title"] == "The Test Legal Document, 2026"
    assert chunks[0]["short_title"] == "Test Legal Document"
    assert chunks[0]["domain"] == "consumer"
    assert chunks[0]["jurisdiction"] == "India"
    assert chunks[0]["document_type"] == "statute"
    assert chunks[0]["status"] == "active"
    assert chunks[0]["authority_level"] == "primary"
    assert chunks[0]["year"] == 2026
    assert chunks[0]["retrieval_priority"] == "high"
    assert chunks[0]["cross_domain_relevance"] == ["cyber"]


def test_archived_documents_are_not_parsed_from_manifest(monkeypatch, tmp_path):
    archived_pdf = tmp_path / "archive" / "archived.pdf"
    archived_pdf.parent.mkdir()
    archived_pdf.write_bytes(b"%PDF-test")
    manifest_path = write_manifest(
        tmp_path,
        [manifest_entry(source_file="archive/archived.pdf")],
    )

    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(ingest, "CORPUS_MANIFEST_PATH", manifest_path)

    documents, skipped = ingest.discover_document_entries()

    assert documents == []
    assert skipped == [{"source_file": "archive/archived.pdf", "reason": "archived document"}]


def test_manual_verification_documents_are_skipped_by_default(monkeypatch, tmp_path):
    pdf_path = tmp_path / "tenancy" / "delhi_rent_act_1995.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")
    manifest_path = write_manifest(
        tmp_path,
        [
            manifest_entry(
                source_file="tenancy/delhi_rent_act_1995.pdf",
                status="manual_verification_required",
                domain="tenancy",
            )
        ],
    )

    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(ingest, "CORPUS_MANIFEST_PATH", manifest_path)

    documents, skipped = ingest.discover_document_entries()

    assert documents == []
    assert skipped == [
        {"source_file": "tenancy/delhi_rent_act_1995.pdf", "reason": "manual_verification_required"}
    ]


def test_parser_dispatch_chooses_expected_parser_family():
    assert ingest.parser_for_document_type("statute") is ingest.parse_statute_document
    assert ingest.parser_for_document_type("supporting_criminal_law") is ingest.parse_statute_document
    assert ingest.parser_for_document_type("constitution") is ingest.parse_constitution_document
    assert ingest.parser_for_document_type("rules") is ingest.parse_rules_document
    assert ingest.parser_for_document_type("regulations") is ingest.parse_regulations_document
    assert ingest.parser_for_document_type("guidelines") is ingest.parse_guidelines_document
    assert ingest.parser_for_document_type("amendment_rules") is ingest.parse_amendment_rules_document
    assert ingest.parser_for_document_type("procedural_user_guide") is ingest.parse_manual_document


def test_chunk_ids_are_deterministic(monkeypatch, tmp_path):
    pdf_path = tmp_path / "consumer" / "test_document.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-test")

    monkeypatch.setattr(ingest, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(ingest, "PdfReader", FakeReader)

    first = ingest.parse_statute_document(pdf_path, manifest_entry())
    second = ingest.parse_statute_document(pdf_path, manifest_entry())

    assert [chunk["chunk_id"] for chunk in first] == [chunk["chunk_id"] for chunk in second]


def test_parse_only_writes_jsonl_and_summary(monkeypatch, tmp_path):
    parsed = parsed_metadata_fixture()
    output_dir = tmp_path / "parsed"
    chunks_path = output_dir / "legal_chunks.jsonl"
    summary_path = output_dir / "parse_summary.json"

    monkeypatch.setattr(ingest, "LEGAL_CHUNKS_PATH", chunks_path)
    monkeypatch.setattr(ingest, "PARSE_SUMMARY_PATH", summary_path)
    monkeypatch.setattr(ingest, "parse_documents", lambda: parsed)

    result = ingest.ingest(parse_only=True)

    assert chunks_path.exists()
    assert summary_path.exists()
    assert result["parse_outputs"]["validation"]["record_count"] == 1
    records = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == result["chunk_count"]

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total_chunks"] == result["chunk_count"]
    assert summary["documents"][0]["source_file"] == "consumer/test_document.pdf"


def test_jsonl_records_preserve_manifest_and_structure_metadata(tmp_path):
    parsed = parsed_metadata_fixture()
    chunks_path = tmp_path / "legal_chunks.jsonl"
    summary_path = tmp_path / "parse_summary.json"

    ingest.write_parse_outputs(parsed, chunks_path=chunks_path, summary_path=summary_path)

    record = json.loads(chunks_path.read_text(encoding="utf-8").splitlines()[0])
    assert record["document_title"] == "The Test Legal Document, 2026"
    assert record["short_title"] == "Test Legal Document"
    assert record["domain"] == "consumer"
    assert record["jurisdiction"] == "India"
    assert record["status"] == "active"
    assert record["retrieval_priority"] == "high"
    assert record["cross_domain_relevance"] == ["cyber"]
    assert record["structure_type"] == "section"
    assert record["section_number"] == "1"
    assert record["section_title"] == "Short title"
    assert record["page_start"] == 1
    assert record["page_end"] == 1


def test_parse_output_validation_rejects_duplicate_chunk_ids(tmp_path):
    parsed = parsed_metadata_fixture()
    duplicate = parsed["chunks"][0].copy()
    parsed["chunks"] = [parsed["chunks"][0], duplicate]
    parsed["chunk_count"] = 2
    chunks_path = tmp_path / "legal_chunks.jsonl"
    summary_path = tmp_path / "parse_summary.json"

    try:
        ingest.write_parse_outputs(parsed, chunks_path=chunks_path, summary_path=summary_path)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("Duplicate chunk IDs should fail parse output validation")


def test_parse_output_validation_rejects_archive_and_manual_documents(tmp_path):
    parsed = parsed_metadata_fixture()
    archived_chunk = parsed["chunks"][0].copy()
    archived_chunk["chunk_id"] = "archive_old__chunk_0001"
    archived_chunk["source_file"] = "archive/old.pdf"
    manual_chunk = parsed["chunks"][0].copy()
    manual_chunk["chunk_id"] = "manual_old__chunk_0001"
    manual_chunk["status"] = "manual_verification_required"

    for bad_chunk, expected in (
        (archived_chunk, "Archived document"),
        (manual_chunk, "Manual-verification document"),
    ):
        bad_parsed = {**parsed, "chunks": [bad_chunk], "chunk_count": 1}
        chunks_path = tmp_path / f"{bad_chunk['chunk_id']}.jsonl"
        summary_path = tmp_path / f"{bad_chunk['chunk_id']}.json"
        try:
            ingest.write_parse_outputs(bad_parsed, chunks_path=chunks_path, summary_path=summary_path)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"{expected} should fail parse output validation")


def test_parse_output_is_deterministic_for_same_input(tmp_path):
    parsed = parsed_metadata_fixture()
    first_chunks = tmp_path / "first.jsonl"
    first_summary = tmp_path / "first_summary.json"
    second_chunks = tmp_path / "second.jsonl"
    second_summary = tmp_path / "second_summary.json"

    ingest.write_parse_outputs(parsed, chunks_path=first_chunks, summary_path=first_summary)
    ingest.write_parse_outputs(parsed, chunks_path=second_chunks, summary_path=second_summary)

    assert first_chunks.read_text(encoding="utf-8") == second_chunks.read_text(encoding="utf-8")
    assert first_summary.read_text(encoding="utf-8") == second_summary.read_text(encoding="utf-8")


def test_parse_only_does_not_build_or_touch_vectorstore(monkeypatch, tmp_path):
    vectorstore_dir = tmp_path / "vectorstore"
    vectorstore_dir.mkdir()
    marker = vectorstore_dir / "index.faiss"
    marker.write_text("existing index", encoding="utf-8")
    before = marker.read_text(encoding="utf-8")
    parsed_dir = tmp_path / "parsed"

    monkeypatch.setattr(ingest, "VECTORSTORE_DIR", vectorstore_dir)
    monkeypatch.setattr(ingest, "INDEX_PATH", marker)
    monkeypatch.setattr(ingest, "METADATA_PATH", vectorstore_dir / "metadata.json")
    monkeypatch.setattr(ingest, "LEGAL_CHUNKS_PATH", parsed_dir / "legal_chunks.jsonl")
    monkeypatch.setattr(ingest, "PARSE_SUMMARY_PATH", parsed_dir / "parse_summary.json")
    monkeypatch.setattr(ingest, "parse_documents", parsed_metadata_fixture)

    def fail_build_vector_store(_parsed_metadata):
        raise AssertionError("parse-only mode must not build FAISS or generate embeddings")

    monkeypatch.setattr(ingest, "build_vector_store", fail_build_vector_store)

    result = ingest.main(["--parse-only"])

    assert result["chunk_count"] == 1
    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == before
    assert not (vectorstore_dir / "metadata.json").exists()


def write_chunks_jsonl(tmp_path: Path, chunks: list[dict]) -> Path:
    path = tmp_path / "legal_chunks.jsonl"
    path.write_text("".join(json.dumps(chunk) + "\n" for chunk in chunks), encoding="utf-8")
    return path


def test_load_legal_chunks_jsonl(tmp_path):
    chunk = parsed_metadata_fixture()["chunks"][0]
    path = write_chunks_jsonl(tmp_path, [chunk])

    chunks = ingest.load_legal_chunks_jsonl(path)

    assert chunks == [chunk]


def test_index_validation_rejects_invalid_or_empty_jsonl(tmp_path):
    empty_path = tmp_path / "empty.jsonl"
    empty_path.write_text("", encoding="utf-8")

    try:
        ingest.validate_chunks_for_indexing(ingest.load_legal_chunks_jsonl(empty_path))
    except ValueError as exc:
        assert "no records" in str(exc)
    else:
        raise AssertionError("Empty JSONL should be rejected")

    invalid_path = tmp_path / "invalid.jsonl"
    invalid_path.write_text("{not json}\n", encoding="utf-8")
    try:
        ingest.load_legal_chunks_jsonl(invalid_path)
    except ValueError as exc:
        assert "Invalid JSONL" in str(exc)
    else:
        raise AssertionError("Invalid JSONL should be rejected")


def test_index_validation_checks_unique_ids_and_required_text():
    chunk = parsed_metadata_fixture()["chunks"][0]
    duplicate = {**chunk, "text": "different"}

    try:
        ingest.validate_chunks_for_indexing([chunk, duplicate])
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("Duplicate chunk IDs should be rejected")

    try:
        ingest.validate_chunks_for_indexing([{**chunk, "chunk_id": "x", "text": ""}])
    except ValueError as exc:
        assert "empty text" in str(exc)
    else:
        raise AssertionError("Empty chunk text should be rejected")


def test_embedding_dimension_validation_requires_384():
    valid_vectors = np.ones((2, 384), dtype="float32")
    validation = ingest.validate_embeddings(valid_vectors)

    assert validation["embedding_dimension"] == 384

    try:
        ingest.validate_embeddings(np.ones((2, 383), dtype="float32"))
    except ValueError as exc:
        assert "Expected embedding dimension 384" in str(exc)
    else:
        raise AssertionError("Unexpected embedding dimension should be rejected")


def test_saved_faiss_index_loads_and_metadata_order_is_aligned(monkeypatch, tmp_path):
    vectorstore_dir = tmp_path / "vectorstore"
    index_path = vectorstore_dir / "index.faiss"
    metadata_path = vectorstore_dir / "metadata.json"
    monkeypatch.setattr(ingest, "VECTORSTORE_DIR", vectorstore_dir)
    monkeypatch.setattr(ingest, "INDEX_PATH", index_path)
    monkeypatch.setattr(ingest, "METADATA_PATH", metadata_path)

    chunk = parsed_metadata_fixture()["chunks"][0]
    chunks = [
        {**chunk, "chunk_id": "consumer_test__chunk_0001", "text": "alpha legal text"},
        {**chunk, "chunk_id": "consumer_test__chunk_0002", "text": "beta legal text"},
        {**chunk, "chunk_id": "consumer_test__chunk_0003", "text": "gamma legal text"},
    ]
    vectors = np.eye(3, 384, dtype="float32")
    index = ingest.faiss.IndexFlatIP(384)
    index.add(vectors)
    metadata = {
        "embedding_provider": "local",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "faiss_index_type": "IndexFlatIP",
        "chunks": chunks,
    }

    validation = ingest.write_vector_store_safely(index, metadata)

    assert index_path.exists()
    assert metadata_path.exists()
    assert validation["faiss_vector_count"] == 3
    assert validation["metadata_record_count"] == 3
    assert validation["alignment_sample_positions"][0]["chunk_id"] == "consumer_test__chunk_0001"
    assert validation["alignment_sample_positions"][-1]["chunk_id"] == "consumer_test__chunk_0003"


def test_build_vector_store_from_jsonl_uses_jsonl_without_parsing(monkeypatch, tmp_path):
    import rag

    chunk = parsed_metadata_fixture()["chunks"][0]
    chunks_path = write_chunks_jsonl(tmp_path, [chunk])
    vectorstore_dir = tmp_path / "vectorstore"
    monkeypatch.setattr(ingest, "VECTORSTORE_DIR", vectorstore_dir)
    monkeypatch.setattr(ingest, "INDEX_PATH", vectorstore_dir / "index.faiss")
    monkeypatch.setattr(ingest, "METADATA_PATH", vectorstore_dir / "metadata.json")

    def fail_parse_documents():
        raise AssertionError("Normal indexing must not parse PDFs")

    def fake_embed_texts(texts):
        assert texts == [chunk["text"]]
        return np.ones((1, 384), dtype="float32")

    monkeypatch.setattr(ingest, "parse_documents", fail_parse_documents)
    monkeypatch.setattr(rag, "embed_texts", fake_embed_texts)

    metadata = ingest.build_vector_store_from_jsonl(chunks_path)

    assert metadata["chunk_count"] == 1
    assert metadata["embedding_dimension"] == 384
    assert metadata["index_build"]["saved_validation"]["faiss_vector_count"] == 1


def test_normal_indexing_path_uses_frozen_jsonl_builder(monkeypatch):
    called = {}

    def fail_parse_documents():
        raise AssertionError("Normal indexing must not parse PDFs")

    def fake_build_vector_store_from_jsonl():
        called["used_jsonl_builder"] = True
        return {"built": True}

    monkeypatch.setattr(ingest, "parse_documents", fail_parse_documents)
    monkeypatch.setattr(ingest, "build_vector_store_from_jsonl", fake_build_vector_store_from_jsonl)

    result = ingest.ingest(parse_only=False)

    assert called["used_jsonl_builder"] is True
    assert result["built"] is True
