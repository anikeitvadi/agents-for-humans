# Good Neighbor Agents: nonprofit / community lane research

Hackathon: AWS "Agents for Humans" (Strands Agents SDK). Track: Good Neighbor Agents.
Date: 2026-09-08. Method: ~200 web searches + direct fetches + live API checks (curl).

Caveat on sources: site-restricted Reddit searches returned nothing and reddit.com is not fetchable from this environment, so "primary voice" evidence below comes from practitioner case studies, sector surveys (Instrumentl, Meals on Wheels America, Feeding America affiliates), advocacy/legal filings, trade press, and vendor blogs that quote coordinators. Vendor sources are marked (vendor).

---

## Candidate long list (12)

| # | Workflow | Who | Existing tools | Gap | Verdict |
|---|---|---|---|---|---|
| 1 | Pantry donation intake: per-item recall check, date-label triage, weight and $ valuation, donor receipt | Volunteer-run pantries (56% MO, 75%+ ME have no paid staff) | MealConnect (retail-to-food-bank only), Link2Feed / Oasis Insight (client intake), PantrySoft (inventory) | Nothing does item-level recall + date + valuation at the sorting table | TOP 6 (#1) |
| 2 | Eviction-docket watch + same-day tenant outreach | Legal aid, tenant unions, RTC programs | LSC Civil Court Data Initiative (analytics), Eviction Lab (research), one-off scrapers (Memphis, SC NAACP) | No off-the-shelf agent that reads today's filings, geocodes, checks RTC eligibility, and sends outreach | TOP 6 (#2) |
| 3 | Meals on Wheels driver-cancellation rebalancing + backfill | Local MoW coordinators (628 surveyed; 53% short on volunteers) | Upper, Routific, ServTracker (route optimization, paid) | The 8:30am "driver cancelled" scramble is still phone calls; no agent re-cuts routes AND calls floaters AND texts clients | TOP 6 (#3) |
| 4 | AFG grant narrative builder for volunteer fire departments | Volunteer FDs (85% of fire service), no grant writer | FEMA narrative guide, paid consultants (FireGrantsHelp/Lexipol, First Responder Grants), generic grant AI (Grantable) | No tool pulls the department's own numbers + comparable awards (OpenFEMA) + census into the 6 narratives | TOP 6 (#4) |
| 5 | Tenant-union building dossier outside NYC | Tenant organizers, tenant unions | JustFix Who Owns What (NYC only), Injustice Watch guide (Chicago, manual), Minneapolis dashboard | Every other city: assessor + SOS + violations + evictions by hand | TOP 6 (#5) |
| 6 | Neighborhood-association agenda watch + public-comment drafting | Neighborhood assns, tenant unions, PTAs | Legistar Agenda Radar (Apify), civic-digest startup (GeekWire 2026), BetaNYC Council MCP, Civic Sunlight | Alerts exist; the end-to-end (summarize, draft comment in the group's voice, collect sign-ons, submit before deadline) does not | TOP 6 (#6) |
| 7 | Youth-sports adult compliance chaser (SafeSport, background check, concussion) | League volunteer admins | Ankored (vendor, does exactly this), SportsEngine background checks | Uniqueness low | Alternate |
| 8 | Volunteer no-show backfill dialer | Volunteer coordinators (30% no-show rate) | VolunteerHub, Rosterfy, Track It Forward (reminders, floaters lists) | Live "call the floater list and confirm" is unbuilt but thin novelty | Alternate |
| 9 | Church benevolence request screening (shut-off notices, rent) | Deacon boards | CharityTracker ($20/user, 2,500 communities; dedupe across churches) | Screening judgment + routing to LIHEAP/211 first is manual | Alternate |
| 10 | Small-town FOIA intake and deadline triage | Town clerks (Milan MI, pop 6k: 50-60 requests/yr; Ann Arbor clerk: half her day) | GovQA, NextRequest, JustFOIA, ClerkBase (priced for cities) | Small towns run it on email; PII/exemption judgment is the hard part | Alternate |
| 11 | School chronic-absenteeism family outreach | Attendance clerks | SchoolStatus Attend (vendor) and SIS add-ons | Crowded, data locked in SIS | Drop |
| 12 | Grant reporting / multi-state charity registration | Grant staff (29.5 hrs/wk manual work) | Instrumentl, GrantStation, Harbor Compliance, Labyrinth | Crowded | Drop |

Deprioritized despite fitting the lane: refugee-resettlement 90-day R&P compliance (FY2026 cap 7,500, ~20 affiliates ordered closed, services frozen, so "who does it" is shrinking: https://www.globalrefuge.org/news/refugee-cap-finalized-at-record-low-7500-for-fy-2026/ , https://wisconsinwatch.org/2026/01/wisconsin-refugee-resettlement-admission-agencies-trump-new-arrivals/). Interpreter coordination: evidence too thin to score.

---

## TOP 6, ranked

### 1. Pantry Sorting-Table Agent: recall check, date-label triage, weight/value log, donor receipt

**Workflow today (concrete steps)**
1. Food drive or retail-rescue load arrives in banana boxes and gaylords.
2. Volunteers sort into categories; for every item: read the date code, decide whether "best by" vs "use by" means keep or toss, look for rust/dents/open packaging.
3. Check the item against the food bank's recall notice (emailed list) or the FDA/USDA site; on a big recall re-sort everything already shelved.
4. Weigh by category, write pounds on a clipboard, key into the food bank's monthly report later.
5. For business/farm donors, someone estimates fair market value and writes a thank-you/receipt for the donor's taxes and the pantry's 990.

**Who / how often / time**
- Feeding America: 200 food banks, ~60,000 community pantries (https://www.food-safety.com/articles/8136-recalls-and-the-true-last-mile).
- 56% of Missouri pantries have no paid staff (Feeding Missouri, FAHH 2021: https://foodsecurity.missouri.edu/wp-content/uploads/2022/05/FAHH-2021-Key-Findings-Feeding-Missouri.pdf); "more than 75%" of ~600 Maine hunger-relief agencies "rely completely on volunteers, with no paid staff", volunteers profiled are 67 to 89 years old (Maine Monitor / NPR, Sept 2025: https://themainemonitor.org/food-pantries-volunteer-shortage/).
- Recalls: volunteers "must inspect and sort through potentially hundreds of gaylord bins, banana boxes, and pallets"; snowballing recalls mean "all of the products must continually be resorted"; volunteer-run partners "may not distribute information to clients" (Food Safety Magazine).
- Date labels: "product dating or date marking on donated food products can be very confusing to volunteers and staff of food pantries" (MSU Extension: https://www.canr.msu.edu/news/date-marking-what-does-it-mean-for-a-food-pantry).
- Sorting is the volunteer job: FBD volunteers "sort food into different food categories, check expiration dates, discard damaged product... and check recalled items" (https://www.fbd.org/get-involved/volunteer/volunteer-opportunities/); South Michigan FB: volunteers pack 85% of food distributed (https://smfoodbank.org/news/food-donations/).
- No clean hours/week figure exists for sorting specifically; the proxies are the volunteer-only staffing rates above and the recall re-sort burden.

**Why still manual**
Item-level work at the table, done by rotating elderly volunteers; the recall signal arrives by email from the food bank; date rules are judgment (quality vs safety); pantry software (Link2Feed, Oasis) is built for client intake, not the receiving dock.

**Public data / APIs (verified live 2026-09-08)**
- openFDA food enforcement: `https://api.fda.gov/food/enforcement.json?search=product_description:"peanut butter"+AND+status:"Ongoing"` returned 8 ongoing recalls with fields recalling_firm, product_description (includes UPCs), reason_for_recall, classification, code_info, recall_initiation_date. Weekly refresh. Docs: https://open.fda.gov/apis/food/enforcement/
- USDA FSIS recall API (meat/poultry/egg): documented at https://www.fsis.usda.gov/science-data/developer-resources/recall-api ; endpoint `https://www.fsis.usda.gov/fsis/api/recall/v/1`. Note: Akamai blocked both the API and the RSS from this environment; test from AWS before relying on it.
- USDA FoodKeeper JSON (400+ items, pantry/fridge/freezer storage windows, updated 2025-01-22): http://www.fsis.usda.gov/shared/data/EN/foodkeeper.json (catalog: https://catalog.data.gov/dataset/fsis-foodkeeper-data)
- Open Food Facts barcode lookup: `https://world.openfoodfacts.org/api/v2/product/0016000275287?fields=product_name,brands,quantity` returned Cheerios 18 oz. Free, no key.
- Valuation: Feeding America FY2025 audited statements value donated product at "$1.90 and $1.97 for fiscal years 2025 and 2024" per pound, from a 31-category wholesale study (Note 6: https://www.feedingamerica.org/sites/default/files/2025-11/Feeding%20America_25%20FS_Final.pdf). USDA FNS publishes per-commodity "Value of Donated Foods" annually (https://www.fns.usda.gov/usda-foods/fr-070924).
- FSIS date-labeling guidance: https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/food-product-dating
- Model input: phone photo of the item or box (multimodal), or a barcode scan.

**Existing tools and the gap**
MealConnect (https://www.feedingamerica.org/hunger-blog/what-mealconnect-learn-about-feeding-americas-food-rescue-platform) matches retail donations to food banks; it does not touch the pantry sorting table. Link2Feed / Oasis Insight are client-visit systems (one reviewer calls Oasis "extremely labor intensive": https://www.capterra.com/p/165737/Oasis-Insight/). Feeding America recall notices go by email to two staff per food bank, then on to pantries (https://feedingamericawi.org/get-involved/pantry_partners/recalls/). Nothing checks an item against openFDA at intake, explains the date label, weighs/values, and writes the donor receipt.

**The moment (5-minute demo)**
Volunteer photographs a mixed box. Agent names each item (vision + Open Food Facts), flags one against a live openFDA Class II recall by UPC with the reason, explains that the "best by" cereal is fine per FoodKeeper but the past-date infant formula must go, totals the pounds and $ at $1.90/lb, posts the line to the pantry's monthly food-bank report, and emails the donor a receipt. Judges see a real federal recall hit on a real product.

**Scores** uniqueness 5 · demoability 5 · data availability 5 · impact 4 · end-to-end fit 4 (total 23)

**Evidence** Food Safety Magazine recall last-mile: https://www.food-safety.com/articles/8136-recalls-and-the-true-last-mile · Maine pantries 75%+ volunteer-only: https://themainemonitor.org/food-pantries-volunteer-shortage/ · MSU date-marking confusion: https://www.canr.msu.edu/news/date-marking-what-does-it-mean-for-a-food-pantry · Feeding America FY25 $1.90/lb: https://www.feedingamerica.org/sites/default/files/2025-11/Feeding%20America_25%20FS_Final.pdf

---

### 2. Eviction Docket Watch: read today's filings, find the tenant, send rights + court date + legal-aid intake

**Workflow today**
1. Staff or volunteer opens the county court's public index each morning and pages through new landlord-tenant filings.
2. Copies tenant name, address, case number, hearing date into a spreadsheet.
3. Checks whether the address is in a right-to-counsel zip / income-eligible area.
4. Mail-merges postcards, sends texts/emails with court date, rights handbook, rental-assistance application link.
5. Logs who responded; attorneys pick up intakes.

**Who / how often / time**
- Memphis/Shelby County (US Digital Response): team scraped court records and now sends 500-700 postcards/week, ~300 texts/week, 100-200 emails/day with court dates and ERA status; before that, outreach was limited and legal staff were doing "manual communications and spreadsheet management" (https://www.usdigitalresponse.org/resources/helping-tenants-avoid-evictions-through-improved-communications).
- South Carolina NAACP Housing Navigator Program: "manually searching through thousands of cases filed daily would make it impossible to help tenants within the 10-day window they have to request an eviction hearing"; SC courts banned scraping; settlement Sept 13, 2023 gives NAACP "timely access to all new eviction filings" (https://www.aclusc.org/press-releases/aclu-and-naacp-secure-access-public-eviction-records-data-scraping-case/ ; background: https://www.courthousenews.com/south-carolina-must-face-naacp-suit-over-ban-on-court-data-scraping/).
- Scale: LSC has collected 30M+ civil records from ~60 public court sites in 30 states since 2016 (https://www.lsc.gov/initiatives/civil-court-data-initiative). "It is not unusual for people to be evicted within weeks of the case being filed" (NCCRC: https://civilrighttocounsel.org/resources/organizing_around_right_to_counsel/).

**Why still manual**
Every county's docket site is different; scraping is legally contested (SC); outreach needs judgment (eligibility, language, which program, tone); the people doing it are legal-aid paralegals and volunteers, not engineers.

**Public data / APIs**
- Maryland statewide eviction case data (Socrata): `https://opendata.maryland.gov/resource/mvqb-b4hf.json?$limit=1&$order=eventdate DESC` returned a July 31 2026 "Failure to Pay Rent" warrant-of-restitution event with county, tenant city/ZIP, case number. Verified live. Limitation: ZIP-level, no street address, so it drives geographic targeting, not individual mail. Dataset: https://opendata.maryland.gov/Housing/District-Court-of-Maryland-Eviction-Case-Data/mvqb-b4hf
- Address-level filings: county public indexes (SC Public Index post-settlement, Shelby County General Sessions), NYC OCA via Housing Data Coalition; LSC CCDI Eviction Tracker for 1,250 counties (https://civilcourtdata.lsc.gov/ ; API not public, data-sharing with legal aid).
- Eligibility rules: NCCRC right-to-counsel jurisdiction list; LSC Eviction Laws Database (https://www.lsc.gov/initiatives/effect-state-local-laws-evictions/lsc-eviction-laws-database).
- Geocoding: US Census Geocoder (free). Messaging: Amazon SNS / Pinpoint, Lob for postcards.
- Also: Eviction Lab methods (https://evictionlab.org/methods/).

**Existing tools and the gap**
LSC CCDI and Eviction Lab are analytics, not outreach. Memphis and SC built one-off scripts. No packaged agent reads a docket page (HTML that changes), extracts cases, screens eligibility, drafts multilingual outreach, and hands intakes to attorneys with a log.

**The moment**
Paste a county docket URL (or point at Maryland's open data). Agent pulls this morning's filings, maps them, flags the ones inside the right-to-counsel ZIPs, drafts the text message in English and Spanish with the hearing date and the 10-day deadline, and sends one to a judge's phone live. Then shows the intake queue it created for the attorney.

**Scores** uniqueness 4 · demoability 4 · data availability 3 · impact 5 · end-to-end fit 4 (total 20)

**Evidence** USDR Memphis: https://www.usdigitalresponse.org/resources/helping-tenants-avoid-evictions-through-improved-communications · ACLU-SC settlement: https://www.aclusc.org/press-releases/aclu-and-naacp-secure-access-public-eviction-records-data-scraping-case/ · LSC CCDI: https://www.lsc.gov/initiatives/civil-court-data-initiative · Maryland dataset: https://opendata.maryland.gov/Housing/District-Court-of-Maryland-Eviction-Case-Data/mvqb-b4hf

---

### 3. Meals on Wheels "Driver Cancelled" Agent: re-cut routes, call floaters, text clients

**Workflow today**
1. 8:30am: a volunteer driver calls in sick. Coordinator pulls the paper route sheet (photocopied addresses, pencil notes).
2. Splits the 25 stops across drivers already out, or phones the backup list one by one.
3. Calls clients who will get a late meal; updates the sheet by hand.
4. Weekly: rebalances routes as clients join/leave; monthly: reports deliveries to the AAA/state grant.

**Who / how often / time**
- Meals on Wheels of Chester County (800+ seniors, 30 rotating drivers): paper route sheets unchanged 3 years, 200+ address changes never incorporated, routes 18 to 35 stops, weekly planning 4 hours, "sick-day absences required over one hour of phone calls to manually rearrange stops", 15% of meals late; after routing software: 30 minutes/week, sick-day fixes "within minutes" (vendor case study: https://www.upperinc.com/success-stories/meals-on-wheels-of-chester-county/).
- MOWA 2025 benchmarking (628 providers): 53% cite volunteer recruiting/retention as a major challenge; 33% have a waitlist, ~36,000 seniors, 115-day average wait (https://www.mealsonwheelsamerica.org/research/state-of-the-meals-on-wheels-network-2025-provider-benchmarking-report/).
- Cancellation policy language shows the pain: "cancellations received after 8:30am on your day to drive are very difficult to cover" (MoW Central Texas handbook: https://www.mealsonwheelscentraltexas.org/uploads/files/general/Volunteer_Handbook.pdf).

**Why still manual**
Routing software costs money and still needs a human to phone floaters and clients; small programs are one coordinator with a landline; routes carry tacit notes ("dog, knock loud, leave in cooler").

**Public data / APIs**
- Routing: Amazon Location Service route calculator or OSRM (self-host, free); Google Maps Distance Matrix.
- Weather: NWS `https://api.weather.gov/points/{lat},{lon}` for heat/ice advisories that change delivery order.
- Voice/SMS: Amazon Connect + Pinpoint, or Twilio, to call the floater list and text clients.
- Client and volunteer roster: the program's own sheet (CSV import). Address validation: USPS API or Census Geocoder.

**Existing tools and the gap**
Upper, Routific, ServTracker (Accessible Solutions), Mobile Meals: optimize routes; none run the human loop of calling backups until one says yes, re-cutting, notifying clients, and logging for the grant report.

**The moment**
Click "Driver Bob cancelled". Agent re-cuts Bob's 25 stops across the four active routes (map animates), phones the first two floaters (live call audio), Bob's route goes to the one who accepts, texts the six clients whose meal will be late, and writes the timestamped log line the state grant requires.

**Scores** uniqueness 3 · demoability 5 · data availability 4 · impact 4 · end-to-end fit 5 (total 21)

**Evidence** Upper/Chester County: https://www.upperinc.com/success-stories/meals-on-wheels-of-chester-county/ · MOWA 2025 report: https://www.mealsonwheelsamerica.org/research/state-of-the-meals-on-wheels-network-2025-provider-benchmarking-report/ · MoW volunteerism decline: https://www.mealsonwheelsamerica.org/stories/the-state-of-volunteerism-in-america/

---

### 4. AFG Narrative Builder for Volunteer Fire Departments

**Workflow today**
1. Chief (unpaid) reads the AFG NOFO and FEMA's narrative guide.
2. Digs out call volume (NFIRS/NERIS), apparatus ages, budget, tax base, population, square miles, mutual-aid area.
3. Writes six narratives (Critical Infrastructure, Financial Need, Organization/Community, Project Description, Cost/Benefit, Statement of Effect), each capped at 4,000 characters; four are peer-reviewed at 25% each (FEMA guide, May 2026).
4. Gets three vendor quotes (no brand names allowed in narrative), builds the budget, pastes into FEMA GO before the June deadline.

**Who / how often / time**
- "Volunteer departments often do not have a designated grant-writer and some find the task of putting together a federal grant application daunting"; volunteers are ~85% of the fire service (FASNY: https://fasny.com/news/helping-serve-developing-assistance-firefighters-grant-application/).
- Demand: "$3.9 billion in FY 24 AFG grant applications. That is over 13x more in requests than the $290 million available" (NVFC one-pager: https://www.nvfc.org/wp-content/uploads/2025/02/AFG-appropriations-one-pager-2025.pdf). FY2025 window was May 19 to June 22 (https://fireandsafetyjournalamericas.com/fire-department-grant-application-periods-open-for-2025/).
- Sector-wide: grant staff spend 29.5 hrs/week on manual tasks; 61% of orgs rely on one or two people (Instrumentl, n=1,031, March 2026: https://www.instrumentl.com/blog/beyond-shadow-work-1000-grant-professionals-on-the-work-that-matters-most-and-the-systems-holding-them-back).

**Why still manual**
The narrative is judgment: local facts, no national stats allowed ("Include only local information, not national statistics"), story not template ("Avoid templated or copied narratives"). Data lives in the department's incident system, the town budget, and the chief's head.

**Public data / APIs (verified live)**
- OpenFEMA AFG awards: `https://www.fema.gov/api/open/v1/NonDisasterAssistanceFirefighterGrants?$filter=vendorState eq 'NY'&$top=2` returned e.g. "VERNON CENTER VOLUNTEER FIRE DEPARTMENT, 2005, $46,828". 77,925 records, fields vendorName, vendorState, programName, fiscalYear, awardAmount (https://www.fema.gov/openfema-data-page/non-disaster-and-assistance-firefighter-grants-v1). Lets the agent show "departments like you in your state won X for Y".
- NERIS Public: national incident dataset, rolling 15 months, refreshed multiple times a week (https://neris.fsri.org/); the department also exports its own NERIS/NFIRS incidents.
- Census ACS API (population, median income, poverty), USDA rural-urban codes, NWS climate normals, state DOT bridge inventory for "critical infrastructure".
- FEMA narrative guide (structure, character limits, scoring): https://www.fema.gov/sites/default/files/documents/fema_rsl_gpd_fy25-afg-narrative-development-guide_05182026.pdf

**Existing tools and the gap**
Paid consultants (FireGrantsHelp/Lexipol, First Responder Grants, Allegiance) and generic grant AIs (Grantable, Instrumentl). None ingest the department's incident export, pull census and comparable-award data, and produce six compliant narratives with a character counter and a "national stat detected" linter.

**The moment**
Chief uploads a NERIS/NFIRS CSV and types the town name. Agent pulls ACS numbers, lists the last five AFG awards to comparable volunteer departments in the state from OpenFEMA, and drafts the Financial Need narrative at 3,950/4,000 characters with the department's real call growth, then flags a sentence that cites a national statistic (disallowed) and rewrites it locally.

**Scores** uniqueness 4 · demoability 4 · data availability 4 · impact 4 · end-to-end fit 4 (total 20)

**Evidence** FEMA narrative guide (May 2026): https://www.fema.gov/sites/default/files/documents/fema_rsl_gpd_fy25-afg-narrative-development-guide_05182026.pdf · NVFC 13x oversubscription: https://www.nvfc.org/wp-content/uploads/2025/02/AFG-appropriations-one-pager-2025.pdf · FASNY no grant writer: https://fasny.com/news/helping-serve-developing-assistance-firefighters-grant-application/ · OpenFEMA dataset: https://www.fema.gov/openfema-data-page/non-disaster-and-assistance-firefighter-grants-v1

---

### 5. Tenant-Union Building Dossier (any city, not just NYC)

**Workflow today (Chicago example, Injustice Watch guide)**
1. City data portal: search address, find Property Group number, filter all building violations since 2006.
2. County assessor: sales history, current owner (usually an LLC).
3. Secretary of State business search: open the LLC, read the Managers tab to find humans.
4. Repeat for each LLC to find sibling buildings; check eviction filings; write the flyer/letter and the demand list.

**Who / how often / time**
- Organizers and tenants; "public records databases like property records and business entity registries... are difficult to navigate... each jurisdiction hosting their own uniquely formatted websites"; "There is no centralized national database" (PESP research guide, May 2026: https://pestakeholder.org/wp-content/uploads/2026/06/PESP_Landlord_ResearchGuide_2026.pdf).
- "Although these records are publicly available, they can be challenging to navigate" (UCLA IRLE workshop, led by an 8.5-year tenant outreach organizer: https://irle.ucla.edu/2025/04/12/property).
- Organizer burnout is documented ("worked to the point of burnout": Convergence, https://convergencemag.com/articles/one-building-at-a-time-wont-do-tenant-organizing-in-a-red-state/). No hours/week number found.

**Why still manual**
Three to five heterogeneous government websites per building, LLC layering, and the output is a persuasive document (flyer, letter to the landlord, testimony), which is judgment work.

**Public data / APIs**
- Chicago Building Violations (Socrata, https://data.cityofchicago.org/Buildings/Building-Violations/22u3-xenr), Cook County Assessor, Illinois SOS business search (https://apps.ilsos.gov/businessentitysearch/). Equivalent open data in most large cities (LA, SF, Minneapolis landlord dashboard, NYC HPD/DOB/ACRIS).
- OpenCorporates API for LLC officers across states. Eviction filings: LSC CCDI, state open data (Maryland verified above).
- Rent-stabilization / subsidy status: HUD Multifamily and LIHTC property datasets (public), NYC RentHistory.org.

**Existing tools and the gap**
JustFix "Who Owns What" is excellent but NYC-only (160,000 properties, GPLv3, no public API: https://github.com/JustFixNYC/who-owns-what). Injustice Watch's guide is manual (https://www.injusticewatch.org/civil-courts/housing/2025/chicago-landlord-code-violations-search/). Nothing generalizes across cities or writes the organizing artifacts.

**The moment**
Tenant photographs a rent-increase letter. Agent reads the address, pulls open violations, the LLC, the human behind it via SOS/OpenCorporates, the other five buildings they own, recent eviction filings, and produces a one-page bilingual flyer ("Your landlord has 31 open violations and owns 6 buildings; meeting Thursday") plus a demand letter.

**Scores** uniqueness 3 · demoability 4 · data availability 3 · impact 4 · end-to-end fit 3 (total 17)

**Evidence** Injustice Watch guide: https://www.injusticewatch.org/civil-courts/housing/2025/chicago-landlord-code-violations-search/ · JustFix WOW (NYC-only): https://github.com/JustFixNYC/who-owns-what · PESP research guide 2026: https://pestakeholder.org/wp-content/uploads/2026/06/PESP_Landlord_ResearchGuide_2026.pdf · Shelterforce on hidden owners: https://shelterforce.org/2022/03/24/how-hidden-property-owners-and-bad-landlord-patterns-are-revealed-in-nyc/

---

### 6. Neighborhood-Association Agenda Watch + Public-Comment Pipeline

**Workflow today**
1. A board member checks the city's Legistar/Granicus page weekly for items touching the neighborhood (zoning, liquor licenses, road projects).
2. Reads the 200-page packet, summarizes in an email to members.
3. Drafts the association's comment, circulates for approval, collects sign-ons, submits by the comment deadline or shows up to speak.

**Who / how often / time**
- Associations "monitor city council agendas, planning board meetings, zoning notices..." and "organize public comments" (https://pulsegulfcoast.com/how-neighborhood-associations-are-shaping-city-council-decisions/). No hours number found; the work is weekly and volunteer.

**Why still manual**
Packets are PDFs; relevance is geographic and topical judgment; the comment must carry the group's voice and be filed on the clerk's schedule.

**Public data / APIs (verified live)**
- Legistar Web API, anonymous: `https://webapi.legistar.com/v1/seattle/events?$top=1&$orderby=EventDate desc` returned a Sept 15 2026 committee meeting with agenda status. Covers Legistar cities; Granicus/CivicClerk/PrimeGov need scraping.
- Parcel/zoning GIS from the city; Census geocoder for "is this item inside our boundary".
- Clerk email/portal for submission.

**Existing tools and the gap (crowded on alerts)**
Legistar Agenda Radar (Apify actor, keyword alerts, claims 80%+ US municipalities: https://apify.com/opalescent_game/legistar-agenda-radar/api); a 2026 civic-digest startup by an ex-Amazon PM (topic digests twice weekly: https://www.geekwire.com/2026/can-ai-revive-democracy-former-amazon-product-manager-builds-tool-to-spark-civic-engagement/); BetaNYC's NYC Council MCP server (https://www.beta.nyc/2026/05/21/new-nyc-digital-democracy-tools-for-ai/). All stop at "here is what's happening". The gap is the back half: boundary-aware filtering, drafting in the association's voice from its past positions, sign-on collection, and filing.

**The moment**
Agent shows Thursday's item (rezoning two blocks from the association), reads the packet, drafts a 250-word comment consistent with the association's 2024 letter (uploaded), collects three member sign-ons by SMS live, and emails it to the clerk with the item number, before the 5pm deadline it computed.

**Scores** uniqueness 2 · demoability 4 · data availability 5 · impact 3 · end-to-end fit 4 (total 18)

**Evidence** Legistar Agenda Radar: https://apify.com/opalescent_game/legistar-agenda-radar/api · GeekWire civic digest tool: https://www.geekwire.com/2026/can-ai-revive-democracy-former-amazon-product-manager-builds-tool-to-spark-civic-engagement/ · BetaNYC Council MCP: https://www.beta.nyc/2026/05/21/new-nyc-digital-democracy-tools-for-ai/

---

## Alternates (evidence collected, not top 6)

- **Youth-sports adult compliance**: workflow = collect consent, submit checks, read results, flag, store, track renewals, repeat every season; "no spreadsheet reminds a coach to finish their check" (Ankored, vendor: https://www.ankored.com/blog/youth-sports-background-check-compliance-challenges); coaches spend up to 36% of their week on admin (Vanta, vendor: https://www.vantasports.ai/blog/reduce-admin-time-youth-sports-clubs-coaches). Uniqueness 2 because Ankored is that product.
- **Volunteer no-show backfill**: "30% of volunteers do not show up on event day" and coordinators "scramble" (VolunteerHub, vendor: https://volunteerhub.com/blog/volunteer-no-shows-preparation); Track It Forward on no-show policies (https://www.trackitforward.com/content/avoiding-stress-dealing-volunteer-no-shows). Could be folded into #3 as the generic floater-dialer.
- **Church benevolence screening**: CharityTracker dedupes assistance across 2,500 communities at $20/user/month (https://www.simonsolutions.com/church, https://www.charitytracker.com/who-we-serve/churches). Unbuilt: reading a shut-off notice, checking LIHEAP/211 first, drafting the deacon summary.
- **Small-town FOIA**: Milan, MI (pop ~6,000) clerk handles 50-60 requests/yr; an Ann Arbor clerk went from a few hours a day to half her day on FOIA (Michigan Advance, Feb 2026: https://michiganadvance.com/2026/02/21/process-of-foia-the-unseen-work-of-providing-government-transparency/). Tools priced for cities (GovQA, NextRequest, JustFOIA, ClerkBase).
- **Grant work generally**: 29.5 hrs/week manual, 5+ tools per grant, 87% walked away from a grant because of process weight (Instrumentl 2026). Crowded; only the fire-specific slice (#4) is open.
- **Multi-state charity registration**: renewal clocks per state, May 15 collides with 990 (Affinity: https://www.fundraisingregistration.com/resources/topic/charitable-registration-deadlines/). Harbor Compliance / Labyrinth own it.

## Score table

| Rank | Candidate | Uniq | Demo | Data | Impact | E2E | Total |
|---|---|---|---|---|---|---|---|
| 1 | Pantry sorting-table agent | 5 | 5 | 5 | 4 | 4 | 23 |
| 2 | Eviction docket watch + outreach | 4 | 4 | 3 | 5 | 4 | 20 |
| 3 | MoW driver-cancelled agent | 3 | 5 | 4 | 4 | 5 | 21 |
| 4 | AFG narrative builder | 4 | 4 | 4 | 4 | 4 | 20 |
| 5 | Tenant-union dossier | 3 | 4 | 3 | 4 | 3 | 17 |
| 6 | Agenda watch + comment pipeline | 2 | 4 | 5 | 3 | 4 | 18 |

Ranking weights uniqueness and impact over raw total, which is why #2 sits above #3.

## Data-source status (checked 2026-09-08)
- openFDA food enforcement: live, JSON, no key needed for low volume.
- Open Food Facts v2 product: live, no key.
- USDA FoodKeeper JSON: download URL published on data.gov (not re-fetched).
- FSIS recall API and RSS: 403 (Akamai) from this machine; retest from AWS or fall back to openFDA + FSIS email list.
- OpenFEMA NonDisasterAssistanceFirefighterGrants v1: live, 77,925 rows, annual refresh.
- Legistar Web API: live, anonymous, Seattle tested.
- Maryland eviction Socrata mvqb-b4hf: live, ZIP-level, "as needed" refresh (last Jan 21 2026 per metadata; rows dated July 31 2026).
- Reddit: not reachable from this environment; no Reddit evidence in this report.
