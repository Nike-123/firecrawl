# Super Lawyers — Intellectual Property Practice Verification

Project root: `/home/user/firecrawl/sl_ip_verification/` (inside the git repo, so it survives
sandbox restarts). Branch: `arena/db9ebbf8-firecrawl`. Verification date on every row: **2026-11-06**.

## The task

The uploaded CSV (`input_original/superlawyers_original.csv`, 216 rows, `field 1` = person name,
`link` = Super Lawyers profile URL) had to be turned into a 12-column verification workbook:

`Serial Number`, `Person Name`, `Super Lawyers Profile URL`, `Current Law Firm Name`,
`Official Law Firm Website URL`, `Firm Verification Status`, `Website Verification Status`,
`Evidence URL`, `Lawyer Association Evidence URL`, `IP Practice Evidence`, `Notes`,
`Verification Date`.

The user chose a **full rebuild** after a sandbox restart destroyed the first run, and chose
**full untruncated Notes**.

## Status right now

* **Phase A — COMPLETE.** All 216 Super Lawyers profiles were fetched and saved to
  `work/profiles.jsonl`: sn 1–216, contiguous, no duplicates, all 18 keys on every row.
  Firm Verification Status: **VERIFIED 167 / SOLO PRACTICE 46 / AMBIGUOUS 3**.
* **Phase B — IN PROGRESS.** 10 of **189** unique firm domains have been fetched and saved to
  `work/sites.jsonl` (sns 1–10, 13, 202). 179 domains are still to check, so their
  Website Verification Status reads **NOT YET VERIFIED** — that value is deliberate and honest,
  not a failure. Worklist: `work/phase_b_queue.txt` (189 lines, `domain|sns|site_url`).
* **Deliverables are built and current** in `output/`. Rebuild any time with
  `python3 scripts/build_outputs.py` (needs `pip3 install --break-system-packages openpyxl`;
  installed packages do not persist between turns).

## Files

| Path | What it is |
| --- | --- |
| `input_original/superlawyers_original.csv` | the user's upload, byte-identical copy |
| `work/input_records.json` | `[{sn, name, url}]` for all 216 rows |
| `work/profile_queue.txt` | `sn\|name\|url` per line |
| `work/profiles.jsonl` | **Phase A findings — the source of truth for rows.** Each row's `note` carries the full derivation, verbatim quotes, IP analysis and recorded anomalies |
| `work/sites.jsonl` | **Phase B findings**, keyed by normalised domain, with equally long evidence notes |
| `work/phase_b_queue.txt` | the remaining Phase B worklist |
| `scripts/save_profiles.py` | upserts `profiles.jsonl` from a JSON array on stdin, prints the next N pending profile URLs verbatim |
| `scripts/save_sites.py` | upserts `sites.jsonl` from a JSON array on stdin |
| `scripts/revise_batch1.py` | the Phase B batch-1 revisions (sn 7, 8, 3, 202, 1) — already applied |
| `scripts/build_outputs.py` | builds the XLSX, CSV, `Summary.txt`, `Checkpoint.json` |
| `scripts/build_error_log.py` | builds `Error_Log.txt` |
| `scripts/verify_outputs.py` | integrity check: CSV ⇄ XLSX equality, key presence, counts |
| `scripts/measure.py` | per-column character measurement helper |
| `output/Super_Lawyers_IP_Verification.xlsx` | **the deliverable workbook** |
| `output/Super_Lawyers_IP_Verification.csv` | the same rows, UTF-8 with BOM, full untruncated Notes |
| `output/Summary.txt` | tallies and data-quality statistics |
| `output/Checkpoint.json` | machine-readable progress state |
| `output/Error_Log.txt` | every anomaly, contradiction and collection error recorded |

## Classification rule (final — reuse verbatim)

