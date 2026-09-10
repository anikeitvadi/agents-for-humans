# Implementation handoff — September 10, 2026

## Start here

Continue the initial Immigration Status Guardian build by fixing the reviewed implementation, then completing its missing demo paths. This document summarizes the implementation and Codex review so a new Claude Code session can continue without the prior conversation.

Read `AGENTS.md` and `CLAUDE.md`, then this document. Use `docs/architecture-spec.md` for design context. Earlier sections of `HANDOFF.md` and parts of the architecture/README contain superseded scope or overstate completion; the reviewed behavior below is the current baseline.

**Working-tree baseline:** HEAD `602e5ae`. The implementation is uncommitted, with most new files untracked. Preserve these files and existing user changes. This handoff adds documentation only; the fixes below have not been implemented.

**Review evidence:** `.venv/bin/python -m pytest -q` returned **52 passed**, with one Starlette/AnyIO deprecation warning. Additional local probes exposed failures the suite misses. Live Bedrock inference and AgentCore deployment were not tested. The earlier claim that everything was written test-first comes from the implementation handoff; the reviewer independently verified test results, not development history.

## Agreed product scope

- Flag an I-94/I-797 document-date discrepancy and prepare an attorney-review message. The gap is arithmetic between two dates, not remaining lawful status.
- Add an unattended bulletin comparison using historical DOS bulletins paired with USCIS chart selections for the same months. Surface an attorney-review flag, not a filing-eligibility conclusion.
- Prove reuse with one thin recall pack: one live source, one seeded receipt, one match, the same gate/persistence path, one alert. Label staged and fallback data clearly.
- Python, FastAPI, SQLite, static HTML/JS, and Strands. Application code enforces evaluation, gating, and persistence. Model work is bounded to extraction and drafting.
- Use synthetic documents only. Lawful-status determinations, F-1/OPT timelines, and unlawful-presence calculations are future work, after this build is validated.
- Local hosting still needs AWS access for Bedrock. AgentCore Runtime is optional, after the local demo works. USCIS OAuth, Federal Register, Memory, Identity, Policy, and Observability are deferred.

## What has been implemented

| Area | Files | Actual behavior |
| --- | --- | --- |
| Project scaffold | `pyproject.toml`, `LICENSE`, `.gitignore`, `AGENTS.md` | Python package configuration, MIT license, development exclusions, repo guidance. |
| Models and storage | `agent/engine/schema.py`, `store.py` | Clock/Event/Alert models; SQLite events and alerts with a uniqueness constraint. Clocks and drafts are not persisted. |
| Engine and gate | `agent/engine/engine.py`, `decision_gate.py` | Takes a caller-computed rule outcome, checks materiality/actionability/window/novelty, and attempts persistence. See transition bug below. |
| Immigration rules | `agent/packs/immigration/rules.py` | Date discrepancy and bulletin comparisons, chart-type mismatch handling, C/U and retrogression branches. Cutoff equality is wrong. |
| Discrepancy pipeline | `agent/packs/immigration/pipeline.py` | Pre-extracted fields → discrepancy rule → gate/store → draft for a surfaced result. |
| Drafting | `agent/llm/draft.py` | Deterministic message core plus optional intro from a real Strands Agent; falls back to the core on invocation failure. App attempts to construct the Agent when credentials are available. Live execution unverified. |
| Extraction helper | `agent/llm/extract.py` | Converse request and JSON-response parsing into value/evidence/status records. Unwired, missing required request parameter, and insufficiently validated. |
| UI/API | `agent/app.py`, `ui/index.html` | Sample JSON display, discrepancy processing, illustrative gate scenarios, canned recall matching. The displayed “Parse step” does not perform extraction. |
| Fixtures | `fixtures/sample_case/`, `fixtures/bulletins/` | Invented extracted fields/evidence, canned recall/receipts, and a placeholder bulletin. No specimen PDF/image assets or real paired bulletin captures. |
| Deployment | `deploy/agentcore_entrypoint.py` | Optional untested wrapper around the discrepancy pipeline. It does not currently supply a Strands Agent to that pipeline. |
| Tests | `tests/` | 52 passing offline tests covering existing rules, mocked extraction, gate/store, pipeline and API behaviors; not proof of completed live integrations. |

