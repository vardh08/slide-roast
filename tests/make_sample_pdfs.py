"""Creates real PDFs for testing and for the demo.

Run:  python tests/make_sample_pdfs.py
Creates assets/sample_deck_v1.pdf (weak draft) and assets/sample_deck_v2.pdf (improved draft)
- these are fictional sample decks written by us, used for the demo and the before/after comparison.
"""
from pathlib import Path

import pymupdf as fitz

ASSETS = Path(__file__).resolve().parent.parent / "assets"

DECK_V1 = [
    ("Campus Barter", "Exchange skills. Not money.\nA team project for Hackathon 2026"),
    ("The Problem", "Students struggle to find help with skills like design, coding and tutoring.\nHiring freelancers is expensive."),
    ("Our Solution", "Campus Barter is a platform leveraging a synergistic skill-exchange paradigm\nusing a scalable microservice architecture."),
    ("How It Works", "1. Create a profile\n2. List skills you offer and need\n3. Get matched"),
    ("Market", "There are many students in colleges. Everyone needs help."),
    ("Team", "Three students from the Computer Science department."),
    ("Thank You", "Questions?"),
]

DECK_V2 = [
    ("Campus Barter", "Trade a skill you have for a skill you need.\nHackathon 2026 - Team of three"),
    ("The Problem", "Students need help with design, coding and tutoring but paying freelancers is expensive.\nWe have not yet surveyed students; we plan to interview 30 students next month."),
    ("Our Solution", "Campus Barter matches two students who want each other's skills.\nExample: a coder helps with a website, a designer makes a logo in return."),
    ("How It Works", "1. Create a profile\n2. List skills you offer and need\n3. Get matched with a student nearby\n4. Agree on a swap and rate each other"),
    ("Who Pays?", "Students use it free.\nProposed revenue (not yet validated): colleges pay a yearly fee for a verified campus community."),
    ("Competition", "Alternatives today: WhatsApp groups, freelance sites, notice boards.\nOur difference: structured matching and ratings for skill swaps only."),
    ("Next Steps", "Build a working prototype, run a pilot at one college, measure completed swaps."),
]


def _write_deck(path: Path, slides: list) -> None:
    doc = fitz.open()
    for title, body in slides:
        page = doc.new_page(width=960, height=540)
        page.insert_text((60, 90), title, fontsize=36, fontname="helv")
        page.insert_textbox(fitz.Rect(60, 140, 900, 480), body, fontsize=22, fontname="helv")
    doc.save(path)
    doc.close()


def build_all():
    ASSETS.mkdir(exist_ok=True)
    _write_deck(ASSETS / "sample_deck_v1.pdf", DECK_V1)
    _write_deck(ASSETS / "sample_deck_v2.pdf", DECK_V2)


if __name__ == "__main__":
    build_all()
    print("Created sample decks in", ASSETS)
