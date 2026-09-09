# Idea trail (what was proposed, and the verdict), Sep 8 to 9

Kept so nobody re-litigates. Ranked board with evidence: `docs/draft-board.html` (open in a browser).

## Existing projects, checked against "new agent that does real work"
- **jobsearch-cli** (public, created Sep 8, inside the window): everything under an agent exists (profile, three board APIs, scoring, posting reader, outreach drafting with voice rules, SQLite pipeline). A Strands agent on top would be a new agent. Verdict: the safe entry; not unique enough for what we want.
- **agent-arena** (Desktop, private): multi-model orchestration framework + benchmark. Its own verdict: "quality holds at parity, total cost rises." Infrastructure, not an agent for people. Good negative-result story elsewhere. No.
- **generation_framework** (home dir, Python): ExperienceProfile research rig, 40% through v1, paused July 5. One reusable angle: the "production-burned API integrator" profile + integration-plan failure checklists = an integration plan reviewer. Interesting, abstract demo. No for this week.
- **Parity / moneylines** (tennis + NFL value-betting lab, git-excluded on purpose, real tickets): NO as an entry (gambling, live litigation over sports contracts, real bankroll). YES as the decision engine inside whichever entry: calibration loop (every call scored, model earns weight by beating the baseline), breakeven-as-contract decision rule, overlays-with-source-tags from research agents, calls journal. Disclose any reused scripts. Keep the data private.

## Fresh ideas proposed, in order
1. Unpaid wages to a filed claim (Good Neighbor). Rejected by Ani as generic.
2. Front desk for a small service business (Good Neighbor). Crowded.
3. Rehearsal coach (Everyday). Common.
4. Integration plan reviewer (Professional). Abstract.
5. **Storm dispatch swarm** for a Houston neighborhood: intake, planner, dispatcher, monitor, auditor agents on live NHC/TxDOT feeds + Amazon Location Service, re-planning on road closures. Coolest video, biggest build. Ani didn't bite; partner read the brief as "everyday personalized tasks, not large scale."
6. "Paste any official letter, get a process" (statutory-rights engine with clocks + citation auditor). Generic per Ani.
7. Medication access navigator (patient side of the Forus problem). Sensitive.
8. Audit-then-deploy for a local business. Meta.
9. Logistics set: owner-operator dispatcher negotiating with brokers; job-shop quoting from drawings (later cut by research: crowded); food-bank closed loop; recall/warranty guardian; clinical trial matcher; visa status guardian; agents negotiating with agents (A2A).

## Ani / partner input
- Partner: Everyday track, "everyday personalized tasks." Liked: health agent (book appointments, supplements), DoorDash deals+macros, visa guardian ("international students have questions, flurries of policy changes").
- Ani: likes the visa idea, worried it's narrow. Expansion given: (1) all statuses + dependents, (2) policy events → personal consequences (visa bulletin, Federal Register fee rules, travel checks), (3) every government clock (DMV, passport, licenses, Medicaid/SNAP renewals, FAFSA, estimated taxes). Pitch: "everyone has clocks."
- Health: **peptides = no** (liability). **Supplements "what to buy" = no** (recommendation, crowded); only an interaction check against real prescriptions is defensible. **Doctor appointment getter that beats ghost networks = real** (a third to half of directory listings are wrong; agent calls offices, verifies plan + new patients, books, prefills intake). Not yet researched with evidence.
- **DoorDash deals + macros = dead** (no consumer ordering API, terms forbid automation, nutrition data sparse). Flip: delivery-platform reconciliation for restaurants (Professional). Not researched.

## Research (five parallel passes, Sep 8, ~30 candidates)
Full reports in `research/`. Top tier after re-ranking for a 4-day, 2-person build and a 5-minute video:
1. Immigration status guardian (Everyday, U5)
2. Recall-to-remedy (Everyday, 23, all feeds live)
3. Aging-parent Medicare guardian (Everyday, 23, heaviest build)
4. Pantry sorting-table agent (Good Neighbor, 23, U5)
5. DataQs violation challenge (Professional, found by 2 lanes, live on any USDOT number)
6. Detention recovery + rate-con redline (Professional)
7. Tariff refund recovery (Professional, found by 2 lanes, pending appeal risk)

**Recommended build:** one engine that reads the government so you don't have to. Modules: immigration clocks (flagship, the story only we can tell) + product recalls (universal, cleanest live demo). Both Everyday, both quiet-until-a-decision, both verified public feeds.

## Status as of Sep 9 morning
No idea chosen. Partner leaning Everyday. Next: pick, then skeleton + architecture diagram, credits claimed by Thu noon PT, Builder IDs, submit Mon by noon.
