"""Render validated slide plans to a single PNG used by both preview and download."""
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from math import ceil, hypot, isfinite
from unicodedata import category, name as unicode_name, normalize

import pymupdf as fitz
from PIL import Image, ImageColor, ImageDraw, ImageFont

from services.pdf_service import scaled_slide_size
from services.slide_redesign import DesignContent, DesignOption, Theme, comparable_metrics, contrast


class SlideRenderError(ValueError):
    """The slide cannot be rendered at a readable size."""


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.right, self.bottom

    def inset(self, amount: int) -> "Box":
        return Box(self.x + amount, self.y + amount, self.width - amount * 2, self.height - amount * 2)


@lru_cache(maxsize=6)
def _typeface(name: str) -> fitz.Font:
    return fitz.Font(name)


@lru_cache(maxsize=96)
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BytesIO(_typeface(name).buffer), size)


def _blend(base: str, accent: str, strength: float) -> tuple[int, int, int]:
    channels = zip(ImageColor.getrgb(base), ImageColor.getrgb(accent))
    return tuple(round(x + (y - x) * strength) for x, y in channels)


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}" if line else word
        if font.getlength(candidate) <= width:
            line = candidate
            continue
        if line:
            lines.append(line)
        line = ""
        if font.getlength(word) > width:
            for character in word:
                if line and font.getlength(line + character) > width:
                    lines.append(line)
                    line = ""
                line += character
        else:
            line = word
    if line:
        lines.append(line)
    return lines


