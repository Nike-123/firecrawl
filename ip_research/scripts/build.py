#!/usr/bin/env python3
"""Build deliverables for the US IP law firm / FindLaw research project.

Inputs : deliverables/data/records.json   (state -> research block, see README)
Outputs: deliverables/US_IP_Law_Firms_Master.csv
         deliverables/US_IP_Law_Firms_Master.xlsx
         deliverables/Processing_Checkpoint.json

Rules enforced here:
  * exactly four columns: State | Law Firm Name | Official Website URL | Attorney / Person Name
  * one row per (firm, attorney); firms with no known attorney get a single row with a blank attorney
  * duplicate (state, firm, website, attorney) rows removed
  * FindLaw / Avvo / LinkedIn / Justia / other directory URLs are never accepted as a firm website
  * verified vs unverified websites are tracked internally, never in the four output columns
"""

import json
import re
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "records.json"
STATES_DIR = ROOT / "data" / "states"
CSV_OUT = ROOT / "US_IP_Law_Firms_Master.csv"
XLSX_OUT = ROOT / "US_IP_Law_Firms_Master.xlsx"
CKPT_OUT = ROOT / "Processing_Checkpoint.json"

COLUMNS = ["State", "Law Firm Name", "Official Website URL", "Attorney / Person Name"]

BLOCKED_DOMAINS = (
    "findlaw.com",
    "lawyers.com",
    "avvo.com",
    "justia.com",
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "yelp.com",
    "martindale.com",
    "nolo.com",
    "superlawyers.com",
    "lawyers.findlaw.com",
    "google.com",
    "bing.com",
    "indeed.com",
    "bbb.org",
    "wikipedia.org",
    "zoominfo.com",
    "bloomberg.com",
    "manta.com",
    "chambers.com",
    "legal500.com",
    "law360.com",
    "courtlistener.com",
    "uspto.gov",
    "statepatent.com",
    "patentattorney.com",
)

STATE_SHEET_MAX = 31  # Excel worksheet name limit


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def clean_firm(name: str) -> str:
    name = re.sub(r"\s+", " ", (name or "").strip())
    name = name.strip(" ,;|-")
    return name


def clean_person(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip())


