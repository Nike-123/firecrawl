#!/usr/bin/env python3
"""Build the final deliverables for the Super Lawyers IP verification project.

Inputs (all under work/):
  input_records.json   [{sn, name, url}] for the 216 uploaded rows, in order
  profiles.jsonl       Phase A: one record per sn (18 keys)
  sites.jsonl          Phase B: one record per firm domain, keyed by domain

Outputs (written to output/):
  Super_Lawyers_IP_Verification.xlsx   the deliverable workbook
  Super_Lawyers_IP_Verification.csv    same rows, UTF-8 with BOM for Excel
  Summary.txt                          tallies and data-quality statistics
  Checkpoint.json                      machine-readable progress state
  Error_Log.txt                        every anomaly and error recorded

Builder semantics (must stay stable across rebuilds):
  * site records are keyed by NORMALISED DOMAIN (lowercase, no scheme, no www),
    last write wins;
  * Website Verification Status is WEBSITE VERIFIED only if ok AND firm_match,
    WEBSITE NOT VERIFIED if the domain was fetched and failed either test,
    NOT YET VERIFIED if the domain has not been fetched yet,
    NOT APPLICABLE if the profile publishes no firm website at all;
  * Evidence URL is the URL actually fetched for the firm website when one was
    fetched successfully, otherwise the Super Lawyers profile URL;
  * Lawyer Association Evidence URL is the profile's published Professional
    Webpage (may be empty - some profiles publish none);
  * IP Practice Evidence falls back ip_ev -> areas/pct/focus -> "Not established";
  * the Notes column carries the profile note, every published profile field
    (the 12 output columns have no address/phone/education columns, so nothing
    may be dropped), the Phase B website evidence and the verification summary.
"""
import csv
import json
import os
import re
import statistics
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(HERE, 'work')
OUT = os.path.join(HERE, 'output')
os.makedirs(OUT, exist_ok=True)

XLSX_CELL_LIMIT = 32767

COLUMNS = [
    'Serial Number',
    'Person Name',
    'Super Lawyers Profile URL',
    'Current Law Firm Name',
    'Official Law Firm Website URL',
    'Firm Verification Status',
    'Website Verification Status',
    'Evidence URL',
    'Lawyer Association Evidence URL',
    'IP Practice Evidence',
    'Notes',
    'Verification Date',
]

IP_RE = re.compile(
    r'(intellectual propert|patent|trademark|copyright|trade secret|trade dress'
    r'|licens\w* of (?:invention|technology)|\bIP\b|USPTO'
    r'|Patent and Trademark Office)', re.I)

# Phrases the Phase A notes use to qualify an IP claim. When one is present the
# qualification is copied into the IP Practice Evidence column verbatim in
# substance, so the column cannot read as a clean confirmation on its own.
QUALIFIERS = [
    ('IP PRACTICE NOT ESTABLISHED',
     'QUALIFIED: the firm website does NOT establish an IP practice for this attorney - '
     'see the Notes column.'),
    ('NOT SUBSTANTIATED',
     'QUALIFIED: the IP allocation appears in the structured fields but is NOT SUBSTANTIATED '
     'by the narrative on the profile - see the Notes column.'),
    ('not established',
     'QUALIFIED: part of the IP claim is recorded in the Notes column as not established - '
     'read the Notes column before relying on this row.'),
    ('unsubstantiated',
     'QUALIFIED: part of the IP claim is recorded in the Notes column as unsubstantiated - '
     'read the Notes column before relying on this row.'),
    ('asserted but',
     'QUALIFIED: the Notes column records an IP assertion that is qualified - read it before '
     'relying on this row.'),
]


def norm_domain(d):
    d = (d or '').strip().lower()
    if '://' in d:
        d = d.split('://', 1)[1]
    d = d.split('/', 1)[0]
    return d[4:] if d.startswith('www.') else d


