import sys
from services.pdf_service import extract_slides
from services.gemini_service import run_all_judges

pdf = extract_slides(open(sys.argv[1], "rb").read())

# Show the shape of the result so we can confirm it matches what we expect
print("PDF result keys:", list(pdf.keys()))

if not pdf.get("ok", True):
    sys.exit("PDF error: " + str(pdf.get("error")))

slides = pdf["slides"]
print("Slides extracted:", len(slides))

results = run_all_judges("Test Project", "", "Hackathon Judges", slides)
for key, r in results.items():
    print("=" * 60, key.upper())
    if r["ok"]:
        d = r["data"]
        print("Score:", d["overall_score"])
        print("Verdict:", d["verdict"])
        print("Categories:", d["category_scores"])
        print("Weaknesses:", len(d["weaknesses"]), "| Questions:", len(d["judge_questions"]))
    else:
        print("FAILED:", r["error"])