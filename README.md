# Immigration Status Guardian

Built for AWS "Agents for Humans" (Strands Agents SDK, Everyday track, due Sep 14, 2026).

## What it does

Flags a **document-date discrepancy** between a person's I-94 and I-797 (a common H-1B situation: CBP admits someone only until their passport expiry, which can be much earlier than what their approval notice says) and drafts a message for their attorney to review. It never states a lawful-status length, an unlawful-presence conclusion, or a filing recommendation — every output is framed as a flag for attorney review, not legal advice.

A second, deliberately thin pack (`agent/packs/recalls/`) matches a live consumer-recall feed to a receipt, proving the same watch → evaluate → gate → surface engine works on an unrelated domain. It is demo-scope (exact match against one seeded receipt), not a general-purpose matcher — see "Known scope limits" below.

## Who it's for

H-1B holders and their attorneys, and international students/workers generally, whose status depends on documents issued by different agencies (CBP, USCIS) on different clocks that can silently disagree.

## How it works

One deterministic engine, two domain packs:

```
agent/
  engine/   schema.py, store.py (SQLite), decision_gate.py, engine.py — the
            deterministic control flow. No LLM in this path.
  llm/      extract.py (Bedrock document extraction, with per-field evidence
            and explicit missing/ambiguous handling), draft.py (attorney
            message — a fixed, always-present safety-boundary core; the LLM
            may only add a personalized intro around it, never edit it)
  packs/
    immigration/  rules.py (I-94/I-797 date-gap check; bulletin-cutoff check
                  requiring the USCIS-designated chart), pipeline.py
    recalls/      rules.py (exact manufacturer+product match, demo-scope)
  app.py    FastAPI backend serving the API + the static UI
ui/index.html   static demo UI (load sample case / decision gate / recall demo)
fixtures/sample_case/   synthetic documents (invented data, real specimen format)
tests/    50 tests covering rules, extraction, the decision gate, and
          replay-safe deduplication
```

**The rules engine is deterministic Python, not an LLM judgment call.** The model is only ever called for two things: extracting fields from a document, and writing the plain-English wrapper around a rules-engine result it cannot alter. See `docs/architecture-spec.md` §4.2 for why this boundary is enforced in code rather than in a prompt.

**The decision gate** (`agent/engine/decision_gate.py`) is why the agent stays quiet: an event only surfaces if it's material, actionable, has an open window, and hasn't already been surfaced for the same event. Everything else updates the ledger silently.

## Known scope limits (by design, for this deadline)

- **No lawful-status, F-1/OPT, or unlawful-presence computation.** That domain logic (INA §212(a)(9)(B) bars, status-length math) is deferred to a later iteration — see `HANDOFF.md`. This build only compares two document dates arithmetically.
- **Recall matching is demo-scope**: exact manufacturer+product match against one seeded receipt, not a general fuzzy matcher. Labeled as such in the UI and here so a judge testing their own receipt doesn't mistake it for general-purpose.
- **Sample case only, no real document uploads** in the live demo — `fixtures/sample_case/fields.json` is a synthetic fixture (invented data in the real I-94/I-797/passport specimen format), so nobody uploads real immigration documents to a hackathon URL.

## Production path (not built for this deadline)

AgentCore Memory, Identity (Cognito), Policy (Cedar), Observability (OTEL), and Gateway-brokered auth for the external feeds are real requirements for shipping this beyond a demo — see `docs/architecture-spec.md` §4.6 for the design. AgentCore Runtime deployment itself was a time-boxed Day-3 attempt; see `deploy/` and the architecture diagram for what that adds without changing any of the logic above.

## Setup

Requires Python 3.11+ and, for anything beyond the rules-engine tests, AWS credentials with Bedrock model access (used for document extraction and draft personalization even when running locally — this is not an AgentCore-only dependency).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/                      # 50 tests, no AWS credentials required
uvicorn agent.app:app --reload     # demo backend + UI at http://127.0.0.1:8000/
```

## Pre-existing code

None. All code in this repository was written new during the hackathon submission window (Aug 10–Sep 14, 2026).

## License

MIT — see `LICENSE`.