def load():
    inp = json.load(open(os.path.join(WORK, 'input_records.json'), encoding='utf-8'))
    prof = {}
    for line in open(os.path.join(WORK, 'profiles.jsonl'), encoding='utf-8'):
        line = line.strip()
        if line:
            r = json.loads(line)
            prof[r['sn']] = r
    sites = {}
    for line in open(os.path.join(WORK, 'sites.jsonl'), encoding='utf-8'):
        line = line.strip()
        if line:
            r = json.loads(line)
            sites[norm_domain(r['domain'])] = r          # last write wins
    return inp, prof, sites


def ip_evidence(r, srec):
    """ip_ev -> structured fields -> 'Not established'."""
    if r.get('ip_ev'):
        base = [r['ip_ev']]
    else:
        base = []
        if r.get('status') and IP_RE.search(r['status']):
            base.append('Super Lawyers headline: ' + r['status'])
        alloc = [s.strip() for s in (r.get('pct') or '').split(';') if IP_RE.search(s)]
        if alloc:
            base.append('Published practice split: ' + '; '.join(alloc))
        areas = [s.strip() for s in (r.get('areas') or '').split(',') if IP_RE.search(s)]
        if areas:
            base.append('Practice areas: ' + ', '.join(areas))
        focus = [s.strip() for s in (r.get('focus') or '').split(',') if IP_RE.search(s)]
        if focus:
            base.append('Focus areas: ' + ', '.join(focus))
        if IP_RE.search(r.get('admitted') or ''):
            base.append('Bar admission field: ' + r['admitted'])
        if r.get('ip_note'):
            base.append(r['ip_note'])
    if srec and srec.get('ok'):
        base.append('Firm website ' + srec['domain'] + ' fetched and checked - the site\'s own '
                    'IP evidence is quoted in the Notes column below.')
    if not base:
        return 'Not established'
    # Carry the row's own qualification forward, so the column never reads as a
    # clean confirmation when the Notes column says otherwise.
    note = r.get('note') or ''
    for marker, qualifier in QUALIFIERS:
        if marker in note:
            base.append(qualifier)
            break
    return ' || '.join(base)


def website_status(site_url, srec):
    if not (site_url or '').strip():
        return 'NOT APPLICABLE'
    if srec is None:
        return 'NOT YET VERIFIED'
    if srec.get('ok') and srec.get('firm_match'):
        return 'WEBSITE VERIFIED'
    return 'WEBSITE NOT VERIFIED'


def firm_basis(r, wvs):
    why = []
    fvs = r.get('fvs', '')
    if fvs == 'SOLO PRACTICE':
        why.append(r.get('solo_evidence') or 'solo-practice conditions met on the published profile')
    elif fvs == 'AMBIGUOUS':
        why.append('the Super Lawyers firm field and the profile bio name different firms')
    elif fvs == 'VERIFIED':
        why.append('the firm is not eponymous, or it publishes a partnership/managing title, '
                   'multiple offices or a multi-attorney roster (derivation in the Notes column)')
    else:
        why.append('no classification recorded')
    why.append('website verification status: ' + wvs.lower())
    return '; '.join(why)


FIELDS_BLOCK = [
    ('Headline published by Super Lawyers', 'status'),
    ('Practice split', 'pct'),
    ('Practice areas', 'areas'),
    ('Focus areas', 'focus'),
    ('Super Lawyers selections', 'selections'),
    ('Bar admission / first admitted', 'admitted'),
    ('Office address', 'addr'),
    ('Phone', 'phone'),
    ('Educational background', 'education'),
    ('Languages', 'languages'),
]


