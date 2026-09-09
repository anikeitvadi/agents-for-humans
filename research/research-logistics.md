# Small-player logistics workflows still done by hand in 2026
## Research for an AWS "Agents for Humans" (Strands Agents SDK) entry

Date: 2026-09-08. Method: ~200 web searches plus primary-source fetches (OOIDA 2023 Detention Time Survey PDF, TruckersReport threads, CBP CAPE page, law-firm IEEPA briefs, vendor pages for gap checks). Reddit blocks direct fetches (403 on www. and old.), so driver-side primary evidence comes from TruckersReport and the OOIDA member survey instead of r/Truckers. Vendor-blog numbers are flagged as such.

---

## 0. The shortlist at a glance

| # | Workflow | Who | Stakes | Uniq | Demo | Data | Impact | E2E | Total |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Accessorial recovery (detention, lumper, TONU, layover) with escalation | Owner-operators, 1-20 truck fleets | $11.5B/yr industry; 14.3 hrs/wk waiting; 17% never paid | 3 | 5 | 4 | 5 | 4 | 21 |
| 2 | IEEPA tariff refund recovery through CAPE | Small importers, DTC brands | $165B pool, 330k importers; small ones priced out | 4 | 4 | 3 | 5 | 3 | 19 |
| 3 | Rejected produce load: inspection, salvage, claim defense | Reefer owner-operators, small produce brokers | $10k+ per rejected load; 3 days stranded | 5 | 4 | 3 | 4 | 3 | 19 |
| 4 | Rate-confirmation fine-print review and counter before signing | Owner-operators | $250 hidden fines; missing detention/TONU clauses | 3 | 5 | 4 | 4 | 4 | 20 |
| 5 | DataQs roadside-violation challenge | Small carriers | CSA score, insurance, broker approval; 39% win rate | 4 | 3 | 4 | 3 | 3 | 17 |
| 6 | Post-de-minimis cross-border returns duty recovery | Shopify/DTC sellers | Duty often exceeds product value; returns are a "triple loss" | 3 | 3 | 2 | 4 | 2 | 14 |

Considered and dropped (reason): FBA reimbursements (Getida, Carbon6, Refunzo are dominant; Amazon auto-reimburses 60-70%), duty drawback (Zollback is an AI SMB product already), oversize/overweight permits (oversize.io), dock appointment scheduling (Opendock shipped an MCP server June 2026; Loadsmart agents), restaurant multi-vendor ordering (Choco raised $211M and runs OpenAI voice agents; Cut+Dry, MarketMan), farm CSA routing (Local Line, CSAware, Farmigo), broker carrier-vetting and fraud (Highway, Carrier Assure, MyCarrierPackets), IFTA (Motive, Samsara, TenTrucks), Carmack cargo claims for small shippers (freightclaims.com, TLI managed claims; moderate but not unique). Broker non-payment bond claims are real and manual but are best folded into #1 as the escalation stage.

Ranking logic: #1 wins on demoability and end-to-end fit; #2 is the most timely (judges will have read the tariff-refund headlines); #3 is the most unique. #1 and #4 are the same persona and combine naturally into one "owner-operator revenue protection" agent (pre-sign review, live accrual, post-load collection) if you want one story with two lean-forward moments.

---

## 1. Accessorial recovery agent: detention, lumper, TONU, layover, then collections

**Workflow as done today**
1. Driver arrives at shipper/receiver; free time (usually 2 hrs) starts. Driver must capture proof: timestamped photo of the gate with truck visible, ELD screenshot, gate check-in receipt, in/out times written on the BOL and signed by the facility.
2. At the 2-hour mark, call or text the broker: "Free time expired, detention accruing at $X/hr per the rate con."
3. After delivery, build a separate detention invoice with the rate con (detention clause highlighted), arrival/departure evidence, and the math; submit within 48 hrs (many rate cons set 48-72 hr submission windows).
4. Lumper: pay at dock (Comcheck/EFS code or cash), get a receipt with facility name, BOL ref, signature; submit as an accessorial line within 48-72 hrs or the broker denies it.
5. Follow up at day 7 and day 14. Brokers deny on "no in/out times on BOL," "not in rate con," "late submission," or go silent.
6. If unpaid: demand letter, shipper escalation, FMCSA NCCDB complaint, BMC-84 surety bond claim (30-90 days, up to 6 months), small claims.

