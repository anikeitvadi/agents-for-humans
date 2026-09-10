# Clockwork — Architecture Spec

*One engine that reads the government so you don't have to.*

**Hackathon:** Agents for Humans (AWS · Strands Agents SDK) · **Track:** Everyday
**Build window:** 4 days, 2 people · **Submission:** Mon Sep 14, 5:00pm PT (target: submit by noon)
**Modules shipped:** Immigration status guardian (flagship, full build) · Recall-to-remedy (thin generality proof, ~20% effort: one feed, one seeded receipt, one match, one ping)

> Naming note: "Clockwork" is a placeholder — pick your own. The pitch line is *"everyone has clocks; missing one costs you your license, your coverage, or your right to stay. This agent runs them quietly and only talks to you when there's a real decision."*

---

## 1. The thesis, stated as an architecture

Every problem in both modules has the same shape:

1. A **document or obligation** you own that has a hidden or moving deadline.
2. A **public source of truth** the government or an agency publishes.
3. A **rule** that turns (1) + (2) into a personal consequence.
4. A **window** in which acting is worth real money or status.

So the system is not "an immigration app." It is **one loop** — *watch official sources, match them to the user's documents, evaluate the rule, act, and ping only on a real decision* — with **domain packs** plugged into it. Immigration is the full build; recalls is a thin second pack (one feed, one seeded receipt, one match, one ping) that exists only to prove the loop is generic, not domain-specific to visas. Everything shared between them — the rules engine, the decision gate, the ledger schema — differs only in which feeds a pack polls, which documents it parses, and which rules it runs. This is what lets two people ship a real flagship and a credible generality proof in four days, and it's the single most important thing the architecture has to make visible to a judge.

---

## 2. Core design principles

- **The ping is the product.** The theme is "surfaces only when there's a real decision." Restraint is a scored feature, not a UX nicety. Every surfaced item must clear a decision gate (see §6). The demo must show the agent silently handling many things and interrupting for one.
- **Decision-support, not advice.** The agent surfaces clocks and the governing rule, and drafts a message *to the user's attorney or to the remedy form*. It never tells someone they are "safe to travel" or gives legal advice. This boundary is stated in the UI and in the demo. (The board already learned this from the DoNotPay/FTC example — apply it hardest to immigration.)
- **Everything runs on a schedule, unattended.** The differentiator over every calendar/reminder app is that the agent reacts to *the world's* changes, not just the user's dates. That means scheduled polling of external feeds is the heart of the system, not an add-on.
- **Live where it counts, cached where it's risky.** Recall feeds are unauthenticated live JSON — demo them live. Immigration's I-94 has no API — that step is document parsing by design, and the visa-bulletin beat runs off a real captured bulletin so a demo-day network blip can't kill the flagship moment.
- **One state model, one engine, two packs.** No forked codebases.

---

## 3. System overview

```
                 ┌───────────────────────────────────────────────────┐
                 │                   USER SURFACE                     │
                 │   Web dashboard  ·  "one thing that needs you"     │
                 │   photograph docs · approve/deny a drafted action  │
                 └───────────────────────────┬───────────────────────┘
                                             │ (JWT via AgentCore Identity)
                 ┌───────────────────────────▼───────────────────────┐
                 │              AGENTCORE RUNTIME                     │
                 │        Strands agent (the shared engine)           │
                 │                                                    │
                 │   ┌────────────┐   ┌───────────────────────────┐  │
                 │   │ Orchestrator│──▶│  Domain packs (pluggable) │  │
                 │   │  (Strands   │   │  • immigration            │  │
                 │   │   agent     │   │  • recalls                │  │
                 │   │   loop)     │   │  (each: feeds+parsers+    │  │
                 │   └─────┬───────┘   │   rules+draft templates)  │  │
                 │         │           └───────────────────────────┘  │
                 └─────────┼──────────────────────────────────────────┘
                           │ tool calls (MCP)          ▲
                 ┌─────────▼───────────┐               │ read/write
                 │  AGENTCORE GATEWAY  │        ┌──────┴───────────┐
                 │  external APIs +    │        │ AGENTCORE MEMORY │
                 │  Lambda tools as    │        │ short-term:      │
                 │  MCP tools, w/ auth │        │  session context │
                 └─────────┬───────────┘        │ long-term:       │
                           │                    │  user clocks,    │
        ┌──────────────────┼─────────────┐      │  docs, prefs,    │
        ▼                  ▼             ▼      │  ping history    │
  ┌───────────┐    ┌─────────────┐  ┌────────┐ └──────────────────┘
  │ USCIS case│    │ Federal     │  │ CPSC / │
  │ status API│    │ Register API│  │ NHTSA /│         ┌──────────────┐
  │           │    │ visa bulln. │  │openFDA │◀────────│  SCHEDULER    │
  └───────────┘    └─────────────┘  └────────┘         │ EventBridge   │
                                                       │ cron → async  │
  ┌─────────────────────────────────┐                  │ Runtime invoke│
  │  Document parsing (I-94, EAD,    │                 └──────────────┘
  │  receipts) — Bedrock multimodal  │
  └─────────────────────────────────┘
```