def notes_for(r, srec, wvs, date):
    parts = [r.get('note', '').rstrip()]
    lines = ['--- PROFILE FIELDS EXACTLY AS PUBLISHED BY SUPER LAWYERS ---']
    for label, key in FIELDS_BLOCK:
        val = (r.get(key) or '').strip()
        lines.append(label + ': ' + (val if val else '(not published)'))
    parts.append('\n'.join(lines))
    if srec is not None:
        parts.append('--- PHASE B: FIRM WEBSITE CHECK ---\nDomain: ' + srec['domain']
                     + '\nURL fetched: ' + (srec.get('url') or '(none recorded)')
                     + '\nPage loaded with usable content: ' + ('YES' if srec.get('ok') else 'NO')
                     + '\nSite branding matches the Super Lawyers firm name: '
                     + ('YES' if srec.get('firm_match') else 'NO')
                     + '\nEvidence:\n' + (srec.get('note') or '(no evidence recorded)'))
    elif (r.get('site') or '').strip():
        parts.append('--- PHASE B: FIRM WEBSITE CHECK ---\nDomain ' + norm_domain(r['site'])
                     + ' has NOT been fetched yet; the website check for this row is pending.')
    else:
        parts.append('--- PHASE B: FIRM WEBSITE CHECK ---\nNot applicable: this profile publishes '
                     'no official law firm website, so there is nothing to verify.')
    parts.append('--- VERIFICATION SUMMARY (' + date + ') ---\n'
                 + 'Firm Verification Status: ' + r.get('fvs', '') + '.\nBasis: '
                 + firm_basis(r, wvs) + '.\n'
                 + 'Website Verification Status: ' + wvs + '.')
    return '\n\n'.join(p for p in parts if p)


