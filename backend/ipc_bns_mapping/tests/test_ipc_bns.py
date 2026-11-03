from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ipc_bns_mapping import ipc_bns


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("My FIR is under section 420 IPC", ["420"]),
        ("case registered u/s 354D/506/509 IPC", ["354D", "506", "509"]),
        ("charged under IPC 420 and 406", ["420", "406"]),
        ("Sections 499 and 500 of the Indian Penal Code", ["499", "500"]),
        ("offence under Section 420 r/w 34 I.P.C.", ["420", "34"]),
        ("what does ipc 354-d say", ["354D"]),
        ("punishable under Sections 376, 292, 465, 469, 509 of IPC", ["376", "292", "465", "469", "509"]),
        ("rape under 376(2) IPC", ["376"]),
    ],
)
def test_finds_ipc_sections(text, expected):
    assert ipc_bns.find_ipc_sections(text) == expected


def test_it_act_section_next_to_ipc_sections_is_not_mistaken_for_ipc():
    # Wording from the Mrs X judgment: 66A belongs to the IT Act, not the IPC.
    text = "FIR No. 448/2016, U/s 66 A, 354D/506/509 IPC, PS Mukherjee Nagar"
    assert ipc_bns.find_ipc_sections(text) == ["354D", "506", "509"]


@pytest.mark.parametrize(
    "text",
    [
        "section 420 of the Consumer Protection Act",
        "my landlord is harassing me",
        "Indian Penal Code, 1860 was replaced",
    ],
)
def test_ignores_text_without_ipc_section_citations(text):
    assert ipc_bns.find_ipc_sections(text) == []


@pytest.mark.parametrize(
    ("ipc_section", "bns_sections"),
    [
        ("420", ["318(4)"]),
        ("415", ["318(1)"]),
        ("354D", ["78"]),
        ("354C", ["77"]),
        ("509", ["79"]),
        ("506", ["351(2)/(3)"]),
        ("503", ["351(1)"]),
        ("499", ["356(1)"]),
        ("120B", ["61(2)"]),
        ("302", ["103(1)"]),
        ("292", ["294"]),
        ("498A", ["85", "86"]),
        ("228A", ["72", "73"]),
        ("143", ["189(2)"]),
        ("376DA", ["70(2)"]),
    ],
)
def test_maps_ipc_to_bns(ipc_section, bns_sections):
    mapping = ipc_bns.lookup(ipc_section)
    assert mapping.status == "mapped"
    assert mapping.bns_sections == bns_sections


@pytest.mark.parametrize("ipc_section", ["124A", "309", "377", "497", "236"])
def test_dropped_sections_say_they_are_not_in_the_government_table(ipc_section):
    mapping = ipc_bns.lookup(ipc_section)
    assert mapping.status == "no_bns_equivalent"
    assert mapping.bns_sections == []
    note = ipc_bns.mapping_note(mapping)
    assert "has no equivalent in the BNS" in note
    assert "Not listed in the government (BPR&D) correspondence table" in note


def test_every_note_carries_a_known_source():
    data = ipc_bns.load_map()
    tags = set(data["source_tags"])
    for entry in data["ipc_to_bns"].values():
        for item in [*entry["bns"], *entry.get("notes", [])]:
            assert item["source"] in tags


@pytest.mark.parametrize("ipc_section", ["143", "376DA", "444", "446"])
def test_hand_added_mappings_are_labelled_as_our_reading_not_the_table(ipc_section):
    mapping = ipc_bns.lookup(ipc_section)
    assert [entry["source"] for entry in mapping.bns] == ["bns_text"]
    note = ipc_bns.mapping_note(mapping)
    assert "Not listed in the government (BPR&D) correspondence table" in note
    assert "Our reading of the BNS text" in note
    assert "Source: BPR&D" not in note


def test_knowledge_from_outside_the_dataset_says_so():
    note = ipc_bns.mapping_note(ipc_bns.lookup("497"))
    assert "Not from the government data or any document in this dataset" in note
    assert "not_in_dataset" in {note["source"] for note in ipc_bns.lookup("377").notes}


def test_table_mappings_cite_the_table():
    assert "Source: BPR&D correspondence table" in ipc_bns.mapping_note(ipc_bns.lookup("420"))


def test_sections_repealed_before_bns_are_reported_as_such():
    mapping = ipc_bns.lookup("165A")
    assert mapping.status == "repealed_before_bns"
    assert "already been repealed" in ipc_bns.mapping_note(mapping)


