#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply ONLY manually verified official firm website URLs to blank rows of
Lawyers_com_US_IP_Firms.csv and rebuild the deliverables.

IMPORTANT: This script contains NO network calls, NO scraping, NO pagination,
and NO URL guessing. Every URL below was individually verified during the
2026-11-02 session by (a) web search for the firm's official domain followed
by (b) fetching that domain and confirming the firm's own name on the live
page, or by re-verifying a URL already present elsewhere in the source file.
Rows whose official site could not be confirmed are left BLANK on purpose.

Re-runnable / idempotent: existing non-blank URLs are never modified.
"""
import csv, json, os, sys
from datetime import datetime, timezone

ROOT = "/home/user/firecrawl"
SRC = os.path.join(ROOT, "lawyers_com_ORIGINAL_upload.csv")
OUT_CSV = os.path.join(ROOT, "Lawyers_com_US_IP_Firms.csv")
OUT_XLSX = os.path.join(ROOT, "Lawyers_com_US_IP_Firms.xlsx")
AUDIT = os.path.join(ROOT, "lawyers_com_verified_additions.csv")
UNRESOLVED = os.path.join(ROOT, "lawyers_com_unresolved.csv")
CHECKPOINT = os.path.join(ROOT, "lawyers_com_checkpoint.json")
LOG = os.path.join(ROOT, "lawyers_com_fill.log")

# firm name -> (url, method, verification evidence)
VERIFIED = {
    # --- externally researched, official homepage fetched and name confirmed ---
    "Ogletree, Deakins, Nash, Smoak & Stewart, P.C.": ("https://ogletree.com/", "external_verified", "Live official homepage title 'Home - Ogletree'; Wikipedia + FindLaw corroborate ogletree.com"),
    "Burr & Forman LLP": ("https://www.burr.com/", "external_verified", "Live official homepage 'Burr & Forman: Law Firm, Attorneys, Lawyers...'"),
    "Jones Walker LLP": ("https://www.joneswalker.com/", "external_verified", "Live official homepage 'Jones Walker LLP | Homepage'; Chambers + FindLaw corroborate"),
    "Baker, Donelson, Bearman, Caldwell & Berkowitz, PC": ("https://www.bakerdonelson.com/", "external_verified", "Live official homepage 'Baker Donelson'; SuperLawyers + LatinCounsel corroborate"),
    "Maynard Nexsen PC": ("https://www.maynardnexsen.com/", "external_verified", "Live official homepage 'Maynard Nexsen'; Buzzfile + Cylex + SuperLawyers corroborate"),
    "Constangy, Brooks, Smith & Prophete, LLP": ("https://www.constangy.com/", "external_verified", "Live official homepage 'Constangy | Labor, Employment, Cybersecurity & Data Privacy Law'"),
    "Gordon Rees Scully Mansukhani, LLP": ("https://www.grsm.com/", "external_verified", "Live official homepage 'Gordon Rees Scully Mansukhani'; Wikipedia + LinkedIn corroborate grsm.com"),
    "Watkins & Eager": ("https://www.watkinseager.com/", "external_verified", "Live official homepage 'Watkins & Eager: Attorneys and Counselors at Law'"),
    "Faegre Drinker Biddle & Reath LLP": ("https://www.faegredrinker.com/en/", "external_verified", "Live official homepage title 'Faegre Drinker Biddle & Reath LLP'"),
    "Moore & Van Allen PLLC": ("https://www.mvalaw.com/", "external_verified", "Live official homepage 'Moore & Van Allen'; LinkedIn + Vault + ZoomInfo corroborate"),
    "Robinson & Cole LLP": ("https://www.rc.com/", "external_verified", "Live official homepage 'Robinson+Cole | Tailored Solutions for a Complex World'"),
    "McNees Wallace & Nurick LLC": ("https://www.mcneeslaw.com/", "external_verified", "Live official homepage 'McNees | Business law firm in PA, MD, OH & Washington, D.C.'; firm rebranded to McNees"),
    "Nixon & Vanderhye P.C.": ("https://www.nixon-vanderhye.com/", "external_verified", "Live official homepage 'Nixon Vanderhye | IP Law Firm'"),
    "Astor Weiss Kaplan & Mandel, LLP": ("https://www.astorweiss.com/", "external_verified", "Live official homepage 'Philadelphia Attorneys | Astor Weiss Kaplan & Mandel, LLP'"),
    "Gislason & Hunter LLP": ("https://www.gislason.com/", "external_verified", "Live official homepage 'Gislason & Hunter'"),
    "Scheef & Stone, L.L.P.": ("https://www.solidcounsel.com/", "external_verified", "Live official homepage 'Scheef & Stone - Scheef & Stone, LLP'; Mackrell + Cience corroborate solidcounsel.com"),
    "Littler Mendelson P.C.": ("https://www.littler.com/", "external_verified", "Live official homepage 'Littler Mendelson P.C. | Built for your tomorrow'"),
    "Adams and Reese LLP": ("https://www.adamsandreese.com/", "external_verified", "Live official homepage 'Adams & Reese | Corporate Law Firm'"),
    "Phelps Dunbar LLP": ("https://www.phelps.com/", "external_verified", "Live official homepage 'Home | Phelps'; phelpsdunbar.com redirects to phelps.com"),
    "Bradley Arant Boult Cummings LLP": ("https://www.bradley.com/", "external_verified", "Live official homepage 'Bradley'; page text names Bradley Arant Boult Cummings"),
    "Balch & Bingham LLP": ("https://www.balch.com/", "external_verified", "Live official homepage 'National Full Service Law Firm | Balch & Bingham LLP'"),
    "Hand Arendall Harrison Sale LLC": ("https://www.handfirm.com/", "external_verified", "Live official homepage 'Welcome to Hand Arendall Harrison Sale'; handarendall.com redirects here"),
    "Wilson Elser": ("https://www.wilsonelser.com/", "external_verified", "Live official homepage 'Wilson Elser' (Wilson, Elser, Moskowitz, Edelman & Dicker LLP)"),
    "Offit Kurman": ("https://www.offitkurman.com/", "external_verified", "Live official homepage 'Offit Kurman | Strategic Legal Solutions for Businesses & Individuals'"),
    "Procopio, Cory, Hargreaves & Savitch LLP": ("https://www.procopio.com/", "external_verified", "Live official homepage 'Procopio -- AmLaw 200 Corporate and Litigation Law Firm'"),
    "Foster Garvey PC": ("https://www.foster.com/", "external_verified", "Live official homepage 'Foster Garvey PC | Full-Service Corporate Law Firm'"),
    "Snell & Wilmer L.L.P.": ("https://www.swlaw.com/", "external_verified", "Live official homepage 'Snell & Wilmer | Full Service Business Law Firm'; Wikipedia + ZoomInfo corroborate swlaw.com"),
    "K&L Gates LLP": ("https://www.klgates.com/", "external_verified", "Live official homepage 'Homepage | K&L Gates'; Wikipedia + Chambers corroborate klgates.com"),
    "Stoel Rives LLP": ("https://www.stoel.com/", "external_verified", "Live official homepage 'Stoel Rives LLP Attorneys - A Leading U.S. Law Firm'"),
    "Bryan Cave Leighton Paisner LLP": ("https://www.bclplaw.com/", "external_verified", "Live official homepage 'BCLP - Bryan Cave Leighton Paisner' (bclplaw.com redirects to /en-US/)"),
    "Womble Bond Dickinson (US) LLP": ("https://www.womblebonddickinson.com/us", "external_verified", "Live official US homepage 'Womble Bond Dickinson | International Law Firm'"),
    "McGuireWoods LLP": ("https://www.mcguirewoods.com/", "external_verified", "Live official homepage 'McGuireWoods'; Wikipedia + Chambers corroborate"),
    "Husch Blackwell LLP": ("https://www.huschblackwell.com/", "external_verified", "Live official homepage 'Husch Blackwell: Trusted Legal Leaders | Husch Blackwell'"),
    "Fenwick & West LLP": ("https://www.fenwick.com/", "external_verified", "Live official homepage 'Fenwick | Homepage'; Wikipedia corroborates fenwick.com"),
    "Dorsey & Whitney LLP": ("https://www.dorsey.com/", "external_verified", "Live official homepage 'Dorsey & Whitney LLP'; Wikipedia corroborates dorsey.com"),
    "Reed Smith LLP": ("https://www.reedsmith.com/", "external_verified", "Live official homepage 'Reed Smith LLP'; FindLaw + LCJ directory corroborate"),
    "Barnes & Thornburg LLP": ("https://www.btlaw.com/", "external_verified", "Live official homepage 'Business Law Firm | Barnes & Thornburg'; Wikipedia corroborates btlaw.com"),
    "Jackson Lewis P.C.": ("https://www.jacksonlewis.com/", "external_verified", "Live official homepage 'Jackson Lewis'; Wikidata + ZoomInfo corroborate"),
    "Foley & Lardner LLP": ("https://www.foley.com/", "external_verified", "Live official homepage 'Foley & Lardner LLP | Top 50 Global Law Firm'"),
    "Cooley LLP": ("https://www.cooley.com/", "external_verified", "Live official homepage 'Cooley | Global Law Firm for Innovative Companies and Investors'"),
    "Duane Morris LLP": ("https://www.duanemorris.com/", "external_verified", "Live official homepage 'Welcome to Duane Morris LLP'; Wikipedia corroborates"),
    "Cozen O'Connor": ("https://www.cozen.com/", "external_verified", "Live official homepage 'Cozen O'Connor'; Wikipedia + ICLG corroborate"),
    "Buchanan Ingersoll & Rooney PC": ("https://www.bipc.com/", "external_verified", "Live official homepage 'Buchanan Ingersoll & Rooney PC'; LinkedIn + Wikipedia corroborate bipc.com"),
    "Polsinelli PC": ("https://www.polsinelli.com/", "external_verified", "Live official homepage 'Polsinelli Law Firm'; FindLaw corroborates"),
    "Quarles & Brady LLP": ("https://www.quarles.com/", "external_verified", "Live official homepage 'Quarles: Attorneys, Lawyers, Law Firm'"),
    "Tonkon Torp LLP": ("https://www.tonkon.com/", "external_verified", "Live official homepage 'Business Law Attorneys | Tonkon Torp LLP | Portland, Oregon'"),
    "Fox Rothschild LLP": ("https://www.foxrothschild.com/", "external_verified", "Live official homepage 'Fox Rothschild LLP - Attorneys at Law'; Wikipedia + Wikidata corroborate"),
    "Vorys, Sater, Seymour and Pease LLP": ("https://www.vorys.com/", "external_verified", "Live official homepage 'Vorys | Law Firm in Ohio, Washington, D.C., Texas, Pennsylvania, California & London'"),
    "Dinsmore & Shohl LLP": ("https://www.dinsmore.com/", "external_verified", "Live official homepage 'Dinsmore - A full-service, national law firm'; LinkedIn + Wikidata corroborate"),
    "Squire Patton Boggs": ("https://www.squirepattonboggs.com/", "external_verified", "Live official homepage 'Squire Patton Boggs | Global law firm'; Wikipedia corroborates"),
    "Tucker Ellis, LLP": ("https://www.tuckerellis.com/", "external_verified", "Live official homepage 'Tucker Ellis LLP | Lead by Example'"),
    "Benesch, Friedlander, Coplan & Aronoff LLP": ("https://www.beneschlaw.com/", "external_verified", "Live official homepage 'Homepage | Benesch'; TerraLex + Mondaq list the full name at beneschlaw.com"),
    "Parker Poe Adams & Bernstein LLP": ("https://www.parkerpoe.com/", "external_verified", "Live official homepage 'Parker Poe | Attorneys & Counselors at Law'"),
    "Fisher & Phillips LLP": ("https://www.fisherphillips.com/", "external_verified", "Live official homepage 'Homepage | Fisher Phillips LLP'; firm's own 2016 rebrand release confirms the URL"),
    "Nixon Peabody LLP": ("https://www.nixonpeabody.com/", "external_verified", "Live official homepage 'Nixon Peabody LLP: Sophisticated Legal Solutions for Businesses'"),
    "Davis Wright Tremaine LLP": ("https://www.dwt.com/", "external_verified", "Live official homepage 'Davis Wright Tremaine'; LinkedIn + ZoomInfo corroborate dwt.com"),
    "Holland & Knight LLP": ("https://www.hklaw.com/", "external_verified", "Live official homepage 'Home | Holland & Knight'; Wikipedia corroborates hklaw.com"),
    "DLA Piper LLP (US)": ("https://www.dlapiper.com/", "external_verified", "Live official homepage 'Global Law Firm | DLA Piper'; ICLG + Wikidata corroborate dlapiper.com"),
    "DLA Piper": ("https://www.dlapiper.com/", "external_verified", "Live official homepage 'Global Law Firm | DLA Piper'; same firm, short-name row"),
    "DLA Piper LLP": ("https://www.dlapiper.com/", "external_verified", "Live official homepage 'Global Law Firm | DLA Piper'; same firm, name variant row"),
    "Ballard Spahr LLP": ("https://www.ballardspahr.com/", "external_verified", "Live official homepage 'Ballard Spahr - National Strategic Law Partners'; Wikipedia corroborates"),
    "Baker & Hostetler LLP": ("https://www.bakerlaw.com/", "external_verified", "Live official homepage 'Home | BakerHostetler'; Wikipedia corroborates bakerlaw.com"),
    "Alston & Bird LLP": ("https://www.alston.com/", "external_verified", "Live official homepage 'Alston & Bird Law Firm | International Attorneys and Lawyers'"),
    "Ropes & Gray LLP": ("https://www.ropesgray.com/", "external_verified", "Live official homepage 'Ropes & Gray LLP'; Wikipedia + Chambers corroborate"),
    "Latham & Watkins LLP": ("https://www.lw.com/", "external_verified", "Live official homepage 'Latham & Watkins LLP | Global Law Firm'; Wikipedia + ICLG corroborate lw.com"),

    # --- exact-name URL already present elsewhere in the SAME uploaded file,
    #     re-verified by fetching that page before copying ---
    "Stoll Keenon Ogden PLLC": ("http://www.skofirm.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Home - Stoll Keenon Ogden PLLC'"),
    "Musca Law": ("https://www.muscalaw.com/naples/", "source_internal_verified", "URL from another row of the same file; fetched 'Naples Criminal Defense Lawyers | Musca Law'"),
    "Dickie, McCamey & Chilcote, P.C.": ("https://www.dmclaw.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Dickie, McCamey & Chilcote'"),
    "Marshall Dennehey": ("http://www.marshalldennehey.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Marshall Dennehey'"),
    "LaFleur & Laborde": ("https://www.lalalawfirm.com/", "source_internal_verified", "URL from another row of the same file; fetched 'About the Firm: LaFleur & Laborde'"),
    "Kerrick Bachert, PSC": ("https://www.kerrickbachertlaw.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Kerrick Bachert, PSC'"),
    "Downs Rachlin Martin PLLC": ("http://www.drm.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Downs Rachlin Martin'"),
    "Thrive IP": ("https://www.thrive-ip.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Thrive IP Intellectual Property / Patent Firm'"),
    "Hinman, Howard & Kattell, LLP": ("http://www.hhk.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Hinman, Howard & Kattell'"),
    "High Tide Legal": ("https://hightide.law/", "source_internal_verified", "URL from another row of the same file; fetched 'High Tide Legal'"),
    "Lipsitz Green Scime Cambria LLP": ("http://www.lipsitzgreen.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Lipsitz Green Scime Cambria'"),
    "Blankingship & Keith, P.C.": ("http://www.blankingshipandkeith.com/", "source_internal_verified", "URL from another row of the same file; fetched 'Blankingship & Keith'"),

    # --- unambiguous short-name variant of an already verified firm ---
    "Maynard Nexsen": ("https://www.maynardnexsen.com/", "verified_name_variant", "Short form of 'Maynard Nexsen PC'; same verified official homepage 'Maynard Nexsen'"),
}

# Explicitly investigated but REJECTED (must stay blank, never guessed)
REJECTED = {
    "Waller Lansden Dortch & Davis, LLP": "wallerlaw.com now redirects to hklaw.com (Holland & Knight); original firm domain not confirmed",
    "Cabaniss, Johnston, Gardner, Dumas & O'Neal LLP": "cabaniss.com resolves to a GoDaddy 'domain for sale' page; no live official firm site found",
    "Middleton Reutlinger, P.S.C.": "middletonlaw.com states the firm dissolved 12/31/2022; no active firm site",
    "Conrad O'Brien": "conradobrien.com could not be fetched (http and https); left unverified",
    "Krieg DeVault LLP": "the same-name URL elsewhere in the file is fuchsandroselli.com, a different firm; not copied",
    "Perkins Coie, LLP": "perkinscoie.com now redirects to ashurstperkinscoie.com after the Ashurst merger; successor site not substituted for the original firm URL",
    "Perkins Coie LLP": "perkinscoie.com now redirects to ashurstperkinscoie.com after the Ashurst merger; successor site not substituted for the original firm URL",
    "Brinks Gilson & Lione": "brinksgilson.com now redirects to crowell.com; the firm's lawyers joined Crowell & Moring, so no original firm homepage remains",
    "Burns & Levinson LLP": "burnslev.com returned '404 - Unknown site' on http, https and /en fetches; live homepage could not be confirmed despite directory corroboration",
}

GENERIC_REASON = "Not yet individually verified; no authentic official URL confirmed, so left blank (no guessing)"


def main():
    with open(SRC, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    assert header == ["Firm Name", "Firm Website URL"], header
    assert all(len(r) == 2 for r in data)

    applied, audit = [], []
    out = [list(header)]
    for idx, r in enumerate(data):
        name, url = r[0], r[1]
        line = idx + 2                       # 1-based CSV line incl. header
        if url.strip():
            out.append([name, url])          # existing URLs: byte-for-byte unchanged
            continue
        if name.strip() in VERIFIED:
            u, method, evidence = VERIFIED[name.strip()]
            out.append([name, u])
            applied.append(line)
            audit.append([line, name, u, method, evidence])
        else:
            out.append([name, url])          # stays blank

    # integrity assertions
    assert len(out) == len(data) + 1
    for i, (a, b) in enumerate(zip(rows, out)):
        if a[1].strip():
            assert a == b, "existing URL row changed at line %d" % (i + 1)
    missing = set(VERIFIED) - {r[0].strip() for r in data if not r[1].strip()}
    assert not missing, "verified names not found as blank rows: %s" % missing

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerows(out)

    # XLSX: exactly two columns, header, filters, frozen top row, widths
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.comments import Comment
        wb = Workbook(); ws = wb.active; ws.title = "Listings"
        for r in out:
            ws.append(r)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF", size=11)
            c.fill = PatternFill("solid", fgColor="1F4E78")
            c.alignment = Alignment(vertical="center")
        ws.row_dimensions[1].height = 22
        ws.column_dimensions["A"].width = 56
        ws.column_dimensions["B"].width = 62
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = "A1:B%d" % ws.max_row
        ws["A1"].comment = Comment(
            "Existing URLs unchanged. %d blank URLs filled from verified official "
            "firm websites on 2026-11-02. Remaining blanks are intentionally "
            "blank: no URL was guessed. See lawyers_com_report.txt." % len(applied),
            "Arena.ai Agent Mode")
        wb.properties.title = "Lawyers.com US IP Firms - verified URL enrichment"
        wb.save(OUT_XLSX)
        xlsx_ok = True
    except ImportError:
        xlsx_ok = False
        print("WARNING: openpyxl unavailable, XLSX not rebuilt", file=sys.stderr)

    with open(AUDIT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Source Line", "Firm Name", "Website URL Added", "Method", "Verification Evidence"])
        w.writerows(sorted(audit))

    pending = []
    with open(UNRESOLVED, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Source Line", "Firm Name", "Reason Left Blank"])
        for idx, r in enumerate(out[1:]):
            if r[1].strip():
                continue
            line = idx + 2
            name = r[0].strip()
            reason = REJECTED.get(name, GENERIC_REASON)
            w.writerow([line, name, reason])
            pending.append(line)

    total = len(data)
    filled_now = len(applied)
    total_urls = sum(1 for r in out[1:] if r[1].strip())
    blanks = total - total_urls
    dup_extra = total - len({r[0].strip() for r in data})
    ts = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    cp = {
        "project": "Lawyers_com_US_IP_Firms.csv blank-URL enrichment",
        "workspace": ROOT,
        "session_branch": "arena/0b640660-firecrawl",
        "generated_at_utc": ts,
        "status": "IN_PROGRESS_PARTIAL_VERIFIED",
        "source_file": SRC,
        "output_csv": OUT_CSV,
        "output_xlsx": OUT_XLSX,
        "verification_policy": ("Only add a URL when the firm's own live official homepage was "
                                "located and the firm name confirmed on that page; never guess, "
                                "never use directory/profile URLs, never substitute a guessed domain."),
        "counts": {
            "total_rows": total,
            "original_urls_present": total - 4862,
            "original_blank_urls": 4862,
            "urls_added_this_run": filled_now,
            "urls_added_external_verified": sum(1 for a in audit if a[3] == "external_verified"),
            "urls_added_source_internal_verified": sum(1 for a in audit if a[3] == "source_internal_verified"),
            "urls_added_verified_name_variant": sum(1 for a in audit if a[3] == "verified_name_variant"),
            "total_rows_with_url_after": total_urls,
            "total_rows_blank_after": blanks,
            "duplicate_extra_rows_preserved": dup_extra,
            "pending_blank_lines": len(pending),
            "explicitly_rejected_after_investigation": len(REJECTED)},
        "rules": {
            "existing_urls_never_modified": True,
            "duplicate_rows_preserved": True,
            "source_order_preserved": True,
            "no_url_invention": True,
            "no_proxies_or_workarounds": True,
            "no_directory_profile_urls_added": True},
        "applied_source_lines": sorted(applied),
        "rejected": REJECTED,
        "pending_source_lines": pending,
        "next_batch_suggestion": ("Continue from the first pending line in "
                                  "lawyers_com_unresolved.csv, verifying each firm's official "
                                  "homepage before adding a URL. Append confirmed pairs to "
                                  "VERIFIED in lawyers_com_apply_verified.py and re-run it."),
        "conflict_note": ("The original LawTally brief (Step 2 rule 10) said not to use external "
                          "searches to fill missing URLs; that rule applied to the never-executed "
                          "LawTally extraction. The user's new instruction explicitly asks to find "
                          "and add original URLs for this separate lawyers.com file, so web research "
                          "was used strictly for verification, never for invention.")
    }
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(cp, f, indent=2, ensure_ascii=False); f.write("\n")

    lines = [
        "%s INFO  lawyers_com_enrich | start (no network calls in this script)" % ts,
        "%s INFO  source=%s rows=%d columns=2 header=%s" % (ts, SRC, total, header),
        "%s INFO  original: %d URLs present, %d blank" % (ts, total - 4862, 4862),
        "%s INFO  applied %d verified URLs (%d external, %d source-internal, %d name-variant)" % (
            ts, filled_now,
            cp["counts"]["urls_added_external_verified"],
            cp["counts"]["urls_added_source_internal_verified"],
            cp["counts"]["urls_added_verified_name_variant"]),
        "%s INFO  existing %d URLs verified unchanged; source order + duplicate rows preserved" % (ts, total - 4862),
        "%s INFO  explicit rejections (%d): see REJECTED dict for per-firm reasons (redirect/merger, domain for sale, dissolved, fetch failed, mismatched duplicate)" % (ts, len(REJECTED)),
        "%s WARN  %d blank rows still unresolved; deliberately left blank (no guessing)" % (ts, blanks),
        "%s INFO  wrote %s, %s, audit, unresolved, checkpoint" % (ts, OUT_CSV, OUT_XLSX),
        "%s INFO  end | total URLs after=%d blank after=%d" % (ts, total_urls, blanks),
    ]
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("rows=%d | filled=%d | URLs after=%d | blank after=%d | dup extra rows=%d | xlsx=%s"
          % (total, filled_now, total_urls, blanks, dup_extra, xlsx_ok))
    print("applied lines:", sorted(applied))


if __name__ == "__main__":
    main()
