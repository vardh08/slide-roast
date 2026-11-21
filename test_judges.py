"""Opt-in live judge check for a PDF you intend to send to Groq."""
from argparse import ArgumentParser
from pathlib import Path

from prompts.judges import JUDGES
from services.groq_service import GroqError, run_judge
from services.pdf_service import extract_slides


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--judge", choices=JUDGES, default="professor")
    args = parser.parse_args()
    result = extract_slides(args.pdf.read_bytes())
    if not result["ok"]:
        parser.error(result["error"])
    try:
        review = run_judge(args.judge, args.pdf.stem, "", "Hackathon Judges", result["slides"])
    except GroqError as exc:
        raise SystemExit(exc.user_message) from None
    print(f"{JUDGES[args.judge]['name']}: {review['overall_score']} / 100")
    print(review["verdict"])
    print("Category scores:", review["category_scores"])


if __name__ == "__main__":
    main()