**SOLO PRACTICE** only when the firm is eponymous **AND** the lawyer is called sole
practitioner / founder / principal / owner **AND** no other attorney is named **AND** there are
no multiple offices or plural attorneys page **AND** no partnership title.
**VERIFIED** when the firm is non-eponymous, or eponymous with managing attorney / partner /
President / co-founder / "& Associates" / multiple offices / a plural attorneys page.
**AMBIGUOUS** when the Super Lawyers firm field and the bio name different firms (sn 22, 48, 172).

Key sub-rules that decided actual rows:

* A team page profiling **exactly one** attorney keeps or forces SOLO unless it carries an
  explicit managing-member / partner title — this flipped **sn 7** to SOLO and confirmed **sn 1**
  and **sn 5**.
* "Founding partner", "managing partner", "Founder and Managing Attorney", "owner and managing
  partner" **are** partnership titles → VERIFIED (sn 2, 4, 167, 176, 193, 202, 204, 209).
* A **descriptive** firm name stays VERIFIED even with one published lawyer, flagged
  (sn 160, 175, 199, 211, 213, 214).
* A bar-association office such as "co-chair, Solo & Small Law Firm Section" is **not** solo
  evidence (sn 38, 145, 159, 203).
* A firm named after a lawyer's **middle name** is eponymous in substance (sn 7: Alonzo
  **McAlpine** Alston → McAlpine PLLC).

## Hard-won operating rules (do not relearn these the expensive way)

1. **Never construct a fetch URL.** Copy the exact string printed by `save_profiles.py` /
   `phase_b_queue.txt`. Fabricated proxy URLs (`routify…aliyuncs.com/proxy_temp_file/…`) return
   `SignatureDoesNotMatch` for the whole batch and waste the turn; this happened 18 times.
   Re-issuing the exact string has succeeded 18/18.
2. **Never pass a big payload through a heredoc.** bash is capped at 64,000 characters and
   oversized or backslash-containing payloads die with a silent `shell_error` (null exit code,
   empty stdout *and* stderr), destroying the fetched batch. Standard pattern: `write_file` the
   JSON array to `work/batch_*.json`, then a tiny bash that only consumes it, `rm`s it and
   commits. Keep payloads ≤ 25 k characters. **Zero backslashes in JSON payloads.**
3. **Commit and push at the end of every batch.** `work/batch_*.json` is git-ignored, so a
   staged-but-unconsumed batch is not durable.
4. **Fetch no more than 10–12 pages per turn** and save them in the very next turn; fetched page
   content is not persisted anywhere.
5. **Chunk 0 is not always enough.** `fetch_page` truncates long pages; Practice areas, First
   Admitted, Professional Webpage and Bar activity sometimes live in chunk 1 (worst case sn 215,
   whose chunk 0 ended at a lone asterisk). Fetch the extra chunk in the same turn.
6. **A truncated practice list causes false "no IP" findings** (sn 170, 184, 197, 194 in an
   earlier pass). Re-derive from the firm's capabilities page. Conversely a homepage that omits
   IP cannot disprove it (sn 6 — IP is UNRESOLVED, not negative).
7. **Read the returned URL and title, not the requested URL** — redirects silently change the
   evidence (sn 8: `amburnlaw.com/dean-amburn/` → `pure.law`).
8. `bash` has no internet. All research goes through `fetch_page` / `web_search`.

## Immediate next steps

1. Phase B batch 2 = `work/phase_b_queue.txt` lines 11–22 (`ashmanlawoffices.com` 11,
   `scalefirm.com` 12, `beckman.law` 14, `belzerlaw.com` 15, `ghbllp.com` 16,
   `bernsteinip.com` 17, `zoebernsteinlaw.com` 18, `practus.com` 19, `blahalaw.com` 20,
   `blumlaw.co` 21, `boehringerlaw.com` 22, `idealawyers.com` 23/180/181/182).