def test_every_real_ipc_section_resolves():
    known = ipc_bns.load_map()["ipc_to_bns"]
    assert len(known) > 550
    assert all(entry["status"] != "mapped" or entry["bns"] for entry in known.values())


def test_note_distinguishes_renumbering_from_substantive_change():
    assert "renumbered; the offence itself is unchanged" in ipc_bns.mapping_note(ipc_bns.lookup("420"))
    assert "changed:" in ipc_bns.mapping_note(ipc_bns.lookup("170"))


def test_retrieval_terms_name_the_bns_section():
    terms = ipc_bns.retrieval_terms(ipc_bns.mappings_for_text("FIR under 420 IPC"))
    assert "Bharatiya Nyaya Sanhita Section 318" in terms
    assert "Cheating" in terms


def test_lookup_accepts_loose_formatting():
    assert ipc_bns.lookup("354-d").ipc_section == "354D"
    assert ipc_bns.lookup("999") is None


def test_citations_dropped_by_a_summary_are_reattached_for_search():
    mappings = ipc_bns.mappings_for_text("FIR u/s 420/506 IPC")
    summary = "User was cheated in an online deal and threatened."
    assert ipc_bns.with_ipc_citations(summary, mappings) == f"{summary} (IPC 420, IPC 506)"
    assert ipc_bns.with_ipc_citations("case under 420 IPC", mappings[:1]) == "case under 420 IPC"


def test_mapped_bns_sections_are_base_section_numbers():
    assert ipc_bns.mapped_bns_sections("u/s 420/506 IPC") == frozenset({"318", "351"})
    assert ipc_bns.mapped_bns_sections("IPC 377") == frozenset()


def test_response_payload_carries_notes_sources_and_transition():
    payload = ipc_bns.response_payload(ipc_bns.mappings_for_text("charged under 420 and 143 IPC"))
    by_section = {item["ipc_section"]: item for item in payload["sections"]}
    assert by_section["420"]["bns_sections"] == ["318(4)"]
    assert by_section["420"]["sources"] == ["bprd_table"]
    assert by_section["143"]["sources"] == ["bns_text"]
    assert "BNS section 358" in payload["transition_note"]
    assert ipc_bns.response_payload([]) is None


def test_prompt_block_lists_each_mapping_and_the_transition():
    block = ipc_bns.prompt_block(ipc_bns.mappings_for_text("IPC 420"))
    assert block.startswith("- IPC 420")
    assert "1 July 2024" in block
    assert ipc_bns.prompt_block([]) == ""


@pytest.mark.parametrize(
    "text",
    [
        "what is IPC 302 now?",
        "IPC 420",
        "420 IPC in BNS",
        "is IPC 377 still a crime",
        "My FIR is under 420 IPC, what is it under BNS?",
        "which section replaced section 124A of the Indian Penal Code",
    ],
)
def test_section_lookups_are_recognised(text):
    assert ipc_bns.is_lookup_question(text)


@pytest.mark.parametrize(
    "text",
    [
        "I was booked u/s 354D/506/509 IPC for Instagram messages, what should I do?",
        "how can I get bail in a 420 IPC case where the seller cheated me online and blocked my number",
        "someone is threatening me online and I want to report it",
        "what is section 302 now?",
    ],
)
def test_case_questions_and_non_ipc_questions_are_not_lookups(text):
    assert not ipc_bns.is_lookup_question(text)


def test_reference_chunks_cover_every_bns_section():
    sections = {str(number) for number in range(1, 359)}
    found = {item["section_number"] for item in ipc_bns.bns_reference_chunks(sections)}
    assert found == sections


def test_reference_chunks_hold_the_section_text_not_a_contents_entry():
    murder = ipc_bns.bns_reference_chunks({"103"})
    assert "Whoever commits murder shall be punished with death" in murder[0]["text"]
    hurt = ipc_bns.bns_reference_chunks({"114"})
    assert "Whoever causes bodily pain, disease or infirmity" in hurt[0]["text"]


def test_reference_chunks_exclude_the_statement_of_objects_and_reasons():
    # Its numbered paragraphs ("6. The Notes on Clauses ...") were once parsed as BNS 6 and 7.
    fractions = ipc_bns.bns_reference_chunks({"6"})
    assert len(fractions) == 1 and "Fractions of terms of punishment" in fractions[0]["text"]
    assert "STATEMENT OF OBJECTS AND REASONS" not in ipc_bns.bns_reference_chunks({"358"})[-1]["text"]
