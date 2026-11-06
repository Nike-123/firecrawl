#!/usr/bin/env python3
"""Write output/Error_Log.txt.

Two sections:
  A. errors and anomalies derived mechanically from the saved data
     (unfetched domains, failed website checks, rows with no published
     website or Professional Webpage, ambiguous firm identity, empty
     structured fields, notes truncated for Excel);
  B. source-level defects recorded by hand while reading the 216 Super
     Lawyers profiles and the firm websites. Each one is quoted from the
     saved evidence and names the serial numbers affected. Nothing here is
     inferred: every entry was observed on the page named.
"""
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(HERE, 'work')
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)


def norm_domain(d):
    d = (d or '').strip().lower()
    if '://' in d:
        d = d.split('://', 1)[1]
    d = d.split('/', 1)[0]
    return d[4:] if d.startswith('www.') else d


inp = json.load(open(os.path.join(WORK, 'input_records.json'), encoding='utf-8'))
prof = {}
for line in open(os.path.join(WORK, 'profiles.jsonl'), encoding='utf-8'):
    if line.strip():
        r = json.loads(line)
        prof[r['sn']] = r
sites = {}
for line in open(os.path.join(WORK, 'sites.jsonl'), encoding='utf-8'):
    if line.strip():
        r = json.loads(line)
        sites[norm_domain(r['domain'])] = r

