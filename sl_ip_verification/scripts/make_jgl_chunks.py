#!/usr/bin/env python3
"""Build the Google Sheets payload for the Just Great Lawyers tab.

Reads input_original/just_great_lawyers_original.csv (the user's upload, copied
byte-identically) and writes work/jgl_chunk_NN.json files, each one a single line
of JSON shaped for the Sheets connector:

    {"range": "'Just Great Lawyers'!A2:D60", "values": [[...], ...]}

Four columns only: Serial Number, Person Name, Law Firm Name,
Official Firm Website URL.  Values are copied EXACTLY as published in the
upload - no normalisation, no invented data.  Blank cells stay blank.

Chunks are capped so that each file stays well under the bash stdout cap and
each emitted tool call stays under a practical payload ceiling.
"""

import csv
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "input_original", "just_great_lawyers_original.csv")
WORK = os.path.join(ROOT, "work")
TAB = "Just Great Lawyers"
CHUNK_CHARS = 11000

COLUMNS = [
    ("Serial Number", "Serial Number"),
    ("Person Name", "Person Name"),
    ("Law Firm Name", "Law Firm Name"),
    ("Official Firm Website URL", "Official Firm Website URL"),
]


def main():
    raw = open(SRC, "rb").read()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    print("source rows:", len(rows))

    values = []
    for r in rows:
        values.append([r[src_col].strip() for _, src_col in COLUMNS])

    chunks = []
    current = []
    size = 0
    for v in values:
        cost = len(json.dumps(v, ensure_ascii=False))
        if current and size + cost > CHUNK_CHARS:
            chunks.append(current)
            current = []
            size = 0
        current.append(v)
        size += cost
    if current:
        chunks.append(current)

    row = 2  # row 1 is the header
    written = []
    for i, chunk in enumerate(chunks):
        start = row
        end = row + len(chunk) - 1
        payload = {
            "range": "'%s'!A%d:D%d" % (TAB, start, end),
            "values": chunk,
        }
        path = os.path.join(WORK, "jgl_chunk_%02d.json" % i)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False))
        written.append((path, payload["range"], len(chunk), os.path.getsize(path)))
        row = end + 1

    for path, rng, n, size in written:
        print("%-28s %-32s rows=%3d bytes=%d" % (os.path.basename(path), rng, n, size))
    print("chunks:", len(written), "total rows:", row - 2, "last row:", row - 1)

    blank_firm = [v[0] for v in values if not v[2]]
    blank_site = [v[0] for v in values if not v[3]]
    print("blank Law Firm Name:", len(blank_firm), blank_firm)
    print("blank Official Firm Website URL:", len(blank_site), blank_site)


if __name__ == "__main__":
    main()
