# Everyday Agents research: personal and family admin lane
AWS "Agents for Humans" hackathon (Strands Agents SDK). Track: Everyday Agents ("runs quietly in the background, pings only when there's a real decision").
Researched 2026-09-08. Method: web search (200-call budget exhausted) + direct fetches of primary sources and live API endpoints. Reddit is blocked from this environment; forum evidence comes from Blind, HN, KFF/CPSC/CMS/NHTSA reports instead.

Scoring key: 1 (weak) to 5 (strong). U = uniqueness, D = demoability, A = data availability, I = impact, Q = "runs quietly, pings only on a real decision" fit.

---

## Candidate longlist (12)

| # | Candidate | One-line gap | U | D | A | I | Q | Sum |
|---|---|---|---|---|---|---|---|---|
| 1 | Recall-to-remedy for everything you own (products, car, drugs/devices) | Amazon only covers Amazon; nobody cross-matches receipts+VIN against CPSC/NHTSA/openFDA and files the remedy | 4 | 5 | 5 | 4 | 5 | 23 |
| 2 | Aging-parent Medicare guardian (claims audit, appeals, Part D re-shop) | Blue Button 2.0 gives an agent Mom's claims; 28 orgs in prod, none is a caregiver's quiet auditor | 4 | 4 | 5 | 5 | 5 | 23 |
| 3 | Immigration status guardian (I-94 vs I-797 vs passport, Visa Bulletin, AR-11, grace periods) | Lawfully/VisaWatch track case status; none run status-integrity and deadline logic | 5 | 4 | 3 | 4 | 5 | 21 |
| 4 | Class-action claims matched to your real purchase history | Payout/ClaimDepot list settlements; none match to your receipts and file only what you qualify for | 3 | 5 | 3 | 3 | 5 | 19 |
| 5 | Medical bill audit + EOB reconciliation + No Surprises PPDR | HealthLock/Goodbill/MyMedBill exist; none quietly reconcile bill vs EOB vs hospital MRF and route self-pay to PPDR | 2 | 4 | 4 | 5 | 4 | 19 |
| 6 | Security-deposit statutory clock (inspection right, deadline, demand letter) | Only 42% get full deposit back; DoNotPay was fined by FTC; no agent runs the clock | 3 | 4 | 4 | 3 | 4 | 18 |
| 7 | Health-insurance denial appeals (patient side) | Counterforce (free, NIH-backed), Claimable, Fight Health Insurance: crowded | 1 | 4 | 3 | 5 | 3 | 16 |
| 8 | Property tax protest | Ownwell dominant (127K Houston protests in 2025) | 1 | 3 | 5 | 4 | 3 | 16 |
| 9 | Price-drop refunds, return windows, card warranties | Purchy (2025, $12.99/mo) does exactly this; Paribus dead | 2 | 4 | 3 | 3 | 5 | 17 |
| 10 | Travel disruption compensation (DOT automatic refunds, EU261) | AirHelp/Flightright take 35 to 50%; DOT rule since Oct 2024 but enforcement paused | 2 | 5 | 4 | 3 | 5 | 19 |
| 11 | FSA year-end forfeiture prevention + substantiation | Half of accountholders forfeit ($441 avg); benefits admins nudge but do not act | 3 | 3 | 2 | 3 | 5 | 16 |
| 12 | Death/estate admin; unclaimed property + benefits (SNAP/EITC) | Empathy (B2B2C) for death admin; state sites for unclaimed property; portals with no APIs for benefits | 2 | 2 | 2 | 5 | 2 | 13 |

Note on #10: high sum, but the space is saturated (AirHelp, Compensair, ClaimCompass, Flighty) and the DOT rule now makes cancellation refunds automatic, so the agent's marginal value is small. Left out of the top 6 on uniqueness.

Design note: #1 and #4 (and #9) share one data spine, the receipts in your inbox. They can ship as one agent with several triggers ("everything you bought, everything it entitles you to"). #2 and #5 share the claims/EOB spine.

---