def norm_key(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load():
    with open(DATA, encoding="utf-8") as fh:
        base = json.load(fh, object_pairs_hook=OrderedDict)
    order = base.get("research_order", [])
    merged = OrderedDict()
    files = {}
    if STATES_DIR.exists():
        for f in sorted(STATES_DIR.glob("*.json")):
            with open(f, encoding="utf-8") as fh:
                block = json.load(fh, object_pairs_hook=OrderedDict)
            m = re.match(r"^(\d+)-", f.name)
            if m:
                files[int(m.group(1))] = block
    for idx in sorted(files):
        block = files[idx]
        merged[block["state"]] = block
    for state in order:
        if state not in merged:
            merged[state] = OrderedDict([("status", "not_started"), ("pages_reviewed", []),
                                         ("listings_reviewed", 0), ("pagination_pages", 0),
                                         ("limitations", "Not yet processed."), ("firms", [])])
    base["states"] = merged
    for key, name in (("phase2_log", "phase2_log.json"), ("phase3_log", "phase3_log.json"), ("phase4_log", "phase4_log.json"), ("phase5_log", "phase5_log.json")):
        log_path = ROOT / "data" / name
        if log_path.exists():
            base[key] = json.loads(log_path.read_text(encoding="utf-8"))
    return base


def build_rows(data):
    rows = []
    seen = set()
    per_state_stats = OrderedDict()
    for state, block in data["states"].items():
        state_stats = {
            "status": block.get("status", "not_started"),
            "listings_reviewed": block.get("listings_reviewed", 0),
            "pagination_pages": block.get("pagination_pages", 0),
            "pages_reviewed": len(block.get("pages_reviewed", [])),
            "limitations": block.get("limitations", ""),
            "firms": 0,
            "rows": 0,
        }
        for firm in block.get("firms", []):
            fname = clean_firm(firm.get("firm", ""))
            if not fname:
                continue
            site = (firm.get("website") or "").strip()
            host = domain_of(site)
            if host and any(host == b or host.endswith("." + b) for b in BLOCKED_DOMAINS):
                site = ""  # directory URLs are never official firm websites
            attorneys = [clean_person(a) for a in firm.get("attorneys", []) if clean_person(a)]
            if not attorneys:
                attorneys = [""]
            state_stats["firms"] += 1
            for person in attorneys:
                key = (state, norm_key(fname), norm_key(person))
                if key in seen:
                    continue
                seen.add(key)
                rows.append([state, fname, site, person])
                state_stats["rows"] += 1
        per_state_stats[state] = state_stats
    return rows, per_state_stats


def write_csv(rows):
    import csv

    with open(CSV_OUT, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        writer.writerows(rows)


def style_header(ws):
    fill = PatternFill("solid", fgColor="1F3864")
    font = Font(bold=True, color="FFFFFF", size=11)
    for col in range(1, 5):
        cell = ws.cell(row=1, column=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:D{ws.max_row}"
    widths = [20, 46, 46, 30]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width


def write_sheet(ws, rows):
    ws.append(COLUMNS)
    for row in rows:
        ws.append(row)
    style_header(ws)
    for r in range(2, ws.max_row + 1):
        cell = ws.cell(row=r, column=3)
        if cell.value:
            cell.hyperlink = cell.value
            cell.font = Font(color="0563C1", underline="single")


def write_xlsx(rows, per_state_stats, order):
    wb = Workbook()
    master = wb.active
    master.title = "Master"
    write_sheet(master, rows)

    for state in order:
        state_rows = [r for r in rows if r[0] == state]
        title = state[:STATE_SHEET_MAX]
        ws = wb.create_sheet(title=title)
        write_sheet(ws, state_rows)
        if not state_rows:
            ws["A2"] = state
            ws["B2"] = "(no eligible IP listings found in FindLaw patents directory)"
            ws["B2"].font = Font(italic=True, color="808080")
    wb.save(XLSX_OUT)


def write_checkpoint(rows, per_state_stats, data):
    order = list(per_state_stats.keys())
    completed = [s for s in order if per_state_stats[s]["status"] == "completed"]
    in_progress = [s for s in order if per_state_stats[s]["status"] == "in_progress"]
    remaining = [s for s in order if per_state_stats[s]["status"] not in ("completed", "partial", "in_progress")]
    firms = {(r[0], norm_key(r[1])) for r in rows}
    sites = {}
    for r in rows:
        key = (r[0], norm_key(r[1]))
        sites[key] = sites.get(key, "") or r[2]
    verified = sum(1 for s in sites.values() if s)
    unique_firm_names = {norm_key(r[1]) for r in rows}
    firms_with_site = {norm_key(r[1]) for r in rows if r[2]}
    attorney_records = sum(1 for r in rows if r[3])
    review = sum(1 for v in data["states"].values() for f in v.get("firms", []) if f.get("needs_review"))
    ckpt = OrderedDict(
        [
            ("project", "US IP Law Firms - state-wise FindLaw research"),
            ("primary_source", "https://lawyers.findlaw.com/patents/"),
            ("last_updated_utc", data.get("last_updated_utc", "")),
            ("states_completed", completed),
            ("current_state", "n/a - all 51 jurisdictions processed"
             if not in_progress and not remaining else
             (in_progress[0] if in_progress else remaining[0])),
            ("states_in_progress", in_progress),
            ("states_partial", [s for s in order if per_state_stats[s]["status"] == "partial"]),
            ("states_with_no_findlaw_listings", [s for s in order if per_state_stats[s]["rows"] == 0]),
            ("states_remaining", remaining),
            ("states_total", len(order)),
            ("total_records", len(rows)),
            ("unique_law_firms", len(firms)),
            ("verified_official_websites", verified),
            ("missing_official_websites", len(firms) - verified),
            ("verified_official_websites_unique_firms", len(firms_with_site)),
            ("missing_official_websites_unique_firms", len(unique_firm_names) - len(firms_with_site)),
            ("attorney_records", attorney_records),
            ("records_requiring_review", review),
            ("findlaw_listings_reviewed", sum(v["listings_reviewed"] for v in per_state_stats.values())),
            ("pagination_pages_processed", sum(v["pagination_pages"] for v in per_state_stats.values())),
            ("state_details", OrderedDict(
                (s, OrderedDict([
                    ("status", per_state_stats[s]["status"]),
                    ("findlaw_listings_reviewed", per_state_stats[s]["listings_reviewed"]),
                    ("pagination_pages_processed", per_state_stats[s]["pagination_pages"]),
                    ("pages_reviewed", per_state_stats[s]["pages_reviewed"]),
                    ("firms_collected", per_state_stats[s]["firms"]),
                    ("records", per_state_stats[s]["rows"]),
                    ("limitations", per_state_stats[s]["limitations"]),
                ]))
                for s in order
            )),
            ("access_notes", data.get("access_notes", "")),
            ("phase2_log", data.get("phase2_log", {})),
            ("phase3_log", data.get("phase3_log", {})),
            ("phase4_log", data.get("phase4_log", {})),
            ("phase5_log", data.get("phase5_log", {})),
        ]
    )
    with open(CKPT_OUT, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def main():
    data = load()
    rows, per_state_stats = build_rows(data)
    write_csv(rows)
    write_xlsx(rows, per_state_stats, list(per_state_stats.keys()))
    write_checkpoint(rows, per_state_stats, data)
    print(f"records={len(rows)} firms={len({(r[0], norm_key(r[1])) for r in rows})}")
    print(f"csv={CSV_OUT.name} xlsx={XLSX_OUT.name} ckpt={CKPT_OUT.name}")


if __name__ == "__main__":
    main()
