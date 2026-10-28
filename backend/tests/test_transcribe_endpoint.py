from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
import voice_transcription

client = TestClient(main.app)


def test_transcribe_endpoint_returns_transcript(monkeypatch):
    monkeypatch.setattr(voice_transcription, "transcribe_audio", lambda content, mime_type: "mera cyber issue hai")

    response = client.post(
        "/api/transcribe",
        files={"file": ("question.webm", b"fake-audio-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json() == {"transcript": "mera cyber issue hai"}


def test_transcribe_endpoint_returns_400_for_bad_request_shape(monkeypatch):
    def raise_shape_error(content, mime_type):
        raise voice_transcription.VoiceTranscriptionError("Unsupported audio format.")

    monkeypatch.setattr(voice_transcription, "transcribe_audio", raise_shape_error)

    response = client.post(
        "/api/transcribe",
        files={"file": ("question.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]


def test_transcribe_endpoint_returns_422_when_transcription_fails(monkeypatch):
    def raise_runtime_error(content, mime_type):
        raise RuntimeError("Could not transcribe that recording. Please try again or type your question.")

    monkeypatch.setattr(voice_transcription, "transcribe_audio", raise_runtime_error)

    response = client.post(
        "/api/transcribe",
        files={"file": ("question.webm", b"fake-audio-bytes", "audio/webm")},
    )

    assert response.status_code == 422
    assert "Could not transcribe" in response.json()["detail"]


def test_transcribe_endpoint_returns_503_when_service_unavailable(monkeypatch):
    def raise_service_unavailable(content, mime_type):
        raise voice_transcription.VoiceServiceUnavailableError("Voice transcription is temporarily unavailable. Please try again or type your question.")

    monkeypatch.setattr(voice_transcription, "transcribe_audio", raise_service_unavailable)

    response = client.post(
        "/api/transcribe",
        files={"file": ("question.webm", b"fake-audio-bytes", "audio/webm")},
    )

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
