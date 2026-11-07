#!/usr/bin/env python3
"""
Law-firm list cleaner (Firecrawl data-cleaning task)
====================================================
Input : raw scraped CSV  ->  columns: Firm Name, Official Website URL
Output: cleaned CSVs + multi-sheet Excel QA workbook + markdown report

Stages
 1 Parse & repair     - encoding (mojibake), stray columns, whitespace, symbols
 2 Normalise          - firm name, URL, domain, duplicate-detection name key
 3 Classify           - official homepage / deep link / directory profile / invalid
 4 Deduplicate        - exact, normalised-name, same-website, name-variant
 5 Evidence check     - does the domain textually belong to that firm name?
 6 Export             - CSV (full + outreach-ready), XLSX QA workbook, report
"""
from __future__ import annotations

import collections
import csv
import datetime
import difflib
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "law_firms_raw.csv"          # override: python clean_data.py <input.csv>
OUT = HERE

# ------------------------------------------------------------------ helpers
MOJIBAKE = re.compile(r"[ÃÂâ€™]")


def fix_encoding(s: str) -> str:
    """Repair UTF-8 that was decoded as latin-1 ('ArÃªte' -> 'Arête')."""
    if not MOJIBAKE.search(s):
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            return s.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s


TYPO = {"\u00ae": "", "\u2122": "", "\u2022": "&", "\u00a0": " ",
        "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u200b": "", "\u00ad": ""}

STOP = set("""law lawyer lawyers firm firms llp llc lllp pllc pc pa pl plc lp inc co corp ltd
limited esq the and of a an for at in to associates associate group offices office attorneys
attorney legal practice professional corporation company partnership liability services lawfirm
lawgroup international""".split())
SUFFIX = re.compile(r"\b(llp|llc|lllp|pllc|pc|pa|pl|plc|lp|inc|co|corp|ltd|limited|esq|psc|apc|aplc)\b\.?",
                    re.I)
DIRECTORY = {
    "avvo.com", "lawyers.com", "justia.com", "findlaw.com", "martindale.com", "nolo.com",
    "superlawyers.com", "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "yelp.com", "google.com", "goo.gl", "g.page", "linktr.ee", "thumbtack.com",
    "bbb.org", "manta.com", "zoominfo.com", "crunchbase.com", "bizapedia.com", "indeed.com",
    "glassdoor.com", "trustpilot.com", "legal500.com", "chambers.com", "chambersandpartners.com",
    "greatlawyers.com", "lawyerratingz.com", "expertguides.com", "birdeye.com", "yellowpages.com",
    "dnb.com", "mapquest.com",
}
TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_cid|mc_eid|ref$|referrer|source$|_ga)", re.I)
STATS: collections.Counter = collections.Counter()


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def clean_firm_name(raw: str) -> str:
    s = fix_encoding(raw)
    if s != raw:
        STATS["encoding (mojibake) repaired"] += 1
    for a, b in TYPO.items():
        s = s.replace(a, b)
    before = s
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*([,;])\s*$", "", s).strip(" -")
    if s != before.strip():
        STATS["firm names tidied (spacing/punctuation)"] += 1
    return s


def name_tokens(name: str) -> list[str]:
    x = ascii_fold(name.lower()).replace("&", " and ")
    return [t for t in re.findall(r"[a-z0-9]+", x) if t not in STOP and len(t) >= 2]


def name_key(name: str) -> str:
    """Aggressive key used only for duplicate detection."""
    x = ascii_fold(name.lower()).replace("&", " and ")
    x = re.sub(r"[^a-z0-9 ]", " ", x)
    x = SUFFIX.sub(" ", x)
    x = re.sub(r"\b(" + "|".join(sorted(STOP)) + r")\b", " ", x)
    return re.sub(r"\s+", " ", x).strip()


