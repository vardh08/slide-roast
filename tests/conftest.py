import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """Retries normally wait 2-4 seconds; skip the waiting in tests."""
    from services import gemini_service

    monkeypatch.setattr(gemini_service, "_sleep", lambda s: None)
