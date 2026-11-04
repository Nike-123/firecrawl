#!/usr/bin/env python3
"""Quick probe of ipcommunity.org DOM/pagination so we can write a correct scraper."""
import re
import sys

import requests
from playwright.sync_api import sync_playwright

URL = "https://www.ipcommunity.org/members?countryid=179"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def raw_check():
    print("=== RAW HTTP (requests) ===", flush=True)
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=30)
    print("status:", r.status_code, "len:", len(r.text))
    ids = re.findall(r"/member/(\d+)/", r.text)
    print("member links in raw html:", len(ids), "unique:", len(set(ids)))
    print("has <table>:", "<table" in r.text.lower())
    print("has 'An unhandled error':", "unhandled error" in r.text.lower())

    # one member profile raw check
    if ids:
        mid = ids[0]
        u = f"https://www.ipcommunity.org/member/{mid}/x"
        p = requests.get(u, headers={"User-Agent": UA}, timeout=30)
        print(f"profile {mid}: status {p.status_code} len {len(p.text)}")
        print("  profile has 'Web' label:", ">Web<" in p.text or "Web\n" in p.text)
        ext = [h for h in re.findall(r'href="(https?://[^"]+)"', p.text) if "ipcommunity.org" not in h]
        print("  external hrefs:", ext[:8])


def dom_probe():
    print("\n=== PLAYWRIGHT DOM PROBE ===", flush=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=UA)
        pg.goto(URL, wait_until="networkidle", timeout=90000)
        pg.wait_for_selector("table tbody tr", timeout=60000)

        info = pg.evaluate("""() => {
          const tables = Array.from(document.querySelectorAll('table')).map(t => ({
            cls: t.className,
            rows: t.querySelectorAll('tbody tr').length
          }));
          const ctrls = Array.from(document.querySelectorAll('button, a, li'))
            .map(el => ({
              tag: el.tagName,
              text: (el.innerText || '').trim().slice(0, 40),
              cls: (el.className || '').toString().slice(0, 80),
              aria: el.getAttribute('aria-label') || '',
              disabled: el.hasAttribute('disabled')
            }))
            .filter(o => o.text || o.aria)
            .filter(o => /next|prev|\\d|»|›|pag/i.test(o.text + o.aria + o.cls));
          return {
            tables,
            ctrls: ctrls.slice(0, 60),
            pagerHtml: (document.querySelector('[class*=pag]') || {}).outerHTML?.slice(0, 2500) || ''
          };
        }""")
        print("tables:", info["tables"])
        print("candidate controls:")
        for c in info["ctrls"]:
            print("  ", c)
        print("pager html snippet:", info["pagerHtml"][:1500])

        first_before = pg.evaluate("() => document.querySelector('table tbody tr a')?.innerText")

        # try clicking anything next-ish
        clicked = pg.evaluate("""() => {
          const cands = Array.from(document.querySelectorAll('button, a'))
            .filter(el => /^next$/i.test((el.innerText||'').trim()) ||
                          /next/i.test(el.getAttribute('aria-label')||'') ||
                          /pager-next|paginator-next|next-page/i.test((el.className||'').toString()));
          if (!cands.length) return 'no-candidate';
          cands[0].click();
          return 'clicked:' + (cands[0].innerText||cands[0].getAttribute('aria-label')||cands[0].className);
        }""")
        print("click attempt:", clicked)
        pg.wait_for_timeout(3500)
        first_after = pg.evaluate("() => document.querySelector('table tbody tr a')?.innerText")
        print("first row before:", first_before)
        print("first row after :", first_after)
        print("URL now:", pg.url)
        b.close()


if __name__ == "__main__":
    try:
        raw_check()
    except Exception as e:
        print("raw_check failed:", type(e).__name__, e)
    try:
        dom_probe()
    except Exception as e:
        print("dom_probe failed:", type(e).__name__, e)
    sys.exit(0)
