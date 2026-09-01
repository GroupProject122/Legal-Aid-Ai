from __future__ import annotations

import sys
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
