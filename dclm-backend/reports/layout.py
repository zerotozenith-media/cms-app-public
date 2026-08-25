"""
Layout for the monthly report PDF.

Kept apart from reports/pdf.py so the queries and the drawing can be
changed independently: this file decides how the report looks, and
knows nothing about the database.

Design intent, approved before it was built: keep the structure the
church already knew (cover, contents, numbered sections) and add what
the old HTML version could not do, which is anything visual. Numbers in
a table say what happened; a trend line says whether it is improving.
"""
import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, NextPageTemplate, KeepTogether, Flowable,
)

# Brand colours, matching the app exactly.
BLUE = colors.HexColor("#0B3C91")
DEEP = colors.HexColor("#082C69")
NIGHT = colors.HexColor("#061F4A")
SKY = colors.HexColor("#EAF1FC")
SKY2 = colors.HexColor("#F4F8FE")
LINE = colors.HexColor("#E4E9F1")
INK = colors.HexColor("#0F1B2E")
MUTED = colors.HexColor("#5A667C")
GREEN = colors.HexColor("#1E9E64")
AMBER = colors.HexColor("#C9891A")
RED = colors.HexColor("#D6202C")

CHURCH = "Deeper Life Bible Church"
LOCATION = "Bahrain"

# The church badge. Its outer ring is navy, so on the dark cover it needs
# a white disc behind it to stay legible. Shipped with the code rather
# than uploaded, since it never changes.
LOGO = str(Path(__file__).resolve().parent / "assets" / "logo-badge.png")
LOGO_RATIO = 298 / 258  # width / height, from the source file


# ----------------------------------------------------------------- styles

def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("CoverTitle", parent=s["Title"], fontName="Helvetica-Bold",
                         fontSize=24, textColor=DEEP, spaceAfter=2, leading=28))
    s.add(ParagraphStyle("CoverSub", parent=s["Normal"], fontName="Helvetica",
                         fontSize=14, textColor=MUTED, alignment=TA_CENTER, spaceAfter=0))
    s.add(ParagraphStyle("CoverLabel", parent=s["Normal"], fontName="Helvetica-Bold",
                         fontSize=16, textColor=BLUE, alignment=TA_CENTER))
    s.add(ParagraphStyle("CoverPeriod", parent=s["Normal"], fontSize=13,
                         textColor=INK, alignment=TA_CENTER))
    s.add(ParagraphStyle("CoverMeta", parent=s["Normal"], fontSize=9.5,
                         textColor=MUTED, alignment=TA_CENTER, leading=14))
    s.add(ParagraphStyle("H2", parent=s["Heading2"], fontName="Helvetica-Bold",
                         fontSize=13, textColor=DEEP, spaceBefore=18, spaceAfter=8))
    s.add(ParagraphStyle("Body", parent=s["Normal"], fontSize=10.5, leading=16,
                         textColor=INK, spaceAfter=6))
    s.add(ParagraphStyle("Muted", parent=s["Normal"], fontSize=10,
                         textColor=MUTED, fontName="Helvetica-Oblique"))
    s.add(ParagraphStyle("Quote", parent=s["Normal"], fontSize=10.5, leading=16,
                         textColor=INK, leftIndent=10, spaceAfter=2))
    s.add(ParagraphStyle("QuoteBy", parent=s["Normal"], fontSize=9,
                         textColor=MUTED, leftIndent=10, spaceAfter=10))
    s.add(ParagraphStyle("KpiLabel", parent=s["Normal"], fontSize=7.5,
                         textColor=MUTED, alignment=TA_CENTER))
    s.add(ParagraphStyle("KpiValue", parent=s["Normal"], fontName="Helvetica-Bold",
                         fontSize=17, textColor=DEEP, alignment=TA_CENTER))
    s.add(ParagraphStyle("TocItem", parent=s["Normal"], fontSize=11, leading=22, textColor=INK))
    s.add(ParagraphStyle("Cell", parent=s["Normal"], fontSize=9.5, leading=12, textColor=INK))
    return s


