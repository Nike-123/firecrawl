#!/usr/bin/env python3
"""Upsert Phase B firm-website findings into work/sites.jsonl, keyed by domain.

Reads a JSON array on stdin. Each record:
  domain    (required) normalised host, no www, lowercase -- the join key
  url       the URL actually fetched
  ok        bool, did the page load and render usable content
  firm_match bool, does the site's own branding match the Super Lawyers firm name
  note      evidence text, quoted from the site
  sns       list of serial numbers publishing this domain
Last write wins per domain, mirroring the builder's semantics.
"""
import json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(HERE, 'work', 'sites.jsonl')

def norm(d):
    d = (d or '').strip().lower()
    if '://' in d:
        d = d.split('://', 1)[1]
    d = d.split('/', 1)[0]
    return d[4:] if d.startswith('www.') else d

def main():
    incoming = json.load(sys.stdin)
    if not isinstance(incoming, list):
        sys.exit('stdin must be a JSON array')
    existing = {}
    order = []
    if os.path.exists(PATH):
        for line in open(PATH, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            k = norm(r['domain'])
            if k not in existing:
                order.append(k)
            existing[k] = r
    saved = 0
    for r in incoming:
        k = norm(r.get('domain'))
        if not k:
            print('SKIPPED record with no domain:', json.dumps(r)[:160]); continue
        r = dict(r); r['domain'] = k
        for f in ('url', 'note'):
            r.setdefault(f, '')
        for f in ('ok', 'firm_match'):
            r.setdefault(f, False)
        r.setdefault('sns', [])
        r['sns'] = sorted({int(x) for x in r['sns']})
        if k not in existing:
            order.append(k)
        existing[k] = r
        saved += 1
    with open(PATH, 'w', encoding='utf-8') as f:
        for k in order:
            f.write(json.dumps(existing[k], ensure_ascii=False) + '\n')
    print('sites saved:', saved, '| total domains:', len(order))
    todo = int(os.environ.get('NEXT_N', '12'))
    print('PENDING domains:', 216 and max(0, todo))
if __name__ == '__main__':
    main()
