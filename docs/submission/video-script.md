# Five-minute demo video script (draft)

Target 4:30, hard cap 4:45 with one optional beat. Screen recording of the local UI plus one terminal window. Voiceover. No slides except the title and the architecture diagram.

## 0:00 – 0:35  The problem, who it's for, why it matters (title card, then a still of the two documents)

[Text cue 1, lower third: THE PROBLEM · The I-94, not the approval notice, is the date that counts.]

"If you live in the US on a visa, your stay runs on dates from agencies that don't talk to each other. CBP stamps an admit-until date on your I-94. USCIS prints a different date on your approval notice. If your passport expires first, CBP cuts the I-94 short, and nothing tells you."

[Text cue 2: WHO IT'S FOR · H-1B and H-4 holders, students and workers on visas, and their attorneys.]

"It's for anyone whose stay depends on paperwork from CBP, USCIS, and the State Department, and for their attorneys."

[Text cue 3: WHY IT MATTERS · The notice says twenty months. The record that governs your stay says fifty-five days.]

"Over a million people are in the employment-based backlog, waiting on a monthly bulletin. This is Immigration Status Guardian. It reads the documents, does the arithmetic, and interrupts you exactly once."

## 0:35 – 1:45  Three documents → 55-day discrepancy → attorney draft → approval

[Screen: the opening scene, page freshly reset. Click Run the sample case. The page scrolls to the upload section (three files land in the inputs), then to the review, which shifts to slate as the result lands.]

"Three synthetic documents: an I-94, an I-797, a passport. They go through the real upload endpoint, the same one your own files would. Bedrock reads each date and shows the evidence it read it from." [Point at the Extracted evidence column.] "Note the label in the top bar: Case review · Live Bedrock. Every result in this product is labeled live or recorded."

"The engine compares the two dates. Fifty-five days apart. That clears the decision gate, so one thing surfaces: 'Your document dates differ by 55 days. Review this with your attorney.'"

[Click Review attorney draft.]

"Here's the draft. The dates and the flag are fixed text the model cannot edit. It says what it is: a flag for the attorney, not a status determination."

[Click Approve for attorney review.]

"Approve for attorney review. That writes a receipt on this clock, event, and rule version. Nothing is sent unless a verified email sender is configured, and the panel says which it is."

[If it fails on camera: extraction falling back shows the top bar as Recorded replay and a Mode line under the upload; say "Bedrock is unreachable right now, so the same check ran on the recorded extraction, and the label says so." If the drawer does not open, click the "Document review" row under Monitoring activity; it opens the same draft.]

## 1:45 – 2:35  September stays silent, October surfaces, the repeat stays silent

[Close the panel. Scroll to 03 Monitor. Click Replay September update; the September panel reads "Stayed quiet".]

"The other half of the job runs unattended. Every month the State Department publishes the Visa Bulletin, and USCIS decides which of its two charts applies. September: the seeded case's priority date isn't current. Silent. No notification."

[Click Replay October update; the October panel reads "Surfaced".]

"October: USCIS switches to the Dates for Filing chart, the date is current, and the guardian pings once with a filing-window draft."

[Scroll back up and click Load bundled sample & process again.]

"Now the important part. Run the document check again. Silent. Already flagged, draft still available. The ledger remembers what it already told you. Restraint is the feature."

[If it fails on camera: the bulletins are local fixtures, so a failure means the demo database; press Reset demo and replay September then October again. A panel reading "Needs review" shows the reason in its detail line; read it out rather than hiding it.]

## 2:35 – 3:35  Ask the guardian (Strands agent with tools, decision trace)

[Type or pick: "My I-94 says 2026-11-03 and my I-797 says 2026-12-28. Do they disagree?"]

"This is a Strands agent. Its only tools are the engine's five checks. It can't compute dates or decide status itself; it picks a tool, runs it, and reports the result. Under the answer is the decision trace: the tool it chose, the input it passed, the data mode, the gate decision, whether a draft was persisted. Execution facts, not chain of thought."

[If it fails on camera: the answer box shows the real error and the list of tools it would have used; say "Bedrock model access is blocked on this account, and the agent reports that instead of failing silently." Then show the `POST /api/ask` live output from the README's Evidence section in the terminal.]

## Optional beats (only if the prerequisites landed; each adds about 15 seconds; use at most one so the total stays under 4:45)

- **Dates agree stays silent.** Needs the `matching` recording committed (`scripts/record_extraction.py --all`). Pick "Dates agree" in the Sample case picker, Load bundled sample & process: the figure reads 0, "the governing dates agree", no draft. "Silent on the first pass, not just on repeats."
- **The ping arrives.** Needs the unattended run provisioned (`deploy/unattended/provision.sh`). Cut to the inbox: one SNS email for October, none for the repeat. "That is the unattended run: one email, once."
- **A follow-up in the same session.** After the first guardian answer, ask "And the passport?" without repeating the dates. The answer builds on the prior tool result and the earlier turn shows under "Earlier in this session".

## 3:35 – 4:05  The spine (architecture diagram)

"Under the hood: one deterministic engine, two domain packs, the model at three edges. Extraction, draft intro, and the tool-calling guardian. The gate and the ledger are plain Python with 204 tests. The same pipeline is deployed on Amazon Bedrock AgentCore Runtime with logs and traces on."

## 4:05 – 4:20  Recall coda (15 seconds)

[Ask the guardian: "Is my speaker receipt affected by a recall?" The trace shows check_recall, feed_mode live.]

"Same engine, different domain. A saved receipt against the live CPSC recall feed, through the same agent. One match, one ping: refund or voucher. That's the proof the engine is generic; immigration is just the first pack."

[If it fails on camera: the CPSC call falls back to the captured recall and the trace says so; say "live feed unreachable, captured fallback, labeled." If the guardian itself is blocked, cut this beat; the architecture card already names the second pack.]

## 4:20 – 4:30  Close

"Everyone has clocks the government moves. This one watches them, and only speaks when there's a decision to make. Immigration Status Guardian."

## Recording checklist

- `rm -f data/demo.db` before recording, or press Reset demo, well before you hit record: the first run after a reset retries live Bedrock before failing over (about 20 s on an account without model access).
- Title and closing cards: slides 1 and 11 of `docs/submission/deck.html` (or pages 1 and 11 of `deck.pdf`); the architecture card is slide 9.
- Record on a machine whose AWS account has Bedrock access, so the top-bar label reads Live Bedrock.
- Start at the very top of the page (the opening scene) at 1920×1080; the page has no external fonts or scripts, so nothing needs to preload.
- Terminal ready with `agentcore invoke '{"prompt": "Do my documents disagree? I-94 2026-11-03, I-797 2026-12-28"}'`.
- Keep the live/recorded label in frame whenever extraction is on screen.