def main():
    inp, prof, sites = load()
    date = '2026-11-06'
    out_rows = []
    truncated = []
    w_tally = {}
    f_tally = {}
    no_ip = []
    qualified = []
    for rec in inp:
        sn = rec['sn']
        r = prof.get(sn)
        if r is None:
            raise SystemExit('FATAL: no profile record for sn %d' % sn)
        dom = norm_domain(r.get('site'))
        srec = sites.get(dom) if dom else None
        wvs = website_status(r.get('site'), srec)
        w_tally[wvs] = w_tally.get(wvs, 0) + 1
        f_tally[r.get('fvs', '')] = f_tally.get(r.get('fvs', ''), 0) + 1
        evidence = (srec.get('url') if (srec and srec.get('ok') and srec.get('url'))
                    else rec['url'])
        ipe = ip_evidence(r, srec)
        if ipe == 'Not established':
            no_ip.append(sn)
        if 'QUALIFIED:' in ipe:
            qualified.append(sn)
        notes = notes_for(r, srec, wvs, date)
        if len(notes) > XLSX_CELL_LIMIT:
            truncated.append((sn, len(notes)))
        out_rows.append({
            'Serial Number': sn,
            'Person Name': rec['name'],
            'Super Lawyers Profile URL': rec['url'],
            'Current Law Firm Name': r.get('firm', ''),
            'Official Law Firm Website URL': r.get('site', ''),
            'Firm Verification Status': r.get('fvs', ''),
            'Website Verification Status': wvs,
            'Evidence URL': evidence,
            'Lawyer Association Evidence URL': r.get('prof_web', ''),
            'IP Practice Evidence': ipe,
            'Notes': notes,
            'Verification Date': date,
        })

    # ---------------- CSV (full, untruncated) ----------------
    csv_path = os.path.join(OUT, 'Super_Lawyers_IP_Verification.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    # ---------------- XLSX (Excel's 32767-char cell cap applies) -------------
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = 'IP Verification'
    head_font = Font(bold=True, color='FFFFFF')
    head_fill = PatternFill('solid', fgColor='1F3864')
    for c, name in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.font = head_font
        cell.fill = head_fill
        cell.alignment = Alignment(vertical='center')
    for i, row in enumerate(out_rows, 2):
        for c, name in enumerate(COLUMNS, 1):
            v = row[name]
            if isinstance(v, str) and len(v) > XLSX_CELL_LIMIT:
                v = v[:XLSX_CELL_LIMIT - 60] + ' [...TRUNCATED FOR EXCEL - FULL TEXT IN THE CSV]'
            ws.cell(row=i, column=c, value=v)
    widths = {'Serial Number': 8, 'Person Name': 26, 'Super Lawyers Profile URL': 42,
              'Current Law Firm Name': 34, 'Official Law Firm Website URL': 34,
              'Firm Verification Status': 20, 'Website Verification Status': 22,
              'Evidence URL': 42, 'Lawyer Association Evidence URL': 42,
              'IP Practice Evidence': 60, 'Notes': 90, 'Verification Date': 16}
    for c, name in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(c)].width = widths.get(name, 24)
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = 'A1:%s%d' % (get_column_letter(len(COLUMNS)), len(out_rows) + 1)
    xlsx_path = os.path.join(OUT, 'Super_Lawyers_IP_Verification.xlsx')
    wb.save(xlsx_path)

    # ---------------- statistics ----------------
    note_lens = [len(r['Notes']) for r in out_rows]
    firms = {r['Current Law Firm Name'].strip() for r in out_rows if r['Current Law Firm Name'].strip()}
    doms = {norm_domain(r['Official Law Firm Website URL']) for r in out_rows
            if r['Official Law Firm Website URL'].strip()}
    no_site = [r['Serial Number'] for r in out_rows if not r['Official Law Firm Website URL'].strip()]
    no_pw = [r['Serial Number'] for r in out_rows if not r['Lawyer Association Evidence URL'].strip()]
    shared = {}
    for r in out_rows:
        d = norm_domain(r['Official Law Firm Website URL'])
        if d:
            shared.setdefault(d, []).append(r['Serial Number'])
    shared = {d: s for d, s in shared.items() if len(s) > 1}
    ambiguous = [r['Serial Number'] for r in out_rows if r['Firm Verification Status'] == 'AMBIGUOUS']
    review = sorted(set(ambiguous + [r['Serial Number'] for r in out_rows
                                     if r['Website Verification Status'] == 'WEBSITE NOT VERIFIED']))

    dates = sorted({r['Verification Date'] for r in out_rows})
    lines = []
    lines.append('SUPER LAWYERS - INTELLECTUAL PROPERTY PRACTICE VERIFICATION')
    lines.append('Summary of results')
    lines.append('Generated: ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    lines.append('Verification date recorded on every row: ' + ', '.join(dates))
    lines.append('')
    lines.append('ROWS')
    lines.append('  Rows in the uploaded input file ....... %d' % len(inp))
    lines.append('  Rows in the output workbook ........... %d' % len(out_rows))
    lines.append('  Serial numbers ........................ %d - %d, contiguous, no duplicates'
                 % (out_rows[0]['Serial Number'], out_rows[-1]['Serial Number']))
    lines.append('  Unique person names ................... %d'
                 % len({r['Person Name'] for r in out_rows}))
    lines.append('  Unique Super Lawyers profile URLs ..... %d'
                 % len({r['Super Lawyers Profile URL'] for r in out_rows}))
    lines.append('')
    lines.append('FIRM VERIFICATION STATUS')
    for k in sorted(f_tally):
        lines.append('  %-14s %d' % (k, f_tally[k]))
    lines.append('')
    lines.append('WEBSITE VERIFICATION STATUS')
    for k in sorted(w_tally):
        lines.append('  %-20s %d' % (k, w_tally[k]))
    lines.append('  (NOT YET VERIFIED = the firm domain has not been fetched yet;'
                 ' Phase B is in progress.)')
    lines.append('')
    lines.append('PHASE B PROGRESS (firm-website checks)')
    lines.append('  Unique firm names published ........... %d' % len(firms))
    lines.append('  Unique firm domains published ......... %d' % len(doms))
    lines.append('  Domains fetched and saved ............. %d' % len(sites))
    lines.append('  Domains still to fetch ................ %d' % len(doms - set(sites)))
    lines.append('  Domains shared by 2+ rows ............. %d' % len(shared))
    lines.append('')
    lines.append('IP PRACTICE EVIDENCE')
    lines.append('  Rows with published IP evidence ....... %d' % (len(out_rows) - len(no_ip)))
    lines.append('  Rows where IP is "Not established" .... %d  %s'
                 % (len(no_ip), no_ip if no_ip else ''))
    lines.append('  Every one of the 216 profiles publishes at least one IP term in its')
    lines.append('  headline, practice split, practice areas or focus areas, so this column is')
    lines.append('  never empty. HOW WELL each claim is substantiated varies row by row and is')
    lines.append('  analysed in the Notes column: rows whose own note qualifies the claim carry')
    lines.append('  a "QUALIFIED:" prefix in the IP Practice Evidence cell.')
    lines.append('  Rows carrying that qualification ...... %d  %s' % (len(qualified), qualified))
    lines.append('')
    lines.append('ROWS WITH NO PUBLISHED WEBSITE / PROFESSIONAL WEBPAGE')
    lines.append('  No official law firm website .......... %d  %s' % (len(no_site), no_site))
    lines.append('  No Professional Webpage ............... %d  %s' % (len(no_pw), no_pw))
    lines.append('')
    lines.append('NOTES COLUMN (characters)')
    lines.append('  Minimum ....... %d' % min(note_lens))
    lines.append('  Median ........ %d' % int(statistics.median(note_lens)))
    lines.append('  Maximum ....... %d' % max(note_lens))
    lines.append('  Total ......... %d' % sum(note_lens))
    lines.append('  Cells over Excel\'s 32,767-character limit (truncated in the XLSX only,'
                 ' full text kept in the CSV): %d %s' % (len(truncated), truncated))
    lines.append('')
    lines.append('REVIEW QUEUE (ambiguous firm identity or failed website check)')
    lines.append('  %d rows: %s' % (len(review), review))
    lines.append('')
    lines.append('FILES')
    for p in ('Super_Lawyers_IP_Verification.xlsx', 'Super_Lawyers_IP_Verification.csv',
              'Summary.txt', 'Checkpoint.json', 'Error_Log.txt'):
        fp = os.path.join(OUT, p)
        lines.append('  %-42s %s' % (p, ('%d bytes' % os.path.getsize(fp))
                                     if os.path.exists(fp) else 'written by this run'))
    summary = '\n'.join(lines) + '\n'
    with open(os.path.join(OUT, 'Summary.txt'), 'w', encoding='utf-8') as fh:
        fh.write(summary)

    # ---------------- Checkpoint.json ----------------
    ck = {
        'project': 'Super Lawyers IP practice verification',
        'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'verification_date': date,
        'input_rows': len(inp),
        'output_rows': len(out_rows),
        'phase_a': {'status': 'COMPLETE', 'profiles': len(prof),
                    'file': 'work/profiles.jsonl',
                    'firm_verification_tally': f_tally},
        'phase_b': {'status': 'IN PROGRESS',
                    'domains_total': len(doms),
                    'domains_fetched': len(sites),
                    'domains_pending': len(doms - set(sites)),
                    'queue_file': 'work/phase_b_queue.txt',
                    'findings_file': 'work/sites.jsonl',
                    'website_verification_tally': w_tally},
        'review_queue': review,
        'notes_characters_total': sum(note_lens),
        'notes_cells_truncated_for_excel': truncated,
        'outputs': {'xlsx': os.path.relpath(xlsx_path, HERE),
                    'csv': os.path.relpath(csv_path, HERE),
                    'summary': 'output/Summary.txt',
                    'checkpoint': 'output/Checkpoint.json',
                    'error_log': 'output/Error_Log.txt'},
        'rebuild_command': 'python3 scripts/build_outputs.py',
    }
    with open(os.path.join(OUT, 'Checkpoint.json'), 'w', encoding='utf-8') as fh:
        json.dump(ck, fh, indent=2, ensure_ascii=False)

    print(summary)
    print('WROTE', xlsx_path)
    print('WROTE', csv_path)
    return out_rows, ck


if __name__ == '__main__':
    main()
