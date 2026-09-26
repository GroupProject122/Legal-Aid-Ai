from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import conversation_state
import turn_memory


def fake_embed(texts: list[str]) -> np.ndarray:
    """Deterministic bag-of-words vectors: identical texts score 1.0, texts sharing words score
    in between. Stands in for the sentence-transformer so tests never load the model."""
    vectors = np.zeros((len(texts), 64), dtype="float32")
    for row, text in enumerate(texts):
        for word in text.lower().split():
            vectors[row, int(hashlib.md5(word.encode()).hexdigest(), 16) % 64] += 1.0
        norm = np.linalg.norm(vectors[row])
        if norm:
            vectors[row] /= norm
    return vectors


@pytest.fixture(autouse=True)
def isolated_turn_memory(tmp_path, monkeypatch):
    """Every test gets its own empty correction memory and a fake embedder, and the turn
    classifier starts with Gemini off (a test that needs it sets GEMINI_API_KEY and mocks the
    client). Without this, a real backend/.env key would make classify_turn call Gemini and
    write to the real legal_aid.db during tests."""
    monkeypatch.setattr(turn_memory, "DB_PATH", tmp_path / "turn_memory_test.db")
    monkeypatch.setattr(turn_memory, "ENABLED", True)
    turn_memory.set_embedder(fake_embed)
    monkeypatch.setattr(conversation_state, "GEMINI_API_KEY", "")
    yield
    turn_memory.set_embedder(None)
