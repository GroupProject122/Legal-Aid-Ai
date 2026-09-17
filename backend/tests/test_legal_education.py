from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import legal_education
import main


client = TestClient(main.app)


def test_categories_endpoint_works():
    response = client.get("/api/legal-awareness/categories")

    assert response.status_code == 200
    categories = response.json()
    assert {category["id"] for category in categories} == {
        "consumer",
        "cyber",
        "tenancy",
        "fundamental_rights",
        "public_services",
    }


def test_only_supported_categories_are_shown():
    categories = client.get("/api/legal-awareness/categories").json()

    assert "employment" not in {category["id"] for category in categories}
    assert all(category["title"] != "Employment Rights" for category in categories)


def test_category_returns_configured_sources_from_manifest():
    response = client.get("/api/legal-awareness/categories/consumer")

    assert response.status_code == 200
    data = response.json()
    titles = [source["short_title"] for source in data["sources"]]
    assert "Consumer Protection Act, 2019" in titles
    assert "E-Commerce Rules, 2020" in titles
    assert data["sources"][0]["source_file"] == "consumer/consumer_protection_act_2019.pdf"


def test_source_metadata_comes_from_manifest():
    response = client.get("/api/legal-awareness/sources/consumer__consumer_protection_act_2019")

    assert response.status_code == 200
    data = response.json()
    assert data["document_title"] == "The Consumer Protection Act, 2019"
    assert data["jurisdiction"] == "India"
    assert data["year"] == 2019
    assert data["document_type"] == "statute"


def test_important_provisions_exist_in_parsed_chunks():
    response = client.get("/api/legal-awareness/sources/consumer__consumer_protection_act_2019")

    assert response.status_code == 200
    provisions = response.json()["important_provisions"]
    labels = {provision["label"] for provision in provisions}
    assert {"Section 2", "Section 35", "Section 39", "Section 69"}.issubset(labels)
    assert all(provision["chunk_id"] for provision in provisions)


def test_provision_detail_returns_heading_and_page():
    response = client.get("/api/legal-awareness/sources/consumer__consumer_protection_act_2019/provisions/section-39")

    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "Section 39"
    assert data["title"]
    assert data["page"]
    assert data["official_excerpt"]
    assert data["source"]["short_title"] == "Consumer Protection Act, 2019"


def test_unknown_category_returns_404():
    response = client.get("/api/legal-awareness/categories/employment")

    assert response.status_code == 404


def test_unknown_source_returns_404():
    response = client.get("/api/legal-awareness/sources/not-a-source")

    assert response.status_code == 404


def test_path_traversal_impossible():
    response = client.get("/api/legal-awareness/sources/..%2F..%2Fsecret")

    assert response.status_code == 404


def test_source_pdf_endpoint_serves_only_known_corpus_file():
    response = client.get("/api/legal-awareness/sources/consumer__consumer_protection_act_2019/file")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_no_gemini_or_faiss_called(monkeypatch):
    monkeypatch.setattr(main.domain_router, "route_issue", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("router called")))
    monkeypatch.setattr(main.rag, "retrieve", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("faiss called")))

    assert client.get("/api/legal-awareness/categories").status_code == 200
    assert client.get("/api/legal-awareness/categories/tenancy").status_code == 200
    assert client.get("/api/legal-awareness/sources/tenancy__delhi_rent_control_act_1958").status_code == 200


def test_index_can_be_reset_and_rebuilt():
    legal_education.reset_index_cache()

    categories = legal_education.list_categories()

    assert categories


# --- Corpus-staleness fix (2026-09-16): get_index() auto-rebuilds when its source files change,
# via an mtime comparison -- not just when something remembers to call reset_index_cache().
# reset_index_cache() alone can't fix this in production: ingest.py (how a corpus change
# actually happens) runs as a separate OS process from the live `uvicorn main:app` server, so a
# call to it from ingest.py's process cannot reach the server process's _INDEX global. This test
# deliberately does NOT call reset_index_cache() between the two reads, to prove the automatic
# mtime check -- not an explicit reset -- is what picks up the change.


