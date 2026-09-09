# SMB / Trades lane: manual, judgment-heavy workflows for an "Agents for Humans" entry

Research date: 2026-09-08. Scope: small businesses and trades in the US.

## Method and limits (read first)

- Reddit was unreachable from this environment by every route tried (WebFetch 403, curl JSON endpoint 403, Playwright hit "Prove your humanity" then a login wall on old.reddit). Bing via headless browser degraded queries to one word. The web-search budget capped at 200 calls.
- So primary evidence below comes from trade forums (Mike Holt, HVAC-Talk, Practical Machinist thread listings), industry surveys (Levelset, AGC via secondary), government process documents (CBP/CIT, DOL, CA DIR), law-firm client alerts, and vendor content. Where a number comes from a vendor blog it is marked (vendor). Where I could only see a thread title, I say so and do not invent its content.
- 14 candidates were screened; 6 ranked. Scores are 1 to 5 on uniqueness (U), 5-minute demoability (D), data availability (Da), impact (I), end-to-end fit (E).

## Ranking at a glance

| # | Workflow | Who | Time burden | U | D | Da | I | E | Total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | IEEPA tariff-refund recovery (CAPE / protest / CIT) | ~330,000 importers of record, incl. small DTC brands and Etsy/Shopify sellers | multi-week one-off campaign; "time and cost of prerequisites can exceed the refund value" for small IORs | 4 | 4 | 4 | 5 | 4 | 21 |
| 2 | CAM reconciliation audit for single-location commercial tenants | restaurants, salons, shops, small clinics on NNN leases | annual; 60 to 180 day audit window or rights forfeited; often not done at all | 4 | 5 | 4 | 4 | 4 | 21 |
| 3 | Electrification rebate and incentive paperwork (utility + HEAR/HOMES) | HVAC, electrical, plumbing shops; per install | 20 to 45 min per utility claim, 60 to 90 min per income-qualified federal claim, ~25 min per resubmission (vendor) | 3 | 5 | 4 | 4 | 4 | 20 |
| 4 | Certified payroll (WH-347 / state eCPR) for small subs on public works | any sub on Davis-Bacon or state prevailing-wage jobs; weekly per project | 1 to 2 hrs per project per week; 15 to 25 hrs/week at 5 projects (vendor) | 2 | 4 | 4 | 4 | 4 | 18 |
| 5 | Sub-side prequalification questionnaires (ISNetworld / Avetta / Veriforce) | subs who want to work for owners/GCs that mandate a platform | 40 to 80 hrs initial, 5 to 10 hrs/month upkeep, 30 to 45 days to approval (consultant) | 4 | 3 | 3 | 4 | 3 | 17 |
| 6 | OEM warranty claim filing (HVAC / water heaters) | HVAC and plumbing contractors; per warranty call | per claim; $50 to $75 processing fee per claim, 30 to 60 day filing windows | 3 | 4 | 3 | 3 | 4 | 17 |

Screened and cut (with why): see section "Candidates 7 to 14".

---

## 1. IEEPA tariff-refund recovery for small importers

**Workflow name:** "Get my tariff money back" (CAPE declaration, PSC, protest, or CIT suit).

**Context (why this exists in 2026):** The Supreme Court held on Feb 20, 2026 (Learning Resources v. Trump) that IEEPA does not authorize tariffs. CBP built CAPE (Consolidated Administration and Processing of Entries) and opened Phase 1 on Apr 20, 2026; Phase 2 on Jun 29, 2026; Phase 3 (finally liquidated entries, litigants only) was ordered by the CIT on Jul 17, 2026, the government appealed, and the Phase 3 deployment was delayed Aug 25, 2026. About $166B was collected across ~330,000 importers and ~53M entries. As of Aug 21, 2026: $132.5B accepted into CAPE, $106.6B sent to Treasury, $1.7B (22,170 refunds) stuck on missing ACH banking details. 272,029 declarations submitted, only 191,494 passed file validation (roughly 30% failed at the file stage). A tracker site advertises "15% of CAPE claims rejected."