**Who, how often, dollars**
- OOIDA 2023 Detention Time Survey (n=253, Feb 2024): average 14.3 hrs/week waiting to load and unload; 49% "always" try to collect, 12% never; of those who never try, 44% say "I won't receive it anyway"; 17% receive no detention pay at all; of those who collect, only 32% collect on all loads and 50% on a quarter of loads; average collected $48-53/hr vs $80 members consider fair; 50% lose 1-2 loads per week to detention; 70% of own-authority owner-operators collect through the broker.
- ATRI (Sept 2024): detention costs the industry 135.9M hours and $11.5B per year; drivers lose $11k-19k/yr.
- Lumper: $25-500 per load, ~$280 average; an owner-operator doing 4-5 lumper deliveries a week spends $2k-5k+/yr; brokers lose $36k-96k/yr on unrecovered lumper receipts (Laneproof, vendor blog).
- Back office overall: ~10 hrs/week of paperwork for an own-authority operator (Advanced Trucking, vendor blog).

**Why still manual**
Proof has to be assembled retroactively from four sources (rate con PDF, ELD, photos, BOL), each broker has different clauses and deadlines, disputes are email/phone, and the escalation path (surety claim through FSC, NCCDB complaint) is a paper process. ELD vendors detect dwell but do not argue with brokers.

**Data and APIs**
- Motive API and Samsara API (OAuth/token; vehicle location, HOS, geofence events) for arrival/departure timestamps.
- Rate con and BOL PDFs (Amazon Textract works well here); Comcheck/EFS receipts.
- FMCSA QCMobile API (free webkey via Login.gov): broker/carrier authority, insurance. FMCSA L&I (li-public.fmcsa.dot.gov, HTML only): BMC-84/85 surety company and bond status for the escalation stage. FMCSA NCCDB: web form for broker non-payment complaints.
- NWS api.weather.gov (free) for layover/weather-delay justification.
- Email/SMS/voice: Amazon SES, SNS, Connect for the broker touchpoints.

**Existing tools and the gap**
DockClaim ($49/mo, owner-operators, GPS geofence, generates the invoice), DetentionIQ (50-200 truck fleets, Samsara/Motive, "proof that survives disputes," invoices), DMRG Detention Pay app, Add On Systems, Toro TMS. All detect and invoice detention only. None: read the rate con to know the clause and submission deadline, send the 2-hour notice, handle lumper/TONU/layover, rebut denials, follow up on a cadence, or escalate to shipper/FMCSA/surety. VAU0 (free AI dispatch) negotiates loads by phone but does not touch accessorials.

**The moment**
Live: a geofence event fires at hour 2:00 at "Walmart DC 6012." The agent pulls the clause from the signed rate con ("detention $50/hr after 2 hrs, must be reported before departure"), texts the broker the notice with the clause quoted, and keeps a running ticker. Then the broker's denial email arrives ("no in/out times on BOL") and the agent replies within seconds with ELD timestamps, the gate photo, and the rate con paragraph, and schedules the day-7 follow-up. Judges see money being defended in real time.

**Scores**: uniqueness 3, demoability 5, data 4, impact 5, end-to-end 4.

**Evidence**
- OOIDA 2023 Detention Time Survey (PDF): https://www.ooida.com/wp-content/uploads/2024/02/2023-Detention-Time-Survey-FINAL.pdf
- ATRI detention research (Sept 2024): https://truckingresearch.org/2024/09/new-research-documents-substantial-financial-and-safety-impacts-from-truck-driver-detention/
- As-done-today workflow and denial tactics: https://truckdispatchexperts.com/resources/detention-time-not-paid/
- Lumper workflow and failure modes: https://www.laneproof.com/blog/lumper-charges-explained-who-pays-liability-reimbursement
- Gap check: https://www.detentioniq.com/ and https://dockclaim.com/compare/detention-tracking-software
- Bond claim process and timelines: https://freightcollectionsolutions.com/navigating-the-bmc-84-bond-claim-process/

---

## 2. IEEPA tariff refund recovery agent for small importers (CAPE)

