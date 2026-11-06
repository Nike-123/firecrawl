#!/usr/bin/env python3
"""Prepare the Google Sheets payload as copy-paste-ready chunk files.

The connector writes cell values inline, so every character has to pass through
model output. The full Notes column is 1,479,746 characters, which is not
feasible; this script therefore emits a COMPACT Notes edition for the sheet -
the first NOTE_CAP characters of the same Notes cell plus an explicit marker
giving the full length and pointing at the CSV/XLSX - and keeps every other
column complete and untruncated.

Writes work/sheets_chunk_NN.json, each one line of JSON in exactly the shape a
batch_update_values `data` element needs:

    {"range": "'IP Verification'!A2:L13", "values": [[...], [...]]}

plus work/sheets_tab_summary.json and work/sheets_tab_errorlog.json for the two
supporting tabs. Prints a manifest of chunk file, range, rows and characters.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'output')
WORK = os.path.join(HERE, 'work')

SHEET = "'IP Verification'"
NOTE_CAP = 500
CHUNK_CHARS = 17000

rows = list(csv.DictReader(open(os.path.join(OUT, 'Super_Lawyers_IP_Verification.csv'),
                                encoding='utf-8-sig')))
cols = list(rows[0].keys())


def compact_note(v):
    if len(v) <= NOTE_CAP:
        return v
    return (v[:NOTE_CAP].rstrip()
            + ' [... FULL NOTE: %d chars, complete text in Super_Lawyers_IP_Verification.csv'
              ' and .xlsx]' % len(v))


values = []
for r in rows:
    values.append([compact_note(r[c]) if c == 'Notes' else r[c] for c in cols])

chunks = []
# header
chunks.append((SHEET + '!A1:L1', [cols]))
start = 2
i = 0
while i < len(values):
    block = []
    size = 0
    j = i
    while j < len(values):
        n = len(json.dumps(values[j], ensure_ascii=False))
        if block and size + n > CHUNK_CHARS:
            break
        block.append(values[j])
        size += n
        j += 1
    rng = '%s!A%d:L%d' % (SHEET, start + i, start + i + len(block) - 1)
    chunks.append((rng, block))
    i = j

manifest = []
for k, (rng, block) in enumerate(chunks):
    path = os.path.join(WORK, 'sheets_chunk_%02d.json' % k)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({'range': rng, 'values': block}, fh, ensure_ascii=False)
    manifest.append((os.path.basename(path), rng, len(block), os.path.getsize(path)))

# supporting tabs
for name, src, tabfile in (('Summary', 'Summary.txt', 'sheets_tab_summary.json'),
                           ('Error Log', 'Error_Log.txt', 'sheets_tab_errorlog.json')):
    lines = open(os.path.join(OUT, src), encoding='utf-8').read().rstrip('\n').split('\n')
    blocks = []
    cur = []
    size = 0
    for ln in lines:
        n = len(ln) + 8
        if cur and size + n > CHUNK_CHARS:
            blocks.append(cur)
            cur = []
            size = 0
        cur.append([ln])
        size += n
    if cur:
        blocks.append(cur)
    payload = []
    row = 1
    for b in blocks:
        payload.append({'range': "'%s'!A%d:A%d" % (name, row, row + len(b) - 1), 'values': b})
        row += len(b)
    with open(os.path.join(WORK, tabfile), 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False)
    manifest.append((tabfile, '%s!A1:A%d' % (name, len(lines)), len(lines),
                     os.path.getsize(os.path.join(WORK, tabfile))))

print('%-26s %-28s %5s %9s' % ('file', 'range', 'rows', 'bytes'))
tot = 0
for m in manifest:
    print('%-26s %-28s %5d %9d' % m)
    tot += m[3]
print('%-26s %-28s %5d %9d' % ('TOTAL', '', len(rows), tot))
print('')
print('main-sheet chunks:', len(chunks), '| Notes cap:', NOTE_CAP,
      '| compact Notes total chars:', sum(len(v[10]) for v in values))
print('other columns total chars:',
      sum(len(v[k]) for v in values for k in range(12) if k != 10))
