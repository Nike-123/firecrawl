#!/usr/bin/env python3
"""Integrity check on the built deliverables.

Verifies:
  * the CSV and the XLSX hold identical values in all 12 columns for all rows;
  * the CSV carries a UTF-8 BOM so Excel opens it correctly;
  * Serial Numbers are 1..216, contiguous, unique, integers in the XLSX;
  * every profile row still has all 18 keys;
  * the single verification date;
  * how many cells are empty and which columns they sit in;
  * Notes length statistics.
Prints PASS/FAIL per check and exits non-zero on any failure.
"""
import csv
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'output')
CSV = os.path.join(OUT, 'Super_Lawyers_IP_Verification.csv')
XLSX = os.path.join(OUT, 'Super_Lawyers_IP_Verification.xlsx')
PROF = os.path.join(HERE, 'work', 'profiles.jsonl')

REQUIRED_KEYS = ['sn', 'date', 'status', 'firm', 'site', 'prof_web', 'addr', 'phone', 'areas',
                 'pct', 'focus', 'selections', 'admitted', 'education', 'languages', 'fvs',
                 'solo_evidence', 'note']

fails = []


def check(label, ok, detail=''):
    print('%-4s %s%s' % ('PASS' if ok else 'FAIL', label, (' -- ' + detail) if detail else ''))
    if not ok:
        fails.append(label)


# ---- BOM -------------------------------------------------------------------
raw = open(CSV, 'rb').read(3)
check('CSV starts with a UTF-8 BOM', raw == b'\xef\xbb\xbf', repr(raw))

# ---- CSV -------------------------------------------------------------------
with open(CSV, encoding='utf-8-sig', newline='') as fh:
    crows = list(csv.DictReader(fh))
check('CSV row count is 216', len(crows) == 216, str(len(crows)))

# ---- XLSX ------------------------------------------------------------------
from openpyxl import load_workbook
wb = load_workbook(XLSX, read_only=True)
ws = wb.active
xrows = list(ws.iter_rows(values_only=True))
header = [str(c) if c is not None else '' for c in xrows[0]]
body = xrows[1:]
check('XLSX row count is 216', len(body) == 216, str(len(body)))
check('XLSX header matches the CSV header', header == list(crows[0].keys()),
      str(header) if header != list(crows[0].keys()) else '')


def s(v):
    return '' if v is None else str(v).strip()


mismatch = 0
first_bad = None
for i, (cr, xr) in enumerate(zip(crows, body), start=2):
    for col in header:
        a = s(cr.get(col))
        b = s(dict(zip(header, xr)).get(col))
        if a != b:
            mismatch += 1
            if first_bad is None:
                first_bad = (i, col, a[:60], b[:60])
check('CSV and XLSX agree cell for cell', mismatch == 0,
      '%d mismatches, first at %s' % (mismatch, first_bad) if mismatch else '')

sns = [dict(zip(header, xr))['Serial Number'] for xr in body]
check('Serial Number is an int in the XLSX', all(isinstance(x, int) for x in sns))
check('Serial Numbers are 1..216 contiguous and unique',
      sorted(sns) == list(range(1, 217)), '%d values, %d unique' % (len(sns), len(set(sns))))

dates = {s(dict(zip(header, xr))['Verification Date']) for xr in body}
check('exactly one verification date', dates == {'2026-11-06'}, str(dates))

# ---- empty cells -----------------------------------------------------------
empties = {}
for xr in body:
    d = dict(zip(header, xr))
    for col in header:
        if s(d.get(col)) == '':
            empties[col] = empties.get(col, 0) + 1
print('     empty cells per column: %s' % (empties if empties else 'none'))
check('no empty cells in the identity or status columns',
      all(empties.get(c, 0) == 0 for c in
          ('Serial Number', 'Person Name', 'Super Lawyers Profile URL',
           'Current Law Firm Name', 'Firm Verification Status',
           'Website Verification Status', 'Evidence URL', 'IP Practice Evidence',
           'Notes', 'Verification Date')), str(empties))

# ---- profiles.jsonl schema -------------------------------------------------
prof = [json.loads(l) for l in open(PROF, encoding='utf-8') if l.strip()]
check('profiles.jsonl holds 216 records', len(prof) == 216, str(len(prof)))
missing = [(r['sn'], [k for k in REQUIRED_KEYS if k not in r]) for r in prof
           if any(k not in r for k in REQUIRED_KEYS)]
check('every profile row has all 18 keys', not missing, str(missing[:5]))
check('profile sns are 1..216', sorted(r['sn'] for r in prof) == list(range(1, 217)))

# ---- notes statistics ------------------------------------------------------
nl = [len(s(dict(zip(header, xr))['Notes'])) for xr in body]
print('     Notes characters: min %d, median %d, max %d, total %d'
      % (min(nl), int(statistics.median(nl)), max(nl), sum(nl)))
check('no Notes cell exceeds Excel\'s 32,767-character limit', max(nl) <= 32767, str(max(nl)))
check('every Notes cell is at least 500 characters', min(nl) >= 500, str(min(nl)))

print('')
print('RESULT: %s' % ('ALL CHECKS PASSED' if not fails else 'FAILURES: %s' % fails))
sys.exit(1 if fails else 0)