**Context (verified)**: Supreme Court held IEEPA tariffs unlawful in Feb 2026 (Learning Resources v. United States). CIT ordered refunds; CBP built the CAPE module inside ACE, live April 20, 2026. Refunds are not automatic: the Importer of Record (or its broker) must file a CSV of entry numbers through an ACE portal account. Government appealed to the Federal Circuit June 2-3, 2026, but Phase 1 refunds continue. As of July 31, 2026 (CBP declaration to the CIT, Aug 4): 75,000+ CAPE declarations, 25.1M entries accepted, 5.02M entries failed validation, 17.69M entries already liquidated without IEEPA duties, ~$128.68B potential/certified refunds. Total pool ~$165B across 53M entries and 330,000+ importers.

**Workflow as done today**
1. Figure out which entries carried IEEPA duties: look for chapter 99 secondary HTS lines (9903.01.xx / 9903.02.xx families) on each CBP Form 7501 entry summary, usually PDFs emailed by the broker.
2. Check each entry's status: unliquidated, liquidated within 80 days (Phase 1 eligible), reconciliation (Phase 2, opened June 29), finally liquidated (Phase 3, currently only for importers who sued at the CIT).
3. Prerequisites: active ACE portal account for the IOR, ACH refund enrollment with CBP (or Form 4811 notify party), valid POA if a broker files.
4. Build the CSV (entry numbers only, max 9,999 rows, under 1MB, apostrophe prefix for leading zeros), upload in ACE, watch for validation failures (open protests, drawback flags, entry types 23/08/09/047).
5. Track liquidation dates and the 180-day protest window for anything outside the current phase; decide whether to protest or file at the CIT (2-year clock running).
6. Wait 60-90 days; reconcile refund plus 19 USC 1505 interest against the 7501s.

**Who, how often, dollars**
- 330,000+ importers, "hundreds of thousands" of small businesses (NRF). Small DTC brands often have exposure spread across many low-value entries.
- Broker fee structures reported at roughly $200 for the first entry plus $125 per additional entry for recoveries under $5,000; professional services $500-2,000+/hr (FindCustomsBroker, vendor blog). FlavorCloud: "for a smaller importer looking at a few hundred or a few thousand dollars in potential refunds, the time and cost of completing those prerequisites can exceed the refund value."
- Skadden: CAPE "relies on importers to come forward and submit evidence" and warns "less sophisticated importers" may miss out.

**Why still manual**
Entry data lives in broker PDFs; ACE has no public API and was "built with licensed customs brokers and high-volume importers in mind"; eligibility depends on liquidation status and phase rules that keep changing; deadlines (80-day window, 180-day protest, 2-year CIT) are per entry.

**Data and APIs**
- Importer's own 7501s and broker statements (PDF; Textract), or ACE portal report exports (ES-001 style entry summary reports; portal only).
- USITC HTS REST API (free, no key): https://hts.usitc.gov/reststop/search?keyword=... for validating chapter 99 codes and base rates.
- CBP IEEPA refunds page and CSMS messages for the current phase rules; IRS overpayment interest rates (Federal Register, quarterly) for the 1505 interest estimate.
- No API to file CAPE; end-to-end stops at "validated CSV plus ACE upload walkthrough" or a broker hand-off email with POA.

**Existing tools and the gap**
Flexport, Avalara, UPS Supply Chain, Shapiro, and every mid-size broker offer CAPE filing as a paid service with minimums. Refund "calculators" (tariffstool, DutyPilot) estimate but do not read your entries. Nobody targets the small IOR who has a folder of 7501 PDFs, no ACE login, and a few thousand dollars at stake.

**The moment**
Drop 40 broker PDFs into the agent. Within a minute it shows: "37 entries with IEEPA lines, $14,312 in refundable duty plus ~$610 interest; 3 entries liquidate in 12 days and drop out of Phase 1; 2 entries are finally liquidated and need a protest by Oct 3." Then it produces the CAPE CSV, a prerequisites checklist (ACE, ACH, Form 4811), and a drafted broker email. Judges lean forward at the dollar figure and the deadlines.

**Scores**: uniqueness 4, demoability 4, data 3, impact 5, end-to-end 3.