class _Canvas:
    def __init__(self, size: tuple[int, int], theme: Theme, typography: str):
        self.image = Image.new("RGB", size, theme.background)
        self.draw = ImageDraw.Draw(self.image)
        self.theme = theme
        self.scale = min(size) / 1080
        self.soft = _blend(theme.background, theme.accent, .12)
        if contrast(theme.text, "#%02x%02x%02x" % self.soft) < 4.5:
            self.soft = ImageColor.getrgb(theme.background)
        self.rule = _blend(theme.background, theme.text, .22)
        self.diagram_ink = theme.accent if contrast(theme.accent, theme.background) >= 3 else theme.text
        detected_serif = any(word in theme.typeface.casefold() for word in ("times", "garamond", "cambria", "baskerville"))
        self.serif = typography == "Editorial" or (typography == "Keep original" and detected_serif)

    def units(self, size: int) -> int:
        return max(1, round(size * self.scale))

    def check_bounds(self, box: Box) -> None:
        if min(box.x, box.y) < 0 or min(box.width, box.height) <= 0 or (
            box.right > self.image.width or box.bottom > self.image.height
        ):
            raise SlideRenderError("The slide has an unsupported aspect ratio or an element could not fit.")

    def panel(self, box: Box, *, fill=None, outline=None) -> None:
        self.check_bounds(box)
        self.draw.rounded_rectangle(box.bounds, radius=self.units(20), fill=fill, outline=outline, width=self.units(2))

    def text(self, box: Box, value: str, *, maximum: int, minimum: int, bold=False, center=False) -> None:
        self.check_bounds(box)
        if not value.strip():
            return
        name = ("tibo" if bold else "tiro") if self.serif else ("hebo" if bold else "helv")
        glyphs = {ord(char) for char in value if not char.isspace()}
        if any(not _typeface(name).has_glyph(char) for char in glyphs):
            name = "cjk"
        if name == "cjk":
            parts = []
            for char in value:
                kind = category(char)
                if char.isspace() or _typeface(name).has_glyph(ord(char)):
                    parts.append(char)
                elif kind == "Cf" or char in ("\ufe0e", "\ufe0f"):
                    continue
                elif kind == "Co" or char == "\ufffd":
                    parts.append(f"[U+{ord(char):04X}]")
                elif 0xFB00 <= ord(char) <= 0xFB06:
                    parts.append(normalize("NFKC", char))
                elif kind.startswith(("S", "P")):
                    parts.append(f"[{unicode_name(char, f'U+{ord(char):04X}').lower()}]")
                else:
                    raise SlideRenderError(f"The available export fonts cannot display U+{ord(char):04X}.")
            value = "".join(parts)
            if not value.strip():
                return

        for size in range(self.units(maximum), self.units(minimum) - 1, -max(1, self.units(2))):
            font = _font(name, size)
            lines = _wrap(value, font, box.width)
            bounds = [font.getbbox(line, anchor="lt") for line in lines]
            heights = [b[3] - b[1] for b in bounds]
            line_height = max(round(size * 1.25), max(heights) + self.units(4))
            height = line_height * (len(lines) - 1) + heights[-1]
            if height > box.height or any(b[2] - b[0] > box.width for b in bounds):
                continue
            y = box.y + (box.height - height) // 2
            for line, (left, top, right, _) in zip(lines, bounds):
                x = box.x + (box.width - (right - left)) // 2 if center else box.x
                self.draw.text((x - left, y - top), line, font=font, fill=self.theme.text, anchor="lt")
                y += line_height
            return
        raise SlideRenderError("This layout cannot fit all the original text at a readable size. Try a simpler layout or split the slide.")

    def arrow(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = hypot(dx, dy)
        if length < 2:
            return
        ux, uy = dx / length, dy / length
        head = min(self.units(13), length * .45)
        base = end[0] - ux * head, end[1] - uy * head
        self.draw.line((start, end), fill=self.diagram_ink, width=self.units(3))
        self.draw.polygon(
            (end, (base[0] - uy * head * .6, base[1] + ux * head * .6),
             (base[0] + uy * head * .6, base[1] - ux * head * .6)),
            fill=self.diagram_ink,
        )


def _grid(box: Box, count: int, columns: int, gap: int) -> list[Box]:
    rows = ceil(count / columns)
    width = (box.width - gap * (columns - 1)) // columns
    height = (box.height - gap * (rows - 1)) // rows
    return [
        Box(box.x + (i % columns) * (width + gap), box.y + (i // columns) * (height + gap), width, height)
        for i in range(count)
    ]


def _list(canvas: _Canvas, area: Box, items: list[str], columns: int = 1) -> None:
    for box, item in _text_rows(canvas, area, items, columns):
        canvas.check_bounds(box)
        margin = canvas.units(22)
        rule_y = box.y + canvas.units(2)
        canvas.draw.line((box.x, rule_y, box.right, rule_y), fill=canvas.rule, width=canvas.units(2))
        canvas.text(Box(box.x + margin, box.y + canvas.units(5), box.width - margin, box.height - canvas.units(5)),
                    item, maximum=38, minimum=23)


def _text_rows(canvas: _Canvas, area: Box, items: list[str], columns: int):
    gap = canvas.units(8)
    cell_width = (area.width - gap * (columns - 1)) // columns
    rows = [items[i:i + columns] for i in range(0, len(items), columns)]
    font = _font("helv", canvas.units(25))
    weights = [max(len(_wrap(item, font, max(1, cell_width - canvas.units(36)))) for item in row)
               for row in rows]
    y = area.y
    available = area.height - gap * (len(rows) - 1)
    total = sum(weights)
    for row, weight in zip(rows, weights):
        height = available * weight // total
        for column, item in enumerate(row):
            yield Box(area.x + column * (cell_width + gap), y, cell_width, height), item
        y += height + gap


def _flowchart(canvas: _Canvas, area: Box, items: list[str]) -> None:
    across = area.width >= canvas.image.height * 1.36 and len(items) <= 6
    if across:
        height = min(area.height, canvas.units(290))
        area = Box(area.x, area.y + (area.height - height) // 2, area.width, height)
    boxes = _grid(area, len(items), len(items) if across else 1, canvas.units(34 if across else 21))
    for box, item in zip(boxes, items):
        canvas.panel(box, fill=canvas.soft, outline=canvas.rule)
        canvas.text(box.inset(canvas.units(11)), item, maximum=36, minimum=22, bold=True, center=True)
    for first, second in zip(boxes, boxes[1:]):
        if across:
            y = first.y + first.height // 2
            canvas.arrow((first.right + 3, y), (second.x - 3, y))
        else:
            x = first.x + first.width // 2
            canvas.arrow((x, first.bottom + 3), (x, second.y - 3))


def _timeline(canvas: _Canvas, area: Box, items: list[str]) -> None:
    boxes = _grid(area, len(items), 1, canvas.units(10))
    x = area.x + canvas.units(18)
    radius = canvas.units(8)
    centers = [box.y + box.height // 2 for box in boxes]
    canvas.draw.line((x, centers[0], x, centers[-1]), fill=canvas.theme.accent, width=canvas.units(4))
    for box, y, item in zip(boxes, centers, items):
        canvas.draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=canvas.theme.accent)
        margin = canvas.units(55)
        canvas.text(Box(box.x + margin, box.y, box.width - margin, box.height), item, maximum=40, minimum=23)


def _cards(canvas: _Canvas, area: Box, items: list[str], comparison: bool) -> None:
    columns = 2 if area.width >= canvas.image.height * .95 and len(items) > 1 else 1
    if len(items) >= 7 and area.width > canvas.image.height * 1.42 and not comparison:
        columns = 3
    for box, item in zip(_grid(area, len(items), columns, canvas.units(25)), items):
        canvas.panel(box, fill=canvas.soft, outline=canvas.rule)
        padding = min(canvas.units(24), box.height // 5)
        canvas.text(box.inset(padding), item, maximum=43, minimum=24, bold=True)


def _chart(canvas: _Canvas, area: Box, items: list[str]) -> None:
    metrics = comparable_metrics(tuple(items))
    if not metrics:
        raise SlideRenderError("The data needs consistent units and labeled values before it can be charted.")
    largest = max(metric.value for metric in metrics)
    for box, metric in zip(_grid(area, len(metrics), 1, canvas.units(16)), metrics):
        label_height = round(box.height * .66)
        canvas.text(Box(box.x, box.y, box.width, label_height), f"{metric.label}: {metric.display}",
                    maximum=38, minimum=22, bold=True)
        bar_height = min(canvas.units(24), box.height - label_height)
        canvas.panel(Box(box.x, box.y + label_height, box.width, bar_height), fill=canvas.soft)
        value_width = round(box.width * float(metric.value / largest))
        if value_width:
            canvas.panel(Box(box.x, box.y + label_height, value_width, bar_height), fill=canvas.theme.accent)


def render_design(
    content: DesignContent, option: DesignOption, theme: Theme, typography: str = "Keep original",
) -> bytes:
    """Reflow source text into a bounded layout and encode a high-resolution PNG."""
    if not all(isfinite(value) and value > 0 for value in (content.source.width, content.source.height)):
        raise SlideRenderError("The source PDF has invalid slide dimensions.")
    aspect = content.source.width / content.source.height
    if not .2 <= aspect <= 5:
        raise SlideRenderError("This slide's aspect ratio is too narrow or wide to redesign.")
    if content.too_dense:
        raise SlideRenderError("This slide has too much text for one readable redesign. Split it into two slides and try again.")
    if sorted(option.order) != list(range(len(content.items))):
        raise SlideRenderError("The design is missing original slide content.")
    size = scaled_slide_size(content.source.width, content.source.height, 1920)
    canvas = _Canvas(size, theme, typography)
    margin = canvas.units(70)
    area = Box(margin, margin, size[0] - 2 * margin, size[1] - 2 * margin)
    if content.source.artwork:
        with Image.open(BytesIO(content.source.artwork)) as source:
            artwork = source.convert("RGBA")
        gap = canvas.units(28)
        if aspect >= 1.3:
            reserved = round(area.width * .29)
            frame = Box(area.right - reserved, area.y, reserved, area.height)
            area = Box(area.x, area.y, area.width - reserved - gap, area.height)
        else:
            reserved = round(area.height * .24)
            frame = Box(area.x, area.bottom - reserved, area.width, reserved)
            area = Box(area.x, area.y, area.width, area.height - reserved - gap)
        artwork.thumbnail((frame.width, frame.height), Image.Resampling.LANCZOS)
        canvas.image.paste(artwork, (frame.x + (frame.width - artwork.width) // 2,
                                     frame.y + (frame.height - artwork.height) // 2), artwork)
    items = [content.items[index] for index in option.order]
    layout = option.layout

    if layout == "spotlight":
        if items:
            raise SlideRenderError("The title spotlight layout would leave out supporting text.")
        canvas.panel(area, fill=canvas.soft, outline=canvas.rule)
        canvas.text(area.inset(canvas.units(48)), content.title, maximum=108, minimum=40, bold=True, center=True)
    elif layout == "editorial" and aspect >= 1.32:
        left_width = round(area.width * .37)
        left = Box(area.x, area.y, left_width, area.height)
        canvas.panel(left, fill=canvas.soft)
        canvas.draw.rectangle((left.x, left.y, left.x + canvas.units(9), left.bottom), fill=theme.accent)
        canvas.text(left.inset(canvas.units(38)), content.title, maximum=92, minimum=31, bold=True)
        if items:
            space = canvas.units(40)
            _list(canvas, Box(left.right + space, area.y, area.width - left_width - space, area.height), items)
    else:
        head_height = round(area.height * (.28 if layout == "editorial" else .23)) if items else area.height
        head = Box(area.x, area.y, area.width, head_height)
        if layout == "editorial":
            canvas.panel(head, fill=canvas.soft)
            head = head.inset(canvas.units(24))
        canvas.text(head, content.title, maximum=96, minimum=34, bold=True)
        if items:
            gap = canvas.units(25)
            body = Box(area.x, area.y + head_height + gap, area.width, area.height - head_height - gap)
            if layout == "flowchart":
                _flowchart(canvas, body, items)
            elif layout == "timeline":
                _timeline(canvas, body, items)
            elif layout == "outline":
                for box, item in _text_rows(canvas, body, items, 1 if aspect < 1.3 or len(items) < 5 else 2):
                    canvas.panel(box, fill=canvas.soft)
                    canvas.text(box.inset(min(canvas.units(16), box.height // 5)), item, maximum=38, minimum=23)
            elif layout in ("cards", "comparison"):
                _cards(canvas, body, items, comparison=layout == "comparison")
            elif layout == "chart":
                _chart(canvas, body, items)
            else:
                columns = 2 if aspect >= 1.3 and len(items) >= 5 else 1
                _list(canvas, body, items, columns=columns)
    result = BytesIO()
    canvas.image.save(result, format="PNG")
    return result.getvalue()
