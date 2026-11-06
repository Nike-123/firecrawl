import json, sys, os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = 'work/profiles.jsonl'
recs = []
if os.path.exists(P):
    recs = [json.loads(l) for l in open(P, encoding='utf-8')]
by = {r['sn']: i for i, r in enumerate(recs)}
raw = sys.stdin.read().strip()
new = json.loads(raw) if raw else []
for r in new:
    if r['sn'] in by:
        recs[by[r['sn']]] = r
    else:
        recs.append(r)
recs.sort(key=lambda x: x['sn'])
with open(P, 'w', encoding='utf-8') as fh:
    for r in recs:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
done = {r['sn'] for r in recs}
print("profiles saved:", len(recs), "| sns:", min(done), "-", max(done))

# next N urls not yet done, exact strings from the input file
N = int(os.environ.get('NEXT_N', '10'))
inp = json.load(open('work/input_records.json', encoding='utf-8'))
pend = [r for r in inp if r['sn'] not in done]
print("PENDING profiles:", len(pend))
for r in pend[:N]:
    print("%3d %s" % (r['sn'], r['url']))
