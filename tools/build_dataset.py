#!/usr/bin/env python3
"""Raw scrape (data/ipcommunity_all.csv) se clean, dedupe kiya hua deliverable banao."""
import csv
import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

SRC = Path("data/ipcommunity_all.csv")
OUT_LIVE = Path("ipcommunity_all_live_records.csv")
OUT_FINAL = Path("ipcommunity_1000_verified_firms.csv")
OUT_HTML = Path("ipcommunity_firms.html")

JUNK_DOMAINS = {
    "aol.com", "earthlink.net", "gmail.com", "yahoo.com", "hotmail.com", "msn.com",
    "comcast.net", "verizon.net", "sbcglobal.net", "att.net", "bellsouth.net", "juno.com",
    "prodigy.net", "netzero.net", "cs.com", "webtv.net", "ix.netcom.com", "mindspring.com",
    "pacbell.net", "covad.net", "peoplepc.com", "excite.com", "lycos.com", "mac.com",
    "me.com", "icloud.com", "outlook.com", "live.com", "aim.com", "compuserve.com",
    "btinternet.com", "ntlworld.com", "bigpond.com", "shaw.ca", "rogers.com",
    "sympatico.ca", "telus.net", "qq.com", "163.com", "126.com", "sina.com", "naver.com",
    "daum.net", "hanmail.net", "rediffmail.com", "googlemail.com", "google.com",
    "wixsite.com", "wordpress.com", "business.site", "godaddysites.com", "weebly.com",
    "blogspot.com", "tumblr.com", "linkedin.com", "facebook.com", "x.com", "twitter.com",
}

PRACTICE = ["Trademark", "Patent", "Copyright", "Design", "Licensing", "Litigation",
            "Domain Names", "Trade Secrets", "IP Portfolio", "Enforcement"]

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI",
    "wyoming": "WY", "district of columbia": "DC", "puerto rico": "PR", "guam": "GU",
    "virgin islands": "VI",
}
ABBREVS = set(STATES.values())


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def clean_practice(raw: str) -> str:
    found, low = [], (raw or "").lower()
    for p in PRACTICE:
        if p.lower() in low and p not in found:
            found.append(p)
    return ", ".join(found) if found else (raw or "").split(",")[0].strip()


def clean_state(rec: dict) -> str:
    # 0) ipcommunity me 'zip' field actually "MA 02021" jaisa hota hai
    for blob in (rec.get("zip", "") or "", rec.get("address", "") or ""):
        m = re.search(r"\b([A-Z]{2})\s+\d{5}", blob)
        if m and m.group(1) in ABBREVS:
            return m.group(1)
    # 1) address me "TX 75093" pattern
    addr = rec.get("address", "") or ""
    m = re.search(r"\b([A-Z]{2})\s+\d{5}", addr)
    if m and m.group(1) in ABBREVS:
        return m.group(1)
    # 2) state/region fields
    for cand in (rec.get("state", ""), *rec.get("region", "").split(",")):
        c = (cand or "").strip()
        low = c.lower()
        if low in STATES:
            return STATES[low]
        if len(c) == 2 and c.upper() in ABBREVS:
            return c.upper()
    # 3) address me state ka poora naam
    for name, ab in STATES.items():
        if re.search(rf"\b{name}\b", addr, re.I):
            return ab
    return ""


def clean_city(rec: dict) -> str:
    city = (rec.get("city", "") or "").strip().strip(",")
    if city and city.lower() not in ("zip code", "city", "state", "usa", "country"):
        return city.title() if city.isupper() else city
    addr = rec.get("address", "") or ""
    m = re.search(r",\s*([A-Za-z .'-]+),\s*[A-Z]{2}\s*\d{5}", addr)
    if m:
        return m.group(1).strip()
    parts = [p.strip() for p in (rec.get("region", "") or "").split(",") if p.strip()]
    if parts:
        return parts[0].title() if parts[0].isupper() else parts[0]
    return ""


def norm_name(n: str) -> str:
    n = re.sub(r"\b(llp|llc|pc|p\.c\.|ltd|law offices?|law firm|attorney|atty|esq)\b", "", n.lower())
    return re.sub(r"[^a-z0-9]", "", n)


