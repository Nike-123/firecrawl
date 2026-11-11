import json,re
BASE='data/states/'
def load(n): return json.load(open(BASE+n,encoding='utf-8'))
def save(n,d): json.dump(d,open(BASE+n,'w',encoding='utf-8'),indent=1,ensure_ascii=False)
def norm(s): return re.sub(r'[^a-z0-9]+','',(s or '').lower())
rep={'fixed':[],'dropped':[],'note':[]}

# NJ: Schoendorf Law official site verified
p='31-new-jersey.json'; d=load(p)
for f in d['firms']:
    if 'schoendorf' in norm(f['firm']):
        f['website']='https://www.schoendorflawllc.com/'; f['website_verified']=True
        f['verification']='schoendorflawllc.com is the firm site for Schoendorf Law, LLC (971 US Hwy 202N, Branchburg NJ; founder Priscilla Schoendorf, Esq., (609) 250-0020) — matches the FindLaw Branchburg listing exactly.'
        f.pop('needs_review',None); f.pop('review_reason',None)
        if 'Priscilla Schoendorf' not in f['attorneys']: f['attorneys'].append('Priscilla Schoendorf')
        rep['fixed'].append('NJ: Schoendorf Law -> schoendorflawllc.com')
save(p,d)

# HI: Hoftiezer standalone listing is a duplicate of Goodsill (current verified affiliation)
p='12-hawaii.json'; d=load(p)
hof=[f for f in d['firms'] if 'hoftiezer' in norm(f['firm'])]
goods=[f for f in d['firms'] if norm(f['firm']).startswith('goodsill')]
if hof and goods:
    d['firms']=[f for f in d['firms'] if f is not hof[0]]
    if 'David J. Hoftiezer' not in goods[0]['attorneys']: goods[0]['attorneys'].append('David J. Hoftiezer')
    goods[0]['verification']=goods[0].get('verification','')+' David J. Hoftiezer (separately listed by FindLaw as "Law Office of David J. Hoftiezer") is documented at Goodsill in independent directory and Honolulu Magazine Best Lawyers data; the standalone record was merged into this firm record to avoid a duplicate person.'
    rep['dropped'].append('HI: Law Office of David J. Hoftiezer (merged into Goodsill as attorney)')
    save(p,d)

# remaining unresolved explicitly documented
p='12-hawaii.json'; d=load(p)
d['limitations']=d.get('limitations','')+' David J. Hoftiezer appears in FindLaw as a standalone "Law Office of" record; independent verification places him at Goodsill Anderson Quinn & Stifel, so the standalone record was merged rather than kept as a separate firm.'
save(p,d)

for fn,note in (('31-new-jersey.json','Sleem Law and Frank Tolin & Associates remain without an official website: FindLaw prints no URL, and repeated searches returned only directory profiles (no firm-controlled domain). URLs left blank rather than guessed.'),
                ('35-north-dakota.json','Atlas Legal Services, PLLC (3933 4th St E, West Fargo; Bart Robert McIlonie) has no verifiable public website — the only domain seen is an email domain (atlasesop.com) that does not resolve to a firm site — and its FindLaw-adjacent listings describe a general practice with trademark filings. Record retained but flagged for manual review; URL left blank.'),
                ('15-indiana.json','Adam D. Decker (Crown Point, IN) keeps a blank website: FindLaw/Justia print no firm URL and no firm-controlled domain was verified; a standalone attorney record is retained.'),
                ('23-michigan.json','Raggio & Dinnin, P.C. (Troy, MI) is listed in the FindLaw patents directory without a website link; no firm-controlled domain was verified, so the URL is blank.'),
                ('49-west-virginia.json','Phillips, Gardill, Kaiser & Altmeyer was removed: its own firm profile (pgka.com) lists banking, corporate, real estate, estates, employment, civil litigation, tax and family law with no intellectual property practice. Schrader Duff Law & Lowe is retained because its Super Lawyers profile lists John Porco with intellectual property litigation, and its URL is now verified.')):
    d=load(fn); d['limitations']=(d.get('limitations','')+' '+note).strip(); save(fn,d)
    rep['note'].append(fn)

json.dump(rep,open('tmp_updates/p14_report.json','w'),indent=1)
print(json.dumps(rep,indent=1))