2. Batch-1 follow-up fetches still owed: `internetlawgroup.com/lawyers/` (roster count);
   `passmanjones.com/practice-areas/` (sn 6 IP verdict) and `/team/`;
   `mcalpinepllc.com` root + chunk 1 + `/s/McAlpine-PLLC-Awards.pdf`;
   `novotechip.com/ourteammembers/stephen-becker/` (sn 13);
   `weissarons.com/attorneys/edward-m-arons/` (sn 10) and the `/attorneys/` index;
   `cdalawllp.com` chunks 1–2 (full roster incl. Arneri); a `pure.law` attorney/team page;
   `thecontentlawyer.com` chunk 1.
3. Highest-value single fetches: **sn 212** `ctwrightlaw.com` (a prior pass found attorney pages
   `/priya-nair/` and `/ashfia-khan/` — that would flip SOLO → VERIFIED), **sn 216**
   `lomnitzerlaw.com/team/kelly-ann-desrosiers/` (same firm as sn 115; settles both rows),
   **sn 172** `wantathome.com` + `hjlawfirm.com` (AMBIGUOUS).
4. After every batch: `python3 scripts/build_outputs.py && python3 scripts/verify_outputs.py`.

## Google Sheet edition — BUILT AND VERIFIED

Spreadsheet: **Super Lawyers - IP Practice Verification (2026-11-06)**
`https://docs.google.com/spreadsheets/d/1LRYq-I2WSRLJ0-BccLHH-OyapBkWkRb-o6bzw_TDocA/edit`
`spreadsheet_id = 1LRYq-I2WSRLJ0-BccLHH-OyapBkWkRb-o6bzw_TDocA`

| Tab | sheet_id | Contents |
| --- | --- | --- |
| `IP Verification` | 1754575256 | header + 216 rows, A1:L217, 12 columns in the required order |
| `Summary` | 147577980 | `Summary.txt` in A1:A60 plus a truncation-disclosure block in A61:A74 |
| `Error Log` | 47903829 | `Error_Log.txt`, complete and untruncated, A1:A166 |

Formatting: frozen header row, autofilter on A1:L217, bold white-on-`1F3864` header with wrap,
per-column widths, coloured tabs.

**The Notes column in the Sheet is truncated to the first 500 characters** and every one of the
216 cells ends with the marker
`[… FULL NOTE: n chars, complete text in Super_Lawyers_IP_Verification.csv and .xlsx]`, where `n`
is that note's true length. The other 11 columns are complete and untruncated in the Sheet.
Reason: the connector sends every cell value inline through model output and the Notes column
totals **1,479,746 characters** (~370 k tokens), which cannot be pushed through it. The Sheet's
own `Summary` tab states this in writing. A Sheets cell holds 50,000 characters and the longest
note here is 13,474, so the API was never the limit — context was.

Verified after writing, by `query_table` against the built files: 216 data rows, sn 1–216;
Firm Verification Status VERIFIED 167 / SOLO PRACTICE 46 / AMBIGUOUS 3; Website Verification
Status NOT YET VERIFIED 200 / WEBSITE VERIFIED 12 / NOT APPLICABLE 4; single Verification Date
2026-11-06 on all 216 rows; 12 rows carrying `QUALIFIED:` in IP Practice Evidence; 216 rows
carrying the truncation marker. Spot checks: sn 7 Alonzo M. Alston SOLO PRACTICE + WEBSITE
VERIFIED, sn 22 Michael Boehringer / sn 48 Alexandra Devine / sn 172 Neven Selimovic AMBIGUOUS,
sn 212 Chun T. Wright SOLO PRACTICE, sn 216 Kelly desRosiers in row 217.

Regenerating the payload: `python3 scripts/make_sheets_chunks.py` writes
`work/sheets_chunk_00.json` … `sheets_chunk_18.json` plus `work/sheets_tab_summary.json` and
`work/sheets_tab_errorlog.json` (NOTE_CAP 500, CHUNK_CHARS 17000). Those files are git-ignored.
Read **one** chunk file per `bash` call — `cat`-ing two or three at once silently truncates the
middle of the output. There is no file-import tool in this connector, so every value is written
inline; ~16 k characters of payload per call is the practical ceiling.