def main() -> None:
    rows = list(csv.DictReader(SRC.open()))
    print(f"raw rows: {len(rows)}")

    live = [r for r in rows if r["verification"] == "LIVE" and host(r["website_final"]) not in JUNK_DOMAINS]
    print(f"live (junk email/ISP domains hatane ke baad): {len(live)}")

    for r in live:
        r["website"] = r["website_final"].rstrip("/")
        r["domain"] = host(r["website_final"])
        r["practice_clean"] = clean_practice(r["practice_areas"])
        r["state_clean"] = clean_state(r)
        r["city_clean"] = clean_city(r)
        zm = re.search(r"\b(\d{5}(?:-\d{4})?)\b", (r["zip"] or "") + " " + (r["address"] or ""))
        r["zip_clean"] = zm.group(1) if zm else ""

    def classify(name: str) -> str:
        n = name.lower()
        if re.search(r"law|attorney|legal|patent|trademark|counsel|esq|llp|pllc|\bllc\b|plc|"
                     r"\bp\.?c\.?\b|\bpa\b|\bltd\b|associat|law offices?|litigation|intellectual",
                     n):
            return "law_firm"
        return "company_other"

    for r in live:
        r["entity_type"] = classify(r["firm_name"])

    # ---- file 1: saare live records
    cols1 = ["firm_name", "practice_clean", "entity_type", "address", "city_clean",
             "state_clean", "zip_clean", "website", "domain", "profile_url", "http_status",
             "checked_at"]
    with OUT_LIVE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["firm_name", "practice_areas", "entity_type", "address", "city", "state",
                    "zip", "website", "domain", "ipcommunity_profile", "http_status", "checked_at"])
        for r in sorted(live, key=lambda x: (x["state_clean"], x["firm_name"].lower())):
            w.writerow([r[c] for c in cols1])
    print(f"wrote {OUT_LIVE} ({len(live)} rows)")

    # ---- file 2: ek website = ek firm (dedupe), 1000 tak
    seen: set[str] = set()
    final = []
    for r in sorted(live, key=lambda x: (x["state_clean"] or "ZZ", x["firm_name"].lower())):
        if r["domain"] in seen:
            continue
        seen.add(r["domain"])
        final.append(r)
    final = final[:1000]
    law_firms = [r for r in final if r["entity_type"] == "law_firm"]
    with OUT_FINAL.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["#", "firm_name", "practice_areas", "type", "address", "city", "state",
                    "zip", "website", "profile_url", "verified_on"])
        for i, r in enumerate(final, 1):
            w.writerow([i, r["firm_name"], r["practice_clean"], r["entity_type"], r["address"],
                        r["city_clean"], r["state_clean"], r["zip_clean"], r["website"],
                        r["profile_url"], r["checked_at"]])
    print(f"wrote {OUT_FINAL} ({len(final)} unique-website firms)")

    with Path("ipcommunity_law_firms_only.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["#", "firm_name", "practice_areas", "address", "city", "state", "zip",
                    "website", "profile_url", "verified_on"])
        for i, r in enumerate(law_firms, 1):
            w.writerow([i, r["firm_name"], r["practice_clean"], r["address"], r["city_clean"],
                        r["state_clean"], r["zip_clean"], r["website"], r["profile_url"],
                        r["checked_at"]])
    print(f"wrote ipcommunity_law_firms_only.csv ({len(law_firms)} rows)")

    # ---- HTML browser
    def esc(s: str) -> str:
        return html.escape(str(s or ""))

    body = "\n".join(
        f"<tr><td>{i}</td><td>{esc(r['firm_name'])}</td><td>{esc(r['practice_clean'])}</td>"
        f"<td>{esc(r['city_clean'])}</td><td>{esc(r['state_clean'])}</td>"
        f"<td><a href='{esc(r['website'])}' target='_blank' rel='noopener'>{esc(r['domain'])}</a></td></tr>"
        for i, r in enumerate(final, 1))
    OUT_HTML.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<title>IP law firms — verified websites ({len(final)})</title>
<style>
body{{font-family:system-ui,sans-serif;margin:24px;color:#111}}
h1{{font-size:20px}} .meta{{color:#666;font-size:13px;margin-bottom:16px}}
input{{padding:8px 10px;width:320px;border:1px solid #ccc;border-radius:6px;margin-bottom:12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid #e5e5e5;padding:6px 8px;text-align:left;vertical-align:top}}
th{{position:sticky;top:0;background:#fafafa;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
tr:hover{{background:#f7fbff}} a{{color:#0b64d0;text-decoration:none}}
</style></head><body>
<h1>IP law firms — verified live websites</h1>
<div class="meta">{len(final)} unique firms · source: ipcommunity.org (USA, 38,059 members scanned) ·
every website checked live on {esc(final[0]['checked_at'] if final else '')}</div>
<input id="q" placeholder="Search firm, city, state, practice…" oninput="f()">
<table id="t"><thead><tr><th>#</th><th>Firm</th><th>Practice</th><th>City</th><th>State</th><th>Website</th></tr></thead>
<tbody>
{body}
</tbody></table>
<script>function f(){{const q=document.getElementById('q').value.toLowerCase();
for(const r of document.querySelectorAll('#t tbody tr')){{
r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none';}}}}</script>
</body></html>""")
    print(f"wrote {OUT_HTML}")

    stats = {
        "source_members_total": 38059,
        "profiles_scanned": len(rows),
        "live_verified_records": len(live),
        "unique_websites": len(seen),
        "delivered_rows": len(final),
        "law_firm_rows": len(law_firms),
        "top_states": Counter(r["state_clean"] for r in final).most_common(10),
        "practice_mix": Counter(r["practice_clean"] for r in final).most_common(8),
    }
    Path("dataset_summary.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
