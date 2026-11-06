#!/usr/bin/env python3
"""Build Just_Great_Lawyers_Verification.xlsx from the byte-identical preserved upload.

Three sheets:
  1. "Just Great Lawyers"   - all 9 source columns, 176 rows, values EXACTLY as published
  2. "Firm + Website Only"  - the 2 fields the user asked for, plus Serial Number + Person Name
  3. "Read Me"              - provenance, blank-cell census, defects found in the source

Nothing is invented, normalised or silently corrected. Blank stays blank; it is only tinted
amber so the gap is visible. Every cell is re-read from the source CSV and compared with the
written workbook at the end.
"""
import csv
import hashlib
import io
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "input_original", "just_great_lawyers_original.csv")
OUT = os.path.join(ROOT, "output", "Just_Great_Lawyers_Verification.xlsx")

BUILD_DATE = "2026-11-06"
NOTE = "values copied exactly as published in the source upload - nothing invented or normalised"

HEADER_BG = "1F3864"
BLANK_BG = "FFF2CC"
LINK_FONT = Font(name="Calibri", size=10, color="0563C1", underline="single")
BODY_FONT = Font(name="Calibri", size=10)
BOLD_FONT = Font(name="Calibri", size=10, bold=True)
HEAD_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
THIN = Side(style="thin", color="D0D0D0")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

STATUS_FILLS = {
    "VERIFIED": "C6EFCE",
    "AMBIGUOUS": "FFEB9C",
    "NOT FOUND": "FFC7CE",
    "SOLO PRACTICE": "DDEBF7",
    "WEBSITE NOT VERIFIED": "FFEB9C",
    "NOT APPLICABLE": "EDEDED",
}


def read_source():
    raw = open(SRC, "rb").read()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    cols = list(rows[0].keys())
    return raw, rows, cols


def style_header(ws, ncols, widths):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = HEAD_FONT
        cell.fill = PatternFill("solid", fgColor=HEADER_BG)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BOX
        ws.column_dimensions[get_column_letter(c)].width = widths[c - 1]
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(ncols)}{ws.max_row}"


def write_data(ws, rows, cols, widths, link_cols, tint_blank):
    ws.append(cols)
    for r in rows:
        line = []
        for c in cols:
            v = r[c]
            if c == "Serial Number":
                line.append(int(v))
            else:
                line.append(v)
        ws.append(line)

    style_header(ws, len(cols), widths)

    for ri, r in enumerate(rows, start=2):
        ws.row_dimensions[ri].height = None
        for ci, c in enumerate(cols, start=1):
            cell = ws.cell(row=ri, column=ci)
            cell.font = BODY_FONT
            cell.border = BOX
            wrap = c in ("Evidence URL", "Notes", "Law Firm Name")
            valign = "top" if wrap else "center"
            cell.alignment = Alignment(vertical=valign, wrap_text=wrap)
            val = r[c].strip()
            if c in link_cols and val.startswith("http"):
                cell.hyperlink = val
                cell.font = LINK_FONT
            if c in ("Firm Verification Status", "Website Verification Status") and val in STATUS_FILLS:
                cell.fill = PatternFill("solid", fgColor=STATUS_FILLS[val])
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.font = BOLD_FONT
            if not val:
                if c in tint_blank:
                    cell.fill = PatternFill("solid", fgColor=BLANK_BG)


def census(rows, cols):
    out = {}
    for c in cols:
        blanks = [r["Serial Number"] for r in rows if not r[c].strip()]
        out[c] = blanks
    return out


def sn_list(sns, per_line=14):
    if not sns:
        return ["none"]
    out = []
    for i in range(0, len(sns), per_line):
        out.append("  " + ", ".join(sns[i:i + per_line]))
    return out