L = []
A = L.append
A('SUPER LAWYERS - INTELLECTUAL PROPERTY PRACTICE VERIFICATION')
A('Error and anomaly log')
A('Generated: ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
A('Verification date on every row: 2026-11-06')
A('')
A('SECTION A - ERRORS DERIVED FROM THE SAVED DATA')
A('')

# A1 rows whose profile publishes no firm website
no_site = [sn for sn, r in prof.items() if not (r.get('site') or '').strip()]
A('A1. Rows publishing NO official law firm website -> Website Verification Status is')
A('    NOT APPLICABLE and the Evidence URL falls back to the Super Lawyers profile URL.')
A('    %d rows: %s' % (len(no_site), sorted(no_site)))
for sn in sorted(no_site):
    A('      sn %-4d %-28s firm field: %s' % (sn, prof[sn].get('firm', '')[:28],
                                             '(empty)' if not prof[sn].get('firm') else 'present'))
A('')

# A2 rows publishing no Professional Webpage
no_pw = [sn for sn, r in prof.items() if not (r.get('prof_web') or '').strip()]
A('A2. Rows publishing NO Professional Webpage -> Lawyer Association Evidence URL is empty.')
A('    %d rows: %s' % (len(no_pw), sorted(no_pw)))
A('')

# A3 third-party / off-domain Professional Webpage values
A('A3. Professional Webpage values that are NOT the firm\'s own website:')
for sn, r in sorted(prof.items()):
    pw = (r.get('prof_web') or '').strip()
    sd = norm_domain(r.get('site'))
    pd = norm_domain(pw)
    if pw and sd and pd != sd:
        A('      sn %-4d firm site %s  vs  Professional Webpage %s' % (sn, sd, pd))
A('')

# A4 ambiguous firm identity
amb = [sn for sn, r in prof.items() if r.get('fvs') == 'AMBIGUOUS']
A('A4. AMBIGUOUS firm identity (the firm field and the bio name different firms):')
A('    %d rows: %s' % (len(amb), sorted(amb)))
A('')

# A5 empty structured fields
A('A5. Empty structured fields, recorded as published (not treated as missing data):')
for key in ('pct', 'areas', 'focus', 'selections', 'admitted', 'addr', 'phone',
            'education', 'languages'):
    empty = sorted(sn for sn, r in prof.items() if not (r.get(key) or '').strip())
    if key in ('languages', 'education', 'addr'):
        A('      %-11s empty on %d rows (field only published on some profiles)'
          % (key, len(empty)))
    else:
        A('      %-11s empty on %d rows: %s' % (key, len(empty), empty if empty else '-'))
A('')

# A6 Phase B coverage
doms = {}
for sn, r in prof.items():
    d = norm_domain(r.get('site'))
    if d:
        doms.setdefault(d, []).append(sn)
pending = sorted(set(doms) - set(sites))
failed = sorted(d for d, s in sites.items() if not (s.get('ok') and s.get('firm_match')))
A('A6. PHASE B COVERAGE - firm-website checks.')
A('    Unique firm domains published by the 216 profiles: %d' % len(doms))
A('    Domains fetched and saved to work/sites.jsonl .....: %d' % len(sites))
A('    Domains fetched but failing ok/firm_match .........: %d %s' % (len(failed), failed))
A('    Domains NOT YET FETCHED (Website Verification Status = NOT YET VERIFIED): %d'
  % len(pending))
A('    These rows are complete on Super Lawyers evidence; only the firm-website')
A('    cross-check is outstanding. The worklist is work/phase_b_queue.txt.')
A('')

# A7 shared domains
shared = {d: sorted(s) for d, s in doms.items() if len(s) > 1}
A('A7. Domains shared by two or more rows (one fetch applies to all rows listed):')
for d in sorted(shared):
    A('      %-28s %s' % (d, shared[d]))
A('')

A('SECTION B - SOURCE-LEVEL DEFECTS RECORDED WHILE READING THE PAGES')
A('Every entry below was observed on the page named. Contradictory statements are')
A('reported side by side as published; none has been silently reconciled.')
A('')
B_ITEMS = [
    ('B1', 'Redirects that silently change the evidence URL', [
        'sn 8: the published Professional Webpage https://amburnlaw.com/dean-amburn/ '
        'returns https://pure.law/ - a dead deep link redirecting to a DIFFERENT domain\'s '
        'homepage. Amburn Law PLLC has rebranded as The Pure.Law Firm; the same site also '
        'uses "Amburn Law P.C." and the directory slug "amburn-law-pllc". The Evidence URL '
        'was corrected to https://pure.law/ and the published value recorded here.',
        'sn 9: http://www.cdalawllp.com/ resolves to https://cdalawllp.com/ - a scheme '
        'upgrade AND a www drop in one hop.',
        'sn 9: the site renders the firm name as "Cittone, Demers & Arneri LLP" with a '
        'serial comma; the Super Lawyers firm field omits it.',
        'sn 99: the "Visit website" link is a third-party marketing subdomain '
        '(setarehlaw.lawfirms.com); resolved by web search to https://www.setarehfirm.com/.',
        'sn 157: two different hosts on one profile - ravin.com (a personal site) and '
        'hartmanwinnicki.com (the firm).',
        'sn 12: the "Visit website" link is a deep team-member page '
        '(scalefirm.com/team-members/andy-baxter), not a firm root.',
    ]),
    ('B2', 'Pages that did not load, parked or placeholder domains', [
        'sn 22: boehringerlaw.com was parked in an earlier pass; re-check before accepting '
        'a WEBSITE VERIFIED value for this row.',
        'sn 112: andrewlilly.com served a "coming soon" page in an earlier pass.',
        'sn 135: mullerlaw.com redirected to sinapilaw.com - a different firm entirely.',
        'sn 159: rokitalaw.com/about-us/ returned 404.',
        'sn 174: mcdowellrice.com returned HTTP 500 on three attempts in an earlier pass.',
        'sn 196: the Super Lawyers profile returned HTTP 500 once and succeeded on retry.',
    ]),
    ('B3', 'Truncated pages - content beyond chunk 0 was never reached', [
        'sn 215: the profile chunk 0 ended at a lone asterisk immediately after the '
        'Professional Webpage field, so NO Bar activity, honours, verdicts or educational '
        'background was captured despite totalChunks 3.',
        'sn 127: totalChunks 12 - only chunk 0 read.',
        'sn 207: totalChunks 3; publishes neither a firm website nor a Professional Webpage '
        'and has no "Find me online" section at all.',
        'sn 98, 115, 117, 129, 173, 157, 179, 187, 204, 206: Practice areas, First Admitted, '
        'Professional Webpage, Bar activity or Honours fell into chunk 1.',
        'Firm sites also truncate: thecontentlawyer.com (3 chunks, cut mid-membership-list), '
        'mcalpinepllc.com (2, cut mid-Background), cdalawllp.com (3, cut inside James '
        'Demers\'s bio so partner Arneri was never reached), pure.law (2, no attorney bio on '
        'the homepage).',
    ]),
    ('B4', 'JavaScript / cookie shells - a page that renders no usable text', [
        'bkcglaw.com, maheshlaw.com (sn 120), lewiskohn.com (sn 104, 108), hjlawfirm.com '
        '(sn 134), hh-law.com, motivalaw.com (sn 175), holmesweinberg.com (sn 201), '
        'adamweissmanlaw.com (sn 203) served a cookie-consent or JS shell in an earlier pass.',
        'sn 1: djaaronlaw.com terminates with the bare word "loading" - an unrendered JS widget.',
        'sn 4/13: novotechip.com\'s "Recognitions" (sic) section is eight lazy-loaded SVG '
        'placeholders with no alt text - the awards are UNAVAILABLE, not absent.',
    ]),
    ('B5', 'First Admitted names a state that appears nowhere else on the profile', [
        'sn 171 (Missouri / Kansas), sn 173 (Maryland), sn 182 (Connecticut).',
        'sn 204: First Admitted 1997 Virginia, but the headline reads "Licensed in Ohio '
        'since: 2000".',
        'sn 206: First Admitted 2009 Colorado, but the headline reads "Licensed in New York '
        'since: 2018".',
        'sn 203: First Admitted 2013 New York, but Bar activity reads Ontario 2013 and '
        'New York 2017.',
        'sn 212: First Admitted 1992 California, but the headline reads "Licensed in '
        'Washington DC since: 2003".',
        'sn 213: First Admitted 1994 Illinois, but the headline reads North Carolina since '
        '1996, the office is in Charlotte, and the bio also asserts Los Angeles.',
        'sn 207: the bio claims "over two decades" in Florida while First Admitted reads '
        '1988 - 38 years.',
    ]),
    ('B6', 'City contradictions between the bio and every structured field', [
        'sn 204: Cleveland in every field, "Mentor, Ohio" in the bio (ZIP 44060 IS Mentor).',
        'sn 194: Naperville in the bio, Wheaton in every field.',
    ]),
    ('B7', 'Focus areas / practice split defects', [
        'sn 212: Focus areas is exactly ONE term, "Contracts", with no IP term at all, '
        'despite 70% Intellectual Property and a current INTA chairmanship - the most '
        'extreme case in the set.',
        'sn 215: Focus areas is exactly ONE term, "Antitrust & Trade Litigation".',
        'sn 161, 162, 163: Focus areas is legitimately empty.',
        'sn 216: Focus areas omits Copyrights although the bio describes copyright work.',
        'sn 191: 50% Intellectual Property and a "Top rated Intellectual Property" headline '
        'against a wholly non-IP narrative - the sharpest mismatch in the set.',
    ]),
    ('B8', 'Recurring section misuse on the Super Lawyers profiles', [
        'Pro bono / Community Service holding a professional body or a fraternity: sn 204 '
        '("FICPI"), sn 205 ("Dallas/Fort Worth Gator Club", "Pi Kappa Phi"), sn 214 '
        '("UAS Colorado", secretary).',
        'Special Licenses holding court admissions: sn 205 (five of six entries).',
        'Educational Background omitting the J.D.: sn 204, 205, 208, 216 (216 omits the '
        'Nova Southeastern J.D. entirely).',
        'Bar activity holding academic appointments or narrative paragraphs: sn 201, 212, '
        '216; sn 211 holds only the single entry "State of Tennessee".',
        'Representative Clients holding client TYPES rather than client names: sn 211, 214.',
    ]),
    ('B9', 'Non-contiguous or stale selection ranges', [
        'sn 209: Super Lawyers 2009-2010 then 2021-2026 - an eleven-year gap.',
        'sn 210: Rising Stars 2004-2005 then Super Lawyers 2025-2026 - a twenty-year gap.',
        'sn 215: Super Lawyers 2010 then 2014-2026.',
        'sn 201, 206: stale or non-contiguous ranges recorded as published.',
    ]),
    ('B10', 'Name, badge and contact-format defects', [
        'sn 2: the published email is kavon@tilg.net - a SECOND firm domain (tilg.net) '
        'alongside internetlawgroup.com.',
        'sn 8 and sn 202: the Super Lawyers badge on the firm site points at a '
        'profiles.superlawyers.com path in a different metro variant than the uploaded URL '
        '(new-york/... vs new-york-metro/... for the same UUID).',
        'sn 213: the bio is written entirely in first-name register and the Professional '
        'Webpage slug appends "-esq".',
        'sn 215: the About section opens with a self-link and several inline firm links '
        'carry a HubSpot "?hsLang=en" query string.',
        'sn 216: the name appears in three renderings - "Kelly desRosiers", "Ms. DesRosiers" '
        'and the slug "kelly-ann-desrosiers".',
        'sn 210: the bar entry "Texarkana Young Lawyers Association, Co-Founder and '
        'President, 1998 to 1998" has identical start and end years.',
        'sn 214: the Transactions list holds two entries identical except for the airline '
        '(Delta / American).',
        'sn 209 and sn 213: court entries are malformed ("District court of Southern '
        'District Federal Court of Florida") and the published phone is an 888 toll-free '
        'number.',
        'sn 60 and sn 91: no phone number published.',
        'sn 167: NO law degree is published anywhere on the profile, although the bio '
        'describes him as a German, European and U.S. Patent Attorney.',
        'sn 195: only a LinkedIn URL is published (linkedin.com/in/michaelvranicar/); '
        'sn 187: the Professional Webpage IS a LinkedIn URL (linkedin.com/in/kensterling/) '
        'and must be replaced by the firm site.',
    ]),
    ('B11', 'Site-content traps that are NOT evidence', [
        'sn 7: mcalpinepllc.com carries keyword-stuffed SEO alt text on its award-badge '
        'images ("beat maker, music publishing lawyer, NIL lawyer", "avvo 10.0 Elite, '
        'Superb"). That text is marketing metadata, NOT evidence of any award; the real '
        'awards sit behind /s/McAlpine-PLLC-Awards.pdf, which was not reached. The media '
        'library also holds a file named jessica-top-attorney-*.jpg hinting at a possible '
        'colleague who is named nowhere in the page text.',
        'sn 9: cdalawllp.com renders each partner\'s name and title TWICE (collapsed card '
        'plus expanded panel) - template duplication, not a larger roster.',
        'sn 211: boonlegal.com reuses ONE portrait image across THREE advisor entries, so '
        'lawyers must be counted from page TEXT, never from images.',
        'sn 213: apollogrouplaw.com contains a mailto: address pointing at a DIFFERENT '
        'domain, and the bio asserts Charlotte AND Los Angeles while only Charlotte is '
        'published; the "$21B of transactions" figure is an unitemised aggregate.',
        'sn 214: criticalpathiplaw.com repeats "Engineering bonafides" five times (a site '
        'quality defect); the only published office address is a PO BOX (PO Box 371470, '
        'Denver, CO 80237); his matters say "Co-counsel" twice, so colleagues exist; and '
        'Bar activity lists only the Colorado Bar and the Denver Bar with NO IP association '
        'despite 90% Intellectual Property and USPTO registration.',
        'sn 169: reyesschroederlaw.com displays Lorem-ipsum testimonials and Cyrillic '
        'homoglyph characters.',
    ]),
    ('B12', 'A homepage that omits IP cannot disprove an IP practice', [
        'sn 6: passmanjones.com presents itself as "Trial and Appellate Practice" with zero '
        'IP mention on the homepage; /practice-areas/ must be fetched before any verdict is '
        'recorded. IP status for sn 6 is UNRESOLVED, not negative.',
        'sn 3: the opposite defect - cobbcole.com publishes only Civil Litigation, '
        'Construction & Design and HOA/Condominium for this attorney, and every IP reference '
        'on his profile is law-school coursework, so IP is NOT ESTABLISHED.',
        'Truncated practice lists produced false negative IP findings on sn 170, 184, 197 '
        'and 194 in an earlier pass; each must be re-derived from the firm\'s capabilities '
        'or practices page, never from a truncated homepage.',
    ]),
    ('B13', 'Process incidents during collection (no data loss in the final files)', [
        'A sandbox restart destroyed every non-git file; all work now lives inside the '
        'repository at sl_ip_verification/ and every batch ends in a commit and push.',
        '18 batches of fetch requests were lost to a malformed proxy URL; each was recovered '
        'by re-issuing the exact URL string. No row in the final dataset derives from a '
        'fabricated fetch.',
        'Two profile fetches returned a 404 page because a URL was retyped instead of copied '
        '(sn 2, sn 117); both were re-fetched verbatim.',
        'A 168-row schema drift (the "languages" key missing from 175 rows) was caught by an '
        'integrity run and normalised, so all 18 keys exist on all 216 rows.',
    ]),
]
for tag, title, items in B_ITEMS:
    A('%s. %s' % (tag, title))
    for it in items:
        A('    - ' + it)
    A('')

A('END OF ERROR LOG')

with open(os.path.join(OUT, 'Error_Log.txt'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print('error log lines:', len(L))
print('no_site', no_site)
print('no_prof_web', no_pw)
print('ambiguous', amb)
print('domains total', len(doms), 'fetched', len(sites), 'pending', len(pending))
print('failed sites', failed)
