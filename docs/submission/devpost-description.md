# Devpost project description (draft, not published)

Track: Everyday Agents. Built with the Strands Agents SDK, deployed on Amazon Bedrock AgentCore Runtime.

## Immigration Status Guardian

**One engine that reads the government so you don't have to.**

### Inspiration

If you live in the US on a visa, your stay runs on dates from agencies that don't talk to each other. CBP stamps an admit-until date on your I-94; USCIS prints a different date on your approval notice. If your passport expires first, CBP cuts the I-94 short and nothing tells you. The notice says twenty months; the record that governs your stay says fifty-five days. Over 1.2 million Indian nationals wait in the employment-based backlog on a monthly Visa Bulletin decision.

### What it does

It reads the three documents, compares the governing dates, and surfaces exactly one thing: "Your document dates differ by 55 days. Review this with your attorney." It drafts the message. You approve it. Then it goes quiet.

It keeps watching. September's Visa Bulletin changes nothing for the sample case, so it stays silent. October's moves the case to current, so it pings once with a filing-window draft. Run the check again: silent.

You can ask it. The guardian is a Strands Agent whose only tools are the engine's five checks; every answer carries a decision trace (tool, input, data mode, gate decision), and follow-ups build on the last result.

Who it's for: H-1B and H-4 holders, students and workers on visas, backlog families, and their attorneys.

### How we built it

- **Deterministic engine.** Rules, decision gate, and ledger are plain Python with 204 offline tests. An event surfaces only if it is material, actionable, in window, and not already surfaced.
- **The model at three edges.** Bedrock extracts fields with per-field evidence and explicit missing/ambiguous states; a Strands Agent writes only the draft's intro around a fixed core it cannot edit; the guardian only calls tools and reports.
- **Honest modes.** Every result is labeled live or recorded; when Bedrock is unreachable the demo replays a byte-verified recording and says so.
- **One human action.** Approval records an idempotent receipt. Nothing is sent unless a verified SES sender is configured.
- **Deployed.** AgentCore Runtime with CloudWatch logs and X-Ray traces. `{}` runs the sample case, verified in the cloud: surfaced once, silent on repeat. The `{"prompt": ...}` guardian path awaits a redeploy.
- **A second, thin pack** matches a receipt against the live CPSC recall feed: the engine is generic.

### Challenges we ran into

- A payment-verification hold returned "Error 002" on every Bedrock model; the failover carried the demo, every response labeled.
- Two bugs only live Bedrock found: JSON wrapped in a code fence, and dates in the document's printed format failing ISO validation.
- Two AgentCore deploy breaks: base-only dependencies from `pyproject.toml` (fixed with a root `requirements.txt`) and a `source_path` that packaged only `deploy/`.
- travel.state.gov blocks automated fetching; the bulletin months are captured fixtures.

### Accomplishments that we're proud of

It stays quiet: a replay, a restart, or a second upload of the same documents never produces a second ping, and the tests prove it. The upload flow is real; the specimens are synthetic.

### What we learned

Keep the model at the edges and the decision in code you can test. Build the fallback before you need it. Execution facts beat a model's explanation of itself.

### What's next

Redeploy the Runtime, provision the scheduled bulletin check, record the two remaining scenarios, then AgentCore Memory, Identity, Policy, and Gateway.

### Built with

Strands Agents SDK, Amazon Bedrock (Converse, multimodal), AgentCore Runtime, SNS and SES (optional), FastAPI, SQLite, vanilla JavaScript. Feeds: DOS Visa Bulletin (captured), CPSC SaferProducts API (live).
