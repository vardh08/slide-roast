"""Visual fixer checks with small, real PDF fixtures and mocked planning."""
from dataclasses import replace
from io import BytesIO

import pymupdf as fitz
import pytest
from PIL import Image, ImageChops

from services import gemini_service, slide_renderer
from services.pdf_service import extract_slides, preview_deck, read_slide_source, render_page_png
from services.slide_redesign import comparable_metrics, detect_theme, fallback_plan, plan_redesign, source_content
from services.slide_renderer import SlideRenderError, render_design



def deck_pdf(title, items, *, dark=False, portrait=False):
    with fitz.open() as doc:
        width, height = (540, 720) if portrait else (960, 540)
        for theme_dark in (dark, dark, not dark):
            page = doc.new_page(width=width, height=height)
            background = (.075, .1, .17) if theme_dark else (.98, .97, .94)
            foreground = (.96, .96, 1) if theme_dark else (.1, .09, .12)
            page.draw_rect(page.rect, color=None, fill=background)
            page.draw_rect(fitz.Rect(42, 48, 106, 55), color=None, fill=(.65, .49, .83))
            page.insert_text((42, 108), title, fontsize=29, fontname="hebo", color=foreground)
            for index, text in enumerate(items, 1):
                page.insert_text((47, 140 + 27 * index), text, fontsize=15, color=foreground)
        return doc.tobytes()


def prepare(pdf, number=1):
    thumbs, fonts = preview_deck(pdf)
    return source_content(read_slide_source(pdf, number), number), detect_theme(thumbs, fonts)


def test_redesign_retains_embedded_artwork():
    artwork = BytesIO()
    Image.new("RGB", (300, 220), (211, 29, 54)).save(artwork, format="PNG")
    with fitz.open() as doc:
        page = doc.new_page(width=960, height=540)
        page.insert_text((32, 65), "Product screenshot", fontsize=34)
        page.insert_text((32, 105), "The interface shows available tasks.", fontsize=18)
        page.insert_image(fitz.Rect(540, 110, 840, 330), stream=artwork.getvalue())
        pdf = doc.tobytes()
    content, theme = prepare(pdf)
    assert content.source.artwork
    for option in fallback_plan(content).options:
        image = Image.open(BytesIO(render_design(content, option, theme)))
        assert image.getpixel((1590, 540)) == (211, 29, 54)


def test_redesign_renders_dense_source_with_unmapped_pdf_symbols():
    content, theme = prepare(deck_pdf("Feasibility and practicality", ("Implementation", "Costs")))
    content = replace(content, items=(
        "Implementation \ue035", "Twelve-month estimate: $12,000",
        "The delivery team will confirm resource availability before work begins. " * 5,
        "Timing assumes approval and recorded dependencies.",
        "Capacity", "Quality checks",
    ))
    assert render_design(content, fallback_plan(content).options[0], theme).startswith(b"\x89PNG")


def test_process_renders_three_distinct_designs_and_real_before(monkeypatch):
    items = ("Upload PDF", "Extract Content", "Analyze Slides", "Generate Feedback", "Improve Pitch")
    pdf = deck_pdf("How Slide Roast Works", items, dark=True)
    # The selected slide is light, but two other slides establish a dark deck theme.
    content, theme = prepare(pdf, number=3)
    assert theme.mode == "dark" and content.items == items
    plan = fallback_plan(content)
    assert plan.slide_type == "process" and plan.options[1].layout == "flowchart"
    arrows = []
    draw_arrow = slide_renderer._Canvas.arrow

    def spy(self, start, end):
        arrows.append((start, end))
        draw_arrow(self, start, end)

    monkeypatch.setattr(slide_renderer._Canvas, "arrow", spy)
    originals = Image.open(BytesIO(render_page_png(pdf, 3, max_side=1920)))
    pngs = [Image.open(BytesIO(render_design(content, option, theme))) for option in plan.options]
    assert len(arrows) == 4 and all(start[0] < end[0] for start, end in arrows)
    assert originals.getpixel((0, 0))[0] > 200
    assert all(image.size == originals.size and image.getpixel((0, 0))[0] < 70 for image in pngs)
    assert all(ImageChops.difference(a, b).getbbox() for a, b in zip(pngs, pngs[1:]))
    selected_theme = detect_theme({3: render_page_png(pdf, 3, max_side=1920)}, ["Helvetica"])
    assert selected_theme.mode == "light"
    for option in plan.options:
        image = Image.open(BytesIO(render_design(content, option, selected_theme)))
        assert image.getpixel((0, 0)) == originals.getpixel((0, 0))