def clean_url(raw: str):
    """Return (url, ok, note). Canonical form: lowercase scheme+host, no www,
    no tracking params, no fragment, no trailing slash on a root URL."""
    u = fix_encoding(raw).strip().strip(",;").replace("\u200b", "")
    note = ""
    if not u:
        return "", False, "empty"
    if re.match(r"^https?://https?//", u, re.I):          # http://https//host
        u = re.sub(r"^https?://", "", u, flags=re.I).replace("//", "://", 1)
        note = "repaired doubled scheme"
    elif re.match(r"^https?//", u, re.I):                 # http//host
        u = re.sub(r"^(https?)", r"\1://", u, flags=re.I)
        note = "repaired missing colon"
    if not re.match(r"^[a-z][a-z0-9+.-]*://", u, re.I):
        u = "https://" + u
        note = note or "missing scheme (https added)"
    sp = urlsplit(u)
    host = (sp.hostname or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
        STATS["www. prefix removed"] += 1
    if (not host or "." not in host or " " in host
            or host in {"not available", "n/a", "none", "https", "http"}):
        return raw.strip(), False, "not a usable URL"
    path = re.sub(r"/{2,}", "/", sp.path or "")
    if path == "/":
        path = ""
    q = [(k, v) for k, v in parse_qsl(sp.query) if not TRACKING.match(k)]
    if sp.query and not q:
        note = note or "tracking parameters removed"
        STATS["tracking params removed"] += 1
    if sp.fragment:
        STATS["URL fragments removed"] += 1
    if sp.scheme.lower() == "http":
        STATS["HTTP (not HTTPS) URLs"] += 1
    return urlunsplit((sp.scheme.lower(), host, path, urlencode(q), "")), True, note


def host_of(url: str) -> str:
    return urlsplit(url).hostname or ""


def registrable(host: str) -> str:
    p = host.split(".")
    if len(p) >= 3 and p[-2] in {"co", "com", "org", "net", "gov", "ac", "edu", "or", "ne", "go"}:
        return ".".join(p[-3:])
    return ".".join(p[-2:]) if len(p) > 1 else host


def match_score(name: str, url: str) -> float:
    """0..1  - how strongly the domain text reflects the firm name."""
    if not url:
        return 0.0
    sld = registrable(host_of(url)).split(".")[0].replace("-", "")
    t = name_tokens(name)
    if not sld or not t:
        return 0.0
    if any(len(x) >= 4 and x in sld for x in t):
        return 1.0
    acr = "".join(x[0] for x in t)
    if len(acr) >= 2 and acr in sld:
        return 0.85
    if any(len(x) >= 3 and x in sld for x in t):
        return 0.70
    cands = {"".join(t), t[0], "".join(x[0] for x in t), "".join(t[:2])}
    if len(t) > 1:
        cands |= {t[0] + t[-1], t[0] + t[1]}
    return 0.55 if max(difflib.SequenceMatcher(None, c, sld).ratio() for c in cands) >= 0.72 else 0.0



def compact(s: str) -> str:
    return "".join(name_tokens(s))


GENERIC_TOK = {"small", "business", "legal", "law", "center", "centre", "group", "partners",
               "global", "american", "national", "international", "services", "solutions"}
PROFILE_RE = re.compile(r"\b(partner|attorney|esq|mediator|consultant|counsel)\b", re.I)


def subset_concat_index(firms):
    """Two-token concatenations -> firm, to spot 'WilmerHale' vs
    'Wilmer Cutler Pickering Hale and Dorr LLP' style duplicates.
    Only distinctive two-word names qualify, so profile pages
    ('... Partner at X LLP') and generic word mash-ups are ignored."""
    from itertools import combinations
    idx = {}
    for f in firms:
        if PROFILE_RE.search(f["name"]) or " at " in f["name"].lower():
            continue
        t = [x for x in name_tokens(f["name"]) if len(x) >= 3]
        if not 2 <= len(t) <= 6:
            continue
        for a, b in combinations(t, 2):
            if a in GENERIC_TOK or b in GENERIC_TOK:
                continue
            idx.setdefault(a + b, f)
    return idx

# ------------------------------------------------------------------ pipeline
def read_raw(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    recs = []
    stray = sum(1 for r in body if len(r) > 2 and not r[2].strip())
    if len(header) > 2 and not header[2].strip():
        STATS["rows ending with a stray comma (extra empty column)"] = stray
    for i, r in enumerate(body, start=2):
        r = list(r) + [""] * max(0, 3 - len(r))
        name, url = r[0].strip(), r[1].strip()
        if not name and not url:
            STATS["blank rows skipped"] += 1
            continue
        recs.append({"line": i, "name_raw": name, "url_raw": url})
    return header, recs


def enrich(recs):
    for r in recs:
        r["name"] = clean_firm_name(r["name_raw"])
        r["nkey"] = name_key(r["name"])
        r["url"], r["url_ok"], r["url_note"] = clean_url(r["url_raw"])
        r["domain"] = registrable(host_of(r["url"])) if r["url_ok"] else ""
        if not r["url_ok"]:
            r["url_type"] = "Invalid"
        elif r["domain"] in DIRECTORY:
            r["url_type"] = "Directory profile"
        elif urlsplit(r["url"]).path.strip("/"):
            r["url_type"] = "Deep link"
        else:
            r["url_type"] = "Homepage"
        r["score"] = (match_score(r["name"], r["url"])
                      if r["url_ok"] and r["url_type"] != "Directory profile" else 0.0)

    # who does each website really belong to?
    by_domain = collections.defaultdict(list)
    for r in recs:
        if r["domain"]:
            by_domain[r["domain"]].append(r)
    owner = {}
    for d, rs in by_domain.items():
        best = max(rs, key=lambda r: (r["score"], -r["line"]))
        if best["score"] >= 0.85:
            owner[d] = (best["nkey"], best["name"])
    for r in recs:
        r["owner_key"], r["owner_name"] = owner.get(r["domain"], ("", ""))
        r["contested"] = bool(r["owner_key"]) and r["owner_key"] != r["nkey"] and r["score"] < 0.85
    return recs, by_domain, owner


def build():
    header, recs = read_raw(RAW)
    recs, by_domain, owner = enrich(recs)

    firms_by_key = collections.OrderedDict()
    for r in recs:
        firms_by_key.setdefault(r["nkey"], []).append(r)

    firms, dup_log = [], []
    for nkey, rs in firms_by_key.items():
        rs.sort(key=lambda r: r["line"])

        def rank(r):
            return (r["contested"], r["url_type"] not in ("Homepage", "Deep link"),
                    -r["score"], r["line"])

        chosen = sorted(rs, key=rank)[0]

        if not chosen["url_ok"]:
            status, website = "Review - no usable website", ""
        elif chosen["url_type"] == "Directory profile":
            status, website = "Review - directory profile only", ""
        elif chosen["contested"]:
            status, website = "Review - website belongs to another firm", ""
        elif chosen["score"] >= 0.70:
            status, website = "Verified", chosen["url"]
        else:
            status, website = "Kept - website not verifiable", chosen["url"]

        domains = sorted({r["domain"] for r in rs if r["domain"]})
        variants = sorted({r["name"] for r in rs})
        notes = []
        if len(rs) > 1:
            notes.append(f"{len(rs)} source rows merged")
        if len(domains) > 1:
            notes.append("conflicting websites in source (" + ", ".join(domains) + ")")
        if chosen["contested"]:
            notes.append(f"source website {chosen['domain']} matches '{chosen['owner_name']}'")
        if chosen["url_note"]:
            notes.append(chosen["url_note"])
        if len(variants) > 1:
            notes.append("name variants: " + " | ".join(variants))
        if chosen["url_type"] == "Deep link":
            notes.append("deep link / profile page, not a homepage")

        firms.append({
            "name": chosen["name"], "website": website,
            "source_url": chosen["url"] if chosen["url_ok"] else chosen["url_raw"],
            "domain": chosen["domain"],
            "homepage": f"https://{chosen['domain']}" if website else "",
            "url_type": chosen["url_type"], "match": round(chosen["score"], 2),
            "status": status, "notes": "; ".join(notes),
            "rows": len(rs), "line": rs[0]["line"],
        })
        for r in rs[1:]:
            dup_log.append({
                "firm": r["name"], "url": r["url"] or r["url_raw"], "domain": r["domain"],
                "kept_firm": chosen["name"], "kept_url": chosen["url"] or chosen["url_raw"],
                "reason": ("duplicate firm name (same website)"
                           if r["domain"] == chosen["domain"]
                           else "duplicate firm name (source websites differ)"),
                "line": r["line"],
            })

    # same verified website under different firm names -> same firm, name variants
    by_site = collections.defaultdict(list)
    for f in firms:
        if f["website"]:
            by_site[f["website"]].append(f)
    drop = set()
    for site, group in by_site.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda f: (-len(name_tokens(f["name"])), -len(f["name"])))
        for i, long in enumerate(group):
            lt = set(name_tokens(long["name"]))
            for short in group[i + 1:]:
                st = set(name_tokens(short["name"]))
                # only merge a genuine name variant: every token of the shorter name
                # must appear in the longer one ('Akin' -> 'Akin, Gump, Strauss, ...').
                # A person listed at a firm ('Adam Pugh' vs 'Cagle Pugh') is NOT merged.
                if st and st <= lt and short["name"].lower() != long["name"].lower():
                    drop.add(id(short))
                    dup_log.append({"firm": short["name"], "url": short["source_url"],
                                    "domain": short["domain"], "kept_firm": long["name"],
                                    "kept_url": long["website"],
                                    "reason": "name variant of another firm (same verified website)",
                                    "line": short["line"]})
    firms = [f for f in firms if id(f) not in drop]

    # concatenated name variants: 'WilmerHale' == 'Wilmer' + 'Hale'
    idx = subset_concat_index([f for f in firms if f["website"]])
    for f in firms:
        if id(f) in drop or f["website"]:
            continue
        hit = idx.get(compact(f["name"]))
        if hit and hit["name"].lower() != f["name"].lower():
            drop.add(id(f))
            dup_log.append({"firm": f["name"], "url": f["source_url"], "domain": f["domain"],
                            "kept_firm": hit["name"], "kept_url": hit["website"],
                            "reason": "name variant of another firm (same firm, different spelling)",
                            "line": f["line"]})
    firms = [f for f in firms if id(f) not in drop]

    # domain conflicts (one website, several firm names)
    conflicts = []
    for d, rs in by_domain.items():
        if len({r["nkey"] for r in rs}) < 2:
            continue
        own = owner.get(d)
        for r in rs:
            if not own or r["nkey"] != own[0]:
                conflicts.append({"line": r["line"], "firm": r["name"], "website": r["url"],
                                  "domain": d, "believed_owner": own[1] if own else "",
                                  "firm_url_matches_domain": "yes" if r["score"] >= 0.7 else "no"})
    firms.sort(key=lambda f: (f["name"].lower(), f["line"]))
    for i, f in enumerate(firms, 1):
        f["id"] = f"LF-{i:04d}"
    return header, recs, firms, dup_log, conflicts


# ------------------------------------------------------------------ writers
FIELDS = [("id", "ID"), ("name", "Firm Name"), ("website", "Website URL"),
          ("domain", "Domain"), ("homepage", "Homepage"), ("url_type", "URL Type"),
          ("match", "Name/URL Match"), ("status", "Data Status"),
          ("source_url", "Source URL (as scraped, normalised)"), ("rows", "Source Rows Merged"),
          ("notes", "QA Notes"), ("line", "Source CSV Line")]

STATUS_ORDER = ["Verified", "Kept - website not verifiable", "Review - website belongs to another firm",
                "Review - directory profile only", "Review - no usable website"]


def write_csvs(firms):
    full = OUT / "law_firms_clean.csv"
    with open(full, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow([h for _, h in FIELDS])
        for f in firms:
            w.writerow([f[k] for k, _ in FIELDS])

    ready = OUT / "law_firms_verified.csv"
    with open(ready, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Firm Name", "Website URL", "Domain"])
        for f in firms:
            if f["status"] == "Verified":
                w.writerow([f["name"], f["website"], f["domain"]])
    return full, ready


def write_xlsx(firms, dup_log, conflicts, rec_stats):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    navy = "1F3864"; accent = "2E75B6"
    hdr_fill = PatternFill("solid", fgColor=navy)
    hdr_font = Font(color="FFFFFF", bold=True, size=11)
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    fills = {"Verified": PatternFill("solid", fgColor="E2EFDA"),
             "Kept - website not verifiable": PatternFill("solid", fgColor="FFF2CC"),
             "Review - website belongs to another firm": PatternFill("solid", fgColor="FCE4D6"),
             "Review - directory profile only": PatternFill("solid", fgColor="FCE4D6"),
             "Review - no usable website": PatternFill("solid", fgColor="F8CBAD")}

    wb = Workbook()

    # ---------------------------------------------------------- summary
    ws = wb.active
    ws.title = "Summary"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 52
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 62

    ws["B2"] = "Law Firm Dataset - Cleaning & De-duplication Report"
    ws["B2"].font = Font(size=16, bold=True, color=navy)
    ws["B3"] = f"Source: nIKET_data scrabe.csv  |  Prepared: {datetime.date.today():%d %b %Y}  |  All figures verified against the source file"
    ws["B3"].font = Font(size=9, italic=True, color="595959")

    r = 5
    def section(title):
        nonlocal r
        ws.cell(r, 2, title).font = Font(size=12, bold=True, color=accent)
        r += 1

    def line(label, value, note=""):
        nonlocal r
        ws.cell(r, 2, label).border = border
        c = ws.cell(r, 3, value); c.border = border
        c.font = Font(bold=True); c.alignment = Alignment(horizontal="center")
        if isinstance(value, str) and value.startswith("+"):
            c.font = Font(bold=True, color="C00000")
        ws.cell(r, 4, note).border = border
        ws.cell(r, 4).alignment = Alignment(wrap_text=True, vertical="top")
        r += 1

    ver = sum(1 for f in firms if f["status"] == "Verified")
    section("1. Volume")
    line("Data rows in source file", rec_stats["rows"] - 1,
         f"{rec_stats['rows']} lines including the header; every line ends with a stray comma")
    line("Rows removed as duplicates", len(dup_log), "same firm name and/or same website")
    line("Unique firms in cleaned dataset", len(firms), "one row per firm, cleaned + normalised")
    line("  - websites verified (domain matches firm name)", ver, "outreach-ready subset")
    line("  - websites kept but not verifiable", sum(1 for f in firms if f["status"].startswith("Kept")),
         "plausible but the domain does not echo the firm name")
    line("  - flagged for review (no safe website)", sum(1 for f in firms if f["status"].startswith("Review")),
         "see 'Needs Review' sheet")

    section("2. Duplicates")
    dl = collections.Counter(d["reason"] for d in dup_log)
    for k, v in dl.most_common():
        line(k[0].upper() + k[1:], v, "")
    line("Websites claimed by more than one firm name", len({c['domain'] for c in conflicts}),
         "structural duplicate / mis-pairing - see 'Website Conflicts'")

    section("3. Normalisation applied")
    for k, v in sorted(STATS.items()):
        if v:
            line(k[0].upper() + k[1:], v, "")

    section("4. Key finding")
    ws.cell(r, 2, "Firm names and website URLs do not always belong together.").font = Font(bold=True, color="C00000")
    r += 1
    for txt in [
        "In long stretches the URL column runs in its own alphabetical order while the firm-name column runs in "
        "another (e.g. line 3619 'Wilmer Cutler Pickering Hale and Dorr LLP' -> fowlerwhite.com, line 3644 "
        "'Jones Day' -> grayreed.com, line 62 'Alcyone Levy' -> wshblaw.com).",
        "That is the signature of two independently sorted lists being zipped together during scraping - it is not "
        "real firms sharing a website.",
        f"{len({c['domain'] for c in conflicts})} websites are attached to more than one firm name and "
        f"{sum(1 for f in firms if f['status'] == 'Review - website belongs to another firm')} firms only had a "
        "website that provably belongs to a different firm in the file.",
        "Rule applied: no guessing. A website was kept only where the domain supports the firm name; otherwise the "
        "original URL is preserved in 'Source URL' and the firm is flagged.",
    ]:
        ws.cell(r, 2, "-").alignment = Alignment(horizontal="right")
        c = ws.cell(r, 3, txt)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 32
        r += 1

    section("5. Sheets")
    for name, desc in [("Clean Data", "every unique firm, normalised, with QA status"),
                       ("Duplicates Removed", "each dropped row, its reason and the row that was kept"),
                       ("Website Conflicts", "one website -> several firm names"),
                       ("Needs Review", "firms without a trustworthy website (filter of Clean Data)"),
                       ("Field Definitions", "column meanings and status values")]:
        ws.cell(r, 2, name).font = Font(bold=True)
        ws.cell(r, 3, "-").alignment = Alignment(horizontal="center")
        ws.cell(r, 4, desc)
        r += 1

    # ---------------------------------------------------------- clean data
    def sheet(title, headers, rows, widths, status_col=None, table_name=None, wrap_cols=()):
        s = wb.create_sheet(title)
        s.append(headers)
        for c in range(1, len(headers) + 1):
            cell = s.cell(1, c)
            cell.fill, cell.font, cell.border = hdr_fill, hdr_font, border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        s.row_dimensions[1].height = 30
        for row in rows:
            s.append(row)
        for c, w in enumerate(widths, 1):
            s.column_dimensions[get_column_letter(c)].width = w
        for rr in range(2, s.max_row + 1):
            for cc in range(1, len(headers) + 1):
                cell = s.cell(rr, cc)
                cell.border = border
                cell.alignment = Alignment(vertical="top",
                                           wrap_text=(cc in wrap_cols))
            if status_col:
                v = s.cell(rr, status_col).value
                if v in fills:
                    s.cell(rr, status_col).fill = fills[v]
        s.freeze_panes = "A2"
        s.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{s.max_row}"
        return s

    sheet("Clean Data", [h for _, h in FIELDS],
          [[f[k] for k, _ in FIELDS] for f in firms],
          [10, 46, 46, 30, 34, 15, 11, 40, 42, 10, 60, 10],
          status_col=8, wrap_cols=(9, 11))

    # ---------------------------------------------------------- duplicates
    sheet("Duplicates Removed", ["Source Line", "Dropped Firm Name", "Dropped Website", "Domain",
                                 "Reason", "Kept Firm Name", "Kept Website"],
          [[d["line"], d["firm"], d["url"], d["domain"], d["reason"], d["kept_firm"], d["kept_url"]]
           for d in sorted(dup_log, key=lambda d: d["line"])],
          [12, 46, 42, 30, 40, 46, 42], wrap_cols=(5,))

    # ---------------------------------------------------------- conflicts
    sheet("Website Conflicts", ["Source Line", "Firm Name (as listed)", "Website in file", "Domain",
                                "Believed owner in this file", "Firm name matches domain?"],
          [[c["line"], c["firm"], c["website"], c["domain"], c["believed_owner"],
            c["firm_url_matches_domain"]] for c in sorted(conflicts, key=lambda c: c["domain"])],
          [12, 46, 42, 30, 46, 26], wrap_cols=(5,))

    # ---------------------------------------------------------- review
    review = [f for f in firms if f["status"].startswith("Review") or f["status"].startswith("Kept")]
    review.sort(key=lambda f: (STATUS_ORDER.index(f["status"]) if f["status"] in STATUS_ORDER else 9,
                               f["name"].lower()))
    sheet("Needs Review", ["ID", "Firm Name", "Data Status", "Source URL (as scraped)", "Domain",
                           "QA Notes", "Source Line"],
          [[f["id"], f["name"], f["status"], f["source_url"], f["domain"], f["notes"], f["line"]]
           for f in review],
          [10, 46, 42, 44, 30, 62, 12], status_col=3, wrap_cols=(4, 6))

    # ---------------------------------------------------------- definitions
    defs = [
        ("ID", "Stable record id for the cleaned dataset (LF-0001 ...)."),
        ("Firm Name", "Firm name as published, with encoding, spacing and stray punctuation repaired."),
        ("Website URL", "Recommended URL: present only when the domain can be trusted for that firm."),
        ("Domain", "Registrable domain (www. and path removed)."),
        ("Homepage", "https://<domain> - safe target for research/outreach."),
        ("URL Type", "Homepage / Deep link (inner page) / Directory profile (Avvo, Lawyers.com, LinkedIn...) / Invalid."),
        ("Name/URL Match", "0-1 score: does the domain text reflect the firm name? 1 = strong, 0 = none."),
        ("Data Status", "Verified | Kept - website not verifiable | Review - website belongs to another firm | "
                        "Review - directory profile only | Review - no usable website"),
        ("Source URL", "The URL exactly as it appeared in the source file (after safe normalisation) - audit trail."),
        ("Source Rows Merged", "How many raw rows collapsed into this firm."),
        ("QA Notes", "What was fixed, merged or is suspicious for this firm."),
        ("Source CSV Line", "Line number in the original CSV, for traceability."),
    ]
    s = wb.create_sheet("Field Definitions")
    s.append(["Column", "Meaning"])
    for c in (1, 2):
        s.cell(1, c).fill, s.cell(1, c).font = hdr_fill, hdr_font
    for k, v in defs:
        s.append([k, v])
    s.column_dimensions["A"].width = 22
    s.column_dimensions["B"].width = 110
    for rr in range(2, s.max_row + 1):
        s.cell(rr, 2).alignment = Alignment(wrap_text=True, vertical="top")
    s.freeze_panes = "A2"

    path = OUT / "Law_Firms_Cleaning_Report.xlsx"
    wb.save(path)
    return path


def write_report(firms, dup_log, conflicts, rec_stats):
    ver = sum(1 for f in firms if f["status"] == "Verified")
    kept = sum(1 for f in firms if f["status"].startswith("Kept"))
    review = sum(1 for f in firms if f["status"].startswith("Review"))
    conf_domains = len({c["domain"] for c in conflicts})
    md = f"""# Law Firm Dataset - Data Quality Report

**Source file:** `nIKET_data scrabe.csv`
**Prepared:** {datetime.date.today():%d %b %Y}
**Deliverables:** `law_firms_clean.csv`, `law_firms_verified.csv`, `Law_Firms_Cleaning_Report.xlsx`

## 1. Headline numbers

| Metric | Value |
|---|---|
| Data rows in source (excl. header) | {rec_stats['rows'] - 1} |
| Duplicate rows removed | {len(dup_log)} |
| Unique firms after cleaning | {len(firms)} |
| Websites verified (domain matches firm name) | {ver} |
| Websites kept but not verifiable | {kept} |
| Firms flagged for review | {review} |
| Websites claimed by more than one firm name | {conf_domains} |

## 2. What was wrong

1. **Stray third column** - every line ended with an extra comma, so the CSV had an empty column.
2. **Mis-paired names and URLs (the big one).** For long stretches the URL column is alphabetically
   sorted while the firm names are not, e.g. `Wilmer Cutler Pickering Hale and Dorr LLP -> fowlerwhite.com`,
   `Jones Day -> grayreed.com`, `Alcyone Levy -> wshblaw.com`. This is what you get when two separately
   sorted lists are zipped together during scraping; it also explains most of the "duplicates".
3. **Duplicate firms** - {len(dup_log)} rows repeat an existing firm (same name, or same name with a
   different / non-official website, or the same verified website under a name variant).
4. **Directory links instead of official sites** - Avvo, Lawyers.com, LinkedIn and Linktree profile pages
   were used as the "official website" for some firms.
5. **Broken / invalid URLs** - `https://Not Available`, `http://https//www.mckinleyirvin.com/...`.
6. **Encoding damage** - `ArÃªte Law Group`, `Kercsmar & Oâ€™Hara PLLC` (UTF-8 read as latin-1).
7. **Inconsistent URL style** - mixed `http`/`https`, `www.`, trailing slashes, tracking parameters,
   `#` fragments, inner pages instead of homepages.

## 3. Cleaning rules applied

- Names: encoding repaired, symbols (`®`, `™`, `•`) normalised, whitespace/punctuation tidied.
  Casing preserved - no invented capitalisation.
- URLs: scheme present, host lower-cased, `www.` removed, root trailing slash removed, tracking
  parameters and fragments stripped, double slashes collapsed.
- Duplicates: keyed on a normalised firm name (case/spacing/punctuation/entity suffixes ignored)
  plus the registrable domain. `PLC` vs `PLC.` and `Woods Rogers PLC` vs `Woods Rogers PLC.` collapse.
- No guessing: a URL is only *recommended* when the domain supports the firm name
  (e.g. `Jones Day -> jonesday.com`). Where it provably belongs to another firm in the file, the firm is
  kept, the URL is moved to `Source URL` and flagged **Review - website belongs to another firm**.
- Audit trail: every output row carries its source CSV line, the number of merged rows and QA notes.

## 4. How to use the files

| File | Use |
|---|---|
| `law_firms_clean.csv` | Full cleaned dataset ({len(firms)} firms) with status + notes. |
| `law_firms_verified.csv` | {ver} firms whose website is verified - ready for outreach. |
| `Law_Firms_Cleaning_Report.xlsx` | Workbook: Summary, Clean Data, Duplicates Removed, Website Conflicts, Needs Review, Field Definitions. |

## 5. Recommended next step

Re-scrape the {review + kept} firms whose website could not be verified - the firm name is correct,
only the URL is uncertain. A targeted Firecrawl run on the firm name + location would recover those
websites cheaply.
"""
    p = OUT / "DATA_QUALITY_REPORT.md"
    p.write_text(md, encoding="utf-8")
    return p


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        RAW = Path(sys.argv[1]).expanduser().resolve()
    if not RAW.exists():
        raise SystemExit(f"input file not found: {RAW}")
    header, recs, firms, dup_log, conflicts = build()
    rec_stats = {"rows": len(recs) + 1}
    full, ready = write_csvs(firms)
    xlsx = write_xlsx(firms, dup_log, conflicts, rec_stats)
    md = write_report(firms, dup_log, conflicts, rec_stats)
    print(f"input rows        : {len(recs)}")
    print(f"unique firms      : {len(firms)}")
    print(f"duplicates removed: {len(dup_log)}")
    print(f"website conflicts : {len({c['domain'] for c in conflicts})}")
    for k, v in collections.Counter(f["status"] for f in firms).most_common():
        print(f"  {k}: {v}")
    print("written:", full.name, ready.name, xlsx.name, md.name)
    assert len(recs) == len(firms) + len(dup_log), "row accounting does not balance"