Cross-cutting: **AgentCore Observability** (OTEL traces → CloudWatch) and **AgentCore Policy** (Cedar gates on any tool that drafts/sends) sit across the Gateway and Runtime. Draw them as a band, not a box in the flow.

---

## 4. Component-by-component

### 4.1 Build order — local first, AgentCore only if Days 1–2 land
The engine and both packs are built and demoed as a **plain Strands agent running locally** first: no AWS dependency, tool calls are plain Python functions hitting the feed APIs directly, scheduling is a loop or a cron on a laptop/EC2 box, state is a JSON file or SQLite with the §5 schema. This is Day 1–2 work and must produce a working demo on its own.

AgentCore Runtime deployment is **Day 3 work, attempted only if Days 1–2 are done**. Before any scaffolding: spend the first hour of Day 1 reading current AgentCore Runtime docs and confirming what deployment actually requires — the details below (invocation modes, Gateway/Memory/Policy behavior) were drafted from general knowledge of the AgentCore docs, not verified against them, and may not match what's live today.

If Day 3 happens: host the same Strands agent in AgentCore Runtime (documented happy path for Strands; "deployed on AgentCore" is a stated Technical Implementation booster), with interactive (`InvokeAgentRuntime`, document upload/approval) and asynchronous/scheduled (the background poll) invocation modes.

### 4.2 The orchestrator — deterministic control flow, LLM as subroutine
**The evaluate→gate→persist ordering is enforced by application code, not by an LLM's plan.** Earlier drafts of this spec said "let the model plan tool use rather than hardcoding flowcharts" and separately "the model's only jobs are extraction and drafting" — those two statements conflict, and application code resolves the conflict in favor of the second one. `agent/engine/engine.py::process_event` is a plain Python function: validate → evaluate rules → run the decision gate → persist → only then hand off to drafting. A prompt is never the only thing standing between a bad input and a persisted alert.

- **Deterministic core** (`agent/engine/`) — `schema.py` (Clock/Event/Alert), `store.py` (SQLite, replay-safe dedup), `decision_gate.py` (the four predicates), `engine.py` (the control flow above). Domain-agnostic; used by both packs.
- **Domain packs** (`agent/packs/immigration/`, `agent/packs/recalls/`) — each pack owns which feeds it polls, which document fields it parses, its rules module (deterministic), and its draft framing. Adding a third clock later = add a pack, touch nothing in `engine/`.
- **LLM subroutines** (`agent/llm/`) — `extract.py` (document field extraction via the raw Bedrock Converse API with multimodal document blocks — the AWS-recommended path for this, not routed through Strands) and `draft.py` (composing the attorney message around a deterministic, always-present safety-boundary core the LLM cannot edit — `build_attorney_draft` invokes a genuine `strands.Agent` for the personalized intro only, via `build_bedrock_agent()`, and falls back to the deterministic core if no AWS credentials are configured or the call fails). These are the two places genuine model reasoning happens; the deterministic pipeline calls them, not the other way around.
- Status math (I-94/I-797 discrepancy — pure date arithmetic) and bulletin-cutoff checks are plain functions with unit tests (`tests/test_immigration_rules.py`), verified against primary sources, not against what an LLM remembers about immigration law. Every surfaced output is framed as "flag for your attorney" — never "you're safe" or "you should file." A wrong bulletin-chart read or a wrong day count on stage is the failure mode that discredits the whole project.

