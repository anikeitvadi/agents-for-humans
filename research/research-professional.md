# Professional Agents lane: research report

Hackathon: AWS "Agents for Humans" (Strands Agents SDK). Track: Professional Agents.
Date: 2026-09-08. Method: WebSearch (first 20 queries), then Brave/Yahoo SERP scraping and direct WebFetch of primary sources after the search budget ran out. Reddit pages are blocked for fetching, so Reddit evidence is quoted from SERP snippets (URLs are real and verifiable).

Crowded lanes confirmed and cut early: submittal review (BuildSync, Part3, Remy, iFieldSmart, SpecLens), bid leveling (Provision, Consight, Struvia, Melt), COI issuance (many vendors; Zywave 2025 survey says only 18% of agencies have automated it, but supply is crowded), dental predeterminations/benefit breakdowns (Zuub, Vyne, Intake.Dental, Verrific, Aron), commercial-insurance remarketing (Aon Broker Copilot, FurtherAI, PowerBroker.ai, Ivans), detention-pay claims (ChargeGuard, SherHaul, GetDockPay, DockClaim, ClockTheDock), gig deactivation appeals (GigAppeal; DoorDash in-app appeals since Mar 2026), IFTA (FleetCollect/Motive/Samsara), franchise self-audits (Operandio, Xenia), body-shop supplements (BainbridgeAI, CCC), PT plan-of-care signature chasing (CMS dropped the physician-signature requirement for initial certification effective 2025-01-01).

---

## Candidate list (12) and verdict