@pytest.mark.parametrize(("title", "items", "layout"), [
    ("Historical events", ("Event in 1857", "Event in 1885", "Event in 1947"), "timeline"),
    ("Inflammatory pathway", ("Infection", "Immune response", "Inflammation"), "flowchart"),
    ("Request-response workflow", ("User sends request", "Server processes request", "Server returns response"), "flowchart"),
    ("Clinical observations", ("Infection", "Immune response", "Inflammation"), "outline"),
])
def test_domain_layout_requires_source_evidence(title, items, layout):
    content, theme = prepare(deck_pdf(title, items))
    option = fallback_plan(content).options[1]
    assert option.layout == layout
    assert render_design(content, option, theme).startswith(b"\x89PNG")


@pytest.mark.parametrize("items", [
    ("AI Judge Review", "Slide-Level Feedback", "Overall Score", "Slide Fixer"),
    tuple(f"Point {n}: Explain the problem clearly, show real evidence, and name the next action." for n in range(1, 7)),
])
def test_feature_cards_and_text_heavy_slide_render_in_portrait(items):
    content, theme = prepare(deck_pdf("Product Features", items, portrait=True))
    plan = fallback_plan(content)
    assert theme.mode == "light" and plan.options[1].layout == "cards"
    for design in plan.options:
        image = Image.open(BytesIO(render_design(content, design, theme)))
        assert image.size == (1440, 1920)


def test_chart_draws_exact_source_values_and_rejects_mixed_units(monkeypatch):
    values = ("April: 12.50%", "May: 17.25%", "June: 20.00%")
    content, theme = prepare(deck_pdf("Research Results", values))
    option = fallback_plan(content).options[1]
    assert option.layout == "chart"
    assert [metric.display for metric in comparable_metrics(content.items)] == ["12.50%", "17.25%", "20.00%"]
    assert not comparable_metrics(("April: $100", "May: 17%"))
    captured = []
    draw_text = slide_renderer._Canvas.text

    def spy(self, box, value, **kwargs):
        captured.append(value)
        draw_text(self, box, value, **kwargs)

    monkeypatch.setattr(slide_renderer._Canvas, "text", spy)
    render_design(content, option, theme)
    assert captured == [content.title, *values]


def test_original_and_redesign_match_for_fractional_page_dimensions():
    with fitz.open() as doc:
        page = doc.new_page(width=613.7, height=403.4)
        page.insert_text((42, 85), "A fractional-size slide", fontsize=24)
        pdf = doc.tobytes()
    content, theme = prepare(pdf)
    original = Image.open(BytesIO(render_page_png(pdf, 1, max_side=1920)))
    for option in fallback_plan(content).options:
        redesigned = Image.open(BytesIO(render_design(content, option, theme)))
        assert redesigned.size == original.size


def test_invalid_model_plan_falls_back_and_does_not_omit_content(monkeypatch):
    pdf = deck_pdf("Workflow", ("Upload PDF", "Analyze slides", "Generate feedback"))
    content, theme = prepare(pdf)
    invalid = fallback_plan(content)
    invalid.options[1].order = [0, 2, 99]
    monkeypatch.setattr(gemini_service, "_call_model", lambda *args: invalid.model_dump_json())
    plan, warning = plan_redesign(content, theme, "Investors")
    assert "unsupported design plan" in warning
    assert plan.options[1].order == [0, 1, 2]
    with pytest.raises(SlideRenderError, match="missing original"):
        render_design(content, invalid.options[1], theme)