**Concrete steps the human does today:**
1. Figure out who the Importer of Record was on each shipment (own EIN, a customs broker under POA, or the carrier: UPS/FedEx/DHL often act as IOR/broker for small parcels). Pull CBP Form 7501 entry summaries for 2025 to 2026.
2. Identify the IEEPA duty lines (Chapter 99 subheadings) and total what was paid, per entry.
3. Update the CBP Form 5106 importer record with an email that is not the broker's; create an ACE Secure Data Portal account; enroll in ACH refund.
4. For each entry, determine liquidation status and which CAPE phase applies (Phase 1: unliquidated or liquidated within 80 days; Phase 2: reconciliation / AD-CVD; Phase 3: finally liquidated, litigants only).
5. Fix correctable errors via Post Summary Correction before filing ("H99 - Data Change-Other" acceptable). Exclude entries where a surety paid, drawback entries, open protests.
6. Build the CSV (entry numbers only, max 9,999 per declaration), upload in ACE. Declarations cannot be amended once accepted.
7. Monitor ACE reports ES-022 (CAPE entry summary), REV-603 (Trade Refund), REV-613 (ACH rejected), REV-615 (CAPE details). Refunds generally 60 to 90 days after acceptance.
8. If a broker or carrier filed, chase the pass-through: POA and service agreements can let the broker offset refunds against invoices or hold them 60 to 90 days. DHL charges its "standard Import Paperwork Fee" to file for you; UPS offers a paid filing service.
9. For finally liquidated entries: decide whether to file at the CIT (protective suit) or wait on the appeal.

**Who / how often / hours:** ~330,000 IORs. For "occasional importers, small DTC brands, or merchants whose IEEPA exposure is spread thinly across many low-value entries," the FlavorCloud guide says "the time and cost of completing those prerequisites can exceed the refund value" and DDU claims "will overwhelmingly go unclaimed." Main Street Alliance: "Small business owners should not have to jump through hoops to get back money they never should have had to pay." No survey with hours-per-importer exists yet; the 30% file-validation failure rate and $1.7B stuck on ACH are the best burden proxies.

**Why still manual:** identity of IOR is buried in broker paperwork; per-entry eligibility is a judgment call across three phases and a moving appeal; CSV must be clean and cannot be amended; brokers' pass-through terms differ; carriers are opaque about automatic pass-through.

**Public data / APIs / automation targets:**
- HTS REST API (public, no auth, JSON): `https://hts.usitc.gov/reststop/search?keyword=...` returns htsno, description, general/special/other rates. Verified live.
- CBP CSMS messages (public): #69066837 (reconciliation entries, Jun 29 2026), #69056483 (goods-value validation removed), #69127837 (warehouse entries excluded Jul 7 2026).
- ACE Secure Data Portal (login; the CAPE upload template and ES/REV reports live here; browser-automation target).
- CBP Form 7501 PDFs and broker/carrier invoices (PDF parsing; the "tariff surcharge" line items on 2024 to 2025 UPS/FedEx invoices).
- Refund tracker with pool numbers: tariffstool.com/tariff-refund-tracker.
- CIT docket via PACER for protective suits.

**Existing tools and the gap:** brokers and carriers (UPS, FedEx, DHL) file for a fee and control the money under POA; Flexport and Avalara publish guides; law firms (Holland & Knight, Skadden, Snell & Wilmer) serve large importers. Nothing self-serve turns a shoebox of 7501s and carrier invoices into a validated CAPE CSV plus a broker demand letter plus a "sue or wait" decision for a $3,000 refund.

**The moment:** Drop a folder of 7501s and UPS invoices. The agent extracts entry numbers, flags the Chapter 99 IEEPA lines, totals "$4,812 owed," sorts entries into Phase 1 / Phase 2 / needs-PSC / finally-liquidated, writes the CAPE CSV, drafts the certified-mail pass-through demand to the broker citing their POA clause, and prints "entry 3 liquidates finally in 11 days: file or lose it."

**Scores:** U 4, D 4, Da 4, I 5, E 4.

