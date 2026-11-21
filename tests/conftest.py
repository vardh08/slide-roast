import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """Skip retry delays in tests."""
    from services import groq_service

    monkeypatch.setattr(groq_service, "_sleep", lambda s: None)
