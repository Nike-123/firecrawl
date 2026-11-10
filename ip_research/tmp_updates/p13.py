import json, re, unicodedata

BASE='data/states/'
def load(n): return json.load(open(BASE+n, encoding='utf-8'))
def save(n,d): json.dump(d, open(BASE+n,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
def norm(s): return re.sub(r'[^a-z0-9]+','',(s or '').lower())

report={'website_fixed':[], 'added':[], 'dropped':[], 'renamed':[], 'review_cleared':[], 'missed':[]}

def find(d,name):
    for f in d['firms']:
        if norm(f['firm'])==norm(name): return f
    for f in d['firms']:
        if norm(name) in norm(f['firm']): return f
    return None

def fix(fname, firm, site, evidence, attorneys=None, clear=True, extra_pages=()):
    d=load(fname); f=find(d,firm)
    if not f:
        report['missed'].append(f'{fname}:{firm} (website)'); return
    f['website']=site; f['website_verified']=True; f['verification']=evidence
    if clear: f.pop('needs_review',None); f.pop('review_reason',None)
    if attorneys:
        for a in attorneys:
            if a not in f['attorneys']: f['attorneys'].append(a)
    for p in extra_pages:
        if p not in d['pages_reviewed']: d['pages_reviewed'].append(p)
    save(fname,d); report['website_fixed'].append(f'{d["state"]}: {f["firm"]} -> {site}')

def add(fname, firm, site, evidence, attorneys, verified=True, review=None, pages=(), listings=0):
    d=load(fname)
    if find(d,firm):
        report['missed'].append(f'{fname}:{firm} (exists)'); return
    rec={'firm':firm,'website':site,'website_verified':verified,'verification':evidence,'attorneys':attorneys}
    if review:
        rec['needs_review']=True; rec['review_reason']=review
    d['firms'].append(rec)
    for p in pages:
        if p not in d['pages_reviewed']: d['pages_reviewed'].append(p)
    d['listings_reviewed']=d.get('listings_reviewed',0)+listings
    save(fname,d); report['added'].append(f'{d["state"]}: {firm}')

def drop(fname, firm, reason):
    d=load(fname); f=find(d,firm)
    if not f: report['missed'].append(f'{fname}:{firm} (drop)'); return
    d['firms']=[x for x in d['firms'] if x is not f]
    save(fname,d); report['dropped'].append(f'{d["state"]}: {f["firm"]} — {reason}')

FL=['https://lawyers.findlaw.com/patents/florida/miami/']
# ---------------- website resolutions (all four-column, no guessing) ----------------
fix('27-montana.json','Calton Hamman & Wolff','https://www.caltonhammanandwolff.com/',
    'FindLaw Billings profile lists Website: https://www.caltonhammanandwolff.com/ (firm site confirms Billings office).',
    extra_pages=('https://lawyers.findlaw.com/montana/billings/2539941_1/','https://lawyers.findlaw.com/patents/montana/billings/'))
fix('27-montana.json','Antoinette M. Tease','https://www.teaselaw.com/',
    'FindLaw Billings profile lists Website: http://www.teaselaw.com; teaselaw.com is the Billings IP boutique site (patent/trademark/copyright prosecution, litigation, expert witness).')
fix('28-nebraska.json','Law Office of Matt Catlett','https://www.catlettlaw.com/',
    'Firm site catlettlaw.com (701 P St, Lincoln NE) states patent and trademark practice; FindLaw Nebraska patents listing.')
fix('46-vermont.json','Merritt & Merritt','http://www.merritt-merritt.com/',
    'Firm domain merritt-merritt.com corroborated by two independent business profiles for 60 Lake St, Burlington VT; Sharon J. Merritt (IP/media) is a firm attorney.',
    attorneys=['Sharon J. Merritt'])
fix('35-north-dakota.json','Fargo Patent & Business Law','https://fargopatentlaw.com/',
    'fargopatentlaw.com is the firm site (Fargo, ND) describing itself as an intellectual property and business law practice; Super Lawyers lists fargopatentlaw.com for the same address.',
    attorneys=['Stephanie Arniel'])
fix('46-vermont.json','Paul Frank + Collins','https://www.pfclaw.com/',
    'FindLaw profile lists http://www.pfclaw.com; pfclaw.com confirms One Church Street, Burlington VT.')
fix('49-west-virginia.json','Schrader Duff','https://www.schraderlaw.com/',
    'FindLaw Wheeling profile lists Website: https://www.schraderlaw.com/. Super Lawyers profile lists John Porco with Intellectual Property Litigation at the firm, so the IP-litigation association is evidenced.',
    attorneys=['John Porco'])
fix('51-wyoming.json','Schwartz, Bon','http://www.schwartzbon.com/',
    'FindLaw Casper profile lists Website: http://www.schwartzbon.com.')
fix('41-south-carolina.json','Henderson & Henderson','https://hhlawsc.com/',
    'FindLaw Charleston profile lists https://hhlawsc.com/; the firm site lists a Trademark Law practice area under Business Law.',
    attorneys=['John Henderson','Wesley Henderson'])
fix('41-south-carolina.json','Hurley Law','https://www.hurleylawsc.com/',
    'FindLaw Greenville profile lists https://www.hurleylawsc.com; firm site covers trademark registration and trademark/business litigation.')
fix('38-oregon.json','The Smith Firm','https://www.thesmithfirmpc.com/',
    'FindLaw West Linn profile lists Website: https://www.thesmithfirmpc.com.', attorneys=['Dave Smith'])
fix('45-utah.json','James Dodge Russell & Stephens','https://www.jdrslaw.com/',
    'FindLaw Salt Lake City profile lists Website: https://www.jdrslaw.com; practice areas include Intellectual Property Litigation.')
fix('23-michigan.json','Drew Cooper & Anding','https://dca-lawyers.com/',
    'FindLaw Grand Rapids profile lists https://dca-lawyers.com/; firm site describes Michigan litigation practice.')
fix('19-louisiana.json','Flowers Davis','https://flowersdavis.com/',
    'Firm domain flowersdavis.com for the Tyler TX office listed on the FindLaw Louisiana record; firm practice list includes Intellectual Property and Patent Prosecution.')
fix('11-georgia.json','Hollin Law Offices','https://www.hollinpatent.com/',
    'hollinpatent.com is the firm site (Fayetteville GA) of registered patent attorney J.T. Hollin; firm name and practice described on FindLaw Atlanta patents listing.',
    attorneys=['J.T. Hollin'])
fix('15-indiana.json','TDW Patents & Consulting','https://www.tdwpatents.com/',
    'FindLaw Greenwood IN profile lists Website: http://www.tdwpatents.com; firm run by Thomas D. Webster, PhD, JD.',
    attorneys=['Thomas D. Webster'])
fix('17-kansas.json','Davis & Jack','http://www.davisandjack.com/',
    'FindLaw Wichita profile lists Website: http://www.davisandjack.com; Kenneth H. Jack practices patent, trademark and copyright law at the firm.',
    attorneys=['Kenneth H. Jack'])
fix('12-hawaii.json','Bailey Law Corporation','https://www.bailey.law/hawaii',
    'FindLaw Honolulu profile lists Website: http://www.bailey.law/hawaii.')

# ---------------- corrections, normalizations, new records ----------------
fix('36-ohio.json','Wesp Barwell','https://www.wesplaw.com/',
    'FindLaw Cleveland/Dublin listing shows the firm as Wesp Barwell Berardino with Website https://www.wesplaw.com/; firm record renamed accordingly.')
d=load('36-ohio.json'); f=find(d,'Wesp Barwell')
if f and f['firm']!='Wesp Barwell Berardino':
    old=f['firm']; f['firm']='Wesp Barwell Berardino'; save('36-ohio.json',d); report['renamed'].append(f'OH: {old} -> {f["firm"]}')
add('36-ohio.json','Krugliak, Wilkins, Griffiths & Dougherty Co., L.P.A.','https://www.kwgd.com/',
    'FindLaw Cleveland patents listing (Canton office) names John B. Schomer at kwgd.com; firm maintains an intellectual property practice group.',
    ['John B. Schomer'], pages=('https://lawyers.findlaw.com/patents/ohio/cleveland/',), listings=4)

add('23-michigan.json','Fleming & Borowicz PLC','https://www.fblawplc.com/',
    'CORRECTION: reinstated. FindLaw patents listings for Detroit/Novi/Saginaw show a patent practice with Gavin J. Fleming, Christina Borowicz and Francis Way (USPTO-registered); fblawplc.com is the Novi firm site. The phase-4 exclusion was based on a mistaken practice-area read.',
    ['Gavin J. Fleming','Christina Borowicz','Francis Way'], pages=('https://lawyers.findlaw.com/patents/michigan/detroit/',), listings=6)
add('23-michigan.json','Murphy & Spagnuolo PC','https://www.mbspclaw.com/',
    'FindLaw Detroit patents listing (Okemos office) with Website https://www.mbspclaw.com/.', [],
    pages=('https://lawyers.findlaw.com/patents/michigan/detroit/',))
add('23-michigan.json','Raggio & Dinnin, P.C.','',
    'FindLaw Detroit patents listing (Troy office). No website is printed on the FindLaw profile and no firm-controlled domain was verified, so the URL is left blank per the no-guessing rule.',
    [], verified=False, review='Official website not verifiable from FindLaw profile; firm domain unconfirmed.', pages=('https://lawyers.findlaw.com/patents/michigan/detroit/',))

add('05-california.json','Harris & Hayden','https://harrishayden.com/',
    'FindLaw Los Angeles patents listing with Website https://harrishayden.com/; Los Angeles IP litigation boutique.', [],
    pages=('https://lawyers.findlaw.com/patents/california/los-angeles/',), listings=3)
add('05-california.json','Sterling Media Law','https://www.sterlingmedialaw.com/',
    'FindLaw Los Angeles patents listing with Website https://www.sterlingmedialaw.com/; media/entertainment practice covering copyright work.', [],
    pages=('https://lawyers.findlaw.com/patents/california/los-angeles/',))

add('44-texas.json','Booth Albanesi Schroeder, PLLC','https://www.ipoftexas.com/',
    'FindLaw Dallas/Houston patents listing with Website https://www.ipoftexas.com/ (Dallas IP firm).', [],
    pages=('https://lawyers.findlaw.com/patents/texas/houston/',), listings=4)
add('44-texas.json','Parker Justiss, P.C.','https://www.pj-iplaw.com/',
    'FindLaw Dallas patents listing with Website https://www.pj-iplaw.com/.', [])
add('44-texas.json','The Wendt Firm, P.C.','https://www.wendtfirm.com/',
    'FindLaw Austin patents listing with Website https://www.wendtfirm.com/ (Austin patent firm).', [])

add('33-new-york.json','Saile Ackerman LLC','https://www.saileackerman.com/',
    'FindLaw patents listing for New York (Poughkeepsie office) with Website https://www.saileackerman.com/.', [],
    pages=('https://lawyers.findlaw.com/patents/new-york/new-york/','https://lawyers.findlaw.com/patents/new-york/buffalo/'), listings=6)
add('33-new-york.json','Lee Palmateer Law Office','https://www.albanyiplaw.com/',
    'FindLaw patents listing for New York (Albany office) with Website https://www.albanyiplaw.com/.', ['Lee Palmateer'])
add('33-new-york.json','Cox Padmore Skolnik & Shakarchy LLP','https://www.cpsslaw.com/',
    'FindLaw New York patents listing with Website https://www.cpsslaw.com/; firm site lists an Intellectual Property practice (license agreements, trademark/copyright infringement and litigation, patents) and partner Steven D. Skolnik lists Patents/Trademarks.',
    ['Steven D. Skolnik'])
add('33-new-york.json','Simpson & Simpson, PLLC','https://www.idealawyers.com/',
    'FindLaw patents listings for Buffalo NY and Palm Beach Gardens FL with Website https://www.idealawyers.com/; multi-state firm recorded under both states.', [])

add('10-florida.json','Simpson & Simpson, PLLC','https://www.idealawyers.com/',
    'FindLaw patents listing for Miami (Palm Beach Gardens office) with Website https://www.idealawyers.com/.', [], pages=FL, listings=4)
add('10-florida.json','The Law Office of Geralyn F. Noonan','https://www.noonanlaw.com/',
    'FindLaw patents listing for Miami (Fort Myers office) with Website https://www.noonanlaw.com/.', ['Geralyn F. Noonan'])

add('14-illinois.json','Law Office of Adrienne B. Naumann','https://www.naumannpatentcopyright.com/',
    'FindLaw Chicago patents listing (Skokie office) with Website https://www.naumannpatentcopyright.com/; patent and copyright practice.',
    ['Adrienne B. Naumann'], pages=('https://lawyers.findlaw.com/patents/illinois/chicago/',), listings=5)

add('26-missouri.json','Lodestar IP & Patent Law','http://www.lodestar.law/',
    'FindLaw Missouri patents listing (Brentwood office) with Website http://www.lodestar.law/.', [],
    pages=('https://lawyers.findlaw.com/patents/missouri/','https://lawyers.findlaw.com/patents/missouri/saint-louis/'), listings=2)

# ---------------- non-IP prune ----------------
drop('49-west-virginia.json','Phillips, Gardill','pgka.com firm profile lists banking, corporate, real estate, estates, employment, civil litigation, tax, family — no intellectual property practice; listed only as an incidental directory placement.')

json.dump(report, open('tmp_updates/p13_report.json','w'), indent=1)
print(json.dumps(report, indent=1))