**Evidence:**
- https://www.hklaw.com/en/insights/publications/2026/06/ieepa-tariff-refund-update-government-appeals
- https://www.ghy.com/trade-compliance/cbp-cape-ieepa-refund-progress/
- https://www.swlaw.com/publication/update-on-ieepa-tariff-refunds-cape-goes-live-with-certain-limitations-for-importers/
- https://flavorcloud.com/resources/blog/ieepa-tariff-refunds-and-cape-declarations-what-importers-need-to-know-in-2026
- https://www.tariffstool.com/tariff-refund-tracker
- https://www.business2community.com/small-business/ieepa-tariff-refunds-small-business-shippers/
- https://www.ecommercebytes.com/2026/04/20/consumers-and-small-sellers-may-get-tariff-refunds-from-shipping-carriers/
- https://www.amundsendavislaw.com/alert-ieepa-tariff-refunds-cape-phase-iii

---

## 2. CAM reconciliation audit for single-location commercial tenants

**Workflow name:** "Is my landlord's year-end CAM bill right?"

**Concrete steps today:**
1. Landlord delivers the year-end reconciliation statement (leases typically require it 90 to 120 days after year-end) showing actual operating expenses, tax, insurance, the tenant's pro-rata share, and a true-up bill.
2. Tenant must exercise audit rights within the lease window (60 to 90 days in NYC-style leases; 90 to 180 days in tenant-favorable leases) or the right is forfeited.
3. Read the lease: CAM definition, exclusions (capital items, leasing commissions, landlord overhead), admin fee cap, controllable-expense cap, gross-up clause, pro-rata denominator (leased vs leasable), tax pass-through method.
4. Line-by-line compare the statement to the lease; request invoices, GL detail, payroll records, tax bills by certified letter.
5. Recompute the share; dispute in writing; choose pay-under-protest or withhold (withholding risks default; in NY you file a Yellowstone injunction before the 10 to 15 day cure period expires).

**Who / how often / cost:** every NNN tenant, annually. Secondary sources report overbilling in "roughly 15 to 25 percent of audited statements." Examples: Chicago restaurant at $4,200/month rent hit with an $11,400 reconciliation; Williamsburg wine bar at $9,200/month got a $47,000 year-end demand; Hell's Kitchen and LIC restaurant owners carrying $200,000 to $400,000 personal-guarantee exposure while disputing CAM. Admin markups of 10 to 15% and capex disguised as maintenance are the most common issues. Audit-cost shifting typically triggers at 3 to 5% overbilling.

**Why still manual:** two PDFs and a 60-page lease; judgment calls; hard deadline; audit firms and software (Occupier, Tango, RE BackOffice) target multi-site retailers, not a taqueria.

**Public data / inputs:** lease PDF, reconciliation PDF, landlord invoices (all local, no external API needed); county assessor/tax-bill records (public) to verify tax pass-throughs; BOMA/ASTM measurement standards; state statutes of limitation (NY CPLR 213(2), six years).

**Existing tools and gap:** Occupier, Tango Analytics, RE BackOffice CAM services (enterprise); law firms; MyLeaseIQ (content). No product for a single-location tenant that reads the lease and the statement and produces the dispute.

**The moment:** Upload lease + landlord statement. Agent returns a table: each line item, the lease clause it maps to, "allowed / excluded / over cap," the recomputed pro-rata share, "$6,340 overbilled," and a certified-mail audit demand letter with "you have 23 days left to invoke Section 7.4."

**Scores:** U 4, D 5, Da 4, I 4, E 4.

**Evidence:**
- https://myleaseiq.com/blog/cam-charges-explained-commercial-tenant-guide
- https://www.yassilaw.com/post/cam-charges-and-rent-escalation-in-nyc-commercial-leases-how-to-spot-overcharges-and-fight-back
- https://www.occupier.com/blog/cam-reconciliation
- https://lbatlaw.com/california-commercial-lease-cam-audit-overcharge/

---

## 3. Electrification rebate and incentive paperwork agent (HVAC / electrical / plumbing)

**Workflow name:** "Nameplate photo to funded rebate."

