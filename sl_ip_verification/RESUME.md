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

## Known blocker for a Google Sheets export

The Notes column totals **1,479,640 characters** (~370 k tokens) across 216 rows. The Sheets
connector passes every cell value inline through model output, so pushing full Notes into a
sheet is not feasible in any reasonable number of `batch_update_values` calls. The XLSX and CSV
in `output/` carry the full text and can be imported into Sheets directly (a cell holds up to
50,000 characters; the longest note here is 13,474). Alternatives if a native sheet is required:
truncated Notes in Sheets plus the full CSV as the record, or full Notes for a named subset.