## Fix confirmed bugs first

### F1 — P1: priority-date equality incorrectly passes

**Location:** `agent/packs/immigration/rules.py::check_bulletin_cutoff`, approximately line 108; `tests/test_immigration_rules.py::test_priority_date_equal_to_cutoff_is_current`.

The implementation uses `priority_date <= cutoff`, and the test asserts that equality is current. DOS instructions require a priority date **earlier than** the cutoff. Use strict comparison and correct the message and test expectation.

**Acceptance:** before cutoff passes; equality and after cutoff do not. Exercise both supported chart types and preserve C/U behavior. Source: [DOS September 2025 bulletin, employment-based chart instructions](https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin/2025/visa-bulletin-for-september-2025.html).

### F2 — P1: Converse request omits `modelId`

**Location:** `agent/llm/extract.py::extract_fields`, approximately line 56.

The request supplies messages but no model ID. Local validation against the installed botocore Converse input schema returned `Missing required parameter in input: "modelId"`. The test fake accepts arbitrary kwargs and hides the failure.

**Acceptance:** pass an explicitly configured model ID; add an offline request-contract check using botocore validation/Stubber or an appropriately strict fake. Confirm current model/region access separately before a live smoke test. Keep request validity distinct from successful inference.

### F3 — P1: silent-to-surfaced transitions break deduplication

**Location:** `agent/engine/engine.py::process_event`, approximately lines 35–37; `agent/engine/store.py::save_alert`.

For one clock/event/rule key, process a material/actionable event with its window closed, then twice with its window open. The reviewed implementation returns:

| Attempt | Returned decision | Stored decision |
| --- | --- | --- |
| Window closed | silent | silent |
| Window opens | surfaced | silent |
| Poll again | surfaced | silent |

The silent row occupies the unique key. Later INSERTs fail; `process_event` ignores the failure and returns the unpersisted surfaced decision. The unchanged silent record never satisfies novelty suppression.

**Acceptance:** record the transition atomically; only one caller claims a new surfaced alert. Verify closed → open → repeated poll, restart, and overlapping attempts. Persisted state must agree with the result. Define how rule-version changes affect novelty, since the database key includes the version but the gate currently ignores it.

### F4 — P1: extraction can accept unsupported values or crash

**Location:** `agent/llm/extract.py`, approximately lines 74–90.

Confirmed input `{"admit_until":{"value":null,"evidence":"","status":"extracted"}}` returns `needs_review=False`. Dataclass annotations do not enforce the value/status contract. Response-envelope indexing occurs outside the guarded parse; JSON arrays, null field objects, and missing content can raise rather than return a review result.

**Acceptance:** validate response shape, allowed statuses, required values, date format, and nonempty evidence. Route missing, ambiguous, malformed, or unsupported critical facts to review before rules execute. Test null/empty values, invalid dates/statuses, non-object JSON, null fields, missing content, and model/API failures. Add cross-document identity/chronology checks when wiring real synthetic documents. Evidence text produced by a model is not independently verified merely because it is nonempty.

### F5 — P2: generated text is inserted as HTML

**Location:** `ui/index.html`, especially the draft rendering near lines 100–103.

API/model text is interpolated into `innerHTML`, allowing returned markup to be interpreted by the browser.

**Acceptance:** construct static layout separately and insert dynamic values using `textContent`/text nodes. Verify HTML-like draft text is displayed literally and event-handler markup does not execute. Apply this consistently to fields, evidence, gate labels, and recall output.

## Complete the planned paths after those fixes

### C1 — Actual sample-document extraction

Create synthetic I-94, I-797, and passport specimen-format assets with coherent dates and identity. Keep expected extracted JSON as test expectations, not the source of a purported live extraction.

Wire sample documents → extraction → validated/evidenced fields → discrepancy pipeline → visible attorney draft. Show missing/ambiguous states in the UI. An explicit recorded-response mode is useful offline, but label it and distinguish it from live parsing.