## TOP 6

### 1. Recall-to-remedy agent ("You bought it. It got recalled. It's handled.")

**Workflow today**
1. A recall is announced (CPSC ~300+/yr; NHTSA ~1,000/yr; FDA drug/device/food enforcement continuous).
2. You hear about it only if you registered the product, Amazon emails you (Amazon purchases only), or the news covers it.
3. You dig for model/lot number, check the recall notice, figure out the remedy (refund vs voucher vs repair vs "stop using"), fill out the manufacturer form, ship the item or book a dealer visit.
4. For cars: nhtsa.gov VIN lookup, call dealer, book appointment, follow up on parts availability.

**Who, how often, stakes**
- Everyone who owns things; passive, continuous.
- CPSC's own 2017 recall-effectiveness workshop put average consumer participation at ~6% across product types, ~4% for products under $20, ~32% for $10,000+ (cited in Koji's recall-notice research, which pulls from CPSC materials). Consumer Reports has cited the same 6% average; CPSC has estimated ~10% of consumers follow up on recalls.
- NHTSA: weighted average completion rate 65.8% for recalls initiated 2012 to 2022; roughly 1 in 3 recalled vehicles is never repaired; an industry analysis of 10,367 NHTSA recalls estimates ~149.5M unrepaired vehicles. Completion falls to 56% for vehicles 6 to 10 years old.
- Live check today: CPSC's API returned 30 recalls for Aug 13 to Sep 3, 2026, including Cambridge Audio speakers with a fire hazard and a choice of "$218 cash refund or $350 voucher".

**Why still manual**
Notice reaches the retailer or registrant, not the owner. Owners must recognize the product, find the model/lot, and pick a remedy. Amazon solved it only for Amazon; nobody joins receipts across retailers plus VINs plus a household med list against three federal feeds.

**Public data / APIs (all verified live, no auth)**
- CPSC: `https://www.saferproducts.gov/RestWebServices/Recall?format=json&RecallDateStart=YYYY-MM-DD` returns RecallID, RecallNumber, RecallDate, Title, Description, ConsumerContact, Products[Name, Model, Type, NumberOfUnits], Hazards, Remedies, RemedyOptions, Retailers, Manufacturers, Images, Injuries.
- NHTSA: `https://api.nhtsa.gov/recalls/recallsByVehicle?make=honda&model=accord&modelYear=2019` returns NHTSACampaignNumber, Manufacturer, ReportReceivedDate, Component, Summary, Consequence, Remedy, Notes, parkIt/parkOutSide/overTheAirUpdate flags. NHTSA vPIC decodes a VIN to make/model/year.
- openFDA: `https://api.fda.gov/device/enforcement.json` (also /drug/ and /food/) returns product_description, reason_for_recall, recall_initiation_date, classification (Class I/II/III), distribution_pattern, code_info (lot/GTIN). No key needed at low volume.
- Inputs: Gmail receipts (product names, models, order numbers), VIN from insurance/registration emails, household meds from pharmacy emails.

**Existing tools and the gap**
- Amazon "Your Recalls and Product Safety Alerts" (2023): Amazon orders only, notify-only.
- myCarfax / Carfax recall alerts: car only, notify-only.
- Purchy ($12.99/mo, 2025): returns, price drops, warranties, subscriptions from Gmail+Plaid; no recalls.
- Koji: B2B recall-notice tooling for manufacturers.
- Gap: one agent that owns the inventory, polls three feeds, matches, and completes the remedy (form, RMA, dealer booking), pinging only for the real choice (refund vs voucher; repair timing).

