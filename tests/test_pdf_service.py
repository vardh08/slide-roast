"""Tests for services/pdf_service.py. Run:  python -m pytest tests -q   (or: python tests/test_pdf_service.py)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymupdf as fitz

from services.pdf_service import extract_slides, slides_to_prompt_text
from tests.make_sample_pdfs import ASSETS, build_all


def _pdf(pages: int, text="This slide has enough text to count.") -> bytes:
    doc = fitz.open()
    for i in range(pages):
        p = doc.new_page()
        if text:
            p.insert_text((72, 100), f"{text} {i + 1}")
    data = doc.tobytes()
    doc.close()
    return data


def test_valid_pdf():
    r = extract_slides(_pdf(3))
    assert r["ok"] and r["page_count"] == 3
    assert [s["slide_number"] for s in r["slides"]] == [1, 2, 3]
    assert all(s["has_text"] for s in r["slides"])


def test_empty_bytes():
    assert not extract_slides(b"")["ok"]


def test_not_a_pdf():
    r = extract_slides(b"this is definitely not a pdf" * 10)
    assert not r["ok"] and "corrupted" in r["error"].lower()


def test_corrupted_pdf():
    r = extract_slides(_pdf(2)[:200])
    assert not r["ok"]


def test_too_many_pages():
    r = extract_slides(_pdf(16))
    assert not r["ok"] and "limit" in r["error"].lower()


def test_exactly_max_pages_ok():
    assert extract_slides(_pdf(15))["ok"]


def test_password_protected():
    doc = fitz.open()
    doc.new_page().insert_text((72, 100), "secret content here for the test")
    data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="pw")
    doc.close()
    r = extract_slides(data)
    assert not r["ok"] and "password" in r["error"].lower()


def test_no_extractable_text_all_pages():
    r = extract_slides(_pdf(2, text=""))
    assert not r["ok"] and "scanned" in r["error"].lower()


def test_some_pages_without_text_gives_warning():
    doc = fitz.open()
    doc.new_page().insert_text((72, 100), "Page one has real readable text")
    doc.new_page()  # blank
    data = doc.tobytes()
    doc.close()
    r = extract_slides(data)
    assert r["ok"] and r["pages_without_text"] == [2] and r["warnings"]


def test_sample_decks_and_prompt_text():
    build_all()
    for name in ("sample_deck_v1.pdf", "sample_deck_v2.pdf"):
        r = extract_slides((ASSETS / name).read_bytes())
        assert r["ok"] and r["page_count"] == 7, name
    txt = slides_to_prompt_text(r["slides"])
    assert "--- SLIDE 1 ---" in txt and "--- SLIDE 7 ---" in txt


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
