from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import voice_transcription as vt


def _fake_client(response_text: str):
    class FakeModels:
        def generate_content(self, **_kwargs):
            class Response:
                text = response_text

            return Response()

    class FakeClient:
        models = FakeModels()

    return lambda **_kwargs: FakeClient()


# --- is_allowed_mime_type ---


def test_known_audio_mime_types_are_allowed():
    assert vt.is_allowed_mime_type("audio/wav")
    assert vt.is_allowed_mime_type("audio/webm")
    assert vt.is_allowed_mime_type("audio/webm;codecs=opus")
    assert vt.is_allowed_mime_type("audio/mp4")


def test_unknown_mime_types_are_rejected():
    assert not vt.is_allowed_mime_type("video/mp4")
    assert not vt.is_allowed_mime_type("text/plain")
    assert not vt.is_allowed_mime_type(None)
    assert not vt.is_allowed_mime_type("")


# --- transcribe_audio: request-shape validation ---


def test_empty_audio_raises_voice_transcription_error():
    with pytest.raises(vt.VoiceTranscriptionError):
        vt.transcribe_audio(b"", "audio/wav")


def test_oversized_audio_raises_voice_transcription_error(monkeypatch):
    monkeypatch.setattr(vt, "MAX_AUDIO_SIZE_MB", 1)
    monkeypatch.setattr(vt, "max_audio_bytes", lambda: 1024)
    with pytest.raises(vt.VoiceTranscriptionError):
        vt.transcribe_audio(b"x" * 2048, "audio/wav")


def test_unsupported_mime_type_raises_voice_transcription_error():
    with pytest.raises(vt.VoiceTranscriptionError):
        vt.transcribe_audio(b"some bytes", "video/mp4")


def test_no_api_key_raises_service_unavailable_error(monkeypatch):
    monkeypatch.setattr(vt, "GEMINI_API_KEY", "")
    with pytest.raises(vt.VoiceServiceUnavailableError):
        vt.transcribe_audio(b"some bytes", "audio/wav")


# --- transcribe_audio: Gemini call ---


def test_successful_transcription_returns_text(monkeypatch):
    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", _fake_client('{"transcript": "mera landlord deposit nahi de raha"}'))

    result = vt.transcribe_audio(b"some bytes", "audio/webm")
    assert result == "mera landlord deposit nahi de raha"


def test_gemini_call_failure_raises_service_unavailable_error(monkeypatch):
    def raise_timeout(**_kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", raise_timeout)

    with pytest.raises(vt.VoiceServiceUnavailableError, match="temporarily unavailable"):
        vt.transcribe_audio(b"some bytes", "audio/wav")


def test_invalid_json_raises_safe_runtime_error(monkeypatch):
    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", _fake_client("{not valid json"))

    with pytest.raises(RuntimeError, match="Could not transcribe"):
        vt.transcribe_audio(b"some bytes", "audio/wav")


def test_empty_transcript_raises_no_speech_runtime_error(monkeypatch):
    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", _fake_client('{"transcript": "  "}'))

    with pytest.raises(RuntimeError, match="No speech was detected"):
        vt.transcribe_audio(b"some bytes", "audio/wav")


def test_mime_type_with_codec_parameters_is_passed_to_gemini_without_parameters(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured["mime_type"] = kwargs["contents"][0].inline_data.mime_type

            class Response:
                text = '{"transcript": "hello"}'

            return Response()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", lambda **_kwargs: FakeClient())

    vt.transcribe_audio(b"some bytes", "audio/webm;codecs=opus")
    assert captured["mime_type"] == "audio/webm"


# --- contains_devanagari ---


def test_contains_devanagari_detects_devanagari_text():
    assert vt.contains_devanagari("मेरा लैंडलॉर्ड डिपॉजिट नहीं दे रहा")
    assert vt.contains_devanagari("mera landlord deposit नहीं de raha")  # mixed


def test_contains_devanagari_is_false_for_latin_hinglish():
    assert not vt.contains_devanagari("mera landlord deposit nahi de raha")
    assert not vt.contains_devanagari("")
    assert not vt.contains_devanagari(None)


# --- transcribe_audio: Devanagari post-check + one retry ---


def test_devanagari_response_is_retried_and_succeeds(monkeypatch):
    responses = iter([
        '{"transcript": "मेरा लैंडलॉर्ड डिपॉजिट नहीं दे रहा"}',
        '{"transcript": "mera landlord deposit nahi de raha"}',
    ])

    class FakeModels:
        def generate_content(self, **_kwargs):
            class Response:
                text = next(responses)

            return Response()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", lambda **_kwargs: FakeClient())

    result = vt.transcribe_audio(b"some bytes", "audio/wav")
    assert result == "mera landlord deposit nahi de raha"


def test_devanagari_response_retried_twice_still_devanagari_raises_runtime_error(monkeypatch):
    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", _fake_client('{"transcript": "मेरा लैंडलॉर्ड"}'))

    with pytest.raises(RuntimeError, match="English letters"):
        vt.transcribe_audio(b"some bytes", "audio/wav")


def test_devanagari_retry_calls_gemini_exactly_twice(monkeypatch):
    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, **_kwargs):
            call_count["n"] += 1

            class Response:
                text = '{"transcript": "मेरा"}'

            return Response()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", lambda **_kwargs: FakeClient())

    with pytest.raises(RuntimeError):
        vt.transcribe_audio(b"some bytes", "audio/wav")
    assert call_count["n"] == 2


def test_already_latin_transcript_does_not_trigger_a_retry_call(monkeypatch):
    call_count = {"n": 0}

    class FakeModels:
        def generate_content(self, **_kwargs):
            call_count["n"] += 1

            class Response:
                text = '{"transcript": "mera landlord deposit nahi de raha"}'

            return Response()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(vt, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vt.genai, "Client", lambda **_kwargs: FakeClient())

    vt.transcribe_audio(b"some bytes", "audio/wav")
    assert call_count["n"] == 1