def build_readme(ws, rows, cols, blanks, sha, size):
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 132
    lines = []
    lines.append(("title", "Just Great Lawyers - law firm name and website verification"))
    lines.append(("blank", ""))
    lines.append(("h", "WHAT THIS FILE IS"))
    lines.append(("b", "An Excel edition of the uploaded dataset Just_Great_Lawyers_Verified.csv (176 lawyers)."))
    lines.append(("b", f"Sheet 1 'Just Great Lawyers' carries all 9 source columns. {NOTE}."))
    lines.append(("b", "Sheet 2 'Firm + Website Only' is the narrow view: Serial Number, Person Name, Law Firm Name, Official Firm Website URL."))
    lines.append(("b", "Serial Number and Person Name are kept in that narrow sheet only so a row can be identified; the two requested fields are the firm name and its website."))
    lines.append(("blank", ""))
    lines.append(("h", "PROVENANCE"))
    lines.append(("b", f"Source upload: Just_Great_Lawyers_Verified.csv, received {BUILD_DATE}."))
    lines.append(("b", "Preserved byte-identically at sl_ip_verification/input_original/just_great_lawyers_original.csv"))
    lines.append(("b", f"sha256 {sha}   size {size} bytes   encoding utf-8-sig (BOM)   line endings CRLF"))
    lines.append(("b", f"Workbook built {BUILD_DATE} by scripts/build_jgl_xlsx.py directly from that file."))
    lines.append(("b", "Serial Number 1-176, contiguous and unique, no duplicate rows."))
    lines.append(("blank", ""))
    lines.append(("h", "BLANK CELLS ARE THE SOURCE FILE'S OWN - THEY ARE NOT MISSING WORK"))
    lines.append(("b", "The upload is itself a verification output, and for some lawyers it published no value. Those cells are left empty here and tinted amber."))
    lines.append(("b", f"Law Firm Name - blank on {len(blanks['Law Firm Name'])} of 176 rows (serial numbers):"))
    for l in sn_list(blanks["Law Firm Name"]):
        lines.append(("m", l))
    lines.append(("b", f"Official Firm Website URL - blank on {len(blanks['Official Firm Website URL'])} of 176 rows (serial numbers):"))
    for l in sn_list(blanks["Official Firm Website URL"]):
        lines.append(("m", l))
    lines.append(("b", f"Evidence URL - blank on {len(blanks['Evidence URL'])} of 176 rows (serial numbers):"))
    for l in sn_list(blanks["Evidence URL"]):
        lines.append(("m", l))
    lines.append(("blank", ""))
    lines.append(("h", "STATUS TALLIES AS PUBLISHED IN THE SOURCE"))
    for col in ("Firm Verification Status", "Website Verification Status"):
        tallies = {}
        for r in rows:
            tallies[r[col].strip()] = tallies.get(r[col].strip(), 0) + 1
        lines.append(("b", col + ": " + ", ".join(f"{k} {v}" for k, v in sorted(tallies.items(), key=lambda kv: -kv[1]))))
    lines.append(("blank", ""))
    lines.append(("h", "DEFECTS AND AMBIGUITIES FOUND IN THE SOURCE (reported, not repaired)"))
    lines.append(("b", "1. Encoding defect, sn 133: the firm name is published as 'O?Melveny & Myers LLP'. The apostrophe in O'Melveny was already lost upstream. Copied verbatim. The firm is O'Melveny & Myers LLP, https://www.omm.com/."))
    lines.append(("b", "2. Seven rows publish several candidate firms in one cell, separated by a slash, because the source could not resolve which one is current: sn 4, 39, 43, 50, 70, 110, 150."))
    lines.append(("b", "3. Three websites serve two rows each: cohnlg.com (sn 2, 3), themyerslg.com (sn 71, 72), haynesboone.com (sn 116, 170). 116 unique domains across 119 populated website cells."))
    lines.append(("b", "4. Some rows carry a firm or office name in the Person Name column instead of a person (for example sn 44 'Isaboke Law Firm', sn 61 'Leavitt & Eldredge Law Firm'). Left as published."))
    lines.append(("blank", ""))
    lines.append(("h", "COLOUR KEY"))
    lines.append(("b", "Dark blue header. Green = VERIFIED. Amber = AMBIGUOUS or WEBSITE NOT VERIFIED. Red = NOT FOUND. Pale blue = SOLO PRACTICE. Grey = NOT APPLICABLE. Pale amber cell = the source published nothing here."))
    lines.append(("blank", ""))
    lines.append(("h", "HYPERLINKS"))
    lines.append(("b", "Lawyer Profile URL and Official Firm Website URL are live links. Evidence URL is left as plain text because that cell often holds several URLs separated by semicolons."))

    ri = 1
    for kind, text in lines:
        cell = ws.cell(row=ri, column=2, value=text)
        if kind == "title":
            cell.font = Font(name="Calibri", size=14, bold=True, color=HEADER_BG)
        elif kind == "h":
            cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="44546A")
        elif kind == "m":
            cell.font = Font(name="Consolas", size=9)
        else:
            cell.font = BODY_FONT
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        ri += 1
    ws.sheet_view.showGridLines = False


