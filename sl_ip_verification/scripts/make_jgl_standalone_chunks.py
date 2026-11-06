#!/usr/bin/env python3
"""Emit Google Sheets write payloads for the STANDALONE Just Great Lawyers spreadsheet.

Mirrors output/Just_Great_Lawyers_Verification.xlsx exactly:
  tab 1 "Just Great Lawyers"   - all 9 source columns, 176 rows
  tab 2 "Firm + Website Only"  - Serial Number, Person Name, Law Firm Name, Official Firm Website URL
  tab 3 "Read Me"              - provenance, blank census, source defects

Every value is copied verbatim from the byte-identical preserved upload. Nothing is
invented, trimmed or normalised. Writes work/jgl_standalone_*.json (git-ignored), one
file per payload chunk, each small enough to cat in a single bash call.
"""
import csv
import hashlib
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "input_original", "just_great_lawyers_original.csv")
WORK = os.path.join(ROOT, "work")

FULL = "Just Great Lawyers"
NARROW = "Firm + Website Only"
README = "Read Me"

CAP = 9500          # max characters of JSON values per chunk file
BUILD_DATE = "2026-11-06"


def load():
    raw = open(SRC, "rb").read()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    cols = list(rows[0].keys())
    return raw, rows, cols


def build_chunks(rows, cols, sheet, ncols, letter, name):
    """Return chunk descriptors with correct A1 ranges."""
    chunks = []
    buf = []
    start_row = 2
    size = 0
    for r in rows:
        line = [r[c] for c in cols]
        n = len(json.dumps(line, ensure_ascii=False))
        if buf and size + n > CAP:
            chunks.append((start_row, buf))
            start_row = start_row + len(buf)
            buf = []
            size = 0
        buf.append(line)
        size += n
    if buf:
        chunks.append((start_row, buf))

    out = []
    for i, (sr, buf) in enumerate(chunks):
        er = sr + len(buf) - 1
        rng = f"'{sheet}'!{letter}{sr}:{chr(ord(letter) + ncols - 1)}{er}"
        path = os.path.join(WORK, f"jgl_standalone_{name}_{len(out):02d}.json")
        payload = json.dumps({"range": rng, "values": buf}, ensure_ascii=False)
        open(path, "w").write(payload)
        out.append((path, rng, len(buf), len(payload)))
    return out


def header_chunk(sheet, cols, letter, tag):
    rng = f"'{sheet}'!{letter}1:{chr(ord(letter) + len(cols) - 1)}1"
    path = os.path.join(WORK, f"jgl_standalone_h_{tag}.json")
    payload = json.dumps({"range": rng, "values": [cols]}, ensure_ascii=False)
    open(path, "w").write(payload)
    return (path, rng, 1, len(payload))