**Concrete steps today (per install):**
1. Photograph indoor and outdoor nameplates (model, serial, refrigerant); confirm refrigerant GWP is 700 or lower (federal eligibility since Jan 1, 2026).
2. Look up the AHRI certificate reference number for the matched system (missing AHRI number is a top denial reason; one cited loss: a $1,600 rebate denied for missing AHRI number and nameplate photo).
3. Build an itemized invoice separating equipment, labor, removal, and electrical.
4. Get the homeowner's wet signature on the program authorization at job completion.
5. Determine the stack: utility rebate (e.g., Duke Energy heat-pump rebates of $300 to $1,200 across six states), state HEAR/HOMES (HEEHRA up to $8,000 below 80% AMI, $4,000 at 80 to 150% AMI; Georgia stacks to $16,000), local programs. Note: the 25C federal credit expired for installs after Dec 31, 2025; HEAR programs are launching state by state through 2026; income-qualified programs require contractor registration and are not claimable after the fact.
6. Fill each program's PDF or portal form, submit within the 30 to 90 day window, check status at 21 days, escalate at 45, answer "requests for additional information," resubmit.
7. Wait 30 to 90 days for funds; at $1,600 x 10 jobs/month that is about $16,000 of working capital tied up (vendor example).

**Who / how often / hours:** residential HVAC and electrical shops, every qualifying install. Bella FSM (vendor): 20 to 45 minutes of office labor per standard utility claim, 60 to 90 minutes per income-qualified federal claim, ~25 minutes per rejection resubmission, $12 to $53 absorbed per job at a $35/hr loaded rate; called "one of the biggest uncontrolled costs in residential shops." HEAR forum users "consistently mention the paperwork as the most frustrating part... missing paperwork is the number one reason rebates get clawed back" (energyrebatecalculator.com).

**Why still manual:** every utility and state has its own form/portal and rules; AHRI matchup and income verification are judgment; refrigerant rule changed in 2026; contractor must be program-registered; rejections loop.

**Public data / APIs:**
- DSIRE API (verified): `http://programs.dsireusa.org/api/v1/getprograms/json`, `getprogramsbydate/[from]/[to]/json`, plus XML/CSV database dumps and a SPARQL endpoint.
- ENERGY STAR Product Finder API and datasets page (energystar.gov/productfinder/advanced; data.energystar.gov redirects there).
- AHRI Directory (ahridirectory.org) public certificate search (site blocked the fetch here; public per multiple contractor guides).
- Utility application PDFs (e.g., Rochester Public Utilities 2025 Electric HVAC & Water Heating Rebate Application, fillable) and state HEAR contractor portals (e.g., energyoffice.colorado.gov/home-energy-rebates-contractors).
- Nameplate OCR from tech photos.

**Existing tools and gap:** Resolv Systems (founded 2024, $1.59M raised, "automates finding, completing, and submitting energy rebate applications for contractors") is a direct competitor at pre-seed stage. RebateManager.ai automates manufacturer/GPO purchase rebates, not utility/consumer rebates. Contractor Commerce shows rebate data inside estimates. Bella FSM sells checklists. Nothing widely adopted starts from a nameplate photo, computes the stack, fills the forms, and runs the resubmission loop.

**The moment:** Tech texts two nameplate photos and the invoice. Agent replies with AHRI ref #, "GWP 466 OK," a stacked incentive table ($1,200 utility + $4,000 HEAR + $250 city), the filled utility PDF, the "submit by Oct 14" date, then (fast-forward) the 21-day status check and a ready-to-send resubmission when the utility asks for the missing serial photo.

**Scores:** U 3, D 5, Da 4, I 4, E 4.

**Evidence:**
- https://www.bellafsm.com/hvac-rebate-paperwork/
- https://energyrebatecalculator.com/guide/hear-program-guide
- https://www.acdirect.com/blog/state-hvac-rebates-2026/
- https://www.dsireusa.org/resources/data-and-tools/
- https://www.cbinsights.com/company/resolv-systems

---

## 4. Certified payroll (WH-347 / state eCPR) for small subs on public works

**Workflow name:** "Weekly certified payroll without the Sunday night."

**Concrete steps today (weekly, per project):**
1. Pull timesheets; map each worker to the wage-determination classification for that county and project type.
2. Look up the wage determination (SAM.gov for Davis-Bacon; state DIR for state prevailing wage). Rates vary by county and year.
3. Compute base + fringe, cash-in-lieu of fringe, overtime, deductions; "not close, exact."
4. Fill Form WH-347 (DOL released an online fillable form and an annotated guide on Dec 16, 2025), sign the Statement of Compliance.
5. Submit into whatever the agency requires: LCPtracker (mandatory in some jurisdictions; free to IIJA recipients via DOE), Elation, California DIR eCPR (online form or XML per CPR XML schema v1.3; records become publicly searchable), or agency-specific portals. Multi-project subs re-key into several systems.
6. Retain three years; answer agency questions.

