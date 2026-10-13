"""
The look shared by the overseer report and the zonal monthly report:
fonts, colours, tables, captions, charts, cover and page frame.

This file knows nothing about the database. The house table style is the
church's own: navy header with white bold text, light blue alternate
rows, grey band rows, everything left-aligned and vertically centred.
"""
import io
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Frame, KeepTogether, ListFlowable, ListItem,
    NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = str(ASSETS / "logo-badge.png")
LOGO_RATIO = 298 / 258

# Liberation Sans has Arial's exact letter widths, and ships with the code
# so the report looks the same on any server.
FONT, BOLD = "Helvetica", "Helvetica-Bold"
try:
    pdfmetrics.registerFont(TTFont("DocSans", str(ASSETS / "LiberationSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("DocSans-Bold", str(ASSETS / "LiberationSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("DocSans", normal="DocSans", bold="DocSans-Bold",
                                  italic="DocSans", boldItalic="DocSans-Bold")
    FONT, BOLD = "DocSans", "DocSans-Bold"
except Exception:          # the built-in face still gives a usable report
    pass

CHURCH = "Deeper Christian Life Ministry, Bahrain"
SHORT = "DCLM Bahrain"
CONTACTS = ("https://dclm-bh.org", "info@dclm-bh.org", "+973 3306 2215")

NAVY = colors.HexColor("#1F4E79")
ZEBRA = colors.HexColor("#E8EFF7")
BAND = colors.HexColor("#D9D9D9")
RULE = colors.HexColor("#BFCBDA")
INK = colors.HexColor("#1A1A1A")
MUTED = colors.HexColor("#5A667C")
RED = colors.HexColor("#C8102E")
TILE = colors.HexColor("#EEF3F9")
# Charts: navy, bright blue, light blue, warm grey, pale blue, then more.
PALETTE = [colors.HexColor(c) for c in ("#1F4E79", "#2B6FD6", "#86AEE0", "#BEBEB2", "#C9DAF2", "#5B7FA6", "#9C9C8C", "#DDE7F4")]
UP, DOWN = colors.HexColor("#3E9E57"), colors.HexColor("#E6A0A0")

PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm
WIDTH = PAGE_W - 2 * MARGIN


def _style(name, size, leading=None, bold=False, colour=INK, align=0, before=0, after=0, indent=0):
    return ParagraphStyle(name, fontName=BOLD if bold else FONT, fontSize=size, leading=leading or size * 1.45,
                          textColor=colour, alignment=align, spaceBefore=before, spaceAfter=after, leftIndent=indent)


BODY = _style("body", 10.5, 15.5, after=7)
H1 = _style("h1", 15, 19, bold=True, colour=NAVY, before=14, after=8)
H2 = _style("h2", 12, 16, bold=True, colour=NAVY, before=10, after=6)
CAPTION = _style("caption", 9.5, 12, bold=True, align=TA_CENTER)
CELL = _style("cell", 8.8, 11)
HEAD = _style("head", 8.2, 10.5, bold=True, colour=colors.white)
SMALL = _style("small", 8.5, 11, colour=MUTED)


def para(text, style=BODY):
    return Paragraph(text, style)


def safe(text):
    return escape(str(text or ""))


def money(v):
    return f"{Decimal(v or 0):,.2f}"


def people(v):
    return f"{int(v or 0):,}"


def pct(part, whole_):
    return int(float(part) / float(whole_) * 100 + 0.5) if whole_ else 0


class Numbers:
    """Tables and figures numbered in order, one counter each."""
    def __init__(self):
        self.t = self.f = 0

    def table(self, title):
        self.t += 1
        return f"Table {self.t}. {title}"

    def figure(self, title):
        self.f += 1
        return f"Figure {self.f}. {title}"


def caption(text):
    return Paragraph(safe(text if text.endswith(".") else text + "."), CAPTION)


def table(header, rows, widths, bands=(), totals=(), repeat=True):
    """The house table. rows are lists of strings. bands are row indexes
    (into rows) drawn as grey group rows spanning the table; totals are
    row indexes drawn grey and bold."""
    data = [[Paragraph(safe(h), HEAD) for h in header]]
    for i, r in enumerate(rows):
        if i in bands:
            data.append([Paragraph(safe(r[0]), CELL)] + [""] * (len(header) - 1))
        else:
            st = _style("tot", 8.8, 11, bold=True) if i in totals else CELL
            data.append([Paragraph(safe(c), st) for c in r])
    colw = [WIDTH * w for w in widths]
    t = Table(data, colWidths=colw, repeatRows=1 if repeat else 0)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, RULE),
    ]
    zebra = 0
    for i in range(len(rows)):
        row = i + 1
        if i in bands or i in totals:
            cmds.append(("BACKGROUND", (0, row), (-1, row), BAND))
            if i in bands:
                cmds.append(("SPAN", (0, row), (-1, row)))
            elif len(header) > 2 and rows[i][0] and rows[i][1] == "":
                # A label such as Average needs more room than a date column.
                cmds.append(("SPAN", (0, row), (1, row)))
            zebra = 0
            continue
        if zebra % 2 == 1:
            cmds.append(("BACKGROUND", (0, row), (-1, row), ZEBRA))
        zebra += 1
    t.setStyle(TableStyle(cmds))
    return t


def captioned_table(title, header, rows, widths, **kw):
    """A table with its caption above, kept on one page when it is short,
    with clear space before and after."""
    cap = caption(title)
    t = table(header, rows, widths, **kw)
    parts = [Spacer(1, 10), cap, Spacer(1, 4), t, Spacer(1, 12)]
    if len(rows) <= 22:
        return [KeepTogether(parts)]
    # A long table may split, but its caption stays with its first rows.
    return [CondPageBreak(5 * cm)] + parts


def captioned_figure(title, drawing):
    return KeepTogether([Spacer(1, 10), drawing, Spacer(1, 4), caption(title), Spacer(1, 12)])


def text_block(text):
    """What somebody typed: blank lines separate paragraphs, lines starting
    with -, * or a bullet become a bulleted list, and lines starting with a
    number and a full stop become a numbered list."""
    import re
    out = []
    for chunk in re.split(r"\n\s*\n", (text or "").strip()):
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        if not lines:
            continue
        bullets = [l for l in lines if re.match(r"^[-*•]\s+", l)]
        numbers = [l for l in lines if re.match(r"^\d+[.)]\s+", l)]
        if bullets and len(bullets) == len(lines):
            out.append(bullet_list([re.sub(r"^[-*•]\s+", "", l) for l in lines]))
        elif numbers and len(numbers) == len(lines):
            out.append(bullet_list([re.sub(r"^\d+[.)]\s+", "", l) for l in lines], numbered=True))
        else:
            # A lead-in line followed by bullets.
            lead = [l for l in lines if l not in bullets]
            if bullets and lines[0] in lead and all(l in bullets for l in lines[len(lead):]):
                out.append(para(safe(" ".join(lead))))
                out.append(bullet_list([re.sub(r"^[-*•]\s+", "", l) for l in bullets]))
            else:
                out.append(para(safe(" ".join(lines))))
    return out


def bullet_list(items, numbered=False):
    style = _style("li", 10.5, 15, after=2)
    return ListFlowable(
        [ListItem(para(safe(i), style), leftIndent=14) for i in items],
        bulletType="1" if numbered else "bullet", start="1" if numbered else None,
        bulletFontName=FONT, bulletFontSize=9 if numbered else 7, leftIndent=14,
        bulletColor=INK, spaceAfter=8)


# ---------------------------------------------------------------- charts

def _s(x, y, text, size=7, colour=INK, anchor="middle", bold=False):
    return String(x, y, text, fontName=BOLD if bold else FONT, fontSize=size, fillColor=colour, textAnchor=anchor)


def _legend(d, items, y, width):
    """Centred legend under a chart. items: [(label, colour)]."""
    widths = [10 + pdfmetrics.stringWidth(label, FONT, 7.5) + 16 for label, _ in items]
    x = (width - sum(widths)) / 2
    for (label, col), w in zip(items, widths):
        d.add(Rect(x, y, 8, 6, fillColor=col, strokeColor=None))
        d.add(_s(x + 11, y, label, 7.5, anchor="start"))
        x += w


def grouped_bars(categories, series, fmt=people, height=190, sublabels=None, totals=None, width=WIDTH):
    """Vertical bars, one group per category, one bar per series.
    series: [(name, colour, [values])]. totals: a label over each group."""
    d = Drawing(width, height)
    left, bottom, top = 8, 34 + (10 if sublabels else 0), height - (22 if totals else 12)
    plot_w = width - left * 2
    n, k = max(len(categories), 1), max(len(series), 1)
    vmax = max([float(v) for _, _, vals in series for v in vals] + [1])
    group_w = plot_w / n
    bar_w = min(48 if n <= 6 else 26, group_w * (0.62 if n <= 6 else 0.8) / k)
    small = n * k > 24
    for i, cat in enumerate(categories):
        gx = left + group_w * i + (group_w - bar_w * k) / 2
        for j, (_, col, vals) in enumerate(series):
            v = float(vals[i] or 0)
            h = (top - bottom) * v / vmax
            x = gx + bar_w * j
            d.add(Rect(x, bottom, bar_w - (1 if k > 1 else 0), h, fillColor=col, strokeColor=None))
            if v and not (small and k > 2) and not (k > 1 and bar_w < 20):
                d.add(_s(x + bar_w / 2, bottom + h + 2, fmt(vals[i]), 5.8 if small else 6.5, MUTED))
        cx = left + group_w * i + group_w / 2
        d.add(_s(cx, bottom - 10, cat, 6.2 if small else 7, MUTED))
        if sublabels:
            d.add(_s(cx, bottom - 19, sublabels[i], 6.2 if small else 7, MUTED))
        if totals:
            hmax = max(float(vals[i] or 0) for _, _, vals in series)
            d.add(_s(cx, bottom + (top - bottom) * hmax / vmax + 10, totals[i], 6.2 if small else 6.8, INK, bold=True))
    d.add(Line(left, bottom, width - left, bottom, strokeColor=MUTED, strokeWidth=0.6))
    if len(series) > 1:
        _legend(d, [(name, col) for name, col, _ in series], 4, width)
    return d


def change_bars(items, width=WIDTH):
    """Horizontal bars either side of zero. items: [(label, percent)]."""
    row = 22
    height = row * len(items) + 16
    d = Drawing(width, height)
    label_w = width * 0.38
    zero = label_w + (width - label_w) * 0.35
    span = max([abs(p) for _, p in items] + [1])
    room = (width - zero - 40)
    for i, (label, p) in enumerate(items):
        y = height - 12 - row * (i + 1) + 6
        w = room * abs(p) / span
        x = zero if p >= 0 else zero - w
        d.add(Rect(x, y, max(w, 1), row - 8, fillColor=UP if p >= 0 else DOWN, strokeColor=None))
        d.add(_s(label_w - 6, y + 4, label, 7.2, INK, "end"))
        d.add(_s((x + w + 4) if p >= 0 else (x - 4), y + 4, f"{p:+d}%", 7, MUTED, "start" if p >= 0 else "end"))
    d.add(Line(zero, 4, zero, height - 6, strokeColor=MUTED, strokeWidth=0.6))
    return d


def donut(items, centre, centre_sub, fmt=people, width=WIDTH / 2, size=118):
    """items: [(label, value, colour)] drawn as a ring with the total in the
    middle and a legend underneath with each share."""
    total = sum(float(v) for _, v, _ in items) or 1
    legend_h = 12 * len(items) + 6
    d = Drawing(width, size + legend_h + 8)
    cx, cy, r = width / 2, legend_h + 8 + size / 2, size / 2
    angle = 90
    for label, v, col in items:
        sweep = 360 * float(v) / total
        if sweep >= 359.99:
            d.add(Circle(cx, cy, r, fillColor=col, strokeColor=colors.white, strokeWidth=1))
        elif sweep > 0:
            d.add(Wedge(cx, cy, r, angle - sweep, angle, fillColor=col, strokeColor=colors.white, strokeWidth=1))
        angle -= sweep
    d.add(Circle(cx, cy, r * 0.6, fillColor=colors.white, strokeColor=None))
    d.add(_s(cx, cy + 1, centre, 11, INK, bold=True))
    d.add(_s(cx, cy - 11, centre_sub, 6.8, MUTED))
    y = legend_h - 6
    lw = max(pdfmetrics.stringWidth(f"{l}  {fmt(v)}  ({pct(v, total)}%)", FONT, 7.2) for l, v, _ in items) + 12
    x = max(4, cx - lw / 2)
    for label, v, col in items:
        d.add(Rect(x, y, 7, 6, fillColor=col, strokeColor=None))
        d.add(_s(x + 11, y, f"{label}  {fmt(v)}  ({pct(v, total)}%)", 7.2, INK, "start"))
        y -= 12
    return d


def side_by_side(a, b):
    t = Table([[a, b]], colWidths=[WIDTH / 2, WIDTH / 2])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


# ---------------------------------------------------------------- pages

def make_doc(buffer, title, running_title, cover_draw):
    """A4 with a drawn cover and numbered inner pages. Page 1 is the page
    after the cover."""
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=2.3 * cm, bottomMargin=2.2 * cm, title=title, author=CHURCH)
    cover = Frame(0, 0, PAGE_W, PAGE_H, id="cover")
    inner = Frame(MARGIN, 2.2 * cm, WIDTH, PAGE_H - 4.5 * cm, id="inner", leftPadding=0, rightPadding=0)

    def draw_inner(c, d):
        c.saveState()
        mh = 0.62 * cm
        c.drawImage(LOGO, MARGIN, PAGE_H - 1.55 * cm, width=mh * LOGO_RATIO, height=mh, mask="auto")
        c.setFont(BOLD, 8.5)
        c.setFillColor(NAVY)
        c.drawString(MARGIN + mh * LOGO_RATIO + 6, PAGE_H - 1.3 * cm, SHORT)
        c.setFont(FONT, 8)
        c.setFillColor(MUTED)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.3 * cm, running_title)
        c.setStrokeColor(NAVY)
        c.setLineWidth(0.8)
        c.line(MARGIN, PAGE_H - 1.72 * cm, PAGE_W - MARGIN, PAGE_H - 1.72 * cm)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.line(MARGIN, 1.55 * cm, PAGE_W - MARGIN, 1.55 * cm)
        c.drawString(MARGIN, 1.1 * cm, CHURCH)
        c.drawRightString(PAGE_W - MARGIN, 1.1 * cm, f"Page {c.getPageNumber() - 1}")
        c.restoreState()

    doc.addPageTemplates([PageTemplate("cover", [cover], onPage=cover_draw),
                          PageTemplate("inner", [inner], onPage=draw_inner)])
    return doc


