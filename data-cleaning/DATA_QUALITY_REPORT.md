# Law Firm Dataset - Data Quality Report

**Source file:** `nIKET_data scrabe.csv`
**Prepared:** 07 Nov 2026
**Deliverables:** `law_firms_clean.csv`, `law_firms_verified.csv`, `Law_Firms_Cleaning_Report.xlsx`

## 1. Headline numbers

| Metric | Value |
|---|---|
| Data rows in source (excl. header) | 4560 |
| Duplicate rows removed | 475 |
| Unique firms after cleaning | 4085 |
| Websites verified (domain matches firm name) | 3348 |
| Websites kept but not verifiable | 528 |
| Firms flagged for review | 209 |
| Websites claimed by more than one firm name | 619 |

## 2. What was wrong

1. **Stray third column** - every line ended with an extra comma, so the CSV had an empty column.
2. **Mis-paired names and URLs (the big one).** For long stretches the URL column is alphabetically
   sorted while the firm names are not, e.g. `Wilmer Cutler Pickering Hale and Dorr LLP -> fowlerwhite.com`,
   `Jones Day -> grayreed.com`, `Alcyone Levy -> wshblaw.com`. This is what you get when two separately
   sorted lists are zipped together during scraping; it also explains most of the "duplicates".
3. **Duplicate firms** - 475 rows repeat an existing firm (same name, or same name with a
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
| `law_firms_clean.csv` | Full cleaned dataset (4085 firms) with status + notes. |
| `law_firms_verified.csv` | 3348 firms whose website is verified - ready for outreach. |
| `Law_Firms_Cleaning_Report.xlsx` | Workbook: Summary, Clean Data, Duplicates Removed, Website Conflicts, Needs Review, Field Definitions. |

## 5. Recommended next step

Re-scrape the 737 firms whose website could not be verified - the firm name is correct,
only the URL is uncertain. A targeted Firecrawl run on the firm name + location would recover those
websites cheaply.