| # | Workflow | Who | Uniqueness (1-5) | Verdict |
|---|---|---|---|---|
| 1 | DataQs challenges (Requests for Data Review) for roadside-inspection violations | Small fleet owners, owner-operators, one-person safety managers | 5 | TOP 6 (#1) |
| 2 | Utility/state rebate filing for installed HVAC equipment | Residential HVAC contractors (office staff) | 4 | TOP 6 (#2) |
| 3 | Workers-comp premium audit prep and dispute (insured side) | Contractors, their bookkeepers and agents | 4 | TOP 6 (#3) |
| 4 | Security-deposit disposition (itemization, depreciation, statutory deadline) | Property managers, small landlords | 4 | TOP 6 (#4) |
| 5 | School immunization compliance (record ingestion, state-rule evaluation, parent letters, exclusion) | School nurses | 3 | TOP 6 (#5) |
| 6 | Below-cost (MAC) claim appeals with statutory-deadline escalation | Independent pharmacists/techs | 2.5 | TOP 6 (#6) |
| 7 | International pet health certificates (VEHCS) | Veterinarians, vet techs | 2 | Cut: Alita, Passpaw, GlobalVetLink, Torly.ai all do this in 2026 |
| 8 | Plan-check correction-letter responses | Architects, designers | 2 | Cut: Sumeria AI Comment Solver, TrussNote City Comment Review (Apr 2026), PlanChecker.ai, permittable, PlanCheckPro |
| 9 | IRS/state notice responses | Small CPA/EA firms | 2 | Cut: TaxNotice.ai, Canopy Notices, TaxDome, CPA Pilot |
| 10 | Certificates of insurance | Agency CSRs | 1 | Cut: crowded vendor market |
| 11 | UST monthly compliance logs | Gas-station owners | 3 | Cut: no primary pain evidence found this session; hard to demo |
| 12 | Death-certificate/benefits paperwork | Funeral directors | 3 | Cut: no hours evidence found; Passare/Osiris case management exists |

---

## TOP 6

### 1. DataQs violation-challenge agent (small fleets)

**Workflow today.** A roadside inspection produces violations that flow into FMCSA's SMS/CSA BASIC scores. To challenge one, the carrier logs into the FMCSA Portal, opens DataQs, picks the inspection report, selects the violation, writes a narrative, attaches evidence (ELD logs, maintenance records, driver qualification file, photos, bills of lading, the inspection report itself), cites the regulation (49 CFR 39x), submits a Request for Data Review, then answers the state agency's questions, and if denied, requests reconsideration and then final review. Inspection records are challengeable up to 3 years after the event; crashes up to 5.

**Who / how often / hours.** Owner-operators and small-fleet owners who have no safety department. FMCSA's system handles "71,000+ annual disputes," of which "63,000+ inspection and violation requests" (88.31%) (TruckerGuide summary of the April 15, 2026 FMCSA DataQs upgrade). Per-request effort is evidence-gathering plus a regulatory narrative; consultants sell it as a service (Fleet Safety Advisors: "virtual consultation, document review, submission support, and follow-up"). No hours-per-week survey found; the burden is episodic (per inspection) but each one is high-stakes because CSA percentiles "influence how carriers are evaluated by regulators, insurers, and industry partners."

**Why still manual.** Portal-only submission behind FMCSA login; judgment about which violations are actually challengeable (wrong carrier/USDOT attached, driver not employed, violation code not applicable to vehicle type, duplicate entry, short-haul exemptions, corrected-on-site); evidence lives in ELD, maintenance and HR systems; the narrative must tie evidence to a CFR section. As of April 2026 FMCSA requires denials to include "full written explanations tied to specific evidence," with "initial reviews: 21 days maximum," "reconsideration: 21 days maximum," "total resolution: 45 days maximum," which makes deadline tracking and structured reasoning newly valuable.

**Public data / APIs.**
- FMCSA QCMobile API (JSON, free `webKey`): `/carriers/:dotNumber`, `/carriers/:dotNumber/basics`, `/oos`, `/authority`, `/operation-classification` (https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcApi).
- SMS public data and downloads (https://ai.fmcsa.dot.gov/SMS/), SAFER company snapshot, FMCSA violation-code table (public CSV of roadside inspection violation codes and BASIC/severity weights).
- eCFR API for 49 CFR Parts 390-399 text citations (ecfr.gov/api).
- DataQs portal itself for submission (https://dataqs.fmcsa.dot.gov/, login required; browser automation or "prepare-and-hand-off").

**Existing tools and gap.** Only human consultancies (Fleet Safety Advisors) and how-to guides (First Underwriters 2026 PDF, LucidELD, TruckerNavi). ELD vendors show CSA scores but do not draft or manage RDRs. No software found that pulls a carrier's inspections, ranks challengeability, assembles evidence, drafts the RDR with citations, and tracks the 21/21/45-day clocks.

**The moment.** Judge types any real USDOT number. Agent pulls the carrier's BASICs and recent inspections live, flags one violation as challengeable (for example a lamp violation cited against a trailer the carrier does not own, or a 395.8 log violation for a driver who qualifies for the 150 air-mile short-haul exception), drafts the RDR with the CFR citation and an evidence checklist, and shows the projected drop in the Unsafe Driving or Vehicle Maintenance percentile if it is removed.

**Scores.** Uniqueness 5 · Demoability 5 · Data availability 5 · Impact 4 · End-to-end fit 4 (submission requires the carrier's portal login; everything up to and including the packet is automatable, submission via browser automation).

**Evidence.**
- https://blog.truckerguideapp.com/post/fmcsa-dataqs-2026-update-new-rules-reshape-denial-reviews
- https://www.fmcsa.dot.gov/newsroom/fmcsa-upgrades-dataqs-program-improve-efficiency-and-transparency-safety-record
- https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcApi
- https://fleetsafetyadvisors.com/dataqs-review-assistance
- https://www.firstunderwriters.com/wp-content/uploads/2026/02/FUW_DataQs_Challenge_Guide_2026.pdf

---

### 2. HVAC rebate filing agent

**Workflow today.** After an install, office staff: look up the AHRI Certified Reference Number for the exact outdoor+indoor+furnace pairing; confirm the pairing hits the program's SEER2/HSPF2/CEE tier and (since Jan 1, 2026 for federally funded electrification rebates) refrigerant GWP <= 700; find which programs the customer's utility/ZIP qualifies for; fill the utility or state portal application (contractor-only portals); attach nameplate photos, AHRI certificate, itemized invoice with labor/equipment split, signed customer authorization, license details; then chase status for 30-90 days. Many programs pay the contractor after the contractor already discounted the homeowner.

**Who / how often / hours.** Residential HVAC office staff and owners. "20 to 45 minutes of office labor per claim for a straightforward utility program, and 60 to 90 minutes for an income qualified federal program" (Bella FSM, Jul 2026). "Small HVAC shops average 15.4 hours per week on admin tasks" (HVAC Know It All citing Industry Pulse 2025). Cash-flow example: ten $1,600 rebates a month is "$16,000 of working capital tied up at any given time."

**Why still manual.** Portals differ per utility; rules change yearly (25C federal credit "ended for systems installed after December 31, 2025"); the top rejection causes are judgment and lookup errors: "Equipment nameplate photo," "AHRI certificate reference number," "Refrigerant GWP confirmation," "Itemized invoice with labor and equipment split," "Signed customer authorization." Reddit shows the failure mode: "there are no matching results for the Rheem Furnace and Bosch Heat Pump" in AHRI (r/hvacadvice 1k0zzgp); a certified contractor installed a non-Energy Star unit "resulting in $8,000 rebate rejection" (r/heatpumps 1kcof1q).

**Public data / APIs.**
- DSIRE API with documentation (https://docs.dsireusa.org/; filter incentives by state, technology, sector, utility).
- ENERGY STAR data portal: every dataset has a Socrata API endpoint, including certified heat pump/AC lists (https://data.energystar.gov/stories/s/ENERGY-STAR-Developer-Resources/me9a-5y43) and the ZIP-based Rebate Finder (https://www.energystar.gov/rebate-finder).
- AHRI Certification Directory (public search, certificate PDF; no official API, scrapeable) (https://www.ahridirectory.org/).
- Utility program PDFs/portals (Mass Save, TECH Clean California, SDG&E, etc.) for form filling.

**Existing tools and gap.** Lookup-only (DSIRE, ENERGY STAR Rebate Finder), generic form fillers (Instafill.ai has an HVAC rebate guide), FSM software with checklists (Bella FSM), automation consultancies. No dominant contractor-side product that validates the AHRI match, picks eligible programs, fills the application and tracks payment.

**The moment.** Type two model numbers and a ZIP. Agent finds the AHRI certificate live, checks the tier and GWP rule, lists eligible programs with dollar amounts, fills the utility PDF, and says: "This coil pairing is not AHRI-matched; swap to model X and the job qualifies for $1,600 more." Then it emails the homeowner the authorization to sign.

**Scores.** Uniqueness 4 · Demoability 4 · Data availability 4 · Impact 4 · End-to-end fit 4.

**Evidence.**
- https://www.bellafsm.com/hvac-rebate-paperwork/
- https://hvacknowitall.com/blog/the-admin-tax-how-paperwork-is-killing-your-service-hours
- https://www.reddit.com/r/heatpumps/comments/1kcof1q/
- https://www.reddit.com/r/hvacadvice/comments/1k0zzgp/
- https://docs.dsireusa.org/ · https://www.ahridirectory.org/

---

### 3. Workers-comp premium audit defense agent (insured side)

**Workflow today.** At policy year end the carrier audits actual payroll against the estimate. The insured (or their bookkeeper/agent) assembles payroll registers, 941/944, state unemployment reports, W-2/1099s, overtime detail, officer exclusions, subcontractor payments and a certificate of insurance for every sub; the auditor assigns payroll to NCCI/state class codes; uninsured subs are charged as employees; the result is an additional-premium bill. Disputes require a written challenge with classification arguments and documentation. Documentation list per ADP: "accounting ledger, tax forms such as W-2, 1099, Form 941, Form 944 and your federal tax return, and a certificate of insurance for every subcontractor."

**Who / how often / hours.** Every workers-comp policyholder, annually; contractors are hit hardest. Bookkeepers and agents do it across many clients each renewal cycle. Reddit r/GeneralContractor: "My insurance company did an audit to verify I was keeping up with subs COIs, and sent me a bill for almost $10k for 'adjusted premium'... since I didn't have COIs from those 2 subs they were treating them as employees." NCCI inspection data cited by ClassCheck: "governing-code changes on more than 60% of inspected files." Rate spread: "clerical work at $0.05-$0.35 per $100 of payroll, roofing runs $15-$45." No hours-per-week survey found; per-audit effort is days of record assembly for a small contractor.

**Why still manual.** Class-code assignment is judgment (interchange of labor rules, standard exceptions, payroll separation by job), sub COI validity is date-and-endorsement checking across PDFs, and the dispute is a written argument. Auditor-side AI exists (weav.ai, Nomad Data, Bevaya), insured-side has only a free checker.

**Public data / APIs.**
- State rating-bureau class-code lookups: NCRB (https://www.ncrb.org/classcodelookup/), WCIRB California, PCRB Pennsylvania, plus public rate tables (workerscompcost.com lists 292 codes across 51 jurisdictions). NCCI Scopes manual is paywalled.
- Payroll via QuickBooks/Gusto/ADP APIs; COIs are ACORD 25 PDFs; state WC coverage-verification lookups for subs (NCCI coverage verification; state DWC sites).
- IRS 941 forms; state unemployment wage reports.

**Existing tools and gap.** ClassCheck (classcodecheck.com): free AI screen of role-to-class-code fit, then "$249 for line-by-line analysis with human review and dispute packet (3-business-day turnaround)." compauditprep.com and vantagepointrisk.com publish guides. Nothing ingests payroll + sub list + COIs, forecasts the audited premium before the auditor arrives, flags uninsured-sub exposure and drafts the dispute.

**The moment.** Upload a payroll register, sub payment list and a folder of COI PDFs. Agent reproduces the auditor's worksheet, shows "expected additional premium $9,800," then finds two subs whose COIs lapsed mid-year ($6,200 of the bill), pulls an office employee out of the roofing code, separates overtime premium, and rewrites the number to $2,340 with a ready-to-send dispute letter citing the classification rule.

**Scores.** Uniqueness 4 · Demoability 4 · Data availability 3 · Impact 4 · End-to-end fit 4.

**Evidence.**
- https://www.reddit.com/r/GeneralContractor/comments/10s2tyk/workers_comp_on_subs_audit/
- https://classcodecheck.com/
- https://insurance.adp.com/-/media/insurance/pdfs/adpia-understanding-your-workers-compensation-audit.pdf
- https://vantagepointrisk.com/learning-center/contractor-workers-comp-audit-explained/

---

### 4. Security-deposit disposition agent

**Workflow today.** After move-out: compare move-in vs move-out inspection (photos, checklist), decide damage vs normal wear, price repairs from vendor invoices, depreciate replaced items by remaining useful life, add unpaid rent/utilities from the ledger, produce an itemized statement with receipts, mail it (often certified) and the refund within the state deadline, and handle the dispute. Formula practitioners use: "Deduction equals replacement cost multiplied by remaining useful life divided by total useful life" (RapidEye), for example carpet with 8-year life destroyed in year 6 = $2,400 x 2/8 = $600.

**Who / how often / hours.** Property managers and small landlords, once per move-out (a 100-unit portfolio at typical turnover is 40-50 dispositions a year). No hours survey; per-disposition it is an inspection reconciliation plus letter and it is deadline-bound. Reddit: r/Landlord "How much do i deduct from security deposit?" debating "$3,500 or $5,500 for wall repairs/painting with $6,600 security deposit" (1m3cti7); r/Landlord "Calculating depreciation for repairs, replacement and damage" (128s5su); r/Bellingham: "They mailed out the deposit and 'itemized' list exactly on the 21st day after move out. Per the RCW, they must provide an itemized list before the 21st day, or must give back the whole deposit" (x6pdwh).

**Why still manual.** Judgment (wear vs damage), math (depreciation), and 51 different statutes: deadlines run 14 days (Arizona, New York) to 60 days (Alabama, Arkansas), penalties include double damages (Alaska, Arizona, Connecticut, Delaware) and treble damages (Colorado, Hawaii, Idaho, Maryland, Massachusetts), Massachusetts is "strict liability, no bad faith required," Texas is "$100 plus three times the amount wrongfully withheld." "Failure to provide itemization often forfeits the landlord's right to keep any portion of the deposit."

**Public data / APIs.**
- 51-jurisdiction statute table with citations (https://www.depositdeadline.com/security-deposit-laws-by-state) and state statute text.
- Useful-life schedules (HUD/Fannie Mae estimated useful life tables; industry schedules like RapidEye's).
- Ledger and lease from Buildium/AppFolio APIs; inspection photos from RentCheck/zInspector; certified mail via Lob/USPS API; e-sign.

**Existing tools and gap.** Micro-calculators (DepositDeduct paint depreciation; LetsGoLandlord deadline calculator), templates (Azibo, Landlord Studio, AAOA form), PMS accounting (AppFolio/Buildium hold the ledger but do not decide deductions or cite statutes). No agent that goes photos + ledger + lease + state to a defensible itemized letter, mailed on time.

**The moment.** Drop move-in and move-out photos, the ledger and the lease. Agent produces the itemization with depreciation math and statute citations, a countdown to the deadline, and a warning: "Carpet is 7 of 8 years old: deduct $150, not $1,200, or you are exposed to treble damages under M.G.L. c.186 s.15B." One click sends the letter and refund.

**Scores.** Uniqueness 4 · Demoability 5 · Data availability 4 · Impact 4 · End-to-end fit 5.

**Evidence.**
- https://www.depositdeadline.com/security-deposit-laws-by-state
- https://www.reddit.com/r/Landlord/comments/128s5su/general_us_calculating_depreciation_for_repairs/
- https://www.reddit.com/r/Landlord/comments/1m3cti7/how_much_do_i_deduct_from_security_deposit/
- https://www.reddit.com/r/Bellingham/comments/x6pdwh/security_deposit_itemization/
- https://rapideyeinspections.com/blog/rental-property-useful-life-schedule/

---

### 5. School immunization compliance agent

**Workflow today.** At enrollment and every fall: collect records (photos of cards, provider PDFs, faxes, foreign records), transcribe doses, look up the state registry (IIS) if the nurse has access, evaluate each student against the state's grade-entry schedule and ACIP validity rules (minimum ages, intervals, invalid doses), handle medical/religious exemptions and provisional (in-progress) status, send warning letters (in multiple languages), call parents, track "days since the warning letter," exclude non-compliant students by the deadline, and file the annual state report (for example Texas ARIS).

**Who / how often / hours.** School nurses; a national NASN/CDC questionnaire of "1,435 school nurses from all 50 states" (average "87.0" kindergartners per school) found "96" percent made phone calls to parents of undervaccinated students, "67" percent sent postal mail, "85" percent documented in electronic systems, only "32" percent used state IIS, and "43" percent excluded students. NYC DOE guidance has staff run the "ATS function daily to identify non-compliant students" and track "Days since the warning letter" before exclusion notices. An Indiana high school started at "66% student immunization compliance" and raised it with letters, calls and email follow-up (PubMed 27573417). Seasonal (August-October) surge on top of clinic duties.

**Why still manual.** Records arrive as images and foreign-language documents; validity rules are intricate (CDC's logic spec is 151 pages); state schedules differ; exemptions and provisional status are judgment calls; parent chasing is multilingual and multi-channel; IIS access is uneven.

**Public data / APIs.**
- CDC CDSi: Logic Specification v4.6 (151 pages), Supporting Data v4.65 (XML, updated Aug 2026), and two test-case spreadsheets, all public (https://www.cdc.gov/iis/cdsi/index.html; also hosted by AIRA).
- State school-entry requirement tables (state DOH PDFs); state annual report packets (Texas ARIS).
- SIS APIs (PowerSchool), state IIS (not public; integrations like Magnus ImmsLink).

**Existing tools and gap.** SNAP Health Center ("calculate state specific compliance for every student with the click of a button" once data is entered), Magnus Health (registry sync; a paid human "certified nurse reviewers" service to enter dose dates), Docket for Schools (letters), SmartVax AI / DocuPipe / LlamaIndex (OCR of immunization records), Inferensys (PowerSchool copilot). Pieces exist; nothing runs the whole loop from a photo of a foreign card to a CDSi-validated decision, a bilingual parent letter, follow-up, and an exclusion-date calendar. Uniqueness is only moderate because of this.

**The moment.** Photograph a handwritten, partly Spanish vaccine card. Agent extracts doses, runs CDSi evaluation (flags a DTaP dose given 3 days before the minimum interval as invalid), checks the state's kindergarten rules, decides "provisional, next dose due by Oct 14," and drafts the parent letter in Spanish with the exclusion date and nearest clinic.

**Scores.** Uniqueness 3 · Demoability 4 · Data availability 4 · Impact 4 · End-to-end fit 4.

**Evidence.**
- https://pmc.ncbi.nlm.nih.gov/articles/PMC6854288/
- https://infohub.nyced.org/docs/default-source/default-document-library/guidance-to-schools-on-immunization-compliance.pdf
- https://pubmed.ncbi.nlm.nih.gov/27573417/
- https://www.cdc.gov/iis/cdsi/index.html
- Tools: https://www.schoolhealth.com/snap-subscription-cloud-service · https://www.smartvaxai.com/ · https://docket.care/schools

---

### 6. Below-cost claim (MAC) appeal and escalation agent

**Workflow today.** Each day the pharmacy reconciles PBM remittances against acquisition cost; for claims reimbursed below cost it files a MAC appeal with the PBM within the state window, supplying "the National Drug Code, quantity, unit price, and invoice date, matched to the date of the claim at issue," then tracks the PBM's statutory response deadline, and if denied, files an external appeal/complaint with the state regulator.

**Who / how often / hours.** Independent pharmacists and techs. NCPA January 2025 survey: "40.8 percent of independent pharmacists said they were paid below the National Average Drug Acquisition Cost (NADAC) on more than 40 percent of the prescriptions they filled for Medicare Part D patients." Reddit r/pharmacy: an independent reporting "~30 daily loss-making prescriptions" and "they have someone almost full time" calling to get claims adjusted (10mw4bu); "Even though 99% are denied, we keep sending them... for evidence when we show legislators" (5upw2p); "hardly any of the claims come back with adjusted reimbursement" (xq295c).

**Why still manual.** Per-PBM portals, short statutory windows (Oklahoma: appeal within 10 business days and PBM response within 10 business days under 59 O.S. s.360; Mississippi: 30 business days each way under Miss. Code s.73-21-156), invoice evidence must be assembled per NDC, and the leverage is in enforcing the state law (missed PBM deadlines, documented patterns), not the individual appeal.

**Public data / APIs.**
- NADAC weekly reference file with API on data.medicaid.gov (https://data.medicaid.gov/dataset/fbb83258-11c7-47f5-8b18-5f8e79f7e704).
- openFDA NDC directory; NCPDP 835 remittance files from the pharmacy system; wholesaler invoice exports.
- State MAC-appeal statutes (all 50 states regulate PBMs in some form) and state complaint portals.

**Existing tools and gap.** Pharmacy Marketplace's PBM Appeals feature already "automatically surfaces" underwater claims, pre-populates acquisition cost and tracks the "3-30 days" state window with a "Submit External Appeal" button; Cardinal Health PSAO "Automated MAC Advantage"; PDC Rx and LucyRx processes. The remaining gap is doing the PBM-portal submissions and the regulator complaint end to end, and building the legislative-evidence pattern file. Ranked last in the top 6 because the space is partly served and win rates are low.

**The moment.** Drop today's 835 remittance. Agent lists 30 underwater claims with the NADAC delta, drafts the appeals with matched invoice lines, starts each state's statutory clock, and when a PBM misses its 10-business-day response, auto-generates the state complaint with the pattern evidence attached.

**Scores.** Uniqueness 2.5 · Demoability 4 · Data availability 5 · Impact 4 · End-to-end fit 4.

**Evidence.**
- https://ncpa.org/sites/default/files/2025-01/1.27.2025-FinalExecSummary.NCPA_.MemberSurvey.pdf
- https://www.reddit.com/r/pharmacy/comments/10mw4bu/below_cost_reimbursement/
- https://www.reddit.com/r/pharmacy/comments/5upw2p/how_hard_is_it_to_get_a_mac_appeal_approved/
- https://www.healthlawalliance.com/blog/mac-appeals-challenging-below-cost-reimbursement
- Existing: https://knowledge.pharmacymarketplace.com/knowledge/how-to-manage-mac-appeals-in-pharmacy-marketplace · https://www.cardinalhealth.com/en/services/retail-pharmacy/business-solutions/psao-services/automated-mac-advantage.html

---

## Cut candidates with the evidence that would otherwise have made them attractive

**International pet health certificates (vets).** Strong pain: r/veterinaryprofession "USDA Vet Services Rant" (25-year vet: "It took NINE DAYS to get a cert approved through VEHCS"), "Health certificates from hell," "these things are a giant pain in the ass"; r/USDA Dec 2025 "massive delays"; $700-800 per certificate is "par for the course" (r/travelwithpets). Public data is excellent (APHIS per-country pages, e.g. Japan: microchip before first rabies shot, two shots >30 days apart, titer >= 0.5 IU/ml, 180-day wait, 40-day advance notice). But Alita (flyalita.com: "automates USDA VEHCS draft generation"), Passpaw, GlobalVetLink (built-in country rules plus concierge) and Torly.ai already sell this. Uniqueness 2.

**Plan-check correction responses (architects).** r/Architects: "15 to 20 comments" per rejection with "8-week review times for resubmittals" (1lwmzvu); reviewers: "Second plus review cycles that blatantly ignore comments" (r/BuildingCodes 1l9023w); a reviewer who analyzed 54k permits: "submitted multiple plans to me with the same issue in every plan" (1sgtzqh). But Sumeria AI's "AI Permit Response & Comment Solver," TrussNote's "City Comment Review" (Apr 2026), PlanChecker.ai, permittable and PlanCheckPro cover it. Uniqueness 2.

**IRS/state notice responses (small tax firms).** TaxNotice.ai ("turns every IRS notice into a tracked case... Your team still does the judgment work"), Canopy Notices, TaxDome, CPA Pilot. Uniqueness 2.

**Certificates of insurance.** "8-15 CSR hours per week" and "45-90 minutes" per COI (IIABA figures via ustechautomations); Zywave 2025: 62% call the workflow "manual and inefficient," 18% automated. Vendor-crowded; excluded by brief.

**Detention pay, gig appeals, IFTA, franchise audits, submittals, bid leveling, dental benefits, insurance remarketing.** Crowded; see the header list.

**Method caveats.** WebSearch budget was exhausted after 20 queries; the rest used Brave/Yahoo SERP scraping (Yahoo intermittently 500s) and direct fetches. Reddit content is quoted from SERP snippets; fmcsa.gov press pages return 403 to the fetcher, so the DataQs volume/turnaround numbers come from TruckerGuide's summary of the April 15, 2026 FMCSA announcement and should be re-verified against the Federal Register notice before use in a pitch. No per-week hours survey exists for DataQs, WC audits or deposit dispositions; those are per-event burdens with high stakes rather than daily grind, which is worth stating honestly in the submission.
