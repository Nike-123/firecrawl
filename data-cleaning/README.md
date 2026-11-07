# Law-firm list — cleaning & de-duplication

Cleans the scraped `Firm Name, Official Website URL` dataset (4,560 rows) into a
de-duplicated, normalised firm list with an auditable QA trail.

## Run

```bash
pip install openpyxl          # only external dependency
python clean_data.py                      # uses raw/law_firms_raw.csv
python clean_data.py path/to/other.csv     # any file with the same two columns
```

## Outputs

| File | What it is |
|---|---|
| `law_firms_clean.csv` | One row per unique firm (4,085): cleaned name, recommended website, domain, URL type, name↔domain match score, QA status, notes, source line. |
| `law_firms_verified.csv` | 3,348 firms whose website is verified against the firm name — ready for outreach. |
| `Law_Firms_Cleaning_Report.xlsx` | Summary · Clean Data · Duplicates Removed · Website Conflicts · Needs Review · Field Definitions. |
| `DATA_QUALITY_REPORT.md` | Written summary of the problems found and the rules applied. |

## Pipeline

1. **Parse & repair** – drops the stray empty third column every line had, fixes UTF-8-read-as-latin-1
   names (`ArÃªte` → `Arête`), tidies spacing and symbols (`®`, `™`, `•`).
2. **Classify URLs** – official homepage / deep link / directory profile (Avvo, Lawyers.com, LinkedIn…) / invalid.
3. **Normalise** – scheme present, host lower-cased, `www.` removed, trailing slash, tracking parameters
   and `#fragments` stripped.
4. **De-duplicate** – normalised firm name (case, spacing, punctuation, entity suffixes ignored), then
   same-website and two-token name variants (`WilmerHale` = `Wilmer Cutler Pickering Hale and Dorr LLP`).
   Every dropped row is logged with the row that was kept.
5. **Evidence check** – the domain must textually support the firm name before a URL is recommended.
   Where a website provably belongs to another firm in the file, the firm is kept, the URL moves to
   `Source URL` and the row is flagged — nothing is guessed or silently deleted.
6. **Export** – CSVs, formatted workbook, markdown report. Row accounting is asserted:
   `source rows == unique firms + duplicate rows`.
