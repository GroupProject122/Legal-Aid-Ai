from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import conversation_state
import turn_memory


def state(domains=("tenancy",), summary="Delhi tenancy: lock-in clause and security deposit dispute."):
    return conversation_state.create_state(list(domains), domains[0], summary, ["Lease has a 6-month lock-in."])


def rules(message, domains=("tenancy",)):
    return conversation_state.deterministic_turn_classification(message, state(domains))


class FakeGemini:
    """Stands in for genai.Client; returns a fixed turn_type and captures the prompt."""

    def __init__(self, turn_type, captured):
        self.turn_type = turn_type
        self.captured = captured
        self.models = self

    def __call__(self, api_key=None):
        return self

    def generate_content(self, model, contents, config):
        self.captured["prompt"] = contents
        self.captured["calls"] = self.captured.get("calls", 0) + 1
        payload = {
            "turn_type": self.turn_type,
            "confidence": "high",
            "reason": "test",
            "updated_case_summary": "",
            "extracted_facts": [],
            "corrected_facts": [],
        }
        return type("Response", (), {"text": json.dumps(payload)})()


def use_gemini(monkeypatch, turn_type):
    captured = {}
    monkeypatch.setattr(conversation_state, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(conversation_state.genai, "Client", FakeGemini(turn_type, captured))
    return captured


# --- keyword rules (the hint, and the fallback when Gemini is unavailable) --------------------


@pytest.mark.parametrize(
    "message",
    [
        "but i dont know how civil courts work",
        "tell me the process",
        "what next",
        "how do i file it",
        "is there a time limit",
        "i need to know my options",
        "ab kya karu",
        "mujhe samajh nahi aaya",
        "ok but what about the deposit",
        "thanks, and what if they ignore the notice",
        "actually can i just stop paying rent",
        "sorry to bother but what if he changes the locks",
    ],
)
def test_questions_without_question_mark_are_recognised(message):
    assert rules(message).turn_type == "follow_up_question"


@pytest.mark.parametrize("message", ["thanks", "ok thank you so much", "understood thanks", "thank you this helps", "got it"])
def test_pure_acknowledgements_are_decided_without_gemini(message):
    result = rules(message)
    assert result.turn_type == "acknowledgement"
    assert result.confidence == "high"


def test_greeting_is_small_talk():
    assert rules("hello").turn_type == "small_talk"


@pytest.mark.parametrize("message", ["it is still not fixed", "they said it is my fault", "the government office said it is under process"])
def test_it_is_alone_is_not_a_correction(message):
    assert rules(message).turn_type != "correction"


@pytest.mark.parametrize("message", ["sorry the rent is 18000 not 15000", "actually it was 25000 not 20000", "i meant water not electricity"])
def test_explicit_corrections(message):
    assert rules(message).turn_type == "correction"


def test_other_legal_area_is_new_issue_even_with_also():
    assert rules("My RTI application also got no reply.", domains=("consumer",)).turn_type == "new_issue"


def test_same_dispute_with_also_is_not_new_issue():
    assert rules("the landlord also took my furniture, can i complain about that too").turn_type == "follow_up_question"


def test_rules_never_mark_fact_content_high_confidence():
    result = rules("the landlord also took my furniture")
    assert result.turn_type == "additional_fact"
    assert result.confidence != "high"


# --- rules as a hint, Gemini deciding ---------------------------------------------------------


def test_gemini_decides_and_sees_rule_hint_as_fallible(monkeypatch):
    captured = use_gemini(monkeypatch, "follow_up_question")

    result = conversation_state.classify_turn("the flat is not up to the mark", state())

    assert result.provider == "gemini"
    assert "HINT that may be wrong" in captured["prompt"]
    assert "turn_type=additional_fact" in captured["prompt"]


def test_pure_acknowledgement_skips_gemini(monkeypatch):
    captured = use_gemini(monkeypatch, "follow_up_question")

    result = conversation_state.classify_turn("thank you", state())

    assert result.turn_type == "acknowledgement"
    assert captured.get("calls", 0) == 0


def test_gemini_cannot_swallow_a_question_as_acknowledgement(monkeypatch):
    use_gemini(monkeypatch, "acknowledgement")

    result = conversation_state.classify_turn("ok but what about the deposit", state())

    assert result.turn_type == "follow_up_question"


def test_gemini_cannot_wipe_context_for_same_dispute(monkeypatch):
    use_gemini(monkeypatch, "new_issue")

    result = conversation_state.classify_turn("the landlord also took my furniture, can i complain about that too", state())

    assert result.turn_type == "follow_up_question"


def test_gemini_new_issue_kept_for_explicitly_new_problem(monkeypatch):
    use_gemini(monkeypatch, "new_issue")

    result = conversation_state.classify_turn("separately my instagram account got hacked", state())

    assert result.turn_type == "new_issue"


def test_gemini_failure_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(conversation_state, "GEMINI_API_KEY", "test-key")

    def broken_client(api_key=None):
        raise RuntimeError("network down")

    monkeypatch.setattr(conversation_state.genai, "Client", broken_client)

    result = conversation_state.classify_turn("tell me the process", state())

    assert result.turn_type == "follow_up_question"
    assert result.error is True


# --- correction memory ------------------------------------------------------------------------


def test_disagreement_is_recorded_as_pending(monkeypatch):
    use_gemini(monkeypatch, "follow_up_question")

    conversation_state.classify_turn("the flat is not up to the mark", state())

    [record] = turn_memory.list_corrections("pending")
    assert record["rule_label"] == "additional_fact"
    assert record["model_label"] == "follow_up_question"
    assert record["response_action"] == "answer_with_context"
    assert record["domains"] == "tenancy"


def test_agreement_is_not_recorded(monkeypatch):
    use_gemini(monkeypatch, "follow_up_question")

    conversation_state.classify_turn("tell me the process", state())

    assert turn_memory.list_corrections(None) == []


def test_repeat_disagreement_bumps_seen_count():
    for _ in range(3):
        turn_memory.record_correction("tell me more", ["tenancy"], "additional_fact", "follow_up_question")

    [record] = turn_memory.list_corrections("pending")
    assert record["seen_count"] == 3


def test_recorded_message_is_redacted():
    turn_memory.record_correction(
        "call me on 9876543210 or mail ravi.k@gmail.com, otp 123456, account 123456789012345",
        ["cyber"], "additional_fact", "follow_up_question",
    )

    message = turn_memory.list_corrections("pending")[0]["message"]
    assert "9876543210" not in message
    assert "ravi.k@gmail.com" not in message
    assert "123456" not in message
    assert "123456789012345" not in message


def test_pending_record_is_example_but_never_shortcut():
    turn_memory.record_correction("i dont know how civil courts work", ["tenancy"], "additional_fact", "follow_up_question")

    assert turn_memory.similar_examples("i dont know how civil courts work") == [
        {"message": "i dont know how civil courts work", "turn_type": "follow_up_question"}
    ]
    assert turn_memory.shortcut_label("i dont know how civil courts work") is None


def test_approved_record_shortcuts_gemini(monkeypatch):
    record_id = turn_memory.record_correction("i dont know how civil courts work", ["tenancy"], "additional_fact", "follow_up_question")
    turn_memory.review(record_id, "approved")
    captured = use_gemini(monkeypatch, "additional_fact")

    result = conversation_state.classify_turn("i dont know how civil courts work", state())

    assert result.turn_type == "follow_up_question"
    assert result.provider == "memory"
    assert captured.get("calls", 0) == 0


def test_examples_reach_gemini_prompt(monkeypatch):
    turn_memory.record_correction("i dont know how civil courts work", ["tenancy"], "additional_fact", "follow_up_question")
    captured = use_gemini(monkeypatch, "follow_up_question")

    conversation_state.classify_turn("i dont know how consumer courts work", state())

    assert "Similar past messages" in captured["prompt"]
    assert "i dont know how civil courts work" in captured["prompt"]


def test_reviewer_can_fix_label_and_rejected_records_are_not_examples():
    first = turn_memory.record_correction("the rent is 15000", ["tenancy"], "additional_fact", "correction")
    second = turn_memory.record_correction("what about the rent", ["tenancy"], "additional_fact", "follow_up_question")
    turn_memory.review(first, "approved", label="additional_fact")
    turn_memory.review(second, "rejected")

    [approved] = turn_memory.list_corrections("approved")
    assert approved["final_label"] == "additional_fact"
    assert approved["response_action"] == "update_case_and_answer"
    assert all(item["message"] != "what about the rent" for item in turn_memory.similar_examples("what about the rent"))


def test_old_pending_records_are_purged():
    record_id = turn_memory.record_correction("old message here", ["tenancy"], "additional_fact", "follow_up_question")
    with turn_memory.connect() as conn:
        conn.execute("UPDATE turn_corrections SET updated_at = '2000-01-01T00:00:00+00:00' WHERE id = ?", (record_id,))

    assert turn_memory.list_corrections(None) == []


def test_memory_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(turn_memory, "ENABLED", False)

    assert turn_memory.record_correction("tell me more", ["tenancy"], "additional_fact", "follow_up_question") is None
    assert turn_memory.similar_examples("tell me more") == []
