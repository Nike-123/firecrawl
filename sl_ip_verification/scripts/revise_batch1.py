#!/usr/bin/env python3
"""Apply the Phase B batch-1 revisions decided on firm-website evidence.

Every branch prints, so a silently-skipped conditional is visible in the output.
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(HERE, 'work', 'profiles.jsonl')

rows = [json.loads(l) for l in open(P, encoding='utf-8')]
by = {r['sn']: r for r in rows}


def addendum(sn, text):
    r = by[sn]
    if text[:60] in r['note']:
        print('sn %-4d addendum ALREADY PRESENT - skipped' % sn)
        return
    r['note'] = r['note'].rstrip() + ' ' + text
    print('sn %-4d addendum appended, note len now %d' % (sn, len(r['note'])))


def set_fvs(sn, new):
    r = by[sn]
    old = r['fvs']
    if old == new:
        print('sn %-4d fvs ALREADY %s - no change written' % (sn, new))
        return
    r['fvs'] = new
    print('sn %-4d fvs CHANGED %s -> %s' % (sn, old, new))


def set_prof_web(sn, new):
    r = by[sn]
    old = r['prof_web']
    if old == new:
        print('sn %-4d prof_web ALREADY %s - no change written' % (sn, new))
        return
    r['prof_web'] = new
    print('sn %-4d prof_web CHANGED %s -> %s' % (sn, old, new))


def set_solo_evidence(sn, text):
    r = by[sn]
    if r.get('solo_evidence') == text:
        print('sn %-4d solo_evidence ALREADY set - no change written' % sn)
        return
    r['solo_evidence'] = text
    print('sn %-4d solo_evidence set (%d chars)' % (sn, len(text)))


# --- sn 7: McAlpine PLLC -- VERIFIED -> SOLO PRACTICE -----------------------
set_fvs(7, 'SOLO PRACTICE')
set_solo_evidence(7, "Firm-website evidence: mcalpinepllc.com/leadership, the published Professional Webpage, profiles exactly ONE attorney and gives him no managing-member, managing-partner or partner title. Under the standing rule a team page profiling exactly one attorney forces SOLO PRACTICE unless it carries an explicit managing-member or partner title. The firm is eponymous in substance: 'McAlpine' is his middle name (Alonzo McAlpine Alston), so McAlpine PLLC is a personal-name firm.")
addendum(7, "PHASE B REVISION 2026-11-06: Firm Verification Status changed from VERIFIED to SOLO PRACTICE on firm-website evidence. The published Professional Webpage profiles exactly ONE attorney and carries no managing-member or partner title, which under the standing rule forces SOLO PRACTICE. The firm is eponymous in substance because 'McAlpine' is his middle name (Alonzo McAlpine Alston). UNRESOLVED ANOMALY RECORDED, NOT RESOLVED: the site's Squarespace media library holds a file named jessica-top-attorney-*.jpg, which hints at a possible colleague named Jessica, but no second lawyer is named anywhere in the page text, so the roster count stands at one attorney on the evidence available. The site's award-badge images carry keyword-stuffed SEO alt text ('beat maker, music publishing lawyer, NIL lawyer', 'avvo 10.0 Elite, Superb') which is NOT evidence of any award; the real awards sit behind /s/McAlpine-PLLC-Awards.pdf, which was not reached. Full website evidence in the Phase B block below.")

# --- sn 8: Amburn Law PLLC -- published deep link redirects to pure.law -----
set_prof_web(8, 'https://pure.law/')
addendum(8, "PHASE B REVISION 2026-11-06: Lawyer Association Evidence URL changed from the published Professional Webpage https://amburnlaw.com/dean-amburn/ to https://pure.law/, because fetching the published deep link returned A DIFFERENT DOMAIN - it redirects to the homepage of The Pure.Law Firm. The firm has rebranded: the Super Lawyers firm field still says 'Amburn Law PLLC', the site brands itself 'The Pure.Law Firm', and the same site also uses 'Amburn Law P.C.' and the directory slug 'amburn-law-pllc'. Firm Verification Status stays VERIFIED. No Dean Amburn biography was reachable on pure.law (homepage only, 2 chunks), so the roster count is NOT established from the website and the site's IP evidence is firm-level, not attorney-level. Full website evidence in the Phase B block below.")

# --- sn 3: Cobb Cole -- IP not established on the firm website --------------
addendum(3, "PHASE B REVISION 2026-11-06: IP PRACTICE NOT ESTABLISHED on the firm website. cobbcole.com publishes his practice areas as only Civil Litigation, Construction & Design and HOA/Condominium law - no intellectual property practice area at all - and every IP reference on his Super Lawyers profile is law-school coursework ('sharpened his attention on intellectual property and business law', 'recognition in numerous intellectual property classes'), not practice. The structured fields still publish 20% Intellectual Property and Focus areas Copyrights, Patents, Trademarks and Intellectual Property Law. Both statements are recorded exactly as published and are deliberately NOT reconciled. Firm Verification Status stays VERIFIED (non-eponymous firm). Full website evidence in the Phase B block below.")

# --- sn 202: Edward M. Arons -- title supplied by the website ---------------
addendum(202, "PHASE B REVISION 2026-11-06: the Super Lawyers profile publishes NO title at all for Edward M. Arons; the firm website weissarons.com supplies 'Managing Partner'. That is a partnership title and therefore excludes SOLO PRACTICE, so Firm Verification Status stays VERIFIED and is now corroborated by the website rather than resting on the profile alone. His claim of involvement in 'the largest internet company acquisition' is corroborated across two sources but remains UNATTRIBUTED - no deal name, party or dollar figure is published - so it is recorded as an unverified assertion, not as a fact. Full website evidence in the Phase B block below.")

# --- sn 1: Daniel J. Aaron -- SOLO confirmed, not flipped -------------------
addendum(1, "PHASE B CONFIRMATION 2026-11-06: Firm Verification Status stays SOLO PRACTICE and is NOT flipped. djaaronlaw.com/attorney-profile/, the published Professional Webpage, resolves without redirect, matches the firm name in substance and profiles exactly ONE attorney under the title 'Member'. 'Member' is an ownership-style designation for a professional corporation but it is NOT the explicit 'managing member' or 'partner' wording the standing rule requires to escape SOLO PRACTICE, so the Phase A classification is confirmed. The site's own practice-area list leads with 'Intellectual property' and separately lists Copyrights, Trade secrets and Trademarks, each linking to a dedicated page, so the IP practice is substantiated by the firm's own site structure rather than asserted once. Full website evidence in the Phase B block below.")

rows.sort(key=lambda x: x['sn'])
with open(P, 'w', encoding='utf-8') as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + '\n')

tally = {}
for r in rows:
    tally[r['fvs']] = tally.get(r['fvs'], 0) + 1
print('rows written:', len(rows), '| fvs tally:', tally)
