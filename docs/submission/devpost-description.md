# Devpost project description (draft, not published)

Track: Everyday Agents. Built with the Strands Agents SDK, deployed on Amazon Bedrock AgentCore Runtime.

## Immigration Status Guardian

**One engine that reads the government so you don't have to.**

### What it does

If you live in the United States on a visa, your life runs on dates issued by agencies that don't talk to each other. Customs and Border Protection stamps an "admit until" date on your I-94 when you enter. USCIS prints a different validity date on your I-797 approval notice. If your passport expires first, CBP cuts the I-94 short, and nothing tells you. The approval notice in your drawer says you have twenty months. The record that actually governs your stay says fifty-five days.

Immigration Status Guardian reads the documents, compares the dates the way an attorney's paralegal would on day one, and surfaces exactly one thing: "Your document dates differ by 55 days. Review this with your attorney." It drafts the message to the attorney. You approve it. Then it goes quiet.

It also watches the world for you. Every month the State Department publishes the Visa Bulletin and USCIS decides which of its two charts applies. The guardian replays that check unattended: September's bulletin changes nothing, so it stays silent. October's bulletin moves the case to "current," so it pings once with a filing-window draft. Run the same check again and it stays silent. Restraint is the product.

A second, deliberately thin pack proves the engine is generic: it matches a saved receipt against the live CPSC recall feed and pings once with the remedy, refund or voucher.

### Who it's for

People whose status depends on paperwork from CBP, USCIS, and the State Department: H-1B and H-4 holders, international students and workers, and the families in the employment-based green-card backlog, and the attorneys who field their "is this normal?" emails.

### How it works

- **A deterministic engine, not a model judgment.** Rules, the decision gate, and the ledger are plain Python with tests. The gate lets an event through only if it is material, actionable, inside its window, and not already surfaced for that clock, event, and rule version. Everything else updates the ledger silently. Replays and restarts never produce a second ping.
- **The model works at three edges only.** Amazon Bedrock extracts fields from the document images with per-field evidence and explicit "missing" and "ambiguous" states. A Strands Agent writes only the intro of the attorney draft around a fixed safety core it cannot edit. And the guardian agent, a Strands Agent whose only tools are the engine's checks, answers questions like "do my documents disagree?" by calling a tool and reporting the result. It cannot compute dates or determine status on its own, and every answer ships with a decision trace of which tool ran, on what input, and what the gate decided.
- **Honest modes.** Every result is labeled live, recorded, or fallback. When Bedrock is unreachable the demo transparently replays the recorded extraction and says so.
- **One human action.** "Approve for attorney review" records an idempotent receipt on the clock, event, and rule version. Nothing is sent; the demo has no mail transport and never claims one.
- **Deployed.** The same pipeline runs on Amazon Bedrock AgentCore Runtime with CloudWatch logs and X-Ray traces on: `{}` runs the sample case (verified: surfaced once, silent on the repeat), and `{"prompt": ...}` hands a question to the guardian agent.

### What it deliberately does not do

It never states whether someone is in status, computes unlawful presence, or gives legal advice. Every output is a flag for the attorney. The upload flow is real, but the demo ships only synthetic specimens in the real I-94, I-797, and passport format, and public-demo mode refuses anything else, so nobody's actual papers touch a hackathon URL.

### Built with

Strands Agents SDK, Amazon Bedrock (Converse API, multimodal documents), Amazon Bedrock AgentCore Runtime, FastAPI, SQLite, vanilla JavaScript. Public feeds: DOS Visa Bulletin with USCIS chart designation (captured), CPSC SaferProducts API (live).