**Who / how often / hours:** any sub on federal (Davis-Bacon, projects over $2,000) or state prevailing-wage work; weekly. BlueWave HR (vendor): 1 to 2 hours per project per week manually; 15 to 25 hours/week at five projects. Penalties: up to $2,782 per violation, liquidated damages up to 2x underpayment, debarment up to 3 years. Mike Holt forum thread "Payroll Certification" exists on this exact pain (could not read body; title only).

**Why still manual:** classification and fringe are judgment; wage determinations are county-specific web pages; portals do not talk to each other; small subs use QuickBooks and a spreadsheet.

**Public data / APIs:**
- SAM.gov wage determinations (public web; no wage-determination API is listed on open.gsa.gov, so scrape/browser-automate).
- DOL WH-347 fillable PDF and annotated guide (public).
- California DIR CPR XML schema v1.3 and eCPR upload (public spec).
- Payroll exports (Gusto, QuickBooks APIs).
- LCPtracker/Elation (login; browser automation).

**Existing tools and gap:** LCPtracker, eMars, Elation, Points North, Foundation, ADP/QuickBooks certified-payroll add-ons, Miter and Lumber (construction payroll). This is the most crowded of the six; the gap is only at the small-sub tier that will not buy a $200/month module and still hand-fills WH-347. Uniqueness is the weak score.

**The moment:** Timesheet CSV + "Fresno County, building" -> agent fetches the WD, classifies, computes fringe, outputs a signed-ready WH-347 and a DIR XML file, and flags "J. Ortiz paid $38.10, WD requires $38.50 + $21.14 fringe: underpaid $0.40/hr, $16 this week."

**Scores:** U 2, D 4, Da 4, I 4, E 4.

**Evidence:**
- https://bluewavehr.com/blog/certified-payroll-reporting-guide-2026.html
- https://www.dol.gov/agencies/whd/forms/wh347
- https://www.dir.ca.gov/Public-Works/Certified-Payroll-Reporting.html
- https://www.energy.gov/infrastructure/weekly-dba-payroll-tracking-lcptracker
- https://forums.mikeholt.com/threads/payroll-certification.83950/

---

## 5. Sub-side prequalification questionnaires (ISNetworld / Avetta / Veriforce / Compass)

**Workflow name:** "Get us green in ISNetworld."

**Concrete steps today:**
1. Owner or GC mandates a platform (28% of commercial owners mandate ISNetworld specifically, per ENR data cited secondhand). Sub pays: ISNetworld $875 to $2,000+/yr plus setup; Avetta ~$249 registration + $450 to $900+/yr; extra fees per client connection.
2. Complete the MSQ (reported at 800 to 2,000 questions).
3. Write and upload 8 to 40 written safety programs matched to work types and regions (fall protection, LOTO, HazCom, confined space, respiratory, hearing, etc.); RAVS review "can take weeks"; Avetta approval 30 to 45 days.
4. Upload COIs, OSHA 300/300A logs, EMR letter, training records; fix "red" items; repeat for each platform (one contractor reports memberships on five platforms).
5. Maintain monthly as documents expire.

**Who / how often / hours:** small electrical, mechanical, industrial-service subs. Evolution Safety Resources (consultant): 40 to 80 hours of administrative labor for documentation, 5 to 10 hours per month ongoing, first-year all-in $5,000 to $15,000 including $2,000 to $10,000 for outsourced program writing. AGC 2024 (via secondary): 38% of subs cite platform fees as an enrollment barrier, 24% cite complexity/time. Combined platform cost "can easily exceed $5,000 before they've bid on a single job."

**Why still manual:** questionnaires are gated and client-specific; which programs are required is a judgment based on work type; documents live in a binder; consultants sell "24 to 48 hour submission" as a service, which is the tell that no software does it.