def draw_cover(c, kind_title, period, generated_on, tiles=None, tiles_title="", scope=""):
    """Navy field with the badge, the church, contacts and the title, and
    the headline figures underneath."""
    c.saveState()
    field = 11.6 * cm
    c.setFillColor(NAVY)
    c.rect(0, field, PAGE_W, PAGE_H - field, stroke=0, fill=1)
    c.setFillColor(RED)
    c.rect(0, field - 0.16 * cm, PAGE_W, 0.16 * cm, stroke=0, fill=1)
    cy = PAGE_H - 5.4 * cm
    c.setFillColor(colors.white)
    c.circle(PAGE_W / 2, cy, 2.05 * cm, stroke=0, fill=1)
    lh = 3.5 * cm
    c.drawImage(LOGO, PAGE_W / 2 - lh * LOGO_RATIO / 2, cy - lh / 2, width=lh * LOGO_RATIO, height=lh, mask="auto")
    c.setFont(BOLD, 17)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 9.4 * cm, CHURCH.upper())
    c.setFont(FONT, 9)
    c.setFillColor(colors.HexColor("#D5E1EF"))
    c.drawCentredString(PAGE_W / 2, PAGE_H - 10.3 * cm, "          ".join(CONTACTS))
    c.setStrokeColor(colors.HexColor("#D5E1EF"))
    c.setLineWidth(0.8)
    c.line(PAGE_W / 2 - 2.4 * cm, PAGE_H - 11.3 * cm, PAGE_W / 2 + 2.4 * cm, PAGE_H - 11.3 * cm)
    c.setFillColor(colors.white)
    c.setFont(BOLD, 26)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 13.0 * cm, kind_title)
    c.setFont(FONT, 14)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 14.0 * cm, period)
    if scope:
        c.setFont(FONT, 10.5)
        c.setFillColor(colors.HexColor("#D5E1EF"))
        c.drawCentredString(PAGE_W / 2, PAGE_H - 14.8 * cm, scope)
    if tiles:
        c.setFillColor(INK)
        c.setFont(BOLD, 8)
        c.drawString(MARGIN, field - 1.25 * cm, tiles_title.upper())
        gap = 0.35 * cm
        tw = (WIDTH - gap * (len(tiles) - 1)) / len(tiles)
        top = field - 1.6 * cm
        for i, (value, label) in enumerate(tiles):
            x = MARGIN + i * (tw + gap)
            c.setFillColor(TILE)
            c.roundRect(x, top - 2.4 * cm, tw, 2.4 * cm, 4, stroke=0, fill=1)
            c.setFillColor(NAVY)
            size = 15 if len(value) <= 8 else 12.5
            c.setFont(BOLD, size)
            c.drawCentredString(x + tw / 2, top - 1.15 * cm, value)
            c.setFillColor(MUTED)
            c.setFont(FONT, 7)
            c.drawCentredString(x + tw / 2, top - 1.8 * cm, label)
    c.setFillColor(MUTED)
    c.setFont(FONT, 9)
    c.drawString(MARGIN, 2.0 * cm, generated_on)
    c.drawRightString(PAGE_W - MARGIN, 2.0 * cm, CHURCH)
    c.restoreState()


def start_inner():
    return [NextPageTemplate("inner"), PageBreak()]


def heading(text):
    return Paragraph(safe(text), H1)


def keep_with_next(*flows):
    return KeepTogether(list(flows))


def render(story_fn):
    buf = io.BytesIO()
    story_fn(buf)
    return buf.getvalue()


__all__ = ["CondPageBreak", "PageBreak", "Spacer"]