S = styles()


# ----------------------------------------------------------------- pieces

class HR(Flowable):
    """A rule under a section heading. Cheaper than a table for one line."""
    def __init__(self, width, thickness=1.6, colour=BLUE):
        super().__init__()
        self.width, self.thickness, self.colour = width, thickness, colour

    def wrap(self, *args):
        return (self.width, self.thickness + 4)

    def draw(self):
        self.canv.setStrokeColor(self.colour)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 2, self.width, 2)


def heading(text, width):
    return KeepTogether([Paragraph(text, S["H2"]), HR(width)])


def kpi_row(items, width):
    """The four headline numbers, as cards rather than a sentence.
    A board member should get the month at a glance."""
    col = width / len(items)
    cells = []
    for label, value, colour in items:
        # Two stacked rows inside each card: small label above, big number below.
        inner = Table(
            [[Paragraph(label.upper(), S["KpiLabel"])],
             [Paragraph(f'<font color="{colour}">{value}</font>', S["KpiValue"])]],
            colWidths=[col - 8],
        )
        inner.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        cells.append(inner)
    table = Table([cells], colWidths=[col] * len(items))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SKY2),
        ("BOX", (0, 0), (-1, -1), 0.8, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.8, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def data_table(header, rows, widths, aligns=None):
    table = Table([header] + rows, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), SKY),
        ("TEXTCOLOR", (0, 0), (-1, 0), DEEP),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.6, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        # Banded rows: easier to follow across a wide table than plain grid.
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SKY2]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for col, align in (aligns or {}).items():
        style.append(("ALIGN", (col, 0), (col, -1), align))
    table.setStyle(TableStyle(style))
    return table


def attendance_chart(width, labels, series):
    """Trend over the month. The table below gives exact figures; this
    answers the question the table cannot, which is the direction."""
    d = Drawing(width, 150)
    chart = HorizontalLineChart()
    chart.x, chart.y = 30, 25
    chart.width, chart.height = width - 60, 105
    chart.data = [series]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = MUTED
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(series) * 1.25
    chart.valueAxis.valueStep = max(20, int(max(series) / 4 / 10) * 10)
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.labels.fillColor = MUTED
    chart.lines[0].strokeColor = BLUE
    chart.lines[0].strokeWidth = 2.2
    chart.lineLabelFormat = "%d"
    chart.lineLabels.fontSize = 8
    chart.lineLabels.fillColor = DEEP
    chart.lineLabels.dy = 7
    d.add(chart)
    return d


def fund_pie(width, data, labels):
    d = Drawing(width / 2, 160)
    pie = Pie()
    pie.x, pie.y = 30, 15
    pie.width = pie.height = 125
    pie.data = data
    pie.labels = [f"{l}" for l in labels]
    pie.sideLabels = True
    pie.slices.strokeWidth = 1
    pie.slices.strokeColor = colors.white
    palette = [BLUE, colors.HexColor("#4A8BE8"), GREEN, AMBER, colors.HexColor("#8AA9D6")]
    for i in range(len(data)):
        pie.slices[i].fillColor = palette[i % len(palette)]
        pie.slices[i].fontSize = 8
        pie.slices[i].fontColor = MUTED
    d.add(pie)
    return d


def expense_bars(width, data, labels):
    d = Drawing(width / 2, 160)
    chart = VerticalBarChart()
    chart.x, chart.y = 35, 30
    chart.width, chart.height = width / 2 - 60, 105
    chart.data = [data]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = MUTED
    chart.categoryAxis.labels.angle = 20
    chart.categoryAxis.labels.dy = -6
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.labels.fillColor = MUTED
    chart.bars[0].fillColor = BLUE
    chart.barWidth = 8
    chart.groupSpacing = 12
    d.add(chart)
    return d


