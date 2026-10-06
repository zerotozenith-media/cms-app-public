"""
The monthly figures as a formatted spreadsheet.

The PDF is the report. This exists for whoever at Zonal combines several
locations and would otherwise retype the numbers out of a document.

Formatted rather than dumped: a CSV opens as a grey wall of text with no
column widths, no number formats and no way to tell a heading from a
total. Someone receiving that has to reformat it before they can read
it, which defeats the point of sending it.
"""
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY = "FF082C69"
BLUE = "FF0B3C91"
SKY = "FFEAF1FC"
BAND = "FFF4F8FE"
LINE = "FFE4E9F1"
INK = "FF0F1B2E"
MUTED = "FF5A667C"
GREEN = "FF14663F"

FONT = "Arial"
_thin = Side(style="thin", color=LINE)
BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)

MONEY = '#,##0.000'


def _title(ws, row, text, span, size=13):
    cell = ws.cell(row=row, column=2, value=text)
    cell.font = Font(name=FONT, size=size, bold=True, color=NAVY)
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=span)
    return row + 1


def _section(ws, row, text, span):
    cell = ws.cell(row=row, column=2, value=text)
    cell.font = Font(name=FONT, size=10.5, bold=True, color="FFFFFFFF")
    for col in range(2, span + 1):
        c = ws.cell(row=row, column=col)
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.border = BORDER
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=span)
    ws.row_dimensions[row].height = 20
    return row + 1


def _header_row(ws, row, headers, start_col=2):
    for i, h in enumerate(headers):
        c = ws.cell(row=row, column=start_col + i, value=h)
        c.font = Font(name=FONT, size=9.5, bold=True, color=NAVY)
        c.fill = PatternFill("solid", fgColor=SKY)
        c.border = BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 28
    return row + 1


def _data_row(ws, row, values, start_col=2, money_cols=(), bold=False, band=False):
    for i, v in enumerate(values):
        c = ws.cell(row=row, column=start_col + i, value=v)
        c.font = Font(name=FONT, size=9.5, bold=bold, color=INK)
        c.border = BORDER
        if band:
            c.fill = PatternFill("solid", fgColor=BAND)
        if i in money_cols:
            c.number_format = MONEY
            c.alignment = Alignment(horizontal="right")
        elif isinstance(v, (int, float)):
            c.alignment = Alignment(horizontal="center")
        else:
            c.alignment = Alignment(horizontal="left", vertical="center")
    return row + 1


def _page_setup(ws, landscape=True):
    """
    Make the sheet print as one readable page across.

    Without this a wide sheet spills its last columns onto a second page
    on their own, which looks like a mistake to whoever opens it and is
    useless if they print it.
    """
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5


