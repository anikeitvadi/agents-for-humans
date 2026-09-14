# builder.aws.com post drafts (three distinct posts, not published)

Each title includes "Agents for Humans" per the bonus rule. Publish before the submission deadline. Each is a different angle: the safety boundary, the deployment story, and the Strands tool design.

---

## Post 1 · "Agents for Humans: why our immigration agent refuses to do the math"

Building for the AWS Agents for Humans hackathon, we picked the one domain where a confident wrong answer does real damage: immigration paperwork. If you're on an H-1B and your passport expires before your approval notice does, CBP cuts your I-94 short. The approval notice says twenty months. The record that governs your stay says fifty-five days. Nobody tells you.

The obvious agent design is "give the model the documents and ask what's wrong." We didn't build that. Here's what we built instead, and why.

**The model works at three edges only.** Amazon Bedrock extracts fields from the document images, and every field comes back with the evidence string it was read from and one of three statuses: extracted, missing, ambiguous. Anything not cleanly extracted blocks the rule; we never run date arithmetic on a guess. A Strands Agent writes the intro paragraph of the attorney message, and only the intro: the dates, the flag, and "this is not legal advice" are fixed text it cannot touch. If the agent fails, the fixed core ships alone. Finally, a tool-calling Strands agent answers questions, but its only tools are the engine's own checks, and its system prompt forbids computing dates or stating status.

**Everything in between is plain Python with tests.** The date comparison is arithmetic. The decision gate is four booleans: material, actionable, window open, not already surfaced. The ledger is SQLite with a uniqueness constraint on clock, event, and rule version, so a replay or a restart can never produce a second ping.

**What it never says.** Not "you're in status." Not "you're safe to travel." Not "file this." Every output is a flag for your attorney. We deferred all status math, grace periods, unlawful-presence bars, because getting one of those wrong on stage would discredit everything else.

The result surfaces once, drafts the email, and goes quiet. For this audience, restraint is the product.

Repo: [link]. Built with the Strands Agents SDK and Amazon Bedrock AgentCore.

---

## Post 2 · "Agents for Humans: deploying a Strands agent to AgentCore Runtime, including the two things that broke"

Our Agents for Humans entry runs locally as a FastAPI app and in the cloud on Amazon Bedrock AgentCore Runtime. Same pipeline, one entrypoint file. Here's the honest deploy log.

**What worked on the first try.** `agentcore configure` with direct code deploy, no container. It auto-created the execution role and S3 bucket, cross-compiled the dependencies for ARM64 with uv, uploaded a 55 MB bundle, and stood up the Runtime with CloudWatch logs and X-Ray traces on.

**Break one: the bundle shipped without the AgentCore SDK.** The toolkit resolves dependencies from the source root and, when it finds `pyproject.toml`, installs only the base dependencies. Our `bedrock-agentcore` dependency lived in an optional `[deploy]` extra. The container crashed on import. Fix: a `requirements.txt` at the repo root, which the toolkit prefers over `pyproject.toml`. Document why it exists or someone will delete it.

**Break two: the source path.** With the entrypoint in `deploy/`, the toolkit packaged only that folder, leaving out the engine and the fixtures. Setting `source_path` to the repo root fixed it; the module resolves as `deploy.agentcore_entrypoint`.

**One thing to keep in mind.** Credentials in the Runtime are not proof that Bedrock works. Our account had a payment-verification hold that returned "Error 002" on every model. The deployed agent still ran end to end because extraction fails over to a recorded replay and the draft falls back to its deterministic core, and every response labels which mode served it. Build the fallback before you need it.

**Invoke.** `agentcore invoke '{}'` runs the sample case: surfaced with a draft the first time, silent with the same draft the second. `agentcore invoke '{"prompt": "Do my documents disagree?"}'` hands the question to the Strands agent, which picks a tool and answers with a decision trace attached.

Repo: [link].

---

## Post 3 · "Agents for Humans: designing Strands tools so the agent can't reach a conclusion the engine didn't"

The Strands Agents SDK makes tools cheap: decorate a function, pass it to `Agent(tools=[...])`, done. The interesting design question is what to give the agent and what to keep from it. For our Agents for Humans immigration guardian we landed on a rule: the agent may only call tools that wrap the deterministic engine, on the same ledger the UI uses, and it must report their results.

**Five tools, each a thin wrapper.** `check_document_dates` compares an I-94 date with an I-797 date and returns the gap. `run_sample_case_check` runs extraction, the rule, the gate, and the draft on the bundled sample. `check_uploaded_case` does the same for the specific case the person just uploaded. `check_visa_bulletin` checks one month against the chart USCIS designated. `check_recall` matches a receipt against the CPSC feed. Each returns a structured JSON result with the data mode (live, recorded, fallback), the gate decision, and the reason.

**The system prompt is a fence, not a persona.** Never compute or compare dates yourself. Never state whether someone is in status. When a tool says surfaced, say one thing needs review and a draft is ready. When it says silent, say nothing new needs attention and why. If the tools can't answer, say so.

**A fresh agent per question.** Requests stay stateless and the tool calls attributed to an answer are exactly the ones made for it. We read them straight from the agent's message history, pair each `toolUse` with its `toolResult`, and return a decision trace: tool, input, status, mode, gate decision, persisted draft. Execution facts, never chain of thought.

**Testing without a model.** A small `Model` subclass plays a script of tool-use and text turns. Strands registers the real tools, runs the real loop, executes the real functions, and feeds real results back. Our tests assert the trace matches the actual tool calls. None of it needs Bedrock to be reachable, which mattered more than we expected.

Repo: [link].
