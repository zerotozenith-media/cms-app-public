"""
The overseer report: the church's own report for any run of months. One
month makes the internal monthly report, three make the quarterly report
for the overseer.

Tables, charts and the sentences that state figures are filled in from
the system. Summary, challenges, worker training and the conclusion are
written by whoever generates it.
"""
import datetime
import io

from reportlab.platypus import CondPageBreak, PageBreak, Spacer

from . import house as H
from .church_data import ZERO, day, gather, period_words, whole

WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]


def _count(n, one, many):
    return f"{n} {one if n == 1 else many}"


def _join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _long_date(d):
    return f"{d.day} {d:%B %Y}"


def scope_name(ctx):
    loc = ctx["scope"].location
    return f"{H.SHORT} ({loc.name})" if loc else H.SHORT


def build(ctx, texts, generated_by=None):
    """ctx from church_data.gather; texts: summary, challenges, training,
    conclusion."""
    months = ctx["months"]
    many = len(months) > 1
    noun = ctx["noun"]
    kind = ctx["kind_word"]
    title = f"{kind} Report" if kind else "Report"
    running = f"{title}, {ctx['label']}"
    n = H.Numbers()
    p = ctx["people"]
    net = ctx["net"]
    fridays = ctx["fridays"]
    when = _long_date(ctx["taken_on"])

    def cover(c, d):
        tiles = [(H.people(ctx["friday_average"]), "Friday Worship average"),
                 (H.money(ctx["income"]), "Giving (BHD)"),
                 (H.money(abs(net)), "Net surplus (BHD)" if net >= 0 else "Net shortfall (BHD)"),
                 (H.people(p["members"]), "Consistent members"),
                 (H.people(p["congregation"]), "Total congregation")]
        H.draw_cover(c, title, ctx["label"], when, tiles, f"The {noun} at a glance")

    # Up to four months fit with full month names. Longer runs use short
    # names and are split into tables of six months, so nothing is squeezed.
    wide = len(months) > 4
    chunks = [months[i:i + 6] for i in range(0, len(months), 6)]

    def head(mf):
        return mf["short"][:3] if wide else mf["short"]

    def part(title, ch):
        if len(chunks) == 1:
            return title
        return f"{title}, {period_words([(m['year'], m['month']) for m in ch])[2]}"

    story = H.start_inner()
    sec = [0]

    def section(name, *first):
        sec[0] += 1
        return [CondPageBreak(4 * H.cm), H.keep_with_next(H.heading(f"{sec[0]}. {name}"), *first)]

    # ------------------------------------------------ at a glance
    if fridays:
        opening = (f"{scope_name(ctx)} held {_count(len(fridays), 'Friday Worship Service', 'Friday Worship Services')} "
                   f"in the {noun}, from {_long_date(fridays[0].date)[:-5]} to {_long_date(fridays[-1].date)[:-5]}.")
    else:
        opening = f"No Friday Worship Service was recorded for {scope_name(ctx)} in the {noun}."
    if ctx["scope"].location:
        opening += f" The figures cover {ctx['scope'].location.name} only."
    story += section(f"The {noun.title()} at a Glance", H.para(H.safe(opening)))
    rows = [["Friday Worship Service, average attendance",
             f"{H.people(ctx['friday_average'])} ({_count(len(fridays), 'service', 'services')})"],
            ["Total giving (BHD)", H.money(ctx["income"])],
            ["Total expenses (BHD)", H.money(ctx["expenses"])],
            ["Net surplus (BHD)" if net >= 0 else "Net shortfall (BHD)", H.money(abs(net))],
            ["Consistent members", H.people(p["members"])],
            ["Newcomers not yet consistent", H.people(p["newcomers"])],
            ["Total congregation", H.people(p["congregation"])]]
    if p["contacts"] is not None:
        rows.append(["Contacts yet to visit", H.people(p["contacts"])])
    rows.append(["Workers", f"{p['workers']}, with {p['in_training']} in training" if p["in_training"] else str(p["workers"])])
    rows.append(["Testimonies", str(len(ctx["testimonies"]))])
    story += H.captioned_table(n.table(f"Headline figures, {ctx['label']}"), ["Measure", "Figure"], rows, [0.55, 0.45])

    # ------------------------------------------------ summary
    if texts.get("summary", "").strip():
        blocks = H.text_block(texts["summary"])
        story += section("Summary", blocks[0]) + blocks[1:]

    # ------------------------------------------------ attendance
    if fridays:
        line = f"Friday Worship Service averaged {ctx['friday_average']} a service over the {noun}."
        if many:
            parts = []
            for mf in months:
                if mf["fridays"]:
                    parts.append(f"{mf['short']} {whole(mf['friday_total'] / len(mf['fridays']))}")
            line += f" By month: {_join(parts)}."
    else:
        line = f"No Friday Worship Service was recorded in the {noun}."
    story += section("Attendance", H.para(H.safe(line)))
    if fridays:
        adults = lambda s: s.men + s.women + s.online_men + s.online_women
        youth = lambda s: s.youth_boys + s.youth_girls + s.online_youth_boys + s.online_youth_girls
        kids = lambda s: s.children_boys + s.children_girls + s.online_children_boys + s.online_children_girls
        if len(fridays) <= 14:
            cats = [day(s.date) for s in fridays]
            series = [("Adults", H.PALETTE[0], [adults(s) for s in fridays]),
                      ("Youth", H.PALETTE[2], [youth(s) for s in fridays]),
                      ("Children", H.PALETTE[3], [kids(s) for s in fridays])]
            totals = [f"Total {s.total}" for s in fridays]
            fig_title = "Friday Worship Service attendance by age group"
        else:
            use = [mf for mf in months if mf["fridays"]]
            cats = [mf["short"][:3] for mf in use]
            avg = lambda mf, f: whole(sum(f(s) for s in mf["fridays"]) / len(mf["fridays"]))
            series = [("Adults", H.PALETTE[0], [avg(mf, adults) for mf in use]),
                      ("Youth", H.PALETTE[2], [avg(mf, youth) for mf in use]),
                      ("Children", H.PALETTE[3], [avg(mf, kids) for mf in use])]
            totals = [f"Total {whole(mf['friday_total'] / len(mf['fridays']))}" for mf in use]
            fig_title = "Friday Worship Service average attendance by age group and month"
        story.append(H.captioned_figure(n.figure(fig_title), H.grouped_bars(cats, series, totals=totals)))
        a, y, k = (sum(f(s) for s in fridays) for f in (adults, youth, kids))
        tot = a + y + k
        shares = sorted([("adults", a), ("youth", y), ("children", k)], key=lambda x: -x[1])
        story.append(H.para(H.safe(
            f"Over the {noun}, " + _join(f"{name} {'made up ' if i == 0 else ''}{H.pct(v, tot)}%" for i, (name, v) in enumerate(shares))
            + " of Friday attendance.")))
        dn = H.donut([("Adults", a, H.PALETTE[0]), ("Youth", y, H.PALETTE[2]), ("Children", k, H.PALETTE[3])],
                     H.people(tot), "Friday attendances", width=H.WIDTH, size=125)
        story.append(H.captioned_figure(n.figure(f"Friday Worship Service attendance by group, {ctx['label']}"), dn))

    meetings = ctx["meetings"]
    if meetings:
        if many:
            for ch in chunks:
                header = ["Meeting"] + [head(mf) for mf in ch]
                rows = []
                for name, per in meetings.items():
                    row, first = [name], not wide
                    for mf in ch:
                        v = per.get((mf["year"], mf["month"]))
                        if v:
                            row.append(f"{v[0]} ({_count(v[1], 'service', 'services')})" if first else f"{v[0]} ({v[1]})")
                            first = False
                        else:
                            row.append("None")
                    rows.append(row)
                w0 = 0.40 if not wide else 0.34
                name_ = "Average attendance by meeting and month" + (", with the number of services" if wide else "")
                story += H.captioned_table(n.table(part(name_, ch)), header, rows,
                                           [w0] + [(1 - w0) / len(ch)] * len(ch))
            first, last = months[0], months[-1]
            changes = []
            for name, per in meetings.items():
                a1, b1 = per.get((first["year"], first["month"])), per.get((last["year"], last["month"]))
                if a1 and b1 and a1[0]:
                    changes.append((name, whole((b1[0] - a1[0]) / a1[0] * 100)))
            if changes:
                grew = [c for c, v in changes if v > 2]
                fell = [c for c, v in changes if v < -2]
                steady = [c for c, v in changes if -2 <= v <= 2]
                bits = []
                if grew:
                    bits.append(f"{_join(grew)} grew")
                if fell:
                    bits.append(f"{_join(fell)} fell")
                if steady:
                    bits.append(f"{_join(steady)} held steady")
                said = bits[0] + (", while " + _join(bits[1:]) if len(bits) > 1 else "")
                story.append(H.para(H.safe(f"From {first['short']} to {last['short']}, {said}.")))
                changes.sort(key=lambda x: -x[1])
                story.append(H.captioned_figure(
                    n.figure(f"Change in average attendance from {first['short']} to {last['short']}"),
                    H.change_bars(changes)))
        else:
            rows = []
            for name in meetings:
                totals = [s.total for s in ctx["sessions"] if s.meeting_type.name == name]
                rows.append([name, str(len(totals)), str(whole(sum(totals) / len(totals))), str(max(totals)), str(min(totals))])
            story += H.captioned_table(n.table("Attendance by meeting"),
                                       ["Meeting", "Services", "Average", "Highest", "Lowest"], rows,
                                       [0.46, 0.13, 0.13, 0.14, 0.14])
    if ctx["programmes"]:
        rows = [[pr["label"], pr["dates"], str(pr["days"]), str(pr["average"])] for pr in ctx["programmes"]]
        story += H.captioned_table(n.table("Special programmes"), ["Programme", "Dates", "Days", "Average attendance"],
                                   rows, [0.42, 0.26, 0.10, 0.22])

    # ------------------------------------------------ finance
    word = "surplus" if net >= 0 else "shortfall"
    story += section("Finance", H.para(H.safe(
        f"Giving of BHD {H.money(ctx['income'])} against expenses of BHD {H.money(ctx['expenses'])} "
        f"left a {word} of BHD {H.money(abs(net))} for the {noun}.")))
    funds, cats = ctx["funds"], ctx["categories"]

    def by_month(names, key, total_label, title):
        if not names:
            return [H.para(H.safe(f"No {'giving' if key == 'by_fund' else 'expenses'} recorded in the {noun}."))]
        if many:
            out = []
            whole_key = "income" if key == "by_fund" else "expenses"
            for ci, ch in enumerate(chunks):
                last = ci == len(chunks) - 1
                header = ["Fund" if key == "by_fund" else "Category"] + [head(mf) for mf in ch] + (["Total"] if last else [])
                rows = [[nm] + [H.money(mf[key].get(nm, ZERO)) for mf in ch]
                        + ([H.money(sum((mf[key].get(nm, ZERO) for mf in months), ZERO))] if last else []) for nm in names]
                rows.append([total_label] + [H.money(mf[whole_key]) for mf in ch] + ([H.money(ctx[whole_key])] if last else []))
                cols = len(header) - 1
                w0 = 0.30 if not wide else 0.22
                out += H.captioned_table(n.table(part(title, ch)), header, rows, [w0] + [(1 - w0) / cols] * cols, totals={len(rows) - 1})
            return out
        total = ctx["income" if key == "by_fund" else "expenses"]
        rows = [[nm, H.money(months[0][key].get(nm, ZERO)), str(H.pct(months[0][key].get(nm, ZERO), total))] for nm in names]
        rows.append([total_label, H.money(total), "100"])
        return H.captioned_table(n.table(title), ["Fund" if key == "by_fund" else "Category", "Amount (BHD)", "Share (%)"],
                                 rows, [0.5, 0.25, 0.25], totals={len(rows) - 1})

    story += by_month(funds, "by_fund", "Total giving", "Giving by fund" + (" and month" if many else "") + " (BHD)")
    story.append(H.captioned_figure(n.figure("Giving and expenses by month" if many else f"Giving and expenses, {ctx['label']}"), H.grouped_bars(
        [mf["short"] for mf in months],
        [("Giving", H.PALETTE[1], [mf["income"] for mf in months]),
         ("Expenses", H.PALETTE[3], [mf["expenses"] for mf in months])],
        fmt=H.money, sublabels=[f"Net {H.money(mf['net'])}" for mf in months], height=185)))
    rings = []
    if funds:
        rings.append(H.donut([(f, sum((mf["by_fund"].get(f, ZERO) for mf in months), ZERO), H.PALETTE[i % 8]) for i, f in enumerate(funds)],
                             H.money(ctx["income"]), "BHD giving", fmt=H.money))
    if cats:
        rings.append(H.donut([(c, sum((mf["by_category"].get(c, ZERO) for mf in months), ZERO), H.PALETTE[i % 8]) for i, c in enumerate(cats)],
                             H.money(ctx["expenses"]), "BHD expenses", fmt=H.money))
    if rings:
        both = funds and cats
        fig = H.side_by_side(*rings) if len(rings) == 2 else rings[0]
        story.append(H.captioned_figure(n.figure(
            ("Giving by fund and expenses by category" if both else ("Giving by fund" if funds else "Expenses by category"))
            + f", {ctx['label']}"), fig))
    story += by_month(cats, "by_category", "Total expenses", "Expenses by category" + (" and month" if many else "") + " (BHD)")

    # Money held, from the month-end balances approved and closed (Kay, 30 October 2026).
    bal = ctx.get("balances") or []
    if bal:
        all_locs = ctx["scope"].location is None
        rows = [[(f"{b['location']}, " if all_locs else "") + f"{b['month']:%B %Y}", H.money(b["opening"]),
                 H.money(b["giving"]), H.money(b["expenses"]), H.money(b["remittance"]), H.money(b["closing"]),
                 H.money(b["difference"])] for b in bal]
        story += H.captioned_table(n.table("Money held at each month end (BHD)"),
                                   ["Month", "Opening", "Giving", "Expenses", "Remittance sent", "Closing", "Difference"],
                                   rows, [0.22, 0.13, 0.13, 0.13, 0.15, 0.12, 0.12])
        notes = [b for b in bal if b["difference"] and b["note"]]
        for b in notes:
            story.append(H.para(H.safe(f"{b['month']:%B %Y} difference of BHD {H.money(abs(b['difference']))}: "
                                       f"{b['note']}")))

    offering = next((f for f in funds if f.strip().lower() == "offering"), None)

    def ratios(mf_list):
        out = []
        ft = sum(m["friday_total"] for m in mf_list)
        fs = sum(len(m["fridays"]) for m in mf_list)
        inc = sum((m["income"] for m in mf_list), ZERO)
        exp = sum((m["expenses"] for m in mf_list), ZERO)
        out.append((f"{ft} ({fs})" if wide else f"{ft} ({_count(fs, 'service', 'services')})") if fs else "None")
        out.append(H.money(inc / ft) if ft else "None")
        if offering:
            off = sum((m["by_fund"].get(offering, ZERO) for m in mf_list), ZERO)
            out.append(H.money(off / fs) if fs else "None")
        out.append(str(H.pct(exp, inc)) if inc else "None")
        out.append(str(sum(m["newcomer_visits"] for m in mf_list)))
        return out

    labels = ["Friday Worship attendances", "Giving per Friday attendance (BHD)"]
    if offering:
        labels.append("Offering per Friday service (BHD)")
    labels += ["Expenses as a share of giving (%)", "Newcomer visits at services"]
    if many:
        for ch in chunks:
            cols = [ratios([mf]) for mf in ch]
            rows = [[lab] + [c[i] for c in cols] for i, lab in enumerate(labels)]
            w0 = 0.40 if not wide else 0.34
            name_ = "Key ratios by month" + (", with Friday services in brackets" if wide else "")
            story += H.captioned_table(n.table(part(name_, ch)), ["Measure"] + [head(mf) for mf in ch], rows,
                                       [w0] + [(1 - w0) / len(ch)] * len(ch))
    else:
        vals = ratios(months)
        story += H.captioned_table(n.table("Key ratios"), ["Measure", "Figure"],
                                   [[lab, vals[i]] for i, lab in enumerate(labels)], [0.6, 0.4])

    # ------------------------------------------------ membership
    story += section("Membership and Outreach", H.para(H.safe(
        f"Membership is not kept month by month, so these figures are as they stood on {when}.")))
    ring = [("Consistent members", p["members"], H.PALETTE[0]), ("Newcomers not yet consistent", p["newcomers"], H.PALETTE[2])]
    if p["contacts"] is not None:
        ring.append(("Contacts yet to visit", p["contacts"], H.PALETTE[3]))
    if sum(v for _, v, _ in ring):
        story.append(H.captioned_figure(n.figure(f"People in reach and the congregation, {when}"),
                                        H.donut(ring, H.people(sum(v for _, v, _ in ring)), "people in reach", width=H.WIDTH, size=125)))
    visits = str(ctx["newcomer_visits"])
    if many:
        visits += " (" + _join(f"{mf['newcomer_visits']} in {mf['short']}" for mf in months) + ")"
    rows = [["Consistent members", H.people(p["members"])], ["Newcomers not yet consistent", H.people(p["newcomers"])],
            ["Total congregation", H.people(p["congregation"])], ["Households", H.people(p["households"])],
            ["Newcomer visits at services", visits]]
    if p["contacts"] is not None:
        rows.append(["Contacts yet to visit", H.people(p["contacts"])])
    rows += [["Workers", H.people(p["workers"])], ["Workers in training", H.people(p["in_training"])]]
    story += H.captioned_table(n.table(f"Membership and workers, {when}"), ["Measure", "Figure"], rows, [0.55, 0.45])

    # ------------------------------------------------ testimonies
    t = ctx["testimonies"]
    if t:
        lead = f"{WORDS[len(t)] if len(t) <= 10 else len(t)} {'testimony was' if len(t) == 1 else 'testimonies were'} shared:"
        story += section("Testimonies", H.para(H.safe(lead)))
        story.append(H.bullet_list([f"{x['date']:%B %Y}: {x['text']}" for x in t]))
    else:
        story += section("Testimonies", H.para(H.safe(f"No testimonies were recorded in the {noun}.")))

    # ------------------------------------------------ challenges
    if texts.get("challenges", "").strip():
        blocks = H.text_block(texts["challenges"])
        story += section("Challenges and Responses", blocks[0]) + blocks[1:]

    # ------------------------------------------------ goals
    goals = ctx["goals"]
    training = texts.get("training", "").strip()
    if goals or training:
        intro = H.para(H.safe("The goals below are taken from the Goals page." if goals else "Worker training and the assumptions behind the plans."))
        story += section("Goals and Plans", intro)
        for horizon, rows in goals.items():
            story += H.captioned_table(n.table(f"{horizon} goals" if horizon.endswith("term") else f"{horizon} goals"),
                                       ["Goal", "Target date", "Measured by"],
                                       [[g["name"], g["target_date"] or "Not set", g["measured_by"] or "Not set"] for g in rows],
                                       [0.5, 0.24, 0.26])
        if training:
            story += [Spacer(1, 4)] + H.text_block(training)

    # ------------------------------------------------ conclusion
    if texts.get("conclusion", "").strip():
        blocks = H.text_block(texts["conclusion"])
        story += section("Conclusion", blocks[0]) + blocks[1:]

    # ------------------------------------------------ appendix
    story += [PageBreak(), H.keep_with_next(H.heading("Appendix: Each Month in Detail"), H.para(H.safe(
        "Every recorded meeting and each month's finances.")))]
    for mf in months:
        rows = [[day(s.date), _name(s), str(s.total), str(s.new_comers)] for s in mf["sessions"]]
        if rows:
            story += H.captioned_table(n.table(f"{mf['name']}: services and finances"),
                                       ["Date", "Meeting", "Attendance", "Newcomers"], rows, [0.14, 0.56, 0.15, 0.15])
        else:
            story.append(H.para(H.safe(f"{mf['name']}: no meetings were recorded.")))
        fund_bits = [f"{f.lower() if f.lower() in ('tithe', 'offering') else f} BHD {H.money(v)}" for f, v in
                     sorted(mf["by_fund"].items(), key=lambda x: -x[1])]
        exp_bits = [f"{c} {H.money(v)}" for c, v in mf["by_category"].items()]
        line = "Finances: " + (", ".join(fund_bits) + ", " if fund_bits else "") + f"total giving BHD {H.money(mf['income'])}. "
        line += f"Expenses BHD {H.money(mf['expenses'])}" + (f" ({', '.join(exp_bits)})" if exp_bits else "") + ". "
        line += f"Net BHD {H.money(mf['net'])}."
        story.append(H.para(H.safe(line)))

    buf = io.BytesIO()
    doc = H.make_doc(buf, f"{H.SHORT} {running}", running, cover)
    doc.build(story)
    return buf.getvalue(), f"{H.SHORT} {running}"


def _name(s):
    return f"{s.meeting_type.name} ({s.fellowship.name})" if s.fellowship_id else s.meeting_type.name


def render(months, location, texts, user=None):
    return build(gather(months, location), texts, user)