def main():
    raw, rows, cols = read_source()
    sha = hashlib.sha256(raw).hexdigest()
    size = len(raw)
    blanks = census(rows, cols)

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Just Great Lawyers"
    write_data(
        ws1, rows, cols,
        widths=[9, 30, 50, 40, 34, 19, 21, 58, 92],
        link_cols={"Lawyer Profile URL", "Official Firm Website URL"},
        tint_blank={"Law Firm Name", "Official Firm Website URL", "Evidence URL"},
    )
    ws1.sheet_properties.tabColor = "1F3864"

    narrow = ["Serial Number", "Person Name", "Law Firm Name", "Official Firm Website URL"]
    ws2 = wb.create_sheet("Firm + Website Only")
    write_data(
        ws2, rows, narrow,
        widths=[9, 32, 46, 38],
        link_cols={"Official Firm Website URL"},
        tint_blank={"Law Firm Name", "Official Firm Website URL"},
    )
    ws2.sheet_properties.tabColor = "59699E"

    ws3 = wb.create_sheet("Read Me")
    build_readme(ws3, rows, cols, blanks, sha, size)
    ws3.sheet_properties.tabColor = "2D8C3D"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)

    # ---- read the workbook back and prove it matches the source cell for cell ----
    from openpyxl import load_workbook
    back = load_workbook(OUT)
    b1 = back["Just Great Lawyers"]
    assert b1.max_row == len(rows) + 1, b1.max_row
    assert [c.value for c in b1[1]] == cols
    diffs = []
    for ri, r in enumerate(rows, start=2):
        for ci, c in enumerate(cols, start=1):
            got = b1.cell(row=ri, column=ci).value
            want = r[c]
            if c == "Serial Number":
                want = int(want)
            if want == "" and got is None:
                got = ""   # openpyxl reads a written empty string back as None; still a blank cell
            if got != want:
                diffs.append((r["Serial Number"], c, repr(want)[:60], repr(got)[:60]))
    b2 = back["Firm + Website Only"]
    assert b2.max_row == len(rows) + 1
    diffs2 = []
    for ri, r in enumerate(rows, start=2):
        for ci, c in enumerate(narrow, start=1):
            got = b2.cell(row=ri, column=ci).value
            want = int(r[c]) if c == "Serial Number" else r[c]
            if want == "" and got is None:
                got = ""
            if got != want:
                diffs2.append((r["Serial Number"], c))

    print(f"WROTE {OUT}  ({os.path.getsize(OUT)} bytes)")
    print(f"sheets: {back.sheetnames}")
    print(f"sheet1 rows x cols: {b1.max_row} x {b1.max_column}")
    print(f"sheet2 rows x cols: {b2.max_row} x {b2.max_column}")
    print(f"readme rows: {back['Read Me'].max_row}")
    print(f"source sha256: {sha}  ({size} bytes)")
    print(f"cell mismatches sheet1: {len(diffs)} {diffs[:5]}")
    print(f"cell mismatches sheet2: {len(diffs2)} {diffs2[:5]}")
    c4 = sum(1 for ri in range(2, b1.max_row + 1) if not b1.cell(row=ri, column=4).value)
    c5 = sum(1 for ri in range(2, b1.max_row + 1) if not b1.cell(row=ri, column=5).value)
    c8 = sum(1 for ri in range(2, b1.max_row + 1) if not b1.cell(row=ri, column=8).value)
    src = (len(blanks["Law Firm Name"]), len(blanks["Official Firm Website URL"]), len(blanks["Evidence URL"]))
    got = (c4, c5, c8)
    print(f"blank cells in workbook (firm name, website, evidence): {got}  source census: {src}  match={got == src}")
    assert got == src, "blank-cell census does not match the source"
    if diffs or diffs2:
        print("RESULT: MISMATCH - workbook does not equal source")
        return 1
    print("RESULT: WORKBOOK MATCHES THE SOURCE CELL FOR CELL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