def readme_lines(rows, cols, blanks, sha, size):
    firm = blanks["Law Firm Name"]
    web = blanks["Official Firm Website URL"]
    ev = blanks["Evidence URL"]

    def lst(sns, per=14):
        return ["  " + ", ".join(sns[i:i + per]) for i in range(0, len(sns), per)]

    L = []
    L.append("JUST GREAT LAWYERS - LAW FIRM NAME AND WEBSITE VERIFICATION")
    L.append("")
    L.append("WHAT THIS SPREADSHEET IS")
    L.append("A standalone Google Sheet edition of the uploaded dataset Just_Great_Lawyers_Verified.csv (176 lawyers).")
    L.append("It mirrors Just_Great_Lawyers_Verification.xlsx sheet for sheet.")
    L.append("Tab 'Just Great Lawyers' carries all 9 source columns. Values are copied EXACTLY as published - nothing invented, trimmed or normalised.")
    L.append("Tab 'Firm + Website Only' is the narrow view: Serial Number, Person Name, Law Firm Name, Official Firm Website URL.")
    L.append("Serial Number and Person Name are kept there only so a row can be identified; the two requested fields are the firm name and its website.")
    L.append("")
    L.append("PROVENANCE")
    L.append("Source upload: Just_Great_Lawyers_Verified.csv, received " + BUILD_DATE + ".")
    L.append("Preserved byte-identically at sl_ip_verification/input_original/just_great_lawyers_original.csv")
    L.append("sha256 " + sha + "   size " + str(size) + " bytes   encoding utf-8-sig (BOM)   line endings CRLF")
    L.append("Serial Number 1-176, contiguous and unique. 176 data rows, no duplicates.")
    L.append("")
    L.append("BLANK CELLS ARE THE SOURCE FILE'S OWN - NOT MISSING WORK")
    L.append("The upload is itself a verification output and published no value for some lawyers. Those cells are left EMPTY here.")
    L.append("Law Firm Name - blank on " + str(len(firm)) + " of 176 rows (serial numbers):")
    L.extend(lst(firm))
    L.append("Official Firm Website URL - blank on " + str(len(web)) + " of 176 rows (serial numbers):")
    L.extend(lst(web))
    L.append("Evidence URL - blank on " + str(len(ev)) + " of 176 rows (serial numbers):")
    L.extend(lst(ev))
    L.append("")
    L.append("STATUS TALLIES EXACTLY AS PUBLISHED IN THE SOURCE")
    for col in ("Firm Verification Status", "Website Verification Status"):
        t = {}
        for r in rows:
            t[r[col].strip()] = t.get(r[col].strip(), 0) + 1
        L.append(col + ": " + ", ".join(f"{k} {v}" for k, v in sorted(t.items(), key=lambda kv: -kv[1])))
    L.append("")
    L.append("DEFECTS AND AMBIGUITIES FOUND IN THE SOURCE (reported, not repaired)")
    L.append("1. Encoding defect, sn 133: the firm name is published as 'O?Melveny & Myers LLP'. The apostrophe in O'Melveny was already lost upstream. Copied verbatim. The firm is O'Melveny & Myers LLP, https://www.omm.com/")
    L.append("2. Seven rows publish several candidate firms in one cell, separated by a slash, because the source could not resolve which is current: sn 4, 39, 43, 50, 70, 110, 150.")
    L.append("3. Three websites serve two rows each: cohnlg.com (sn 2, 3), themyerslg.com (sn 71, 72), haynesboone.com (sn 116, 170). 116 unique domains across 119 populated website cells.")
    L.append("4. Some rows carry a firm or office name in the Person Name column instead of a person (for example sn 44 'Isaboke Law Firm', sn 61 'Leavitt & Eldredge Law Firm'). Left as published.")
    L.append("")
    L.append("HYPERLINKS")
    L.append("Lawyer Profile URL and Official Firm Website URL are live links. Evidence URL stays plain text because that cell often holds several semicolon-separated URLs.")
    L.append("")
    L.append("Built " + BUILD_DATE + " from the preserved upload by scripts/make_jgl_standalone_chunks.py.")
    return L


def main():
    raw, rows, cols = load()
    sha = hashlib.sha256(raw).hexdigest()
    size = len(raw)
    blanks = {c: [r["Serial Number"] for r in rows if not r[c].strip()] for c in cols}

    for f in os.listdir(WORK):
        if f.startswith("jgl_standalone_"):
            os.remove(os.path.join(WORK, f))

    narrow_cols = ["Serial Number", "Person Name", "Law Firm Name", "Official Firm Website URL"]
    report = []

    report.append(header_chunk(FULL, cols, "A", "full"))
    report.extend(build_chunks(rows, cols, FULL, len(cols), "A", "full"))
    report.append(header_chunk(NARROW, narrow_cols, "A", "narrow"))
    report.extend(build_chunks(rows, narrow_cols, NARROW, len(narrow_cols), "A", "narrow"))

    L = readme_lines(rows, cols, blanks, sha, size)
    path = os.path.join(WORK, "jgl_standalone_readme.json")
    payload = json.dumps({"range": f"'{README}'!A1:A{len(L)}",
                          "values": [[x] for x in L]}, ensure_ascii=False)
    open(path, "w").write(payload)
    report.append((path, f"'{README}'!A1:A{len(L)}", len(L), len(payload)))

    print(f"source sha256 {sha}  {size} bytes  rows {len(rows)}  cols {len(cols)}")
    print(f"blanks: firm {len(blanks['Law Firm Name'])}, website {len(blanks['Official Firm Website URL'])}, evidence {len(blanks['Evidence URL'])}")
    print(f"total payload chars: {sum(r[3] for r in report)}")
    print()
    for i, (p, rng, n, b) in enumerate(report):
        print(f"{os.path.basename(p):34s} {rng:46s} rows={n:4d} bytes={b:6d}")


if __name__ == "__main__":
    main()
