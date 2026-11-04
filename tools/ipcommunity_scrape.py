#!/usr/bin/env python3
"""
ipcommunity.org -> verified IP law-firm list (target: 1000 firms with a WORKING website).

Strategy (based on live probing of the site):
  * listing table is prerendered by the server (15 rows/page) -> raw HTTP works
  * pagination is a Blazor "Fluent UI" pager: <fluent-button aria-label="Go to next page">
    => needs a real browser to click through
  * each /member/<id>/<slug> profile page is also prerendered -> parse with requests
  * the "Web" field is often malformed ("https://http//www.foo.com") or junk -> must verify

Pipeline:
  1. playwright page: collect 15 member URLs -> hand them to a worker pool
  2. workers: HTTP GET profile -> parse name/areas/address/web -> verify website
  3. stop as soon as N verified LIVE websites collected
Outputs (committed back to the repo):
  data/ipcommunity_all.csv     - every profile checked (+status)
  data/ipcommunity_live.csv    - only LIVE, de-duplicated by domain (the deliverable)
  data/ipcommunity_stats.json  - counters
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright

BASE = "https://www.ipcommunity.org"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
SITE_SOCIALS = ("x.com/iprcommunity", "linkedin.com/in/ipcommunity",
                "facebook.com/pages/ip-attorneys-community", "jsksoftware.com",
                "ipcommunity.org", "twitter.com/iprcommunity")

PARKED = ["hugedomains", "domain is for sale", "this domain is for sale", "buy this domain",
          "buy now", "sedo", "afternic", "parkingcrew", "bodis", "dan.com", "undeveloped",
          "domain parking", "this page is parked", "godaddy", "namecheap", "site not found",
          "account suspended", "coming soon", "under construction", "web page is parked",
          "domain for sale", "purchased domain", "website is for sale"]
SOCIAL = ("facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com",
          "youtube.com", "tiktok.com")
BAD = ("ibm.net", "example.com", "domain.com", "yourdomain.com")

FIELDS = ["firm_name", "practice_areas", "entity_type", "address", "city", "state", "zip",
          "region", "website_declared", "website_final", "http_status", "verification",
          "page_title", "profile_url", "checked_at", "notes"]

lock = threading.Lock()
debug_left = [40]
seen_ids: set[str] = set()
seen_domains: set[str] = set()
rows: list[dict] = []
live: list[dict] = []
counts: Counter = Counter()


PROGRESS = Path("data/progress.log")


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        PROGRESS.parent.mkdir(parents=True, exist_ok=True)
        with PROGRESS.open("a") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def git_checkpoint(note: str, include_csv: bool = False) -> None:
    """Actions runner se progress repo me push karo (sandbox me logs block hain)."""
    import os
    import subprocess
    branch = os.environ.get("GITHUB_REF_NAME", "")
    if not branch:
        return
    try:
        subprocess.run(["git", "add", "-f", "data/progress.log"], check=False,
                       capture_output=True, timeout=60)
        if include_csv:
            for f in ("data/ipcommunity_all.csv", "data/ipcommunity_live.csv",
                      "data/ipcommunity_stats.json", "data/debug_anchors.txt"):
                subprocess.run(["git", "add", "-f", f], check=False,
                               capture_output=True, timeout=60)
        subprocess.run(["git", "commit", "-m", f"data: {note} [skip ci]"], check=False,
                       capture_output=True, timeout=60)
        subprocess.run(["git", "pull", "--rebase", "origin", branch], check=False,
                       capture_output=True, timeout=120)
        subprocess.run(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], check=False,
                       capture_output=True, timeout=120)
    except Exception:
        pass


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def host_of(u: str) -> str:
    try:
        return (urlparse(u).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def clean_site(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    s = re.sub(r"^https?:(//)?", "", s)
    s = re.sub(r"^//", "", s)
    s = s.strip("/ ")
    if not s or "." not in s or " " in s:
        return None
    return "https://" + s


# ------------------------------------------------------------------ profile parse

def extract_web(soup, html: str) -> str:
    """Profile page se website nikalo.

    Strategy: document order me pehla external anchor jo domain jaisa dikhe,
    site ke apne social/vendor links aur mailto/tel ko chhod ke.
    """
    cands = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        text = a.get_text(" ", strip=True)
        if href.lower().startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        blob = text if "." in text and " " not in text else href
        blob = html_unescape(blob)
        blob = blob.replace("https://http://", "").replace("https://http//", "")
        blob = blob.replace("http://http://", "").replace("http://http//", "")
        blob = re.sub(r"^https?://(https?://)", r"\1", blob)
        low = blob.lower()
        if "." not in blob or low.startswith(("mailto", "tel")):
            continue
        if any(s in low for s in SITE_SOCIALS):
            continue
        if "ipcommunity.org" in low:
            continue
        cands.append((href, blob))
    return cands


def html_unescape(t: str) -> str:
    import html as _h
    return _h.unescape(t or "")


def parse_profile(html: str) -> dict:
    from bs4 import BeautifulSoup

    out = {"firm_name": "", "practice_areas": "", "address": "", "city": "", "state": "",
           "zip": "", "website_declared": "", "debug": ""}
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if h1:
        out["firm_name"] = h1.get_text(" ", strip=True)

    areas = re.findall(r"practicearea=([a-z]+)", html)
    names = [a.strip().capitalize() for a in dict.fromkeys(areas)]
    kw = re.findall(r"searchkeyword=[^\"&]+\"[^>]*>(?:<[^>]+>)*\s*([^<]{2,60})</a>", html)
    for k in kw:
        k = html_unescape(k).strip()
        if k and k.lower() not in [n.lower() for n in names]:
            names.append(k)
    out["practice_areas"] = ", ".join(n for n in dict.fromkeys(names) if n)

    cands = extract_web(soup, html)
    out["debug"] = " | ".join(f"{b}" for _, b in cands[:4])
    if cands:
        out["website_declared"] = clean_site(cands[0][1]) or ""

    txt = soup.get_text("\n", strip=True)
    am = re.search(r"Address\s*\n(.{0,200}?)\n(City|Postal Address)", txt, re.S)
    if am:
        out["address"] = re.sub(r"\s+", " ", am.group(1)).strip(" ,")
    for key, label in (("city", "City"), ("state", "State"), ("zip", "Zip Code")):
        km = re.search(rf"^{label}\s*\n([^\n]{{1,60}})$", txt, re.M)
        if km:
            out[key] = km.group(1).strip()
    return out


def verify(site: str) -> tuple[str, str, str, str]:
    if not site:
        return "NO_WEBSITE", "", "", ""
    h = host_of(site)
    if h in BAD or ".ipt" in h:
        return "INVALID", "", "", "junk entry in directory"
    if any(h == s or h.endswith("." + s) for s in SOCIAL):
        return "SOCIAL_ONLY", site, "", ""
    try:
        r = requests.get(site, timeout=12, allow_redirects=True,
                         headers={"User-Agent": UA, "Accept-Language": "en"})
        final = r.url
        title = ""
        mt = re.search(r"<title[^>]*>(.*?)</title>", r.text or "", re.I | re.S)
        if mt:
            title = re.sub(r"\s+", " ", mt.group(1)).strip()[:120]
        body = (r.text or "")[:80000].lower()
        fh = host_of(final)
        if r.status_code >= 400:
            return "DEAD", final, str(r.status_code), f"HTTP {r.status_code}"
        if any(p in body for p in PARKED) or any(x in fh for x in
                                                 ("hugedomains", "sedo", "afternic", "dan.com", "parking")):
            return "PARKED", final, str(r.status_code), "domain for sale / parked"
        if any(fh == s or fh.endswith("." + s) for s in SOCIAL):
            return "SOCIAL_ONLY", final, str(r.status_code), ""
        if fh and h and fh != h and h not in fh and fh not in h:
            return "REDIRECT_OTHER", final, str(r.status_code), f"redirect -> {fh}"
        return "LIVE", final, str(r.status_code), ""
    except requests.exceptions.SSLError:
        return "DEAD", site, "", "SSL error"
    except requests.exceptions.Timeout:
        return "DEAD", site, "", "timeout"
    except Exception as e:  # noqa: BLE001
        return "DEAD", site, "", type(e).__name__


def process_one(item: dict, target: int) -> None:
    mid = item["id"]
    with lock:
        if mid in seen_ids:
            return
        seen_ids.add(mid)
        if len(live) >= target:
            return

    try:
        r = requests.get(item["url"], timeout=25, headers={"User-Agent": UA})
        rec = parse_profile(r.text) if r.status_code == 200 else {
            "firm_name": item["name"], "practice_areas": item["practice"],
            "address": "", "city": "", "state": "", "zip": "", "website_declared": ""}
    except Exception as e:  # noqa: BLE001
        rec = {"firm_name": item["name"], "practice_areas": item["practice"],
               "address": "", "city": "", "state": "", "zip": "",
               "website_declared": "", "_err": type(e).__name__}

    declared = rec.get("website_declared") or ""
    status, final, code, note = verify(declared)
    if not rec.get("firm_name"):
        rec["firm_name"] = item["name"]

    name = rec["firm_name"]
    low = name.lower()
    entity = "law_firm" if re.search(r"law|attorney|legal|patent|ip |llp|llc|p\.?c\.?|esq|"
                                     r"office|associate|counsel", low) else "company_other"

    row = {
        "firm_name": name,
        "practice_areas": rec.get("practice_areas") or item["practice"],
        "entity_type": entity,
        "address": rec.get("address", ""),
        "city": rec.get("city", ""),
        "state": rec.get("state", ""),
        "zip": rec.get("zip", ""),
        "region": item["region"],
        "website_declared": declared,
        "website_final": final,
        "http_status": code,
        "verification": status,
        "page_title": "",
        "profile_url": item["url"],
        "checked_at": now(),
        "notes": note,
    }

    with lock:
        if debug_left[0] > 0:
            debug_left[0] -= 1
            try:
                with open("data/debug_anchors.txt", "a", encoding="utf-8") as fh:
                    fh.write(f"{item['url']}\n  name={name}\n  cands={rec.get('debug','')}\n"
                             f"  declared={declared} -> {status}\n")
            except Exception:
                pass
        counts[status] += 1
        rows.append(row)
        if status == "LIVE":
            dom = host_of(final) or host_of(declared)
            if dom and dom not in seen_domains:
                seen_domains.add(dom)
                live.append(row)
                print(f"  LIVE[{len(live)}] {name} -> {final}", flush=True)


# ------------------------------------------------------------------ main

ROWS_JS = """() => Array.from(document.querySelectorAll('table tbody tr')).map(tr => {
    const a = tr.querySelector('a[href*="/member/"]');
    const tds = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
    if (!a) return null;
    const m = a.href.match(/\\/member\\/(\\d+)\\//);
    return {id: m ? m[1] : a.href, name: tds[0] || a.innerText.trim(),
            region: tds[1] || '', practice: tds[2] || '', url: a.href};
}).filter(Boolean)"""

FIRST_ROW_JS = "() => ((document.querySelector('table tbody tr a')||{}).innerText||'').trim()"

NEXT_JS = """() => {
  const sels = ['fluent-button[aria-label="Go to next page"]',
                'fluent-button[title="Go to next page"]',
                'button[aria-label="Go to next page"]',
                'fluent-button[aria-label*="next" i]'];
  for (const s of sels) {
    const el = document.querySelector(s);
    if (el && !el.hasAttribute('disabled')) { el.click(); return s; }
  }
  return null;
}"""


def scrape(target: int, max_pages: int, workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    pool = ThreadPoolExecutor(max_workers=32)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1400, "height": 1000})
        page = ctx.new_page()
        page.goto(BASE + "/members?countryid=179", wait_until="domcontentloaded", timeout=90000)
        page.wait_for_selector("table tbody tr", timeout=90000)
        page.wait_for_timeout(4000)

        # page-size dropdown? (agar 100/page mil jaye to bahut time bachega)
        try:
            print("paginator:", page.evaluate(
                "() => (document.querySelector('.paginator')||{}).innerText?.replace(/\\n/g,' | ')"),
                  flush=True)
            print("selects:", page.evaluate(
                "() => Array.from(document.querySelectorAll('select,fluent-select')).map(s => s.outerHTML.slice(0,300))"),
                  flush=True)
        except Exception:
            pass

        pages = 0
        fails = 0
        log(f"start: target={target} live, page size 15")
        while pages < max_pages and len(live) < target:
            rows_now = page.evaluate(ROWS_JS)
            pages += 1
            for it in rows_now:
                if len(live) >= target:
                    break
                pool.submit(process_one, it, target)

            if pages % 10 == 0 or pages <= 3:
                log(f"page {pages:>4} | checked {len(rows)} | live {len(live)} | {dict(counts)}")

            if pages % 100 == 0:
                write_csv(Path("data/ipcommunity_all.csv"), rows)
                write_csv(Path("data/ipcommunity_live.csv"), live)
                git_checkpoint(f"progress page {pages}, live {len(live)}")

            before = page.evaluate(FIRST_ROW_JS)
            clicked = page.evaluate(NEXT_JS)
            if not clicked:
                # fallback: real mouse click
                try:
                    page.locator('fluent-button[aria-label="Go to next page"]').click(timeout=5000)
                    clicked = "locator-click"
                except Exception as e:  # noqa: BLE001
                    log(f"  no next button ({type(e).__name__}) -> pager html: "
                        + str(page.evaluate("() => (document.querySelector('.paginator')||{}).innerText"))[:300])
                    break

            changed = False
            for _ in range(40):
                page.wait_for_timeout(500)
                if page.evaluate(FIRST_ROW_JS) != before:
                    changed = True
                    break
            if not changed:
                fails += 1
                log(f"  page {pages+1} did not load (fail {fails}); url={page.url}")
                if fails >= 4:
                    # last resort: reload aur usi page se aage badho
                    log("  4 fails -> stopping pagination")
                    break
                page.wait_for_timeout(8000)
                continue
            fails = 0
            time.sleep(0.6)

        pool.shutdown(wait=True)
        browser.close()


def write_csv(path: Path, data: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in data:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    print(f"  wrote {path} ({len(data)} rows)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--max-pages", type=int, default=3000)
    ap.add_argument("--workdir", default="data")
    args = ap.parse_args()

    wd = Path(args.workdir)
    t0 = time.time()
    scrape(args.target, args.max_pages, wd)

    rows.sort(key=lambda r: (r["verification"] != "LIVE", r["firm_name"].lower()))
    live.sort(key=lambda r: r["firm_name"].lower())
    write_csv(wd / "ipcommunity_all.csv", rows)
    write_csv(wd / "ipcommunity_live.csv", live)

    stats = {
        "generated_at": now(),
        "target": args.target,
        "profiles_checked": len(rows),
        "live_verified": len(live),
        "status_breakdown": dict(counts),
        "elapsed_minutes": round((time.time() - t0) / 60, 1),
    }
    (wd / "ipcommunity_stats.json").write_text(json.dumps(stats, indent=2))
    log(f"done: {json.dumps(stats)}")
    git_checkpoint(f"final {len(live)} live / {len(rows)} checked", include_csv=True)
    print(json.dumps(stats, indent=2))
    return 0 if len(live) >= args.target else 2


if __name__ == "__main__":
    sys.exit(main())
