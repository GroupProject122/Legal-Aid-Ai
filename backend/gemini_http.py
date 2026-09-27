"""Shared HTTP settings for every Gemini client in the backend."""
from __future__ import annotations

from google.genai import types

import config


def gemini_http_options() -> types.HttpOptions:
    # google-genai takes the timeout in milliseconds.
    return types.HttpOptions(timeout=int(config.GEMINI_TIMEOUT_SECONDS * 1000))