### 4.3 Tool contracts — external world
These are plain Python functions in the build (Days 1–2); if Day 3's AgentCore deploy happens, the same contracts move behind AgentCore Gateway as MCP tools with brokered auth. Either way, the contract shape is what matters — normalize outputs (same shape for all three recall sources, etc.) so one rules engine can consume every feed.

| Tool | Backing source | Auth | Module |
|---|---|---|---|
| `uscis_case_status` | USCIS case status API (sandbox 1K/day, prod 150K/day) | API key | immigration |
| `federal_register_search` | Federal Register API (public) | none | immigration |
| `visa_bulletin_fetch` | State Dept visa bulletin (captured, not live-scraped) | none | immigration |
| `cpsc_recalls` (or one recall source, whichever is cleanest) | CPSC/NHTSA/openFDA recall JSON | none | recalls (thin pack — one source is enough) |
| `parse_document` | Bedrock multimodal call (I-94, EAD, receipt) | API creds | shared |
| `draft_message` | Template + model fill (attorney email, remedy form) | — | shared |

### 4.4 State — the clock ledger
The persistent brain, and the reason the agent is more than a cron job: every tracked document, its parsed dates, derived deadlines, the rules that apply, and **ping history** (what was surfaced, what the user decided — feeds the decision gate so nothing already-dismissed re-surfaces). For the build this is a local JSON file or SQLite table matching the §5 schema — no AgentCore Memory dependency. Namespacing per user only matters once there's more than one demo user, which there isn't.

### 4.5 Scheduler
A cron job or a loop with a sleep, invoking the poll on a cadence per feed: recall source a few times daily, visa bulletin around the captured publication date, Federal Register daily. Each run iterates the clock ledger, calls the tool contracts, and runs the decision gate — this produces the "the bulletin dropped and the agent acted while you slept" demo beat without needing EventBridge.

### 4.6 Production path (not built — README + diagram only)
Identity (Cognito), Policy (Cedar gating on outbound actions), Memory (AgentCore managed extraction over DynamoDB), Observability (OTEL → CloudWatch), and Gateway-brokered auth are real requirements for shipping this beyond a hackathon demo. They get one paragraph and a box on the architecture diagram, not build time: judges reward the diagram, and each of these is a multi-day integration on its own, unverified against current docs. Naming them shows the team knows the gap between demo and production without spending the two days it would cost to close it.

---

## 5. Data model (the clock ledger)

One schema serves both modules. This is the concrete form of "one engine."

```jsonc
// Clock — one tracked obligation
{
  "clock_id": "uuid",
  "user_id": "cognito-sub",
  "module": "immigration | recalls",
  "source_doc": {                 // what the user gave us
    "type": "i94 | ead | receipt | vin | ...",
    "parsed_fields": { "...": "..." },
    "storage_ref": "s3://.../doc"
  },
  "derived": {                    // what the rule computed
    "deadline": "2026-11-03",
    "window_opens": "2026-09-15",
    "rule_id": "i94_status_vs_i20 | price_protection_30d | ...",
    "consequence": "3-year bar if 180+ days overstay",
    "value_at_stake_usd": 218      // recalls; null for status clocks
  },
  "watch": {                      // which feeds can change this clock
    "feeds": ["visa_bulletin", "federal_register"],
    "match_keys": { "priority_date": "2019-05-01", "category": "EB2-India" }
  },
  "state": "quiet | window_open | action_drafted | awaiting_user | resolved",
  "ping_history": [
    { "ts": "...", "reason": "...", "user_decision": "approved|dismissed|snoozed" }
  ]
}
```

- A **feed event** (recall published, bulletin posted) is matched against every clock's `watch.match_keys`. A hit moves the clock's `state` and may open a window.
- The **decision gate** reads `state` + `derived.window_opens` + `ping_history` to decide surface-vs-stay-silent.

---

## 6. The decision gate (why it stays quiet)

A surfaced item must pass all of:

1. **Materiality** — real dollars or real status consequence attached (`value_at_stake_usd` above a floor, or a status/legal consequence present).
2. **Actionability** — there is a specific action the user can take now (a form to file, an email to approve, an appointment to book).
3. **Window** — the action's window is open or opening soon; nothing gained by pinging earlier.
4. **Novelty** — not already surfaced-and-dismissed for the same event (checked against `ping_history`).

Fail any → the agent updates the ledger silently and says nothing. Pass all → it drafts the action and surfaces exactly one card. In the demo, narrate this: show three things processed, two staying silent (fail the gate), one surfacing.

