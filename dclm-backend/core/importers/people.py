"""Read the people list (DCLMBH.csv): name, status, phone, email, address, invited by, Adult or Youth and Bro or Sis."""
import csv, re


def read_people(path):
    rows = list(csv.reader(open(path, newline="", encoding="utf-8-sig")))
    head = next(i for i, r in enumerate(rows) if any(c.strip().lower() == "name" for c in r))
    cols = {c.strip().lower(): j for j, c in enumerate(rows[head]) if c.strip()}
    get = lambda r, k: (r[cols[k]] if cols.get(k) is not None and cols[k] < len(r) else "").strip()
    people = []
    for r in rows[head + 1:]:
        name = " ".join(get(r, "name").split())
        if not name:
            continue
        kind = get(r, "adults / youth / child").lower()
        people.append({
            "name": name, "status": get(r, "status").lower() or "member",
            "phone": re.sub(r"\D", "", get(r, "phone number") or get(r, "phone")), "email": get(r, "email"),
            "address": " ".join(get(r, "address").replace(" ,", ",").split()), "invited_by": get(r, "invited by"),
            "gender": "Female" if "sis" in kind else ("Male" if "bro" in kind else ""),
            "adult": "adult" in kind, "youth": "youth" in kind,
        })
    return people


def read_simple(path):
    """The newcomers and contacts lists: Name, Phone, Gender, Invited by."""
    out = []
    for r in csv.DictReader(open(path, newline="", encoding="utf-8-sig")):
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        if r.get("name"):
            out.append({"name": " ".join(r["name"].split()), "phone": re.sub(r"\D", "", r.get("phone", "")),
                        "gender": r.get("gender", "").title(), "invited_by": r.get("invited by", "")})
    return out
