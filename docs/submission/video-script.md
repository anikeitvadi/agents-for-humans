# Five-minute demo video script (draft)

Target 4:30. Screen recording of the local UI plus one terminal window. Voiceover. No slides except the title and the architecture diagram.

## 0:00 – 0:35  The problem (title card, then a still of the two documents)

"If you live in the US on a visa, your life runs on dates from three agencies that don't talk to each other. CBP stamps an 'admit until' date on your I-94 when you land. USCIS prints a different date on your approval notice. If your passport expires first, CBP cuts your I-94 short and nothing tells you. The approval notice in your drawer says twenty months. The record that actually governs your stay says fifty-five days.

This is Immigration Status Guardian. It reads the documents, does the arithmetic, and interrupts you exactly once."

## 0:35 – 1:45  Three documents → 55-day discrepancy → attorney draft → approval

[Screen: UI, step 1 'Upload your documents'. Click Load bundled sample & process.]

"Three synthetic documents: an I-94, an I-797, a passport. They go through the real upload endpoint, the same one your own files would. Bedrock reads each date and shows the evidence it read it from." [Point at the Extracted evidence column.] "Note the label at the top: Live Bedrock parse. Every result in this product is labeled live or recorded."

"The engine compares the two dates. Fifty-five days apart. That clears the decision gate, so one thing surfaces: 'Your document dates differ by 55 days. Review this with your attorney.'"

[Click Review attorney draft.]

"Here's the draft. The dates and the flag are fixed text the model cannot edit. It says what it is: a flag for the attorney, not a status determination."

[Click Approve for attorney review.]

"Approve for attorney review. That writes a receipt on this clock, event, and rule version. Nothing is sent; there's no mail transport in this build and the UI never pretends there is."

## 1:45 – 2:35  September stays silent, October surfaces, the repeat stays silent

[Close the panel. Click Replay September update.]

"The other half of the job runs unattended. Every month the State Department publishes the Visa Bulletin, and USCIS decides which of its two charts applies. September: the seeded case's priority date isn't current. Silent. No notification."

[Click Replay October update.]

"October: USCIS switches to the Dates for Filing chart, the date is current, and the guardian pings once with a filing-window draft."

[Click Load bundled sample & process again.]

"Now the important part. Run the document check again. Silent. Already flagged, draft still available. The ledger remembers what it already told you. Restraint is the feature."

## 2:35 – 3:35  Ask the guardian (Strands agent with tools, decision trace)

[Type or pick: "My I-94 says 2026-11-03 and my I-797 says 2026-12-28. Do they disagree?"]

"This is a Strands agent. Its only tools are the engine's four checks. It can't compute dates or decide status itself; it picks a tool, runs it, and reports the result. Under the answer is the decision trace: the tool it chose, the input it passed, the data mode, the gate decision, whether a draft was persisted. Execution facts, not chain of thought."

[If Bedrock is still blocked at recording time: show the box's error state and say "Bedrock model access is pending on this account; the agent reports that instead of failing silently." Then show the terminal `agentcore invoke '{"prompt": ...}'` output from the README's Evidence section.]

## 3:35 – 4:05  The spine (architecture diagram)

"Under the hood: one deterministic engine, two domain packs, the model at three edges. Extraction, draft intro, and the tool-calling guardian. The gate and the ledger are plain Python with 180 tests. The same pipeline is deployed on Amazon Bedrock AgentCore Runtime with logs and traces on."

## 4:05 – 4:20  Recall coda (15 seconds)

[Ask the guardian: "Is my speaker receipt affected by a recall?" The trace shows check_recall, feed_mode live.]

"Same engine, different domain. A saved receipt against the live CPSC recall feed, through the same agent. One match, one ping: refund or voucher. That's the proof the engine is generic; immigration is just the first pack."

## 4:20 – 4:30  Close

"Everyone has clocks the government moves. This one watches them, and only speaks when there's a decision to make. Immigration Status Guardian."

## Recording checklist

- `rm -f data/demo.db` before recording, or press Reset demo.
- Record on a machine whose AWS account has Bedrock access, so the label reads Live Bedrock parse.
- Terminal ready with `agentcore invoke '{"prompt": "Do my documents disagree? I-94 2026-11-03, I-797 2026-12-28"}'`.
- Keep the live/recorded label in frame whenever extraction is on screen.