---

## 7. The two modules, concretely

### Immigration status guardian (flagship — the full build)

**Scope correction (2026-09-10):** this module does **not** compute lawful-status length, F-1/OPT timelines, or unlawful-presence bars — that domain logic is deferred to a later iteration (too much unresolved legal surface for this deadline; see HANDOFF.md). What ships now: a **document-date discrepancy check** between the I-94 and the I-797, framed as an arithmetic fact flagged for attorney review, never a legal conclusion.

- **Onramp:** user photographs 3 PDFs — **I-94, I-797, passport** (not I-20/EAD — this is the H-1B case, and passport expiry is what drives the discrepancy). `agent/llm/extract.py` extracts dates via Bedrock, with per-field evidence and explicit missing/ambiguous handling (a `needs_review` result on any ambiguous critical field, never a confident guess).
- **Flagship beat:** "Your I-94 admit-until date and I-797 validity end date disagree by 55 days" — CBP cut the I-94 to the passport expiry. This is **pure date arithmetic**, computed by `agent/packs/immigration/rules.py::check_i94_i797_discrepancy`, never a status or bar determination. Draft the attorney email (`agent/llm/draft.py`) with a deterministic, always-present safety-boundary core ("flag for attorney review, not legal advice"); the LLM may only add a personalized intro around that core, never edit it.
- **Unattended beat:** scheduled `visa_bulletin_fetch` against a **captured** DOS bulletin **and** the matching-month USCIS chart-selection page (DOS publishes both charts; USCIS separately designates which one applies — `check_bulletin_cutoff` requires both and returns `needs_review` if the designation is missing or mismatched). Output is an attorney-review draft, never "file the I-485."
- **Boundary:** every output drafts to the *attorney*; never advises on travel, eligibility, or status.
- **Sample case, not real uploads:** nobody should upload real immigration documents to a hackathon URL. The "load sample case" button (`GET /api/sample-case`) loads `fixtures/sample_case/fields.json` — a synthetic fixture built to match the public specimen layouts CBP/USCIS themselves publish for the I-94/I-797/passport (real format, invented data). This is the *only* live-demo path and doubles as the extraction test fixture.

### 7a. Testing without real data
Two different things are tested, with different fixtures — both implemented under `tests/`:
- **Rules engine** (`tests/test_immigration_rules.py`): hand-verified cases for the discrepancy check (arithmetic only) and the bulletin-cutoff check, covering cutoff equality, `C`/`U` codes, retrogression, missing/mismatched chart selection, and a missing category. This is where correctness is actually proven; it doesn't require a single document image.
- **Bulletin-matching logic**: same test file — cutoff comparisons are tested directly against constructed `BulletinChart` fixtures; real historical DOS bulletins should be substituted before the demo (`fixtures/bulletins/`, not yet populated).
- **Extraction** (`tests/test_extraction.py`): tested against a fake Bedrock client so the evidence/missing/ambiguous/`needs_review` logic is proven without a live AWS call. Live extraction against the real synthetic sample-case documents still needs to be verified once Bedrock access is confirmed (Day 1 prerequisite).

