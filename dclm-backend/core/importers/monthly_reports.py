"""Read the Bahrain monthly report CSVs into the records the import will create."""
import csv, datetime, json, re
MON={"Jul":7,"Aug":8,"Sep":9}
def num(x):
    try: return float(str(x).replace(",",""))
    except: return None
def nil0(cells):
    """A row with real numbers may write Nil for a group with nobody in it
    (September's Ministers' Renewal did). Count Nil as 0 then, but leave a
    row with no numbers at all (XX, GCK) alone."""
    vals=[num(x) for x in cells]
    if any(v is not None for v in vals):
        return [0.0 if (v is None and str(x).strip().lower() in ("nil","-","")) else v for v,x in zip(vals,cells)]
    return vals
def d(s, year=2026):
    s=str(s).strip()
    try:
        if "/" in s: return datetime.datetime.strptime(s,"%d/%m/%Y").date()
        dd,mm=s.split("-"); return datetime.date(year, MON[mm[:3]], int(dd))
    except Exception: return None
WEEKLY={"FRIDAY":("Friday Worship Service","in-person-and-online"),"MONDAY":("Monday Bible Study","online"),"WEDNESDAY":("Wednesday Revival and Evangelism Training","online")}
FUNDS=[(11,"DLICC Vow"),(12,"GCK"),(13,"Special Fund"),(14,"Tithe"),(15,"Offering")]
def parse(path, month):
    R=[r+[""]*(42-len(r)) for r in csv.reader(open(path,newline=""))]
    last=datetime.date(2026,month,28)+datetime.timedelta(days=4); last=last-datetime.timedelta(days=last.day)
    out={"sessions":[],"giving":[],"expenses":[],"testimonies":[]}
    act=None
    for i in range(5,20):
        r=R[i]
        if r[1].strip(): act=r[1].replace("\n"," ").strip().split()[0]
        dt=d(r[2])
        if not dt or act not in WEEKLY: continue
        c=[num(x) for x in r[3:10]]
        name,mode=WEEKLY[act]
        if all(x is not None for x in c):
            out["sessions"].append({"date":dt.isoformat(),"meeting":name,"mode":mode,"men":c[0],"women":c[1],"youth_boys":c[2],"youth_girls":c[3],
                                    "children_boys":c[4],"children_girls":c[5],"newcomers":c[6],"new_converts":0,"total":sum(c),"edition_name":"","edition_place":""})
        for col,fund in FUNDS:
            v=num(r[col])
            if v: out["giving"].append({"date":dt.isoformat(),"fund":fund,"service":name,"sar":v})
    for i in range(22,27):
        r=R[i]
        for dc,mc,fc,name in ((2,3,4,"Saturday Workers Meeting"),(6,8,9,"Tuesday Leadership Development")):
            dt=d(r[dc]); m,f=num(r[mc]),num(r[fc])
            if dt and m is not None and f is not None:
                out["sessions"].append({"date":dt.isoformat(),"meeting":name,"mode":"online","men":m,"women":f,"youth_boys":0,"youth_girls":0,"children_boys":0,"children_girls":0,
                                        "newcomers":0,"new_converts":0,"total":m+f,"edition_name":"","edition_place":""})
    title=" ".join(R[2][17].split())
    theme=title.split(" - ")[-1].strip() if " - " in title else ""
    mrc=False
    for i in range(5,20):
        r=R[i]
        if "MINISTER" in r[18].upper(): mrc=True; continue
        dt=d(r[19]); c=nil0(r[20:27])
        if not dt or not all(x is not None for x in c): continue
        label=r[18].strip()
        if mrc:
            meeting, ename, place = "Ministerial Renewal", "", ""
        else:
            meeting="Global Crusade with Kumuyi (GCK)"
            place={"Pakistan GCK":"Pakistan","Benin Rep GCK":"Benin Republic"}.get(label,"")
            ename=theme
        out["sessions"].append({"date":dt.isoformat(),"meeting":meeting,"mode":"online","men":c[0],"women":c[1],"youth_boys":c[2],"youth_girls":c[3],
                                "children_boys":c[4],"children_girls":c[5],"newcomers":0,"new_converts":c[6],"total":sum(c),"edition_name":ename,"edition_place":place})
    for i in range(24,29):
        desc=R[i][12].strip(); v=num(R[i][16])
        if desc and v: out["expenses"].append({"date":last.isoformat(),"category":desc,"sar":v})
    t=" ".join(R[33][20].split())
    if t: out["testimonies"].append({"date":last.isoformat(),"text":t})
    return out
if False:
    import sys
    U="/mnt/user-data/uploads/"
    allr={}
    for m,f in ((7,"Bahrain_July_2026_Report.csv"),(8,"Bahrain_August_2026_Report.csv"),(9,"Bahrain_September_2026_Report.csv")):
        allr[m]=parse(U+f, m)
        o=allr[m]
        print(m, "sessions", len(o["sessions"]), "| attendance", sum(s["total"] for s in o["sessions"]), "| giving SAR", round(sum(g["sar"] for g in o["giving"]),2), "| expenses SAR", round(sum(e["sar"] for e in o["expenses"]),2), "| testimonies", len(o["testimonies"]))
    json.dump(allr, open("/home/claude/import/records.json","w"), indent=1)
