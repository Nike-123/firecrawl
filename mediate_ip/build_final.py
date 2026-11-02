import csv, json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "mediate_ip_firms.csv")
BASE = "https://mediate.com/mediator-profile/"

# 1) keep the 41 already-verified rows; drop 2 search-index-only profiles that
#    are NOT in the site's 76-member IP-filtered set (name search returns none).
with open(SRC, newline="", encoding="utf-8") as f:
    rows = list(csv.reader(f))
HEAD, old = rows[0], rows[1:]
kept = [r for r in old if "Richard-Samson" not in r[4] and "uid=29282" not in r[4]]

def P(slug, uid): return "%s%s/?id=%s" % (BASE, slug, uid)

# 2) the 35 additional profiles found via matter=Intellectual+Property + location=<term>
#    name, website, firm/practice, location, (id, slug), note
NEW = [
("Frank Fallon","http://www.alternativelaw.com/","Alternative Law Mediation Results","United States, California",29124,"Frank-Fallon","Website field on profile"),
("Mark Batson Baril","http://www.resologics.com/mediation","Resologics","Reno / Las Vegas / SF Bay Area, Nevada",26677,"Mark-Batson-Baril","Website field on profile"),
("Marc Bouret","http://www.adr-resolve.com/","Bouret ADR & Mediation Firm","Walnut Creek, California",29104,"Marc-Bouret","Website field on profile"),
("BARB North","http://winwintraining.com/","WinWin Training","Woodland Hills, California",27976,"BARB-North","Website field on profile"),
("Rene Diaz","http://www.diazmediation.com/","Diaz Mediation","San Antonio, Texas",29637,"Rene-Diaz","Website field on profile"),
("Cari Rincker","http://www.rinckerlaw.com/","Rincker Law, PLLC","Champaign, New York",29352,"Cari-Rincker","Website field on profile"),
("Mari Frank","http://www.MariFrank.com/","Mari J. Frank, Esq. & Associates","Apollo Beach, Florida",29833,"Mari-Frank","Website field on profile"),
("Arthur L. Pressman","http://www.arthurlpressman.com/","Arthur L. Pressman (IP mediation)","Natick, Massachusetts",27153,"Arthur-L.-Pressman","IP-focused mediator; website field on profile"),
("David Hoffman","http://www.BLC.law/","Boston Law Collaborative, LLC","Newton, Massachusetts",26538,"David-Hoffman","Website field on profile"),
("Brian Balconi","http://www.balconimediation.com/","Balconi Mediation","Marshfield Hills, Massachusetts",40524,"Brian-Balconi","Website field on profile"),
("Abigail Pessen","http://www.pessenadr.com/","Pessen ADR","New York, New York",29112,"Abigail-Pessen","Website field on profile"),
("Ava Abramowitz","","","Leesburg",31934,"Ava-Abramowitz","No website listed on profile"),
("Lisa Cameron","https://mediate.com/ombuds","OM Services Employment Practice Group","Elkton, Maryland",29054,"Lisa-Cameron","Directory link listed on profile, not an independent firm site"),
("Tracy Allen","","","Grosse Pointe Farms, Michigan",27897,"Tracy-Allen","Profile contact block not retrievable; left blank, not guessed"),
("Robert Benjamin","http://www.rbenjamin.com/","Robert Benjamin mediation practice","San Francisco Bay Area, Oregon",26447,"Robert-Benjamin","Website field on profile"),
("Susan Bulfinch","http://www.susanbulfinch.com/","Susan Bulfinch mediation practice","Cave Creek, Arizona",28005,"Susan-Bulfinch","Website field on profile"),
("James Abrams","http://abramsadr.com/","Abrams ADR","Hamden, Connecticut",40525,"James-Abrams","Website field on profile"),
("Jeffrey Zuckerman","","","New York, New York",30224,"Jeffrey-Zuckerman","No website listed on profile"),
("Courtney Chicvak","http://cacmediation.com/","CAC Mediation / LIDRC","Kings Park, New York",29753,"Courtney-Chicvak","Website field on profile"),
("Mark Cobb","https://gcaam.com/","Georgia Center for Arbitration & Mediation","Atlanta, Georgia",40801,"Mark-Cobb","Website field on profile"),
("Jerome Weiss","https://mediate.com/mediationinc","Mediation Inc.","",27826,"Jerome-Weiss","Directory link listed on profile"),
("Dr. Gary Clayton","http://www.Negotiate.Pro","Negotiate.Pro","Dallas, Texas",28383,"Dr.-Gary-Clayton","Website field on profile"),
("Ivan K. Stevenson, Esq.","https://mediate.com/stevenson","Confidential Mediation and Dispute Resolution","Rolling Hills Estates, California",29092,"Ivan-K.-Stevenson,-Esq.","Directory link listed on profile"),
("Nicole Gesher","http://geshermediation.com/","Gesher Mediation","San Francisco, California",29280,"Nicole-Gesher","Website field on profile"),
("Philip Diamond","https://diamonddisputeresolution.com/","Diamond Dispute Resolution","San Rafael, California",29317,"Philip-Diamond","Website field on profile"),
("Frank Burke","http://burkemediation.com/","Frank Burke Mediation and Arbitration PC","San Francisco, California",27058,"Frank-Burke","Website field on profile"),
("June Jacobson, J.D., M.S.W.","https://mediate.com/junejacobson","June Jacobson divorce mediation practice","New York, New York",29058,"June-Jacobson,-J.D.,-M.S.W.","Directory link listed on profile"),
("ACCTM -","","American College of Civil Trial Mediators","Winter Park, Florida",29066,"ACCTM--","Profile page empty; no website retrievable"),
("Brian Jerome","http://www.mdrs.com/","Massachusetts Dispute Resolution Services","Salem, Massachusetts",26734,"Brian-Jerome","Website field on profile"),
("Amy Van Horne","https://www.kutakrock.com/","Kutak Rock LLP","Omaha, Nebraska",29490,"Amy-Van-Horne","Website field on profile"),
("Willie Harris","http://www.adrma.com/","Alternative Dispute Resolution (MA)","Houston, Texas",29450,"Willie-Harris","Website field on profile"),
("Laila Ollapally","http://www.campmediation.in/our-team","Centre of Advanced Mediation Practice (CAMP)","Bangalore, India",26923,"Laila-Ollapally","Website field on profile"),
("Chittu Nagarajan","","Modria / ODRworld","Chennai, India",29320,"Chittu-Nagarajan","No website listed on profile"),
("Prathamesh D Popat","https://www.mumbaimediators.com/","Mumbai Mediators","Mumbai, India",28238,"Prathamesh-D-Popat","Website field on profile"),
("Arkansas Community Dispute Resolution Centers, Inc.","http://www.acdrc.net/","Arkansas Community Dispute Resolution Centers, Inc.","Little Rock, Arkansas",28480,"Arkansas-Community-Dispute-Resolution-Centers,-Inc.","Website field on profile; 76th listing found via location=Arkansas"),
]
extra = [[n, w, f, loc, P(s, i), note] for (n, w, f, loc, i, s, note) in NEW]
ROWS = kept + extra

out = os.path.join(ROOT, "mediate_ip_firms.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(HEAD); w.writerows(ROWS)
with open(os.path.join(ROOT, "mediate_ip", "sheet_values.json"), "w", encoding="utf-8") as f:
    json.dump([HEAD] + ROWS, f, ensure_ascii=False)

with open(os.path.join(ROOT, "mediate_ip", "final_values.json"), "w", encoding="utf-8") as f:
    json.dump([["Firm / Mediator Name","Website URL","Firm / Practice","Location","Mediate.com Profile","Source / Notes"]] + ROWS, f, ensure_ascii=False)

print("total rows:", len(ROWS))
print("kept from first pass:", len(kept), "| new:", len(extra))
print("with website:", sum(1 for r in ROWS if r[1]), "| blank:", sum(1 for r in ROWS if not r[1]))
print("unique profile urls:", len(set(r[4] for r in ROWS)))
print("all http(s):", all((not r[1]) or r[1].startswith(("http://","https://")) for r in ROWS))