**Acceptance:** a live integration check reads the synthetic document bytes and verifies expected fields; the UI shows their evidence. Offline tests run without AWS. Document which mode was actually tested.

### C2 — Persistent case and draft lifecycle

Current storage retains only event/alert records. Draft text exists only in the first response; reprocessing the same sample returns silent with no draft. A reload can therefore lose access to an unresolved draft.

Persist enough case and draft state to retrieve existing unresolved work without generating another notification. Define pending/failed/ready draft handling and retry behavior. If approval is added, show the draft first and define approval as a recorded user decision; sending email is not part of this task.

**Acceptance:** a reload/restart retrieves the original draft; repeat polling produces no new ping; draft failure/retry does not silently lose the action.

### C3 — Unattended bulletin flow

The comparator exists, but there is no loader, poll/scheduler entrypoint, case-matching pipeline, or bulletin draft/timeline. Replacing `sample_month.json` alone is insufficient.

Capture two chronological real DOS bulletins and matching-month USCIS chart-selection sources, with URLs and effective dates. Explicitly seed priority date, preference category, and chargeability with provenance. Wire a poll through the shared engine and persistence. Use an injectable/fixed date for time-dependent window behavior; the discrepancy date gap itself does not need one.

**Acceptance:** a clearly labeled historical replay changes the case from not current to current and generates one attorney-review alert unattended. Repeat and restart suppress duplicates. Missing/mismatched-month sources and failed feeds produce visible review/error states. Keep chart movement and the individual's cutoff result distinguishable when handling retrogression.

### C4 — Recall through the shared engine

`agent/app.py::recalls_check` currently reads `recall_demo.json` and invokes the matcher directly. It does not fetch CPSC, use `process_event`, run the gate, or persist a deduplicated alert. README currently overstates this.

Add one real recall feed with a captured-real fallback, normalized events, a seeded receipt, and the shared rule/gate/store/draft flow. Keep matching deliberately narrow.

**Acceptance:** matched receipt → one persisted alert/remedy draft; unmatched receipt → no ping; repeated poll/restart → no duplicate. Clearly identify live versus fallback data in the UI and docs.

## Suggested execution order and finish checks

1. Reproduce F1–F4 with failing regressions before changing behavior. Fix them and F5; rerun relevant tests, then the full offline suite.
2. Complete C1 and C2. Demonstrate actual sample parsing, visible evidence, and a retrievable attorney draft before declaring the first end-to-end milestone complete.
3. Complete C3, then C4. Prove both run through the same engine with persisted decisions.
4. Reconcile README, architecture and HANDOFF with observed behavior. Label mocked, recorded, live-tested, unverified, and deferred pieces accurately. Preserve the narrow scope and correct old claims about status calculations or “no AWS dependency.”
5. Attempt AgentCore only after the local paths work. Verify its imports, data-directory initialization, payload contract, model wiring, and state lifetime. A placeholder wrapper is not evidence of deployment.

Useful local commands:

```bash
git status --short
.venv/bin/python -m pytest -q
.venv/bin/uvicorn agent.app:app --reload
```

The app tests currently construct the real app/factory; make offline tests explicitly inject/disable model access so configured AWS credentials cannot unexpectedly trigger inference. Keep a separate marked live integration check.

Report final test commands/results, live checks actually performed, and any remaining gaps. Do not equate a passing fake-client test with verified Bedrock extraction. The public repository, exported architecture diagram, and video are still submission work; publishing is not requested by this handoff.

## Prompt to start the next Claude Code session

> Read AGENTS.md, CLAUDE.md, and docs/implementation-handoff-2026-09-10.md. Continue from the existing uncommitted implementation; preserve current work. Fix F1–F5 with regression checks first, then complete C1–C4 in the documented order. Keep the initial document-discrepancy/attorney-review scope. Verify current SDK contracts before changing integrations, separate offline from live validation, and update HANDOFF.md with what was actually verified and what remains. Start by confirming the baseline and reproducing the listed bugs.