## Just Great Lawyers tab — second dataset (added 2026-11-06)

Second upload: Just_Great_Lawyers_Verified.csv, 176 rows, 9 columns, utf-8-sig with a BOM and CRLF
line endings. Preserved byte-identically at input_original/just_great_lawyers_original.csv
(65,659 bytes, sha256 2a4e8ffbdf287610e86b582f57f02c9752e409b7b2cf59ae0e3c087f14a6e733).

The user asked for ONLY two fields from it — the law firm name and that firm's website URL — added to
the existing spreadsheet. Delivered as a new tab in the SAME spreadsheet:

  tab            Just Great Lawyers   sheet_id 659568122   index 1 (right after IP Verification)
  header A1:D1   Serial Number | Person Name | Law Firm Name | Official Firm Website URL
  data           A2:D177 (176 rows, 708 cells) — written in ONE batch_update_values, 3 ranges
  formatting     frozen row 1, basic filter A1:D177, header bold/white on 1F3864 wrapped, 56px row
                 widths A46 B230 C420 D320, legend column F (620px) F1:F10
  tab colour     rgb 0.35 / 0.42 / 0.62

Serial Number and Person Name were added on my own judgement so a row can be identified at all; the
user never asked for them. Offer to strip them if they want a strict 2-column tab.

VERIFIED IN-SHEET (query_table + 6 batch_get_values spot checks against the source CSV):
  count(A) 176, min 1, max 176 — count(C) 146 rows carry a firm name, count(D) 119 carry a website.
  Both tallies equal 176 minus the source's own blanks (30 and 57), so nothing was invented or lost.
  Spot checks sn 1, 44, 61, 79, 133, 176 all byte-identical to the upload, including the curly
  quotes in Robert D. “Bob” Katz and the blank C/D on sn 176.

THE BLANKS ARE THE SOURCE FILE'S, NOT MINE. This upload is itself a verification output and already
published no value for some rows:
  Law Firm Name blank on 30 rows: 7, 10, 24, 25, 27, 28, 29, 33, 49, 56, 69, 80, 95, 101, 103, 113,
    114, 128, 134, 138, 143, 145, 148, 158, 162, 164, 168, 172, 175, 176
  Official Firm Website URL blank on 57 rows: 4, 7, 9, 10, 24, 25, 27, 28, 29, 33, 39, 43, 47, 49,
    50, 56, 63, 69, 70, 73, 80, 90, 95, 101, 103, 104, 107, 110, 113, 114, 115, 118, 119, 126, 128,
    134, 136, 137, 138, 141, 142, 143, 145, 148, 149, 150, 158, 159, 162, 164, 168, 169, 171, 172,
    173, 175, 176
  Evidence URL blank on 9 rows: 24, 25, 29, 56, 69, 95, 103, 134, 162
  Firm Verification Status in the source: VERIFIED 132, AMBIGUOUS 29, NOT FOUND 13, SOLO PRACTICE 2
  Website Verification Status: VERIFIED 119, WEBSITE NOT VERIFIED 42, NOT FOUND 14, N/A 1
  116 unique domains; three serve two rows each — cohnlg.com (sn 2, 3), themyerslg.com (71, 72),
    haynesboone.com (116, 170).
  7 rows publish several candidate firms separated by a slash because the source could not resolve
    the current one: sn 4, 39, 43, 50, 70, 110, 150.
  Encoding defect copied verbatim, NOT silently corrected: sn 133 reads O?Melveny & Myers LLP — the
    apostrophe in O'Melveny was already lost upstream. The real firm is O'Melveny & Myers LLP (omm.com).

If the user wants the 87 blank cells researched, the columns NOT copied into the sheet — Lawyer
Profile URL, Evidence URL, both status columns, Notes — are still in the preserved upload and are the
starting point for each row.