def build_spreadsheet(ctx):
    """Returns the workbook as bytes, ready to send."""
    wb = Workbook()

    # ---------------------------------------------------------- attendance
    ws = wb.active
    ws.title = "Attendance"
    ws.sheet_view.showGridLines = False
    widths = {"A": 3, "B": 13, "C": 30, "D": 18, "E": 8, "F": 8, "G": 8,
              "H": 9, "I": 9, "J": 9, "K": 11, "L": 11, "M": 11, "N": 9}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    span = 14
    r = 2
    r = _title(ws, r, f"{ctx['church_name']}, {ctx['location_name']}", span)
    sub = ws.cell(row=r, column=2, value=f"Monthly figures, {ctx['period_label']}")
    sub.font = Font(name=FONT, size=10, color=MUTED)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=span)
    r += 2

    r = _section(ws, r, "SERVICES", span)
    r = _header_row(ws, r, [
        "Date", "Meeting", "Led by", "Men", "Women", "Youth",
        "Children", "In person", "Online", "New comers", "New converts", "Total", "Offering",
    ])
    first_data = r
    for i, a in enumerate(ctx["attendance_rows"]):
        in_person = a["total"] - a.get("online", 0)
        r = _data_row(ws, r, [
            str(a["date"]), a["meeting"], a.get("led_by", ""),
            a["men"], a["women"], a["youth"], a["children"],
            in_person, a.get("online", 0),
            a.get("new_comers", 0), a.get("new_converts", 0), a["total"],
            float(a.get("offering", 0)),
        ], money_cols=(12,), band=(i % 2 == 1))

    if r > first_data:
        # A formula, not a number: whoever receives this can add a row and
        # the total follows, which a pasted figure would not.
        r = _data_row(ws, r, [
            "", "Total", "", "", "", "", "",
            f"=SUM(I{first_data}:I{r-1})", f"=SUM(J{first_data}:J{r-1})",
            f"=SUM(K{first_data}:K{r-1})", f"=SUM(L{first_data}:L{r-1})",
            f"=SUM(M{first_data}:M{r-1})", f"=SUM(N{first_data}:N{r-1})",
        ], money_cols=(12,), bold=True)
        for col in range(2, span + 1):
            ws.cell(row=r - 1, column=col).fill = PatternFill("solid", fgColor=SKY)
    ws.freeze_panes = ws.cell(row=first_data, column=2)
    r += 1

    r = _section(ws, r, "SUMMARY", span)
    for label, value in [
        ("Average attendance", ctx.get("attendance_average", 0)),
        ("Highest attendance", ctx.get("attendance_highest", 0)),
        ("Lowest attendance", ctx.get("attendance_lowest", 0)),
        ("New comers", ctx.get("new_comers_total", 0)),
        ("New converts", ctx.get("new_converts_total", 0)),
    ]:
        c = ws.cell(row=r, column=2, value=label)
        c.font = Font(name=FONT, size=9.5, color=INK)
        c.border = BORDER
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        ws.cell(row=r, column=3).border = BORDER
        v = ws.cell(row=r, column=4, value=value)
        v.font = Font(name=FONT, size=9.5, bold=True, color=NAVY)
        v.border = BORDER
        v.alignment = Alignment(horizontal="center")
        r += 1

    # ---------------------------------------------------------- finance
    fs = wb.create_sheet("Finance")
    fs.sheet_view.showGridLines = False
    for col, w in {"A": 3, "B": 30, "C": 16, "D": 14, "E": 26}.items():
        fs.column_dimensions[col].width = w

    r = 2
    r = _title(fs, r, "Income and expenditure", 5)
    sub = fs.cell(row=r, column=2, value=ctx["period_label"])
    sub.font = Font(name=FONT, size=10, color=MUTED)
    r += 2

    r = _section(fs, r, "GIVING BY FUND", 5)
    r = _header_row(fs, r, ["Fund", "Amount", "Share", "Remitted to"])
    start = r
    total_given = sum(float(f["total"]) for f in ctx["by_fund"]) or 1
    for i, f in enumerate(ctx["by_fund"]):
        amt = float(f["total"])
        r = _data_row(fs, r, [
            f["fund"], amt, amt / total_given, f.get("remitted_to", ""),
        ], money_cols=(1,), band=(i % 2 == 1))
        fs.cell(row=r - 1, column=4).number_format = '0.0%'
        fs.cell(row=r - 1, column=4).alignment = Alignment(horizontal="right")
    if r > start:
        r = _data_row(fs, r, ["Total income", f"=SUM(C{start}:C{r-1})", "", ""],
                      money_cols=(1,), bold=True)
        for col in range(2, 6):
            fs.cell(row=r - 1, column=col).fill = PatternFill("solid", fgColor=SKY)
    r += 1

    r = _section(fs, r, "EXPENSES BY CATEGORY", 5)
    r = _header_row(fs, r, ["Category", "Amount", "", ""])
    estart = r
    for i, x in enumerate(ctx["by_category"]):
        r = _data_row(fs, r, [x["category"], float(x["total"]), "", ""],
                      money_cols=(1,), band=(i % 2 == 1))
    if r > estart:
        r = _data_row(fs, r, ["Total expenses", f"=SUM(C{estart}:C{r-1})", "", ""],
                      money_cols=(1,), bold=True)
        for col in range(2, 6):
            fs.cell(row=r - 1, column=col).fill = PatternFill("solid", fgColor=SKY)
    r += 1

    net = fs.cell(row=r, column=2, value="Net position")
    net.font = Font(name=FONT, size=11, bold=True, color=NAVY)
    net.border = BORDER
    v = fs.cell(row=r, column=3, value=float(ctx["net_total"]))
    v.font = Font(name=FONT, size=11, bold=True,
                  color=GREEN if float(ctx["net_total"]) >= 0 else "FF9B1C26")
    v.number_format = MONEY
    v.border = BORDER
    v.alignment = Alignment(horizontal="right")

    # ---------------------------------------------------------- fellowships
    hs = wb.create_sheet("Fellowships")
    hs.sheet_view.showGridLines = False
    for col, w in {"A": 3, "B": 13, "C": 20, "D": 20, "E": 12, "F": 9,
                   "G": 9, "H": 9, "I": 11, "J": 11, "K": 9, "L": 13}.items():
        hs.column_dimensions[col].width = w

    r = 2
    r = _title(hs, r, "House caring fellowships", 12)
    sub = hs.cell(row=r, column=2, value=ctx["period_label"])
    sub.font = Font(name=FONT, size=10, color=MUTED)
    r += 2
    r = _header_row(hs, r, ["Date", "Fellowship", "Led by", "Lesson", "Men", "Women",
                            "Youth", "Children", "New comers", "New converts",
                            "Total", "Offering"])
    hstart = r
    for i, m in enumerate(ctx.get("fellowship_rows", [])):
        r = _data_row(hs, r, [
            str(m["date"]), m["fellowship"], m["led_by"], m["lesson"],
            m["men"], m["women"], m["youth"], m["children"],
            m["new_comers"], m["new_converts"], m["total"], float(m["offering"]),
        ], money_cols=(11,), band=(i % 2 == 1))
    if r > hstart:
        r = _data_row(hs, r, ["", "Total", "", "", "", "", "", "",
                              f"=SUM(J{hstart}:J{r-1})", f"=SUM(K{hstart}:K{r-1})",
                              f"=SUM(L{hstart}:L{r-1})", f"=SUM(M{hstart}:M{r-1})"],
                      money_cols=(11,), bold=True)
        for col in range(2, 14):
            hs.cell(row=r - 1, column=col).fill = PatternFill("solid", fgColor=SKY)
    else:
        note = hs.cell(row=r, column=2, value="No fellowship meetings recorded this period.")
        note.font = Font(name=FONT, size=9.5, italic=True, color=MUTED)
    hs.freeze_panes = hs.cell(row=hstart, column=2)

    sheets = [ws, fs, hs]
    # Issue 3: the all-locations report gets each location side by side,
    # with the same figures as the PDF's By location page.
    if ctx.get("by_location"):
        bl = ctx["by_location"]
        ls = wb.create_sheet("By location", 0)
        ls.sheet_view.showGridLines = False
        for col, w in {"A": 3, "B": 18, "C": 22, "D": 16, "E": 16, "F": 14, "G": 13}.items():
            ls.column_dimensions[col].width = w
        r = 2
        r = _title(ls, r, "By location", 6)
        sub = ls.cell(row=r, column=2, value=ctx["period_label"])
        sub.font = Font(name=FONT, size=10, color=MUTED)
        r += 2
        r = _section(ls, r, "EACH LOCATION FOR THE MONTH", 6)
        r = _header_row(ls, r, ["Location", "Friday Worship average", "Giving (BHD)", "Expenses (BHD)", "Net (BHD)", "Newcomers"])
        first = r
        for i, row in enumerate(bl["rows"]):
            _data_row(ls, r, [row["location"], row["fw_average"] if row["fw_services"] else "None recorded", float(row["giving"]),
                              float(row["expenses"]), float(row["net"]), row["newcomers"]], money_cols=(4, 5, 6), band=i % 2 == 1)
            r += 1
        last = r - 1
        _data_row(ls, r, ["Total", "", f"=SUM(D{first}:D{last})", f"=SUM(E{first}:E{last})", f"=SUM(F{first}:F{last})", f"=SUM(G{first}:G{last})"],
                  money_cols=(4, 5, 6), bold=True)
        r += 3
        r = _section(ls, r, "FRIDAY WORSHIP AVERAGE BY MONTH", 6)
        r = _header_row(ls, r, ["Location"] + bl["months"])
        for i, row in enumerate(bl["rows"]):
            _data_row(ls, r, [row["location"]] + row["trend"], band=i % 2 == 1)
            r += 1
        sheets.insert(0, ls)
        _page_setup(ls, landscape=False)

    _page_setup(ws, landscape=True)
    _page_setup(fs, landscape=False)
    _page_setup(hs, landscape=True)
    for sheet in sheets:
        sheet.print_area = sheet.dimensions

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
