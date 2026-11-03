"""Gives these tests the same protection as backend/tests: every test runs against its own temporary
database and upload folder, and opening the real backend/legal_aid.db fails loudly. The fixtures
are reused from backend/tests/conftest.py rather than copied, so the two cannot drift apart."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

_spec = importlib.util.spec_from_file_location("backend_shared_conftest", BACKEND_DIR / "tests" / "conftest.py")
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

refuse_real_database = _shared.refuse_real_database
isolated_app_storage = _shared.isolated_app_storage