**Evidence**
- CBP IEEPA Duty Refunds (CAPE rules, CSV format, validation): https://www.cbp.gov/trade/programs-administration/trade-remedies/ieepa-duty-refunds
- BDO FAQ with July 31, 2026 statistics: https://www.bdo.com/insights/tax/ieepa-tariff-refunds-frequently-asked-questions
- Holland & Knight on the appeal and phases: https://www.hklaw.com/en/insights/publications/2026/06/ieepa-tariff-refund-update-government-appeals
- Skadden ($165B, 330k importers, "less sophisticated importers"): https://www.skadden.com/insights/publications/2026/03/tariff-refund-mechanism-takes-shape
- FlavorCloud on small DTC importers being priced out: https://flavorcloud.com/resources/blog/ieepa-tariff-refunds-and-cape-declarations-what-importers-need-to-know-in-2026

---

## 3. Rejected produce load agent: inspection, salvage, claim defense

**Workflow as done today**
1. Receiver rejects all or part of a reefer load (quality, temperature, "chill damage"). Driver calls dispatch/broker and insurance.
2. Request a USDA/AMS inspection fast (SC-237 form; ~$350; inspections more than 2-3 days after arrival can be challenged as untimely). Pull the reefer download and any portable temperature recorder; take pulp temps.
3. Respond to the broker's "disposition" request: rework, re-deliver, salvage, or dump. Delays get the driver blamed and claims denied.
4. Salvage: find a wholesaler near a terminal market willing to take the product on consignment; they must later provide an itemized accounting (15% commission allowed; storage and undocumented dumping fees disallowed).
5. If dumped: landfill charges by weight; keep receipts to bill back.
6. Claim fight: broker withholds freight pay against the claim; carrier must show BOL temperature instructions were followed, reefer logs, USDA grade, prior clean runs.

**Who, how often, dollars**
- TruckersReport thread (2025): small carrier, lettuce load, 75% rejected for "chill damage," claim over $10,000, salvage $1,900, broker (TQL) withheld $5,000+ from other loads; carrier had reefer logs, pulp temps 32-34F, and a USDA inspection grading US No. 1. Forum advice: "avoid fresh produce loads for this very reason."
- TruckersReport thread (rejected broccoli, TX to GA/NC): driver stranded nearly 3 days across a weekend, drove 200 extra miles, "I've been waiting for 6 hours for the broker to figure out with his client how to get rid of the product," "I'm losing money by the minute." Top answer: landfill, bill ~$1,100 disposal to the broker.
- Reefer is 20% of OOIDA respondents' primary equipment; refrigerated freight is 20% of primary freight.

**Why still manual**
Time-critical (hours, over weekends), multi-party (shipper, broker, receiver, USDA, wholesaler, insurer), PACA does not cover carriers so there is no dispute mechanism for them, and the evidence (reefer telematics, BOL instructions, inspection certificate) lives in different systems. Nobody has built for the carrier side.

