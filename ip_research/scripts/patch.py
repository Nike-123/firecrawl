#!/usr/bin/env python3
"""Apply verification updates to state research files.

Usage:  python3 scripts/patch.py updates.json

updates.json = list of objects:
  {"state": "Illinois", "firm": "Mudd Law",
   "website": "https://www.muddlawoffices.com/",      # optional
   "website_verified": true,                          # optional
   "verification": "text evidence",                   # optional
   "attorneys_add": ["Name"],                          # optional
   "needs_review": false,                              # optional
   "drop": false}                                      # optional -> remove firm
"""
import json
import pathlib
import sys

STATES = pathlib.Path(__file__).resolve().parents[1] / "data" / "states"


def norm(s):
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def main(path):
    updates = json.load(open(path, encoding="utf-8"))
    files = {}
    for f in STATES.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        files[d["state"]] = (f, d)
    applied, missed = 0, []
    for u in updates:
        state = u["state"]
        if state not in files:
            missed.append((state, u["firm"], "unknown state"))
            continue
        f, d = files[state]
        hit = None
        for firm in d["firms"]:
            if norm(firm["firm"]) == norm(u["firm"]):
                hit = firm
                break
        if hit is None:
            missed.append((state, u["firm"], "firm not found"))
            continue
        if u.get("drop"):
            d["firms"].remove(hit)
            applied += 1
            continue
        if "website" in u:
            hit["website"] = u["website"]
        if "website_verified" in u:
            hit["website_verified"] = u["website_verified"]
        if "verification" in u:
            hit["verification"] = u["verification"]
        for name in u.get("attorneys_add", []):
            if name not in hit.setdefault("attorneys", []):
                hit["attorneys"].append(name)
        if "needs_review" in u:
            if u["needs_review"]:
                hit["needs_review"] = True
            else:
                hit.pop("needs_review", None)
        applied += 1
    # persist only files that changed
    touched = {u["state"] for u in updates if u["state"] in files}
    for state in touched:
        f, d = files[state]
        f.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # audit log (append-only)
    import datetime
    audit = STATES.parent / "audit_log.jsonl"
    with open(audit, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                             "source": path, "applied": applied, "missed": missed,
                             "updates": updates}, ensure_ascii=False) + "\n")
    print(f"applied={applied} missed={len(missed)}")
    for m in missed:
        print("  MISS:", *m)


if __name__ == "__main__":
    main(sys.argv[1])
