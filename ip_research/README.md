# US IP Law Firms — FindLaw State-wise Research

Primary source: **https://lawyers.findlaw.com/patents/** (with FindLaw's `lawyers.findlaw.com/intellectual-property-law/`,
`/trademarks/` and `/copyrights/` category pages, FindLaw firm/attorney profile pages, and — where the patents city pages
are client-rendered and return an empty shell to the fetcher — FindLaw-network listing data from Lawyers.com).

## Deliverables

| File | Contents |
|---|---|
| `US_IP_Law_Firms_Master.xlsx` | `Master` worksheet (all records) + 51 jurisdiction worksheets, 4 columns each, clickable website URLs |
| `US_IP_Law_Firms_Master.csv` | Combined dataset, UTF-8, 4 columns, de-duplicated |
| `Processing_Checkpoint.json` | Per-state status, counts, pages/listing reviewed, limitations |

Columns, in order: `State`, `Law Firm Name`, `Official Website URL`, `Attorney / Person Name`.
One row per (firm, attorney). A firm with no attributable attorney keeps a single row with a blank attorney field.
No emails, phones, addresses, ratings or descriptions are stored.

## Pipeline

```
data/records.json            project header, research order, access notes
data/states/NN-<state>.json  one file per jurisdiction (status, pages reviewed, limitations, firms)
scripts/build.py             builds XLSX + CSV + checkpoint from the state files
```

Rebuild after editing any state file:

```bash
python3 scripts/build.py
```

## Rules enforced by the builder

* Directory URLs (findlaw.com, lawyers.com, avvo.com, justia.com, linkedin.com, martindale.com, superlawyers.com, …)
  are **never** accepted as an official firm website — they are blanked if found.
* Duplicate `(state, firm, attorney)` records are dropped; firm names are whitespace-normalised.
* Verified vs unverified websites, and records needing manual review, are tracked in the checkpoint only —
  never in the four output columns.
* States with no eligible listing keep a state spreadsheet containing an explanatory note rather than invented rows.

## Coverage honesty

* `completed` — every FindLaw listing page and pagination page reachable for that jurisdiction was reviewed
  (typically states whose city pages report "Results 1 to N of N").
* `partial` — listings were found but pagination or additional city pages could not be fully enumerated through the
  fetch layer (large markets: California, New York, Texas, Illinois, Massachusetts, Pennsylvania, Ohio, Washington,
  New Jersey, Maryland, Virginia, Tennessee, North Carolina-adjacent metros). The state's `limitations` string in the
  checkpoint names exactly what was and was not reviewed.
* Nationwide sponsored placements (NovoTech Patent Firm, Ream Law Firm, The Simon Law Firm, Goldstein Law Offices,
  Sisun Law, AU LLC, Zoe Bernstein Law, Dale Jensen PLC, Stange Law Firm, Morgan & Morgan, etc.) were **not**
  attributed to a state unless the firm has an office there.
* Firms surfaced by FindLaw's patents category but whose profile shows no IP practice (personal injury, family law,
  criminal defence, securities litigation) were excluded — e.g. `Law Offices of Roger H. Sigal` (criminal defence),
  `Littman Family Law`, `Stange Law Firm`, `Bernstein Litowitz Berger & Grossmann`, `Marsh, Rickard & Bryan`,
  `Goldman & Associates`, `Morgan & Morgan`, `Paule, Camazine & Blumenthal`.
* Where an official website could not be captured from the listing, the field is **blank** and the record is flagged
  `needs_review` in the checkpoint rather than guessing a domain.