**Public data / inputs:** the sub's own safety manual, OSHA 300A, EMR letter, COIs; OSHA standards on ecfr.gov (public) to draft compliant programs; ISN/Avetta/Veriforce portals (login; browser-automation target); Billy (GC-side, free for subs) as an alternative.

**Existing tools and gap:** consultants (1 Stop Compliance, Industrial Compliance & Safety, Evolution Safety Resources, Safety Procedure Systems), Billy (only if the GC adopts it), US Tech Automations. No agent that reads what the sub already has, answers the questionnaire, writes the missing programs, and tracks expirations.

**The moment:** Upload safety manual + 300A + COI. Agent answers a 200-question MSQ export, shows three gaps ("no written Hearing Conservation program"), drafts them from the manual and 29 CFR 1910.95, and prints the projected grade and the two items that expire in 30 days.

**Scores:** U 4, D 3 (portals are gated; demo against an exported questionnaire), Da 3, I 4, E 3.

**Evidence:**
- https://evolutionsafetyresources.com/avetta-compliance-support-for-contractors/
- https://billyforinsurance.com/resources/billy-vs-isnetworld-vs-avetta-subcontractor-prequalification/
- https://ustechautomations.com/resources/blog/construction-subcontractor-compliance-automation-comparison-2026
- https://www.industrialcompliancesafety.com/isnetworld-questions/

---

## 6. OEM warranty claim filing (HVAC / water heaters)

**Workflow name:** "Is it covered, and get us paid for it."

**Concrete steps today (per warranty call):**
1. Tech diagnoses; office looks up entitlement by serial. Goodman's lookup requires serial, model, homeowner last name, zip, and install type (verified form); Trane has an open serial lookup; Carrier's covers ICP brands (Heil, Comfortmaker, etc.); Lennox has no public lookup. Coverage depends on whether the installer registered within 60 to 90 days (10-year vs 5-year parts).
2. Get an RGA / claim number from the distributor; replace the part; return the defective part within the window (e.g., 30 days).
3. Submit claim with model/serial, install date, proof of purchase, customer info, description, diagnostics, photos. Manufacturer language: "All claims for reimbursement must be received at the factory within 60 days from date of service... All claims outside this time period will be void."
4. Track the credit on the distributor statement; dispute short-pays. Manufacturers pay "a ridiculously low amount for warranty labor and charge processing fees of $50 to $75 per claim" (ACHR News, via Warranty Re). Flat-rate labor allowances "may not always cover the contractor's actual costs."

**Who / how often / hours:** every HVAC and plumbing contractor, on every warranty call. No survey gives hours per claim; the burden shows up as deadline-voided claims, $50 to $75 processing fees, and internal labor cost of $55 to $120 per call (BLS median $27.55/hr x 1.5 to 3 hours, secondary). HVAC-Talk thread "Parts AND Labor warranty" exists on this (paywalled by Tollbit; title only).

**Why still manual:** each OEM/distributor has its own portal and rules; entitlement depends on registration history; part-return logistics; deadline traps; small shops do it from the truck.

**Public data / automation targets:** OEM serial entitlement lookups (Goodman URL verified; Trane, Carrier/ICP, Rheem per contractor guides); serial-number age decoders (hvacchecker.com, intrysys.com); distributor claim portals (login; browser automation); invoice PDFs; nameplate OCR.

**Existing tools and gap:** JB360 for ServiceTitan and JB Warranties (extended labor warranties, not OEM parts claims), ServiceTitan/BuildOps warranty tracking, Warranty Re, HVAC Warranty LLC. The OEM parts claim to the distributor is still typed by hand; nothing starts from a nameplate photo and ends with a filed RGA and a part-return reminder.

**The moment:** Nameplate photo -> serial decoded (mfg. Mar 2021) -> entitlement pulled ("compressor parts through 2031, registered; labor not covered") -> agent pre-fills the distributor RGA, prints the part-return label, sets "claim due in 47 days," and drafts the customer's out-of-pocket labor quote.

**Scores:** U 3, D 4, Da 3, I 3, E 4.

**Evidence:**
- https://hvacprosales.com/hvac-contractor-business/hvac-warranty-management-for-hvac-contractors/
- https://warranty-re.com/feeds/blog/profit-hvac-labor-warranties
- https://warranty.goodmanmfg.com/entitlement/GenericEntitlementLookup.htm?site=Goodman
- https://hvac-talk.com/vbb/threads/2249895-Parts-AND-Labor-warranty