Regenerate the tab payload with: python3 scripts/make_jgl_chunks.py
  -> work/jgl_chunk_00.json (A2:D153, 152 rows) and work/jgl_chunk_01.json (A154:D177, 24 rows).
Those are git-ignored, so they must be re-made after any restart.

## Durability incident 2026-11-06 — the global *.csv ignore ate two files

The upstream .gitignore carries a bare `*.csv` rule. Because of it, neither input_original/*.csv nor
output/Super_Lawyers_IP_Verification.csv was ever committed, and a workspace restore wiped them from
disk while every tracked file came back. Recovery:

  input_original/superlawyers_original.csv — restored from /tmp/arena-coding-uploads/superlawyers.csv
    (that upload IS the Task 1 source, not an unrelated file). Re-checked against the tracked
    work/input_records.json: 216 rows, 0 mismatches. sha256
    89c53c521c9a038abf7f62c2a2f4a50330efa4fe655ff8614ebb93c99348f884, 30,400 bytes.
  output/Super_Lawyers_IP_Verification.csv — rebuilt with scripts/build_outputs.py from the tracked
    profiles.jsonl + sites.jsonl. Came back at exactly 1,629,219 bytes, and verify_outputs.py passes
    all 15 checks again (CSV and XLSX agree cell for cell).

Fix now committed: two negation rules in .gitignore —
  !sl_ip_verification/input_original/*.csv
  !sl_ip_verification/output/*.csv
RULE: after any new CSV deliverable or upload is written, confirm with `git ls-files` that it is
tracked. A file that is not in git does not survive a restart. openpyxl does not survive either;
reinstall with pip3 install --break-system-packages openpyxl before running build_outputs.py.


## Just Great Lawyers Excel deliverable (added 2026-11-06)

The user then asked for this dataset on its own as an Excel file, not only as a Google Sheet tab.

  output/Just_Great_Lawyers_Verification.xlsx   51,999 bytes
  built by scripts/build_jgl_xlsx.py from input_original/just_great_lawyers_original.csv
  (source sha256 2a4e8ffbdf287610e86b582f57f02c9752e409b7b2cf59ae0e3c087f14a6e733, 65,659 bytes)

Three sheets:
  1. Just Great Lawyers   A1:I177 - all 9 source columns, freeze A2, filter A1:I177, tab 1F3864
                          widths 9/30/50/40/34/19/21/58/92, Notes + Evidence + firm name wrapped
  2. Firm + Website Only  A1:D177 - Serial Number, Person Name, Law Firm Name, Official Firm Website URL
                          freeze A2, filter A1:D177, tab 59699E, widths 9/32/46/38
  3. Read Me              45 rows - provenance, blank-cell census with serial numbers, status tallies,
                          source defects, colour key, tab 2D8C3D

295 live hyperlinks (176 profile URLs + 119 website URLs on sheet 1, 119 on sheet 2). Evidence URL is
plain text on purpose: that cell often holds several semicolon-separated URLs.

Status cells are colour-coded exactly as published: Firm VERIFIED 132, AMBIGUOUS 29, NOT FOUND 13,
SOLO PRACTICE 2. Website VERIFIED 119, WEBSITE NOT VERIFIED 42, NOT FOUND 14, NOT APPLICABLE 1.
Empty cells are tinted pale amber FFF2CC and left EMPTY - blanks are the source's own and are never
filled in from memory.

The builder verifies itself: it reloads the saved workbook and compares all 176 x 9 plus 176 x 4 cells
against the CSV. It reports RESULT: WORKBOOK MATCHES THE SOURCE CELL FOR CELL only when there are zero
differences, and asserts the blank census equals the source's (30 firm names, 57 websites, 9 evidence).
Gotcha worth remembering: openpyxl writes "" but reads it back as None, so the comparison must treat
those as equal - the first run reported 96 and 87 false mismatches for exactly that reason
(96 = 30 + 57 + 9, 87 = 30 + 57).
