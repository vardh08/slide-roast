"""PDF processing service (PyMuPDF).

INPUT : raw PDF bytes (what Streamlit's uploader gives us)
OUTPUT: a dict like
    {
      "ok": True,
      "error": None,
      "page_count": 8,
      "slides": [{"slide_number": 1, "text": "...", "has_text": True}, ...],
      "pages_without_text": [4],
      "warnings": ["..."],
    }
If something is wrong, "ok" is False and "error" holds a friendly message.

We never write the PDF to disk: PyMuPDF can open it straight from memory,
so nothing needs to be cleaned up afterwards.
"""
from dataclasses import dataclass

import pymupdf as fitz  # PyMuPDF (new import name; aliased so the code below reads the same)

from utils.helpers import MAX_FILE_MB, MAX_PAGES

MIN_CHARS_FOR_TEXT = 15  # a page with fewer characters is treated as "no text"


def _fail(message: str) -> dict:
    return {"ok": False, "error": message, "page_count": 0, "slides": [], "pages_without_text": [], "warnings": []}


def extract_slides(pdf_bytes: bytes) -> dict:
    """Validate a PDF and extract text slide-by-slide. Never raises."""
    if not pdf_bytes:
        return _fail("The file is empty.")
    if len(pdf_bytes) > MAX_FILE_MB * 1024 * 1024:
        return _fail(f"File is larger than the {MAX_FILE_MB} MB limit.")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return _fail("This file could not be opened. It may be corrupted or not a real PDF.")

    try:
        if doc.needs_pass or doc.is_encrypted:
            return _fail("This PDF is password-protected. Please remove the password and upload it again.")
        if doc.page_count == 0:
            return _fail("This PDF has no pages.")
        if doc.page_count > MAX_PAGES:
            return _fail(f"This PDF has {doc.page_count} pages. The limit is {MAX_PAGES}.")

        slides, no_text_pages = [], []
        for index in range(doc.page_count):
            try:
                text = doc[index].get_text("text").strip()
            except Exception:
                text = ""
            text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            has_text = len(text) >= MIN_CHARS_FOR_TEXT
            if not has_text:
                no_text_pages.append(index + 1)
            slides.append({"slide_number": index + 1, "text": text, "has_text": has_text})

        if len(no_text_pages) == len(slides):
            return _fail(
                "No text could be extracted. This looks like a scanned or image-only PDF. "
                "Please export your slides as a text-based PDF (e.g. 'Save as PDF' from PowerPoint or Google Slides)."
            )

        warnings = []
        if no_text_pages:
            pages = ", ".join(str(p) for p in no_text_pages)
            warnings.append(
                f"No extractable text on slide(s) {pages}. They may be image-only, so the judges "
                "cannot read them and will not score them."
            )
        return {
            "ok": True,
            "error": None,
            "page_count": doc.page_count,
            "slides": slides,
            "pages_without_text": no_text_pages,
            "warnings": warnings,
        }
    except Exception:
        return _fail("Something went wrong while reading this PDF. Please try another file.")
    finally:
        doc.close()


def _page_png(page: fitz.Page, zoom: float) -> bytes:
    return page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False).tobytes("png")


def scaled_slide_size(width: float, height: float, max_side: int) -> tuple[int, int]:
    scale = max_side / max(width, height)
    return max(1, round(width * scale)), max(1, round(height * scale))


def render_page_png(
    pdf_bytes: bytes, slide_number: int, zoom: float = 1.5, *, max_side: int | None = None,
) -> bytes | None:
    """Render a 1-based PDF page to PNG, optionally fitting its longest edge to max_side."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if not 1 <= slide_number <= doc.page_count:
                return None
            page = doc[slide_number - 1]
            if max_side is not None:
                zoom = max_side / max(page.rect.width, page.rect.height)
                size = scaled_slide_size(page.rect.width, page.rect.height, max_side)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                if (pixmap.width, pixmap.height) != size:
                    pixmap = fitz.Pixmap(pixmap, *size, None)
                return pixmap.tobytes("png")
            return _page_png(page, zoom)
    except Exception:
        return None


@dataclass(frozen=True)
class TextLine:
    text: str
    bounds: tuple[float, float, float, float]
    size: float
    font: str


@dataclass(frozen=True)
class SlideSource:
    width: float
    height: float
    lines: tuple[TextLine, ...]
    has_images: bool
    artwork: bytes | None = None


def read_slide_source(pdf_bytes: bytes, slide_number: int) -> SlideSource:
    """Read text geometry for the selected slide, without copying embedded images."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if not 1 <= slide_number <= doc.page_count:
            raise ValueError("The selected slide is missing from the PDF.")
        page = doc[slide_number - 1]
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT, sort=True)["blocks"]
        lines = []
        for block in blocks:
            for line in block.get("lines", []):
                spans = line["spans"]
                text = "".join(span["text"] for span in spans).strip()
                if text:
                    largest_span = max(spans, key=lambda span: span["size"])
                    lines.append(TextLine(text, tuple(line["bbox"]), largest_span["size"], largest_span["font"]))
        images = page.get_image_info(xrefs=True)
        artwork = None
        for image in sorted(images, key=lambda info: fitz.Rect(info["bbox"]).get_area(), reverse=True):
            box = fitz.Rect(image["bbox"])
            if not image["xref"] or not .025 <= box.get_area() / page.rect.get_area() <= .8:
                continue
            try:
                pix = fitz.Pixmap(doc, image["xref"])
                if pix.colorspace is None:
                    continue
                if pix.colorspace.n not in (1, 3):
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                scale = min(1, 1100 / max(pix.width, pix.height))
                if scale < 1:
                    pix = fitz.Pixmap(pix, round(pix.width * scale), round(pix.height * scale), None)
                artwork = pix.tobytes("png")
                break
            except (RuntimeError, ValueError):
                continue
        return SlideSource(page.rect.width, page.rect.height, tuple(lines), bool(images), artwork)


def preview_deck(pdf_bytes: bytes, max_side: int = 240) -> tuple[dict[int, bytes], list[str]]:
    """Render deck thumbnails and collect typefaces in one PDF pass."""
    thumbnails, fonts = {}, []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for number, page in enumerate(doc, 1):
            try:
                thumbnails[number] = _page_png(page, max_side / max(page.rect.width, page.rect.height))
                fonts.extend(font[3] for font in page.get_fonts())
            except (RuntimeError, ValueError, ZeroDivisionError):
                continue
    return thumbnails, fonts


def slides_to_prompt_text(slides: list[dict]) -> str:
    """Turn the slide list into the text block we paste into the judge prompts."""
    parts = []
    for s in slides:
        body = s["text"] if s["has_text"] else "[NO EXTRACTABLE TEXT ON THIS SLIDE]"
        parts.append(f"--- SLIDE {s['slide_number']} ---\n{body}")
    return "\n\n".join(parts)