def test_index_auto_rebuilds_when_source_files_change_without_manual_reset(tmp_path, monkeypatch):
    manifest_path = tmp_path / "corpus_manifest.json"
    chunks_path = tmp_path / "legal_chunks.jsonl"
    source_file = "testdomain/test_act.pdf"

    def write_manifest():
        manifest_path.write_text(
            json.dumps(
                {
                    "documents": [
                        {
                            "source_file": source_file,
                            "domain": "consumer",
                            "document_title": "The Test Act, 2026",
                            "document_type": "statute",
                            "jurisdiction": "India",
                            "year": 2026,
                            "authority_level": "primary",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def write_chunks(section_title: str, text: str):
        chunks_path.write_text(
            json.dumps(
                {
                    "source_file": source_file,
                    "section_number": "5",
                    "section_title": section_title,
                    "text": text,
                    "page": 1,
                    "chunk_id": "c1",
                }
            )
            + "\n",
            encoding="utf-8",
        )

    write_manifest()
    write_chunks("Original Title", "Original provision text.")
    monkeypatch.setattr(legal_education, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(legal_education, "CHUNKS_PATH", chunks_path)
    legal_education.reset_index_cache()

    source_id_value = legal_education.source_id(source_file)
    try:
        first = legal_education.get_provision(source_id_value, "section-5")
        assert first["title"] == "Original Title"
        assert first["official_excerpt"].startswith("Original provision text.")

        time.sleep(0.01)  # ensure a distinct mtime on filesystems with coarse mtime resolution
        write_chunks("Updated Title", "Updated provision text after a corpus change.")

        # No reset_index_cache() call here -- the mtime check inside get_index() must catch this
        # on its own, the same way it would for a real ingest.py run against the live server.
        second = legal_education.get_provision(source_id_value, "section-5")

        assert second["title"] == "Updated Title"
        assert second["official_excerpt"].startswith("Updated provision text after a corpus change.")
    finally:
        legal_education.reset_index_cache()


# --- Search across provisions ---


def test_search_endpoint_finds_matching_provisions():
    response = client.get("/api/legal-awareness/search", params={"q": "refund"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "refund"
    assert len(body["results"]) > 0
    first = body["results"][0]
    assert {"category_id", "category_title", "source_id", "source_short_title", "provision_id", "provision_label", "excerpt"}.issubset(first)


def test_search_is_case_insensitive():
    lower = legal_education.search_provisions("essential supply")
    upper = legal_education.search_provisions("ESSENTIAL SUPPLY")

    assert len(lower) > 0
    assert {r["provision_id"] for r in lower} == {r["provision_id"] for r in upper}


def test_search_matches_provision_text_not_just_title(monkeypatch, tmp_path):
    # Deliberately constructed so the search term appears only in the provision body, never in
    # its title/label -- proves the text field is actually searched, not just the title.
    manifest_path = tmp_path / "corpus_manifest.json"
    chunks_path = tmp_path / "legal_chunks.jsonl"
    source_file = "testdomain/test_act.pdf"
    manifest_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "source_file": source_file,
                        "domain": "consumer",
                        "document_title": "The Test Act, 2026",
                        "document_type": "statute",
                        "jurisdiction": "India",
                        "year": 2026,
                        "authority_level": "primary",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    chunks_path.write_text(
        json.dumps(
            {
                "source_file": source_file,
                "section_number": "9",
                "section_title": "Miscellaneous Provisions",
                "text": "This section mentions a xyzzyplatypus somewhere in the body text only.",
                "page": 1,
                "chunk_id": "c1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(legal_education, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(legal_education, "CHUNKS_PATH", chunks_path)
    monkeypatch.setattr(
        legal_education.config,
        "CATEGORIES",
        {
            **legal_education.config.CATEGORIES,
            "test_category": {"title": "Test Category", "description": "Test.", "source_files": [source_file]},
        },
    )
    legal_education.reset_index_cache()
    try:
        results = legal_education.search_provisions("xyzzyplatypus")
        assert len(results) == 1
        assert "xyzzyplatypus" not in results[0]["provision_title"].lower()
        assert results[0]["provision_label"] == "Section 9"
    finally:
        legal_education.reset_index_cache()


def test_search_empty_query_returns_no_results():
    assert legal_education.search_provisions("") == []
    assert legal_education.search_provisions("   ") == []

    response = client.get("/api/legal-awareness/search", params={"q": ""})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_result_deep_links_to_a_real_provision():
    results = legal_education.search_provisions("refund")
    assert results

    for result in results[:3]:
        provision = legal_education.get_provision(result["source_id"], result["provision_id"])
        assert provision["label"] == result["provision_label"]


def test_search_only_returns_provisions_from_displayed_categories():
    # Every result's category_id must be one of the categories actually shown on the landing
    # page (list_categories()) -- search is a shortcut into the existing browse hierarchy, not a
    # door to content that isn't otherwise browsable.
    displayed_category_ids = {category["id"] for category in legal_education.list_categories()}
    results = legal_education.search_provisions("the")  # a broad, high-hit-count term

    assert results
    assert all(result["category_id"] in displayed_category_ids for result in results)


def test_search_respects_limit():
    results = legal_education.search_provisions("the", limit=3)
    assert len(results) <= 3