def goal_bar(width, pct):
    """A filled bar reads faster than a percentage in a column, and the
    colour says whether it needs attention without being read."""
    d = Drawing(width, 13)
    colour = GREEN if pct >= 80 else (AMBER if pct >= 50 else RED)
    d.add(Rect(0, 2, width, 8, fillColor=SKY, strokeColor=None, rx=4, ry=4))
    d.add(Rect(0, 2, width * min(pct, 100) / 100, 8, fillColor=colour, strokeColor=None, rx=4, ry=4))
    return d


# ----------------------------------------------------------------- chrome

def draw_cover(canvas, doc, ctx):
    """
    Drawn entirely on the canvas rather than flowed, so every element sits
    exactly where it should.

    The headline figures appear on the cover on purpose. A board member
    who reads nothing else still learns how the month went, and it gives
    the lower half of the page something to do besides be empty.
    """
    canvas.saveState()
    w, h = A4
    navy_bottom = 13.0 * cm

    # Deep field across the top two thirds.
    canvas.setFillColor(NIGHT)
    canvas.rect(0, navy_bottom, w, h - navy_bottom, stroke=0, fill=1)

    # Faint concentric arcs, a nod to the badge, for texture rather than
    # decoration. Kept close to the background so they read as depth.
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#0E2A57"))
    canvas.setLineWidth(1.1)
    for r in (5.6, 7.2, 8.8, 10.4):
        canvas.circle(w * 0.5, h - 5.0 * cm, r * cm, stroke=1, fill=0)
    canvas.restoreState()

    # Accent rule where the field ends.
    canvas.setFillColor(RED)
    canvas.rect(0, navy_bottom - 0.14 * cm, w, 0.14 * cm, stroke=0, fill=1)

    # Badge on a white disc, since its outer ring is navy.
    canvas.setFillColor(colors.white)
    canvas.circle(w / 2, h - 5.0 * cm, 1.72 * cm, stroke=0, fill=1)
    logo_h = 2.9 * cm
    logo_w = logo_h * LOGO_RATIO
    canvas.drawImage(LOGO, w / 2 - logo_w / 2, h - 5.0 * cm - logo_h / 2,
                     width=logo_w, height=logo_h, mask="auto")

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 19)
    canvas.drawCentredString(w / 2, h - 7.9 * cm, CHURCH.upper())
    canvas.setFont("Helvetica", 11.5)
    canvas.setFillColor(colors.HexColor("#9DB4D8"))
    canvas.drawCentredString(w / 2, h - 8.75 * cm, LOCATION.upper())

    canvas.setStrokeColor(RED)
    canvas.setLineWidth(2)
    canvas.line(w / 2 - 1.5 * cm, h - 9.9 * cm, w / 2 + 1.5 * cm, h - 9.9 * cm)

    # The title, letterspaced so it reads as a masthead rather than a line
    # of body text.
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 27)
    canvas.drawCentredString(w / 2, h - 11.9 * cm, "MONTHLY REPORT")
    canvas.setFont("Helvetica", 14)
    canvas.setFillColor(colors.HexColor("#9DB4D8"))
    canvas.drawCentredString(w / 2, h - 12.95 * cm, ctx["period_label"].upper())

    # ---- the month at a glance ----
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(w / 2, navy_bottom - 1.5 * cm, "THE MONTH AT A GLANCE")

    net = float(ctx["net_total"])
    figures = [
        ("Friday Worship, avg", str(ctx["fw_average"]), DEEP),
        ("Giving", f'BHD {float(ctx["income_total"]):,.0f}', GREEN),
        ("New newcomers", str(ctx["newcomers_registered"]), DEEP),
        ("Net position", f"BHD {net:,.0f}", GREEN if net >= 0 else RED),
    ]
    margin = 2.2 * cm
    total = w - margin * 2
    card_w = total / len(figures)
    top = navy_bottom - 2.1 * cm
    card_h = 2.0 * cm

    canvas.setFillColor(SKY2)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.8)
    canvas.rect(margin, top - card_h, total, card_h, stroke=1, fill=1)

    for i, (label, value, colour) in enumerate(figures):
        cx = margin + card_w * i + card_w / 2
        if i:
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(0.8)
            canvas.line(margin + card_w * i, top - card_h, margin + card_w * i, top)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(cx, top - 0.62 * cm, label.upper())
        canvas.setFillColor(colour)
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawCentredString(cx, top - 1.42 * cm, value)

    # ---- provenance and contact ----
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 9.5)
    canvas.drawCentredString(w / 2, 7.1 * cm,
                             "Attendance, giving, newcomers and progress against the church's goals")
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(w / 2, 6.1 * cm, f"Generated {ctx['generated_date']} by {ctx['generated_by_name']}")

    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.8)
    canvas.line(margin, 2.3 * cm, w - margin, 2.3 * cm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawCentredString(w / 2, 1.75 * cm, "dclm-bh.org  ·  +973 0000 0000")
    canvas.restoreState()


def draw_inner(canvas, doc, period, generated, generated_by):
    canvas.saveState()
    w, h = A4
    mark_h = 0.72 * cm
    mark_w = mark_h * LOGO_RATIO
    canvas.drawImage(LOGO, 2.2 * cm, h - 1.62 * cm, width=mark_w, height=mark_h, mask="auto")
    canvas.setFillColor(DEEP)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawString(2.2 * cm + mark_w + 0.22 * cm, h - 1.35 * cm, f"{CHURCH}, {LOCATION}")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawRightString(w - 2.2 * cm, h - 1.35 * cm, f"Monthly Report, {period}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.7)
    canvas.line(2.2 * cm, h - 1.6 * cm, w - 2.2 * cm, h - 1.6 * cm)

    canvas.line(2.2 * cm, 1.55 * cm, w - 2.2 * cm, 1.55 * cm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawString(2.2 * cm, 1.1 * cm, f"Generated {generated} by {generated_by}")
    canvas.drawRightString(w - 2.2 * cm, 1.1 * cm, str(canvas.getPageNumber() - 1))
    canvas.restoreState()


# ----------------------------------------------------------------- content

def build_report_pdf(ctx):
    """
    Draw the report from the context dict gather_report_data returns.

    Every section degrades on its own: a month with no testimonies still
    produces a valid report with that section saying so, rather than
    failing or leaving a confusing gap.
    """
    buffer = io.BytesIO()
    period = ctx["period_label"]
    generated = ctx["generated_date"]
    generated_by = ctx["generated_by_name"]

    def cover(canvas, doc):
        draw_cover(canvas, doc, ctx)

    def inner(canvas, doc):
        draw_inner(canvas, doc, period, generated, generated_by)

    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.2 * cm, bottomMargin=2.2 * cm,
        title=f"Monthly Report, {period}", author=CHURCH,
    )
    doc.addPageTemplates([
        PageTemplate(id="Cover",
                     frames=[Frame(2.2 * cm, 2.2 * cm, doc.width, doc.height, id="cover")],
                     onPage=cover),
        PageTemplate(id="Body",
                     frames=[Frame(2.2 * cm, 2.0 * cm, doc.width, doc.height - 0.6 * cm, id="body")],
                     onPage=inner),
    ])
    W = doc.width
    story = [Spacer(1, 1), NextPageTemplate("Body"), PageBreak()]

    money = lambda v: f"BHD {float(v):,.0f}"

    # ---- contents ----
    story.append(heading("Contents", W))
    toc = [
        ("1", "Executive Summary"), ("2", "Attendance"), ("3", "Finance"),
        ("4", "Newcomers and Follow-up"), ("5", "Testimonies"), ("6", "Challenges"),
        ("7", "Goals and Growth"), ("8", "Conclusion"),
    ]
    t = Table([[n, Paragraph(label, S["TocItem"])] for n, label in toc],
              colWidths=[1.1 * cm, W - 1.1 * cm])
    t.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (0, -1), BLUE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (0, -1), 11),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    # ---- 1. executive summary ----
    story.append(heading("1. Executive Summary", W))
    story.append(kpi_row([
        ("Friday Worship, average", str(ctx["fw_average"]), "#082C69"),
        ("Giving", money(ctx["income_total"]), "#1E9E64"),
        ("New newcomers", str(ctx["newcomers_registered"]), "#082C69"),
        ("Net position", money(ctx["net_total"]),
         "#1E9E64" if ctx["net_total"] >= 0 else "#D6202C"),
    ], W))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        f"Friday Worship attendance totalled <b>{ctx['fw_total']}</b> across "
        f"<b>{ctx['fw_session_count']}</b> recorded session(s) in {period}, an average of "
        f"<b>{ctx['fw_average']}</b> per service. Giving for the period totalled "
        f"<b>{money(ctx['income_total'])}</b> against <b>{money(ctx['expense_total'])}</b> "
        f"in expenses, leaving a net position of <b>{money(ctx['net_total'])}</b>. "
        f"<b>{ctx['newcomers_registered']}</b> newcomer(s) were registered, of whom "
        f"<b>{ctx['newcomers_contacted']}</b> have been contacted and "
        f"<b>{ctx['newcomers_visiting']}</b> have returned.", S["Body"]))

    # ---- 2. attendance ----
    story.append(heading("2. Attendance", W))
    if len(ctx["trend_values"]) >= 2:
        story.append(attendance_chart(W, ctx["trend_labels"], ctx["trend_values"]))
        story.append(Spacer(1, 6))
    if ctx["attendance_rows"]:
        # Meeting and location wrap as Paragraphs: a name like "Saturday
        # Workers Meeting" overflows a fixed cell and collides with the
        # column beside it.
        story.append(data_table(
            ["Date", "Meeting", "Location", "Men", "Women", "Youth", "Children", "Total"],
            [[str(r["date"]), Paragraph(r["meeting"], S["Cell"]),
              Paragraph(r["location"], S["Cell"]), str(r["men"]), str(r["women"]),
              str(r["youth"]), str(r["children"]), str(r["total"])]
             for r in ctx["attendance_rows"]],
            [2.3 * cm, 4.3 * cm, 2.1 * cm, 1.2 * cm, 1.4 * cm, 1.3 * cm, 1.6 * cm, 1.3 * cm],
            aligns={3: "CENTER", 4: "CENTER", 5: "CENTER", 6: "CENTER", 7: "CENTER"}))
    else:
        story.append(Paragraph("No filled sessions recorded this period.", S["Muted"]))

    # ---- 3. finance ----
    story.append(heading("3. Finance", W))
    story.append(kpi_row([
        ("Income", money(ctx["income_total"]), "#1E9E64"),
        ("Expenses", money(ctx["expense_total"]), "#D6202C"),
        ("Net", money(ctx["net_total"]),
         "#082C69" if ctx["net_total"] >= 0 else "#D6202C"),
    ], W))
    story.append(Spacer(1, 10))

    funds = ctx["by_fund"][:5]
    cats = ctx["by_category"][:5]
    if funds or cats:
        left = (fund_pie(W, [float(f["total"]) for f in funds], [f["fund"] for f in funds])
                if funds else Spacer(1, 1))
        right = (expense_bars(W, [float(x["total"]) for x in cats], [x["category"] for x in cats])
                 if cats else Spacer(1, 1))
        charts = Table([[left, right]], colWidths=[W / 2, W / 2])
        charts.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(charts)
        cap = Table([[Paragraph("Giving by fund" if funds else "", S["Muted"]),
                      Paragraph("Expenses by category" if cats else "", S["Muted"])]],
                    colWidths=[W / 2, W / 2])
        cap.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(cap)
        story.append(Spacer(1, 10))

    if ctx["by_fund"]:
        total_given = sum(float(f["total"]) for f in ctx["by_fund"]) or 1
        story.append(data_table(
            ["Fund", "Amount (BHD)", "Share"],
            [[f["fund"], f"{float(f['total']):,.3f}",
              f"{float(f['total']) / total_given * 100:.1f}%"] for f in ctx["by_fund"]],
            [W - 6.6 * cm, 3.6 * cm, 3.0 * cm], aligns={1: "RIGHT", 2: "RIGHT"}))
    else:
        story.append(Paragraph("No giving recorded this period.", S["Muted"]))

    # ---- 4. newcomers ----
    story.append(heading("4. Newcomers and Follow-up", W))
    story.append(kpi_row([
        ("Registered", str(ctx["newcomers_registered"]), "#082C69"),
        ("Contacted", str(ctx["newcomers_contacted"]), "#082C69"),
        ("Returned", str(ctx["newcomers_visiting"]), "#1E9E64"),
        ("Open follow-ups", str(ctx["open_followups"]),
         "#C9891A" if ctx["open_followups"] else "#082C69"),
    ], W))
    story.append(Spacer(1, 10))
    if ctx["newcomer_rows"]:
        story.append(data_table(
            ["Source", "Registered", "Contacted", "Returned"],
            [[r["source"], str(r["registered"]), str(r["contacted"]), str(r["returned"])]
             for r in ctx["newcomer_rows"]],
            [W - 9.6 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm],
            aligns={1: "CENTER", 2: "CENTER", 3: "CENTER"}))
    else:
        story.append(Paragraph("No newcomers registered this period.", S["Muted"]))

    # ---- 5. testimonies ----
    story.append(heading("5. Testimonies", W))
    if ctx["testimonies"]:
        for t_ in ctx["testimonies"]:
            story.append(Paragraph(f'<i>"{t_["text"]}"</i>', S["Quote"]))
            story.append(Paragraph(f'{t_["who"]}, {t_["service"]}', S["QuoteBy"]))
    else:
        story.append(Paragraph("None recorded this period.", S["Muted"]))

    # ---- 6. challenges ----
    story.append(heading("6. Challenges", W))
    if ctx["notes"]:
        story.append(data_table(
            ["Department", "Raised"],
            [[n["department"], Paragraph(n["challenges"], S["Body"])] for n in ctx["notes"]],
            [4.2 * cm, W - 4.2 * cm]))
    else:
        story.append(Paragraph("None recorded this period.", S["Muted"]))

    # ---- 7. goals ----
    story.append(heading("7. Goals and Growth", W))
    if ctx["goals"]:
        rows = [[Paragraph(g["name"], S["Body"]), g["horizon"],
                 f"{g['current']}{g['unit']} / {g['target']}{g['unit']}",
                 goal_bar(2.8 * cm, g["pct"]), f"{g['pct']}%"] for g in ctx["goals"]]
        t = Table([["Goal", "Horizon", "Progress", "", "%"]] + rows,
                  colWidths=[W - 11.4 * cm, 2.4 * cm, 2.6 * cm, 3.2 * cm, 1.2 * cm],
                  repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SKY),
            ("TEXTCOLOR", (0, 0), (-1, 0), DEEP),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("GRID", (0, 0), (-1, -1), 0.6, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SKY2]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (4, 0), (4, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No goals set.", S["Muted"]))

    # ---- 8. conclusion ----
    story.append(heading("8. Conclusion", W))
    if ctx.get("other_additions"):
        story.append(Paragraph(ctx["other_additions"], S["Body"]))
        story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Compiled from live records in the DCLM Bahrain Church Management System "
        f"as of {generated}.", S["Muted"]))

    doc.build(story)
    return buffer.getvalue()