### Recall-to-remedy (thin second pack — proves the engine is generic, not a co-headliner)
Scope this to ~20% of the effort immigration gets: **one** recall source (pick whichever is cleanest live, e.g. CPSC), **one** seeded receipt, **one** match, **one** ping. Its only job is to show the same loop (watch → match → evaluate → ping) runs on a second, unrelated domain without touching the orchestrator or decision-gate code — not to be a second fully-built module.
- **Onramp:** drop a receipt (no inbox OAuth — that's scope creep for no demo value).
- **Live beat:** during the demo, a real recent recall item is fetched **live, no auth**, matched to the seeded receipt, remedy form prefilled, one ping: "refund $218 or voucher $350?"
- **Honesty in framing:** general recall-to-receipt matching is fuzzy and not built to be robust — this demo runs on a pre-staged recall + matching receipt, with a captured-but-real fallback in case the feed hiccups on stage. Label it "demo scope" in the README so a judge who tries their own receipt doesn't hit a fake match and read it as dishonest.

---

## 8. Demo structure (maps to architecture)

Five minutes, story then proof:

1. **Hook (immigration, ~2.5 min):** three photos → "55 days not 20 months" → attorney email drafted → then time-jumps to the bulletin dropping overnight and the agent acting unattended. Emotional, high-stakes, the story only you can tell. This is the pitch; give it most of the runtime.
2. **Proof (recalls, ~1 min):** a real recall fetched live during the demo, matched to a seeded receipt, remedy drafted. Same engine — say so on screen — now shown on a second, unrelated domain. Brief: it's a generality proof, not a second pitch.
3. **The quiet (~30s):** show the decision gate — many events processed, silence, one ping. This *is* the theme.
4. **The spine (~1 min):** the architecture diagram. Point at what's actually built (Strands agent, local/Runtime, the decision gate) and what's the production path (Memory/Identity/Policy/Observability, labeled as such). Close on the pitch line.

Required deliverables checklist: architecture diagram (this doc's §3), public repo w/ MIT or Apache license in the About section, README, demo video ≤5 min, AWS Builder ID, optional live-demo link (scores higher — stand up the recall dashboard publicly if you can). **Bonus:** write all three builder.aws.com posts (0.6 pts, guaranteed).

---

## 9. Four-day build plan (2 people)

**Split:** Person A owns the engine (orchestrator, decision gate, local runtime, and the Day-3 AgentCore attempt if Days 1–2 land). Person B owns the immigration pack (feeds, parsers, rules, draft templates) + the thin recall pack + the dashboard + demo capture.

- **Day 1 — spine up, local only.** Hour 1: read current AgentCore Runtime docs, confirm what deployment actually requires (don't scaffold AgentCore before this). Hour 2: pull the actual rule text (USCIS Policy Manual, INA §214, that month's bulletin instructions) for status math and bulletin-chart selection — write it down before writing code against it. Then: verify every feed live (USCIS sandbox, Federal Register, the one chosen recall source; note USDA FSIS was blocked from the researchers' machine — retest if you ever need it). Build a trivial local Strands agent with plain-function tool calls and the ledger schema from §5 as a JSON/SQLite file. Person B starts building the synthetic sample-case fixture set (§7's "load sample case") and the hand-verified rules-engine test fixtures (§7a) in parallel with immigration parsing — these are on the critical path, not polish.
- **Day 2 — immigration parsing + status math.** I-94 parsing, status math, attorney-email draft, all running locally end-to-end against the sample-case fixture. Rules engine passes its hand-verified test fixtures before it's considered done. This is your working demo by end of Day 2; everything after is upside.
- **Day 3 — unattended beat + thin recall pack + AgentCore attempt.** Capture a real visa bulletin, wire the unattended beat off it. Build the thin recall pack (one feed, one seeded receipt, one match, one ping) in whatever's left of the day. Only if all of the above is done: attempt AgentCore Runtime deploy as a bonus, time-boxed — if it's not working by a hard cutoff, demo locally and call AgentCore the production path in the README.
- **Day 4 — polish + record.** Decision-gate narration, dashboard "one thing" view, record the 5-min video, README (with the production-path paragraph + demo-scope label on recall matching) + diagram, license in About. Submit by noon Sunday with a buffer. Draft the three build-story posts in parallel across the week.

**Risk register:**
- *Live feed hiccup on stage* → captured-real fallback for every live beat.
- *AgentCore Runtime deploy doesn't work in the Day-3 time box* → demo runs locally; README covers AgentCore as the production path. This is an accepted outcome, not a failure.
- *Scope creep into a third module, or recall pack growing past its 20% budget* → don't. Third clock is a diagram promise; recall stays thin.
- *Immigration liability read* → keep the attorney-draft boundary explicit in UI + video.
- *Rules engine gets a chart-selection or day-count wrong on stage* → the failure mode that discredits the whole project. Mitigate with hand-verified test fixtures against primary sources (§7a) before demo day, not by trusting the LLM's immigration knowledge.
- *Recall matcher mistaken for general-purpose* → label it demo-scope in the README; don't let the video imply it works on arbitrary receipts.

---

## 10. Why this wins (one paragraph for the pitch)

Every calendar app reacts to *your* dates. This agent reacts to *the government's* changes on your behalf and only interrupts you when there's money or status on the line — immigration status you didn't know you were losing, a recall on something you already own. It's one engine reading official feeds, matching them to your documents, and drafting the one action that matters, built on the AWS agent stack it's designed for. Everyone has clocks. Most people lose things not because they don't qualify, but because a paperwork clock ran out while they weren't looking. This runs them quietly.