**Data and APIs**
- USDA MARS API (free key; base https://marsapi.ams.usda.gov/services/v1.2): terminal market and shipping point prices to set a salvage floor and value the loss.
- USDA PACA license search (HTML; data.gov listing) to find licensed wholesalers/brokers near the rejection point.
- USDA AMS SCI inspection offices and SC-237 form (no API; form plus phone).
- Reefer telematics: Thermo King TracKing, Carrier Transicold APIs, or the unit's downloaded PDF; ELD via Motive/Samsara.
- NWS weather; Google/HERE for nearest terminal markets and landfills.

**Existing tools and the gap**
Blue Book Services (paid credit and PACA data for produce traders), Produce Blue Book "Trading Assistance," transload/rework warehouses, insurance adjusters. Broker-side TMSs log claims. No product runs the carrier's playbook: inspection request, salvage sourcing, disposition plan, and claim-defense packet.

**The moment**
"Receiver rejected 18 pallets of romaine at Hunts Point, 4:40 pm Friday." The agent pulls the reefer log (set 34F per BOL, held 33-35F), files the SC-237 inspection request for Saturday morning, lists three PACA-licensed wholesalers within 15 miles with today's MARS terminal price for romaine, drafts the disposition message to the broker with the salvage floor, and starts a claim-defense file. The judge sees a weekend disaster turned into a plan in 60 seconds.

**Scores**: uniqueness 5, demoability 4, data 3, impact 4, end-to-end 3.

**Evidence**
- TruckersReport reefer produce claim thread: https://www.thetruckersreport.com/truckingindustryforum/threads/reefer-produce-claim.1771440/
- TruckersReport rejected broccoli thread: https://www.thetruckersreport.com/truckingindustryforum/threads/rejected-load-due-to-bad-produce.1525044/
- Blue Book: reefer carriers and PACA (inspection timing, salvage accounting): https://www.bluebookservices.com/blueprints/reefer-carriers-and-paca-what-freight-folks-need-to-know/
- USDA MARS API: https://mymarketnews.ams.usda.gov/mymarketnews-api
- PACA search: https://www.ams.usda.gov/rules-regulations/paca/licensing

---

## 4. Rate-confirmation fine-print review and counter before signing

**Workflow as done today**
1. Broker emails a rate con PDF, often 2-6 pages of terms. Driver is expected to sign within minutes to hold the load.
2. Driver skims for rate, pickup/delivery windows, and maybe detention. Misses: tracking-app mandates with fines, late-fee schedules, no-TONU clauses, 24-hour POD deadlines, lumper caps, "detention only with signed in/out times," offset/withholding rights against other loads.
3. If a term is bad, driver calls the broker and negotiates verbally; corrections must come as a revised rate con, which brokers often never send.

**Who, how often, dollars**
- Every load for an own-authority owner-operator: 4.69 loads/week per truck (OOIDA mean).
- TruckersReport "Macropoint $250 fine" thread: "Macropoint must be activated 2 hours prior to pickup, otherwise carrier is subject to a $250 fine." "I rejected the load, btw, after I saw that."
- Industry guidance: "If you sign it, you've agreed to every word, even the stuff you didn't read"; "a missing line in the rate confirmation can cause carriers to lose their week."
- Per-mile pay fell 10% in 2023 ($2.61 to $2.36), so accessorial terms are a bigger share of margin.

**Why still manual**
PDF terms vary by broker, the negotiation is phone/email under time pressure, and the carrier has no template of their own "floor terms." Load boards show rate, not clauses.

**Data and APIs**
- Rate con PDFs (Textract or LLM parsing). Carrier's own term sheet (detention rate, free time, TONU, layover, tracking policy).
- Market rate context: DAT RateView (developer portal account, partner approval; setup fee reported $500-1,000 by third parties), Truckstop partner API, or 123Loadboard API (usage agreement forbids analytics/data-mining). For a demo, use the carrier's own history or a cached lane rate.
- FMCSA QCMobile for broker authority age and status; L&I for bond.

**Existing tools and the gap**
VAU0 (AI voice agents negotiate loads by phone, free through 2026), HappyRobot and Fleetworks (broker-side voice agents), truckercalc rate-con checklists (static). None parse the signed document and redline it against the carrier's floor.

**The moment**
Rate con lands in the inbox; 20 seconds later the agent returns a redline: "$250 Macropoint fine (strike), detention $25/hr after 4 hrs (counter: $50 after 2), no TONU (add $150), POD due in 24 hrs (change to 48)," with a drafted reply and a "do not sign" flag. Then it books the negotiation call or sends the counter. Pairs directly with #1: the same terms drive the accrual clock.

**Scores**: uniqueness 3, demoability 5, data 4, impact 4, end-to-end 4.

**Evidence**
- TruckersReport Macropoint $250 fine thread: https://www.thetruckersreport.com/truckingindustryforum/threads/macropoint-250-fine.321143/
- FreightWaves "How to read your rate con like a pro": https://www.freightwaves.com/news/how-to-read-your-rate-con-like-a-pro
- Owner-operator rate con checklist: https://logitydispatch.com/blog/rate-confirmation-checklist/
- Gap check (VAU0 scope): https://vau0.com/owner-operators.html

---

## 5. DataQs roadside-violation challenge agent for small carriers

**Workflow as done today**
1. Roadside inspection produces a report with violations (49 CFR 393, 396, 395). Violations flow into FMCSA SMS and the carrier's CSA BASICs, which affect insurance premiums and broker approval.
2. Carrier decides whether to challenge via DataQs (dataqs.fmcsa.dot.gov): must identify the factual or regulatory error (e.g., windshield crack outside the 393.60(c) exception; tire tread measured at the wrong location), gather evidence (photos, repair receipts, driver statement, video), and write a Request for Data Review.
3. Submit within 30 days for best odds; the state agency responds in 10 days nominally, "one week to three months" in practice; may need to appeal.

**Who, how often, dollars**
- Only 39% of violation challenges succeed (FMCSA data cited by Overdrive); carrier service providers win ~60% on crash reviews vs 43% for drivers.
- "If your appeal amounts to nothing more than your word against the officer's, there's a 99% chance that it will be denied." Small carriers pay compliance consultants (CNS, Reliance Partners, CDL Consultants) to file.
- Indirect stakes: CSA scores drive insurance renewals and broker vetting, which are now stricter after Montgomery v. Caribe Transport II (May 14, 2026) removed brokers' preemption defense in negligent-selection suits.

**Why still manual**
Requires reading the regulation and its exceptions, matching them to inspection-report details, and assembling evidence; the DataQs portal is form-based; small carriers do not know which violations are worth contesting.

**Data and APIs**
- FMCSA QCMobile API (free webkey): carrier BASICs, inspection and crash summaries.
- FMCSA SMS data downloads (monthly), eCFR API (ecfr.gov/api) for 49 CFR text, CVSA out-of-service criteria (paid PDF).
- Inspection report PDF and photos (Textract); DataQs portal (no API; submission is the human step).

**Existing tools and the gap**
Consultants and compliance services; Trucksafe and CNS guides; no agent that scores challenge-worthiness and drafts the RDR with citations.

**The moment**
Upload an inspection report; the agent flags "393.75(a)(3) tire tread: officer measured at the edge; regulation requires major tread groove," pulls the eCFR text, asks for the tire photo, drafts the RDR, and predicts the odds. Good, but a portal screenshot is less visceral than money moving.

**Scores**: uniqueness 4, demoability 3, data 4, impact 3, end-to-end 3.

**Evidence**
- Overdrive on DataQs win rates: https://www.overdriveonline.com/partners-in-business/safety-compliance/article/15737200/how-to-win-dataqs-challenges-remove-bad-violations-improve-csa-scores
- Trucksafe "5 tips" (30-day window, evidence): https://trucksafe.com/post/5-tips-for-a-successful-dataqs-appeal
- FreightWaves (10-day target vs one week to three months): https://www.freightwaves.com/news/how-to-successfully-dispute-violations-with-dataqs
- FMCSA QCMobile API docs: https://mobile.fmcsa.dot.gov/QCDevsite/docs/qcApi

---

## 6. Post-de-minimis cross-border returns duty recovery for small DTC sellers

**Context (verified)**: US de minimis suspended for all countries Aug 29, 2025; CBP made it permanent by regulation June 24, 2026; statute terminates it July 1, 2027. The Supreme Court's IEEPA ruling did not restore it. Every inbound parcel now needs a 10-digit HTS classification and duty; a $12 product from China can carry $14-24 in duties and fees plus $2-5 brokerage (vendor estimates).

**Workflow as done today**
1. Customer returns an item across a border. Seller eats the original duty, the return shipping, and the sale. Recovery requires proving the goods physically left, matching the original import entry to the return, and filing with the right authority: Canada Casual Refund Program or NRI process; UK/EU VAT via IOSS for low-value returns and formal customs claims above thresholds; US HTS 9801.00.10 for returned US-origin/previously exported goods (commercial shipments only; postal returns no longer qualify).
2. Most sellers do not have the entry documents because a 3PL or carrier was the importer of record ("the party with standing lacks the capacity to claim; the parties with capacity lack the standing").

**Who, how often, dollars**: Shopify/Etsy/DTC sellers shipping cross-border; returns run 15-30% in apparel. No public survey of recovery rates was found; Passport and Zonos describe "weeks to months" timelines and say most merchants skip it.

**Why still manual**: fragmented per-country rules, documents held by carriers/3PLs, formal customs procedures.

**Data and APIs**: USITC HTS API; carrier APIs (UPS, FedEx, DHL) for shipment and customs docs; Shopify Admin API for orders and returns; Zonos/Passport landed-cost APIs; CBSA and HMRC forms (no APIs).

**Existing tools and the gap**: Zonos, Passport, Swap, FlavorCloud, Global-e handle landed cost and DDP; ClaimLane and Passport publish guides. Refund recovery on returns is largely unserved for small sellers, but it depends on brokers and postal channels the agent cannot drive.

**The moment**: agent matches a Shopify return to its original entry, determines the recovery path, and produces the filing packet. Demo is document-heavy and slow to show.

**Scores**: uniqueness 3, demoability 3, data 2, impact 4, end-to-end 2.

**Evidence**
- Passport, recovering duties and taxes on international returns: https://passportglobal.com/blog/recovering-duties-and-taxes-on-international-returns-us-ecommerce-merchants/
- CBP on HTS 9801.00.10 requirements: https://www.cbp.gov/trade/programs-administration/entry-summary/hts-subheading-9801
- De minimis status 2026: https://blog.ordoro.com/2026/02/25/de-minimis-exemption-2026/
- Zonos docs on duty refunds for returns: https://zonos.com/docs/guides/country-guides/united-states/returns-and-duty-and-tax-refunds

---

## 7. Other candidates researched (not in top 6)

- **FBA reimbursements with cost documentation** (sellers): since March 31, 2025 Amazon reimburses at manufacturing cost with a 60-day claim window and requires supplier invoices; auto-reimbursement catches 60-70% of eligible cases; 1-3% of revenue recoverable. SP-API report types: GET_FBA_REIMBURSEMENTS_DATA, inventory ledger/adjustments (codes E1, E3, E7, M). Gap is small: Getida, Carbon6, Refunzo, Seller Labs. Uniqueness 1.
- **Broker non-payment collections and bond claims** (carriers): freight fraud $500M-1B/yr; FMCSA got 8,000+ double-brokering complaints in 2025; bond claims via FSC take 30-90 days, up to 6 months; broker fines rise to $50k per violation with new rules phasing in by Jan 2027. Fold into #1 as the escalation stage.
- **Duty drawback for SMBs** (importers/exporters): $11-15B unclaimed annually, ~80% of eligible refunds unclaimed, legacy providers require $100k+ refund potential; but Zollback already markets an AI SMB platform. Uniqueness 2.
- **Restaurant multi-vendor ordering**: orders still arrive as texts, voicemails, photos of handwritten notes (Choco), but Choco ($211M raised, OpenAI voice agent), Cut+Dry, MarketMan, Notch cover it. Uniqueness 1.
- **Oversize/overweight permits**: each state has its own portal (TxPROS, MPG, MoDOT Carrier Express); oversize.io prices permits and routes. Uniqueness 2.
- **Dock appointment scheduling**: Opendock MCP server live June 2026; Loadsmart scheduling agent. Uniqueness 1.
- **Farm CSA routing**: Local Line, CSAware, Farmigo generate route-sorted manifests. Uniqueness 1.
- **Carmack cargo claims for small shippers**: 9-month filing floor, 30-day carrier acknowledgment, documentation-heavy; freightclaims.com and managed-freight providers exist. Uniqueness 2.

---

## 8. Practical notes for the build

- Reddit is not fetchable from this environment; if you want r/Truckers quotes for the pitch deck, pull them by hand. TruckersReport threads above are quotable.
- Load-board APIs are partner-gated (DAT developer portal, Truckstop, 123Loadboard usage agreement bans analytics). Do not make the demo depend on them; use the carrier's own documents and FMCSA/USDA/USITC public APIs, which are free.
- ACE, DataQs, and USDA inspection requests have no APIs. Make the agent stop at a "ready to submit" artifact plus a human-in-the-loop confirm, and show that step honestly in the demo; the judges' brief is "real work end to end," and a visible approval gate reads as trust design rather than a gap.
- AWS-native pieces that map cleanly: Textract for 7501s, rate cons, BOLs; Location Service for geofences if you do not have Motive/Samsara access; Connect or SNS for the broker text/call; Bedrock for the model; EventBridge for the 2-hour timer.
