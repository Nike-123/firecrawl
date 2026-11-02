import csv, json, os
BASE = "https://mediate.com/mediator-profile/"
def p(slug, uid=None):
    return BASE + slug + "/" + ("?id=%s" % uid if uid else "")

# name, website, firm/practice, location, profile, notes
R = [
["Amy Foust","https://foustiplaw.com/","Foust IP Law","North Miami, Florida",p("Amy-Foust","28593"),"Website field on Mediate.com profile"],
["Lori Adelson","http://www.milesadr.com/","Approved Dispute Resolution / Miles ADR","Fort Lauderdale, Florida",p("Lori-Adelson","29508"),"Website field on profile"],
["Barry Ross, Esq., MBA","http://www.rossmediation.com/","Ross Mediation","Dallas, Texas",p("Barry-Ross,-Esq.,-MBA","29776"),"Duplicate source listing of the Pasadena Barry Ross row; same website"],
["Arthur House","","","Chevy Chase, Maryland",p("Arthur-House","40121"),"No website listed on profile"],
["Robin Caral Shaw","http://ladymediator.net/mediator/","Lady Mediator / Mediation Training Group","Boca Raton, Florida",p("Robin-Caral-Shaw","29501"),"Website field on profile"],
["Hon. Frank J. Ochoa (Ret.)","http://destinationadr.com/","Destination ADR (Of Counsel, The Sanger Firm)","Santa Barbara, California",p("Hon.-Frank-J.-Ochoa-(Ret.)","40200"),"Website field on profile"],
["Robert Wright","http://www.thepeacetalks.com/","The Peace Talks","Grand Rapids, Michigan",p("Robert-Wright","27095"),"Website field on profile"],
["Amy Lieberman","http://www.insightmediation.com/","Insight Employment Mediation","Scottsdale, Arizona",p("Amy-Lieberman","29135"),"Website field on profile"],
["Barbara Allen","http://mediatorsandarbitratorsofamerica.com/","Mediators & Arbitrators of America","Georgetown, Texas",p("Barbara-Allen","29454"),"Website field on profile"],
["Sangeeta Mehrotra","http://www.linkedin.com/in/sangeetamehrotradelhi","Independent mediator","New Delhi, India",p("Sangeeta-Mehrotra","29805"),"Profile lists a LinkedIn URL, not a firm website"],
["Michael B. Smith","https://rfbllp.com/team-michael-smith","Metrowest Mediation Services / Rottenstreich Farley Bronstein Fisher Potter Hodas LLP","New York, New York",p("Michael-B.-Smith","32041"),"As listed on indexed profile; that link currently returns 404"],
["Barry Wernick","http://www.barrywernick.com/","Barry Wernick","Dallas, Texas",p("Barry-Wernick","29640"),"Website field on profile"],
["DENNIS COHEN","http://www.settlementworks.com/","Settlement Works","Marina Del Rey, California",p("DENNIS-COHEN","29330"),"Website field on profile"],
["Matthew Carroll","http://keystonemediation.com/","Keystone Mediation","Dyer, Indiana",p("Matthew-Carroll","40512"),"Website field on profile"],
["William Stempel","http://wdstempel.com/","William D. Stempel","Hamden, Connecticut",p("William-Stempel","29266"),"Website field on profile"],
["Clare Fowler","https://www.clarefowler.com/","Clare Fowler / Mediate.com","Eugene, Oregon",p("Clare-Fowler","28244"),"Website field on profile"],
["Nicholas Jack Marino (Nick)","http://linktr.ee/nicholasjackmarino","Attorney / Mediator / Arbitrator","New York, New York",p("Nicholas-Jack-Marino-(Nick)","29233"),"Profile lists a Linktree URL, not a firm website"],
["Jim Melamed","","Mediate.com / ODR.com","Sunriver, Oregon",p("Jim-Melamed","26316"),"No website listed on profile"],
["Erik Feig","https://feigmediationgroup.com/","Feig Mediation Group","Bethesda, Maryland",p("Erik-Feig","29952"),"Website field on profile"],
["Cara Gruszecki Smalley","","","Nashville, Tennessee",p("Cara-Gruszecki-Smalley","30796"),"No website listed on profile"],
["Tricia Schafer","http://triciaschafer.com/","Tricia Schafer Dispute Resolution PLLC","Scottsdale, Arizona",p("Tricia-Schafer","40520"),"Website field on profile"],
["Gary L. Cole","https://www.garylcolelaw.com/","Gary L. Cole, AIA, Esq.","Chicago, Illinois",p("Gary-L.-Cole-","29647"),"Website field on profile"],
["John Siffert","https://www.lswlaw.com/lawyers/john-siffert/","Lankler Siffert & Wohl LLP","New York, New York",p("John-Siffert","40195"),"Firm attorney page as listed on profile"],
["BARRY ROSS, Esq., MBA","http://www.rossmediation.com/","Ross Mediation","Pasadena, California",p("BARRY-ROSS,-Esq.,-MBA","29133"),"Same person as the Dallas Barry Ross row (duplicate source listing)"],
["Stanley Zamor","http://www.effectivemediationconsultants.com/","Effective Mediation Consultants","Pembroke Pines, Florida",p("Stanley-Zamor","29105"),"Website field on profile"],
["Brian B. Egan","http://www.mediationclarity.com/","Clarity Mediation","Corvallis, Oregon",p("Brian-B.-Egan","29276"),"Website field on profile"],
["Peter Vogel","http://www.vogelitlaw.com/","Vogel IT Law / Peter S. Vogel, PC","Dallas, Texas",p("Peter-Vogel","40206"),"Live firm site verified; contact field from indexed profile"],
["Lisa Renee Pomerantz","http://www.lisapom.com/","Law & Dispute Resolution Practice of Lisa Renee Pomerantz","Bohemia, New York",p("Lisa-Renee-Pomerantz","29312"),"Website field on profile"],
["Roy Wepner","http://kbsiplaw.com/","KBS IP Law","New Brunswick, New Jersey",p("Roy-Wepner","40743"),"Website field on profile"],
["Todd A. Higgins, Higgins ADR LLC","https://www.higginsadr.com/","Higgins ADR LLC","New York, New York",p("Todd-A.-Higgins,--Higgins-ADR-LLC","40120"),"Website field on profile"],
["Tim Dowling","http://resolvium.com/","Resolvium Mediation Group","Schaumburg, Illinois",p("Tim-Dowling","40704"),"Website field on profile"],
["Tamara Weinmann","http://theneutralparty.com/","The Neutral Party Mediation Service","Bellevue, Washington",p("Tamara-Weinmann","40550"),"Website field on profile"],
["Darin Klemchuk","https://www.ip-mediations.com/","Klemchuk Mediation / Klemchuk PLLC","Dallas, Texas",p("Darin-Klemchuk"),"IP-only mediator; found via indexed IP profile"],
["F. Peter Phillips","http://www.businessconflictmanagement.com/","Business Conflict Management LLC","Montclair, New Jersey",p("F.-Peter-Phillips"),"Found via indexed IP profile"],
["Amy Gordon","http://www.themediationgroup.org/","The Mediation Group (TMG)","Boston, Massachusetts",p("Amy-Gordon"),"Found via indexed IP profile"],
["Corey Pollard","https://cpollardlaw.com/","Corey Pollard Law","Richmond, Virginia",p("Corey-Pollard"),"Found via indexed IP profile"],
["Dustin Hecker","http://heckeradr.com/","Hecker ADR","Boston, Massachusetts",p("Dustin-Hecker"),"Found via indexed IP profile"],
["Brandon Diamond","http://diamondmediations.com/","Salmon and Dulberg Dispute Resolution","Hollywood, Florida",p("Dr.-Brandon-Diamond"),"Found via indexed IP profile"],
["Ken Strongman","http://www.kpstrongman.com/","Ken Strongman Mediation","Walnut Creek, California",p("Ken-Strongman"),"Found via indexed IP profile"],
["Jeff Trueman, Esq., LL.M","http://www.jefftrueman.com/","Jeff Trueman Mediation","Baltimore, Maryland",p("Jeff-Trueman,-Esq.,-LL.M"),"Found via indexed IP profile"],
["Philip Argy","http://www.argystar.com/","ArgyStar","Sydney, NSW, Australia",p("Philip-Argy"),"Found via indexed IP profile"],
["Richard Samson","","Media / IP mediator (former NY Times Co.)","New York, New York",p("Richard-Samson"),"Profile contact field not retrievable"],
["Robert Berliner","","","","https://www.mediate.com/mediator-profile/?uid=29282","Profile contact field not retrievable"],
]
HEAD = ["Firm / Mediator Name","Website URL","Firm / Practice","Location","Mediate.com Profile","Source / Notes"]
out = os.path.join(os.path.dirname(__file__), "..", "mediate_ip_firms.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(HEAD); w.writerows(R)
print("rows", len(R), "with_url", sum(1 for r in R if r[1]), "blank", sum(1 for r in R if not r[1]))
print("unique profiles", len(set(r[4] for r in R)))
with open(os.path.join(os.path.dirname(__file__), "sheet_values.json"), "w", encoding="utf-8") as f:
    json.dump([HEAD]+R, f, ensure_ascii=False)