**The moment (5-min demo)**
Agent is idle. A CPSC recall drops (use a real one from the feed, or replay this week's Cambridge Audio one). Agent matches it to a 2024 receipt in the inbox, pulls the model number from the order email, pre-fills the manufacturer's remedy form, and pings: "Your Yoyo speaker is a fire hazard. Refund $218 or voucher $350. Which?" One tap. In parallel it shows the car lane: new NHTSA campaign for the family Honda, dealer appointment already requested by email, "Tuesday 9am, no charge, confirm?"

**Scores** U 4 · D 5 · A 5 · I 4 · Q 5

**Evidence**
- CPSC API info page: https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information
- Recall response rates (CPSC 2017 workshop figures, awareness vs action funnel): https://www.koji.so/docs/product-recall-notice-research
- NHTSA report to Congress on completion rates (Apr 2026): https://www.nhtsa.gov/document/report-congress-improving-vehicle-safety-recall-completion-rates ; unrepaired estimate: https://www.recallmasters.com/nhtsa-recall-compliance-2015to2025/
- Amazon recall page launch: https://www.aboutamazon.com/news/how-amazon-works/amazon-creates-new-page-to-share-recalls-for-customers
- CPSC literature review on recall effectiveness (PDF): https://www.cpsc.gov/s3fs-public/RecallEffectiveness.pdf

---

### 2. Aging-parent Medicare guardian ("Mom's claims, watched every night")

**Workflow today**
1. Parent (Original Medicare) receives a Medicare Summary Notice every 3 to 4 months, plus Part D EOBs monthly, plus provider bills.
2. Adult child (often remote) is supposed to reconcile MSN lines against actual visits, spot services never received (fraud), duplicate claims, denied lines, and bills that exceed the MSN's "you may be billed" amount.
3. If a line is wrongly denied: file a Redetermination (form CMS-20027 or write on the MSN) within 120 days; MAC decides within 60 days. Five appeal levels.
4. Every Oct 15 to Dec 7: re-shop Part D against the parent's actual drug list on Medicare Plan Finder.

**Who, how often, stakes**
- 53M family caregivers (AARP/NAC 2020, verified); the 2025 update reports ~63M (not fetched directly, treat as reported).
- Medicare FFS improper payments FY2024: 7.66%, $31.70B; Medicare Advantage $19.07B; Part D $3.58B (CMS fact sheet).
- KFF: 69% of beneficiaries did not compare plans during open enrollment; 69% of PDP enrollees did not compare drug coverage.
- KFF (Jan 2025, 2023 data): only ~12% of MA prior-auth denials were appealed; 81.7% of appeals were fully or partly overturned. Appeals work; nobody files them.
- Senior Medicare Patrol 2024: 283,724 individual interactions, $35.1M expected recoveries, and MSN review is its core detection tool (HHS-OIG). The program is volunteers reading paper statements.

**Why still manual**
Statements arrive on paper months late; the caregiver has no feed; Blue Button 2.0 apps exist but are aimed at research, plan sponsors, and PHRs, not at a remote daughter who wants a quiet auditor. Plan Finder is a manual re-entry exercise every fall.

**Public data / APIs**
- CMS Blue Button 2.0 API: FHIR R4 (CARIN Blue Button IG) ExplanationOfBenefit, Coverage, Patient; OAuth 2.0 beneficiary consent (a parent can authorize a caregiver's app). Sandbox with synthetic data for 10,000 enrollees; 2,000+ developers, 28 orgs in production. Covers Part A, B, D claims back to 2014. https://bluebutton.cms.gov/developers
- Medicare Physician Fee Schedule and HCPCS on data.cms.gov (to price what a line "should" cost).
- CMS Part D public-use files: "Prescription Drug Plan Formulary, Pharmacy Network, and Pricing Information Files" (quarterly; verify current URL on cms.gov) for the AEP re-shop; Medicare Plan Finder as fallback.
- CMS-20027 Redetermination form (PDF verified): https://www.cms.gov/medicare/cms-forms/cms-forms/downloads/cms20027.pdf
- SMP fraud reporting and 1-800-MEDICARE for "service never received."

**Existing tools and the gap**
- HealthLock ($27.99 to $34.99/mo): syncs 250+ commercial insurers, flags overbilling, helps appeal. Commercial-insurance-first, not a caregiver product, not built on Blue Button.
- Chapter (500K+ enrollees, licensed human advisors) and Healthpilot: plan selection, not claims auditing, not year-round.
- Blue Button production apps (Humetrix iBlueButton, Verily, etc.): PHR/research.
- Gap: a caregiver-side agent that ingests every new EOB the night it posts, prices it, flags the 5% that matter, drafts the CMS-20027 with the 120-day clock, and re-shops Part D each October against real fills.

**The moment**
Agent polls the (sandbox) Blue Button feed. A new EOB posts: a $1,900 DME line from a supplier Mom has never seen, plus a denied ambulance line. Agent cross-checks the supplier against her visit history (none), drafts the SMP fraud report and the CMS-20027 for the ambulance denial with the deadline computed from the MSN date, and pings the daughter: "Two things happened last night. One looks like fraud, one is a denial we can probably win (82% of appeals overturn). Approve both?" Second beat: "It's October 16. Re-priced her 6 meds across 22 PDPs in 78701: switching saves $611/yr. Say yes and I'll enroll her."

**Scores** U 4 · D 4 · A 5 · I 5 · Q 5

**Evidence**
- CMS FY2024 improper payments: https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2024-improper-payments-fact-sheet
- KFF 7 in 10 do not compare plans: https://www.kff.org/medicare/nearly-7-in-10-medicare-beneficiaries-did-not-compare-plans-during-medicares-open-enrollment-period/
- KFF MA prior auth (12% appealed, 81.7% overturned): https://www.kff.org/medicare/medicare-advantage-insurers-made-nearly-53-million-prior-authorization-determinations-in-2024/
- HHS-OIG SMP 2024 performance data: https://oig.hhs.gov/reports/all/2025/2024-performance-data-for-the-senior-medicare-patrol-projects
- Blue Button 2.0 developer docs (sandbox, FHIR R4, OAuth): https://bluebutton.cms.gov/developers
- 120-day redetermination window, CMS-20027, 60-day decision: https://www.aarp.org/medicare/how-to-appeal-medicare-claims/

---

### 3. Immigration status guardian ("The dates that can end your life here, watched")

**Workflow today (H-1B / EB backlog family)**
1. After every entry, check the I-94 on i94.cbp.dhs.gov; compare "admit until" to the I-797 validity and passport expiry. CBP routinely shortens the I-94 to the passport expiry; if you miss it you are out of status on a date nobody told you about.
2. Track Visa Bulletin monthly (Final Action vs Dates for Filing; USCIS announces which chart it will honor); when the priority date goes current, file I-485/EAD/AP inside that month's window.
3. Move: file AR-11 within 10 days (INA 265), for every family member.
4. Job loss: 60-day grace period (8 CFR 214.1(l)(2)) to transfer or change status.
5. Passport renewal 6+ months before travel; visa stamping appointment; dependent kids' CSPA age-out math; EAD renewal 180 days out; I-140 portability after 180 days.

**Who, how often, stakes**
- Employment-based green-card backlog: 1,264,495 people as of Dec 2025; 996,599 are Indian nationals (79%); Cato's projections say 400K+ will die waiting. Every one of them lives on these dates for a decade or more.
- Blind threads show the failure mode repeatedly: "I-94 expiration date before I-797", "I-94 shortened and overstay >180 days", "passport expiry I-94 mismatch", "overstayed I-94 expiration date mistakenly". A 180+ day overstay triggers a 3-year bar; the fix is a nunc pro tunc filing with attorney fees.
- Stakes: job, residence, and the entire green-card queue position. Dollar cost of the safest fix (attorney + NPT filing) runs into thousands; the worst case is a multi-year bar.

**Why still manual**
The data lives in four systems that do not talk (CBP I-94, USCIS, DOS Visa Bulletin, the employer's attorney portal). Case-tracker apps watch one thing (receipt status). Attorneys are paid per filing, not to watch your I-94.

**Public data / APIs**
- USCIS Case Status API (Torch platform, developer.uscis.gov): OAuth 2.0 client credentials; GET /{receiptNumber} returns form type, current status (EN/ES), description, submitted/modified dates, and history. Sandbox: 1,000 requests/day, 5 TPS; production: 150,000/day after 5 consecutive days of sandbox traffic. Spec verified: https://developer.uscis.gov/sites/default/files/apidoc_specs/case-status-api-smartdoc_26.yaml
- USCIS processing times pages (HTML), USCIS "which Visa Bulletin chart to use" page (monthly).
- DOS Visa Bulletin (monthly HTML tables at travel.state.gov; no official JSON; community mirrors exist).
- CBP I-94: no API; the user retrieves the PDF from i94.cbp.dhs.gov and the agent parses it. Same for I-797 and passport (OCR).
- AR-11 online at uscis.gov/ar-11; USPS change-of-address confirmation email is a natural trigger.

**Existing tools and the gap**
- Lawfully (6M+ cases, case status + bulletin + processing-time predictions), VisaWatch, Visa Bulletin & Case Tracker apps: they watch USCIS receipts and the bulletin. None hold the I-94/I-797/passport triangle, the AR-11 10-day clock, grace periods, or CSPA math, and none draft the filing or the email to counsel.
- Immigration case-management software (eImmigration, Docketwise): for law firms.
- Gap: a personal status-integrity agent.

**The moment**
User drops in three PDFs (I-94, I-797, passport bio page). Agent: "Your I-797 runs to 05/04/2028 but CBP admitted you only to 11/02/2026 because your passport expires 11/02/2026. You have 55 days of lawful status, not 20 months. Two fixes: renew passport and re-enter, or file I-539/I-129 before 11/02. Draft to your attorney is ready." Second beat, unattended: the Visa Bulletin posts on the 12th; agent reads it, sees USCIS will honor Dates for Filing, your PD is now current, and pings "File I-485 this month. Here is the document checklist and the EAD/AP combo."

**Scores** U 5 · D 4 · A 3 · I 4 · Q 5

**Evidence**
- Backlog numbers (Dec 2025): https://www.businesstoday.in/nri/visa/story/179-year-wait-green-card-backlog-traps-nearly-1-million-indians-making-up-79-of-total-queue-551948-2026-08-28 ; Cato 1.8M (2023): https://www.cato.org/blog/18-million-employment-based-green-card-backlog
- Blind threads on I-94 shortened to passport expiry: https://www.teamblind.com/post/i-94-expiration-date-before-i-797-b-uogpvsnz , https://www.teamblind.com/post/passport-expiry-i94-mismatch-wq66kfac , https://www.teamblind.com/post/i-94-shortened-and-overstay-gt180-33bt4nzx
- USCIS Case Status API: https://developer.uscis.gov/api/case-status
- Lawfully (what exists today): https://www.lawfully.com/case-tracker

---

### 4. Class-action claims matched to your real purchase history

**Workflow today**
1. A settlement opens (100+ open at any time on ClaimDepot; 155 accepting claims per one 2026 tracker, ~50 with no proof of purchase).
2. You find out via a postcard, a spam-looking email, or a Reddit post.
3. You check eligibility (dates, products, states), dig up receipts or account emails, fill the administrator's form, e-sign an attestation, then wait 6 to 18 months for a $5 to $500 payment.

**Who, how often, stakes**
- FTC 2019 study of 149 consumer settlements: median claims rate 9%, weighted mean 4%; email-notice settlements 3%. Unclaimed money reverts to defendants, cy pres, or state funds.
- Payout app: 500K+ downloads, 300K+ claims filed, average payout ~$50 per claim; some users over $1,000 total. Top-10 settlements in 2025 exceeded $70B in total value.
- Recent examples with real money: Kroger prescription pricing (pro rata, deadline Dec 21, 2026), Autobell data breach (up to $5,000), Dr. Squatch ($0.50 to $12.50).

**Why still manual**
Administrators (Kroll, Epiq, Angeion, JND) each run their own web forms; there is no registry API; eligibility depends on facts only you have (did you buy X between dates Y and Z), and attestations are made under penalty of perjury, so blind auto-filing is both fraud-prone and (reportedly) under crackdown by administrators.

**Public data / APIs**
- Settlement listings: ClaimDepot, ClassAction.org, TopClassActions (scrape), and administrator sites (Playwright).
- CourtListener / RECAP API for the docket, settlement agreement, and claim deadlines (free API).
- Your side: Gmail receipts and account-creation emails ("Welcome to Cash App"), Plaid transactions.

**Existing tools and the gap**
- Payout (free, mobile), ClaimDepot (listings + newsletter), ClassActionBuddy (stores your details and autofills forms), MoneyPilot (claims to automate discovery to filing).
- Gap: none connect to your actual purchase/account history to (a) file only where you truly qualify, (b) prioritize proof-of-purchase claims that pay more, and (c) run silently with one attestation tap per claim. That attestation tap is exactly the "real decision" ping.

**The moment**
A new settlement posts (e.g., a retailer's pricing case). Agent searches the inbox, finds 14 qualifying orders in the class period, computes the estimated pro-rata payout, pre-fills the administrator's form with order numbers as proof, and pings: "You qualify for about $86. I filed nothing yet because you must attest. Sign?" Tap; Playwright submits; agent adds the 9-to-14-month payout to its watch list.

**Scores** U 3 · D 5 · A 3 · I 3 · Q 5

**Risk to name in the pitch**: fraudulent and bot-filed claims are a live issue for administrators (widely reported 2024 to 2025; verify with a current citation). Positioning "we only file what your receipts prove, and you sign every one" turns the risk into the differentiator.

**Evidence**
- FTC 2019 claims-rate study summary: https://www.carltonfields.com/insights/blogs/classified-the-class-action-blog/migrated/take-notice-ftc-reports-on-claims-rates-and-settlement-notices
- Payout (what exists): https://trypayout.app/
- ClaimDepot open settlements: https://www.claimdepot.com/settlements
- ClassActionBuddy autofill: https://classactionbuddy.com/settlements/

---

### 5. Medical bill audit + EOB reconciliation + No Surprises PPDR

**Workflow today**
1. Bill arrives; request the itemized bill with CPT/HCPCS codes (most people do not).
2. Match each line to the insurer's EOB (allowed amount, plan paid, patient responsibility); flag lines billed above the EOB, duplicates, unbundled or upcoded items, "services not rendered."
3. Compare to the hospital's own published negotiated rate for your payer (machine-readable file) or cash price; compare to the Medicare rate.
4. Call billing, write the dispute, escalate to the insurer appeal (internal, then external).
5. Self-pay: if the bill exceeds the Good Faith Estimate by $400+, file the federal Patient-Provider Dispute Resolution within 120 days with a $25 fee.

**Who, how often, stakes**
- KFF (2024 data): HealthCare.gov insurers denied 19% of in-network claims (85M of 451M); fewer than 1% of denials were appealed; 25% of denials were "administrative."
- Consumer surveys: half of respondents reported incorrect charges of at least $200; a quarter reported $500+; 41% "significantly frustrated" with the correction process (TechTarget summary of a consumer survey).
- The "80% of bills have errors" figure is industry lore (Medical Billing Advocates of America); use with care. AMA's older claims-processing error rate is 7.1%. HealthLock claims "over half."
- PPDR usage: CMS has not published patient-provider dispute volumes prominently (GAO's 490K figure is the provider-payer IDR, not PPDR). Treat PPDR as a near-unused consumer right.

**Why still manual**
Codes on the bill, the EOB, and the price file do not line up without work; CPT is AMA-licensed; hospital MRFs are huge and inconsistent even after the 2024 standard template; nobody sits between the inbox, the insurer portal, and the hospital's file.

**Public data / APIs**
- CMS Hospital Price Transparency MRFs: standard CSV/JSON template required since July 1, 2024 (all fields by Jan 1, 2025); schema and validator on GitHub: https://github.com/CMSgov/hospital-price-transparency
- DoltHub hospital-price-transparency datasets (1,000+ hospitals; state-of-data post Jan 2025).
- Turquoise Health Consumer Pricing API (negotiated rates, refreshed monthly): https://turquoise.health/api/docs/
- Medicare Physician Fee Schedule and HCPCS on data.cms.gov; NCCI bundling edits (public) to catch unbundling.
- No Surprises PPDR rules ($400 over GFE, 120 days, $25): https://www.congress.gov/crs-product/IF12338 and https://www.cms.gov/nosurprises/consumers/medical-bill-disagreements-if-you-are-uninsured
- Insurer EOBs: portal scrape or PDF/email parse; payer Transparency-in-Coverage files for allowed amounts.

**Existing tools and the gap**
- HealthLock ($27.99 to $34.99/mo): continuous claims monitoring across 250+ insurers, appeals help. Closest incumbent.
- Goodbill: hospital-bill review and negotiation, often via employers/TPAs (Sana), takes a share of savings.
- MyMedBill ($9.99/mo), IQBill, MedBillChecker: upload-a-bill AI reviewers.
- Counterforce Health (free, NIH-backed): appeal letters for denials, 75%+ success claimed.
- Gap: nobody reconciles bill vs EOB vs the hospital's own MRF line, and nobody routes self-pay patients into PPDR. But the space is crowded; uniqueness is the weak score.

**The moment**
Photo of an itemized bill. Agent OCRs the lines, pulls the matching EOB from the insurer portal, opens the hospital's MRF, and shows three lines side by side: billed $2,340, EOB allowed $910, hospital's own posted negotiated rate for that payer $910. "You are being balance-billed $1,430 you do not owe, plus a duplicate 'IV push' line. Dispute letter is drafted; send?"

**Scores** U 2 · D 4 · A 4 · I 5 · Q 4

**Evidence**
- KFF claims denials and appeals, 2024 data: https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/
- Consumer frustration with billing corrections: https://www.techtarget.com/revcyclemanagement/news/366600577/Consumers-are-Frustrated-with-Healthcare-Billing-Correction-Process
- CMS HPT template repo: https://github.com/CMSgov/hospital-price-transparency ; DoltHub state of data: https://www.dolthub.com/blog/2025-01-28-state-of-hospital-price-transparency-data/
- HealthLock (incumbent): https://www.healthlock.com/ ; Counterforce: https://www.counterforcehealth.org/

---

### 6. Security-deposit statutory clock

**Workflow today**
1. Two weeks before move-out: request the pre-move-out inspection (a statutory right in CA and NY) so you can fix deductions before they happen.
2. Move-out: photos, video, forwarding address in writing.
3. Wait for the landlord's itemized statement and refund: 21 days in California (Civ. Code 1950.5(h)), 14 days in New York (GOB 7-108).
4. If late or unexplained: demand letter citing the statute and the penalty (CA: up to 2x the deposit in statutory damages for bad faith; NY: landlord forfeits any right to retain any portion, plus up to 2x punitive damages for willful violation).
5. Small claims filing if ignored.

**Who, how often, stakes**
- Zillow 2024 renter survey (21,000+ renters): 87% paid a deposit; of movers, only 42% got the entire deposit back, 20% most, 20% some, 10% nothing.
- Rent.com 2024: 26% lost part of the deposit; 36% of those got no explanation.
- Renters who documented and told the landlord were most likely to get it all back (50%) vs the base rate.
- Stakes: typically one month's rent ($1,500 to $3,500 in big metros), doubled where penalties apply.

**Why still manual**
Deadlines and penalties vary by state, tenants do not know the inspection right exists, and the moment the clock lapses is invisible. DoNotPay marketed this and was fined $193K by the FTC (2024) for overclaiming its "robot lawyer."

**Public data / APIs**
- State statutes as primary sources: CA Civ. Code 1950.5 (leginfo), NY GOB 7-108 (nysenate.gov); comparable tables for other states.
- Inputs: lease PDF (dates, deposit amount, landlord contact), move-out photos, forwarding-address email.
- Outputs: inspection request email, demand letter, small-claims form pre-fill (county-specific PDFs).

**Existing tools and the gap**
- DoNotPay (demand-letter templates; FTC action), Roost (B2B deposit alternatives for property managers), tenant unions and legal-aid PDFs.
- Gap: no consumer agent runs the calendar: inspection request at T-14, evidence capture at T-0, statute deadline at T+14/21, demand letter at T+1 day past deadline, only pinging to approve sending.

**The moment**
Lease end date is in the calendar. Day 22 in California passes with no itemized statement. Agent, unprompted: "It has been 22 days. Under Civ. Code 1950.5(h) your landlord is late. Demand letter citing 1950.5(m) (up to 2x = $5,200) is drafted and addressed to the management company on your lease. Send, or wait a week?"

**Scores** U 3 · D 4 · A 4 · I 3 · Q 4

**Evidence**
- Zillow Consumer Housing Trends Report 2024 (renters): https://www.zillow.com/research/renters-housing-trends-report-2024-34387/
- CA Civ. Code 1950.5: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1950.5
- NY GOB 7-108: https://www.nysenate.gov/legislation/laws/GOB/7-108
- FTC v. DoNotPay (Sept 2024): https://www.ftc.gov/news-events/news/press-releases/2024/09/ftc-announces-crackdown-deceptive-ai-claims-schemes

---

## Not in the top 6, with the one number that says why

- Health-insurance denial appeals: Counterforce Health is free, NIH/Penn-backed, 75%+ success; Claimable and Fight Health Insurance also exist. Crowded. https://www.counterforcehealth.org/
- Property tax protest: Ownwell handled 127,298 Houston-area protests in 2025 (+94% YoY); 68% of Texas homes still do not protest and left $1.2B on the table; 8 in 10 protests succeed. Great data, dominant incumbent. https://www.ownwell.com/results/texas-protest-vs-non-protest
- Price drops / return windows / card warranties: Purchy (iOS, $12.99/mo) tracks return deadlines, price drops, warranties, subscriptions from Gmail + Plaid. Paribus is dead. https://www.purchy.ai/
- Travel compensation: DOT automatic-refund rule effective Oct 28, 2024; refunds were still the top complaint (1,881 of 6,448 in May 2025) and enforcement is paused on part of the rule until June 2026; AirHelp takes 35 to 50%. Saturated. https://www.transportation.gov/briefing-room/what-airline-passengers-need-know-about-dots-automatic-refund-rule
- FSA forfeitures: EBRI (3.2M accounts, 2022 data): about half forfeit, average $441. Real but small per person. https://www.ebri.org/content/new-analysis-of-3.2-million-flexible-spending-accounts-finds-average-contributions-increasing-while-half-forfeiting-funds-to-their-employers
- Death/estate admin: Empathy's Cost of Dying: 15 months of tasks (18 for executors), $12,616 average spend; Empathy is distributed through employers and insurers. High impact, not "quiet." https://www.empathy.com/costofdying
- Unclaimed benefits and property: NCOA says older adults miss $58B/yr across SNAP, SSI, MSP (9.1M eligible seniors not on SNAP); NAUPA says states hold $70B for 1 in 7 Americans and returned $4.49B in FY2024. Enormous, but benefit portals have no APIs and unclaimed property is a one-shot lookup. https://www.ncoa.org/article/the-58-billion-benefits-gap-affecting-older-adults/ ; https://unclaimed.org/annual-report-news/

## Recommendation
Build #1 (recall-to-remedy) or #2 (Medicare guardian). #1 has the cleanest demo: three live, keyless federal APIs and a receipt inbox, and the agent visibly moves before the owner knew. #2 has the biggest number ($31.7B improper payments, 69% never re-shop) and a synthetic-data sandbox that lets you demo real API calls without a real grandmother. #3 is the most unique and the most personal story for this founder, but the I-94 side has no API, so the demo leans on document parsing rather than a live feed.
