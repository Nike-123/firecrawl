#!/usr/bin/env python3
"""Probe #2: figure out ipcommunity.org Blazor table pagination."""
import re
import sys

from playwright.sync_api import sync_playwright

URL = "https://www.ipcommunity.org/members?countryid=179"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

CAND_JS = """() => Array.from(document.querySelectorAll('button, a, li, span[role=button]'))
  .map((el, i) => ({i, tag: el.tagName, text: (el.innerText||'').trim().slice(0,30),
                    cls: (el.className||'').toString().slice(0,70),
                    aria: el.getAttribute('aria-label')||'',
                    dis: el.hasAttribute('disabled')}))
  .filter(o => o.text || o.aria)
  .filter(o => /next|prev|last|first|\\d|»|›|‹|«/i.test(o.text + o.aria))
  .slice(0, 40)"""


def first_row(pg):
    return pg.evaluate("() => (document.querySelector('table tbody tr a')||{}).innerText || ''")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=UA)
        pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_selector("table tbody tr", timeout=60000)
        pg.wait_for_timeout(4000)  # let Blazor hydrate

        print("title:", pg.title())
        print("rows:", pg.evaluate("() => document.querySelectorAll('table tbody tr').length"))
        print("pager candidates:")
        for c in pg.evaluate(CAND_JS):
            print("  ", c)

        # dump any pagination container html
        print("\ncontainer html:", pg.evaluate("""() => {
            const sels = ['.mud-table-pagination','.rz-paginator','.pagination','[class*=paginator]','[class*=pager]','nav'];
            for (const s of sels) { const el = document.querySelector(s); if (el) return s + ' => ' + el.outerHTML.slice(0,1200); }
            return 'none found';
        }"""))

        before = first_row(pg)
        print("\nfirst row before:", before)

        # strategy 1: click by aria/text
        res = pg.evaluate("""() => {
          const all = Array.from(document.querySelectorAll('button, a, li, span[role=button]'));
          const pick = all.find(el => /^next$/i.test((el.innerText||'').trim()))
                    || all.find(el => /next/i.test(el.getAttribute('aria-label')||''))
                    || all.find(el => /next|paginator-next|pager-next/i.test((el.className||'').toString()));
          if (!pick) return 'no next candidate';
          pick.click();
          return 'clicked <' + pick.tagName + '> ' + ((pick.innerText||'').trim() || pick.getAttribute('aria-label') || pick.className);
        }""")
        print("click result:", res)
        pg.wait_for_timeout(3500)
        after = first_row(pg)
        print("first row after :", after, "| changed:", before != after)
        print("url now:", pg.url)

        # strategy 2: numbered buttons
        if before == after:
            res2 = pg.evaluate("""() => {
              const btns = Array.from(document.querySelectorAll('button, a, li'))
                 .filter(el => /^\\s*2\\s*$/.test((el.innerText||'')));
              if (!btns.length) return 'no page-2 button';
              btns[0].click();
              return 'clicked page-2 button';
            }""")
            print("strategy2:", res2)
            pg.wait_for_timeout(3500)
            print("first row now:", first_row(pg), "| url:", pg.url)

        # if paging works, walk 5 pages and report
        if first_row(pg) != before:
            seen = set()
            for i in range(6):
                rows = pg.evaluate("() => Array.from(document.querySelectorAll('table tbody tr a')).map(a => a.href)")
                seen.update(rows)
                nxt = pg.evaluate("""() => {
                  const all = Array.from(document.querySelectorAll('button, a, li, span[role=button]'));
                  const b = all.find(el => /^next$/i.test((el.innerText||'').trim()))
                         || all.find(el => /next/i.test(el.getAttribute('aria-label')||''));
                  if (!b) return false; b.click(); return true;
                }""")
                if not nxt:
                    print("no next button at page", i + 2)
                    break
                pg.wait_for_timeout(2500)
                print(f"page {i+2}: total unique urls {len(seen)}, url {pg.url}")
        b.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FAILED:", type(e).__name__, e)
    sys.exit(0)