---

## Candidates 7 to 14 (screened, not ranked)

7. **PBM audit response for independent pharmacies.** A desk audit "routinely consumes the pharmacist-in-charge's time and a technician's time for days, not hours"; appeal windows 14 to 60 days; "missing any deadline waives the appeal at that level"; extrapolation inflates demands. Tools: PAAS National audit-assistance membership, law firms. U 3, but PHI makes a public demo awkward and numbers are thin. https://www.healthlawalliance.com/blog/what-a-pbm-audit-costs-an-independent-pharmacy

8. **Workers' comp premium audit prep and dispute.** Annual; audit "usually takes 30 days"; requires payroll by class code, 941s, 1099s, and a COI for every sub or their pay gets charged as payroll. Insurer-side software exists (Majesco); nothing for the insured SMB. U 4 but weak evidence and an unexciting moment. https://www.insureon.com/blog/what-is-a-workers-compensation-insurance-audit

9. **Third-party delivery error-charge disputes (restaurants).** DoorDash 14-day window, Uber Eats 30; "up to 5% of third-party orders result in disputes"; Firehouse Subs 82% win-back, $297/location/month. Crowded: Lunchbox Dispute Manager, Voosh, Loop, Otter, Cuboh, Ascero. U 1. https://lunchbox.io/third-party-disputes-the-silent-restaurant-revenue-killer

10. **Subcontractor COI tracking (GC side).** Crowded: myCOI, TrustLayer, Jones, BCS, Certificial, Billy, TrackMyVendor. U 1. https://www.vertikalrms.com/article/best-coi-tracking-software-2026-top-coi-platforms-for-contractors/

11. **Preliminary notices / lien deadlines.** Only 11% prelim every project (2020) rising to 23% (2021); 75% have had to file a lien; Levelset (Procore), Siteline, Handle own it. U 1 to 2. https://www.levelset.com/blog/why-subcontractors-dont-send-prelims-and-why-theyre-wrong/

12. **Permit pulling and inspection scheduling.** PermitFlow (7,000+ AHJs), Pulley, GreenLite (~$86M raised), Permitio, Permitech. Mike Holt thread "Speaking of permits.. or avoiding them" (title only). U 2. https://permitio.ai/blog/best-permit-automation-software

13. **Machine-shop RFQ quoting from drawings.** Practical Machinist threads: most shops take 4 to 5 days to a week; some "99% of quotes in 48 hours"; "spend a vast chunk of the week's labor on ultra detailed quotation, which doesn't pay anything." Paperless Parts, Xometry, Protolabs dominate. U 2. https://www.practicalmachinist.com/forum/threads/methods-to-expedite-quoting.375813/

14. **Public bid discovery for small contractors.** SAM.gov Get Opportunities API is public (api.sam.gov/opportunities/v2/search, api key, 1,000 records/request); Jorpex, OryonIQ, SLED.AI, GovDash already do semantic matching. U 2. https://open.gsa.gov/api/get-opportunities-public-api/

Also considered and dropped for lack of evidence in this session: H-2A filings (Seso ~$1,000/application already automates), small-landlord rental registration/lead compliance, 1099/W-9 season (Track1099/Tax1099), sales tax (Avalara/TaxJar).

## Data sources verified live in this session

- HTS REST API: https://hts.usitc.gov/reststop/search?keyword=heat%20pump (JSON, no auth)
- DSIRE API and dumps: https://www.dsireusa.org/resources/data-and-tools/
- SAM.gov Opportunities API: https://open.gsa.gov/api/get-opportunities-public-api/ (no wage-determination API listed at https://open.gsa.gov/api/)
- Goodman warranty entitlement form inputs: https://warranty.goodmanmfg.com/entitlement/GenericEntitlementLookup.htm?site=Goodman
- California DIR eCPR (online form or XML schema v1.3): https://www.dir.ca.gov/Public-Works/Certified-Payroll-Reporting.html
- ENERGY STAR Product Finder API & datasets page: https://www.energystar.gov/productfinder/advanced
