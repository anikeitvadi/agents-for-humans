# Presentation plan (draft, 2026-09-11 evening)

Deadline: Mon Sep 14, 5:00pm PT. Submit by noon PT Monday. Judging is five equal criteria: Technical Implementation, Design, Potential Impact, Creativity & Originality, Presentation. Presentation is one fifth of the score and the video is the only thing every judge will definitely watch, so it gets the most care.

## What we already have

| Material | Where | State |
|---|---|---|
| Architecture diagram (built vs. production path) | `docs/architecture.svg` | Done; needs a refresh if PR #2 merges (recall tab removed, five tools) |
| Screenshots (hero, case review, draft + approval, mobile) | `docs/screenshots/*.png` | Regenerated 2026-09-11 after the redesign |
| README with quickstart, cited "Why it matters", Evidence | `README.md` | Done; PR #2 rewrites parts for the upload flow |
| Devpost description | `docs/submission/devpost-description.md` | Draft, ready to paste; adjust one paragraph if upload ships |
| Video script (4:30) | `docs/submission/video-script.md` | Draft; button names change if PR #2 merges (see below) |
| Three builder.aws posts | `docs/submission/builder-posts.md` | Drafts, ready to publish once the repo is public (they link to it) |
| Deployed AgentCore Runtime + real invoke output | README Evidence, HANDOFF | Real; predates the trace/upload code, needs one redeploy |
| Live Bedrock evidence | Partner's account, PR #2 | 5 live tests pass; `used_llm_personalization: true` seen |
| Recorded-fallback evidence | README Evidence | Real, from Ani's blocked account |

## The one narrative

Three documents → 55-day discrepancy → attorney draft → approval. September stays silent, October surfaces. Repeat check stays silent. Fifteen-second recall coda proves the engine generalizes. Every beat exists in the app today; nothing in the video needs to be faked.

Lead line: "The approval notice in your drawer says twenty months. The record that actually governs your stay says fifty-five days." One cited impact number on screen: over 1.2 million Indian nationals in the EB backlog (NFAP via Boundless, in the README).

## Decision that changes the plan: PR #2 (partner, real upload + live Bedrock)

If it merges, the video gets stronger and the script changes in four places:
1. "Load sample case" becomes **Load bundled sample & process**, which sends the three specimen PNGs through the real upload endpoint. Say that out loud: "these go through the same endpoint your own files would."
2. Record on the partner's machine (or with the partner's credentials) so extraction is **live** and the draft intro is model-written. Keep the "Live Bedrock parse" label in frame.
3. The guardian question can use `check_uploaded_case`, bound to the case just uploaded. Show the decision trace.
4. The recall tab is gone from the UI. Do the coda through the guardian: ask "Is my speaker receipt affected by a recall?" and let the trace show `check_recall` with `feed_mode: live`. Or run `curl` against `/api/recalls/check` in the terminal for ten seconds. Either is honest and short.

If it does not merge by Saturday night, record on `main` exactly as the current script says, in recorded mode, and say so on screen.

Recommendation: merge it Saturday morning after Ani clicks through it once. It passes 204 offline tests here, keeps the failover, trace, approval, and reset work intact, and turns the demo's weakest claim ("this would parse your documents") into a shown fact. One condition: keep the README's warning that this is a demo and nobody should upload real immigration documents to a shared deployment, and do not publish a public live link with upload enabled.

## Who does what

The day-by-day order lives in `HANDOFF.md` (resume block at the top) so it stays current.

## Recording setup

- Screen: 1920×1080, browser at 100% zoom, one window, the light editorial theme as shipped (2026-09-14 redesign). Close other tabs.
- Terminal window pre-sized on the right for the AgentCore invoke and the curl coda, font 16pt.
- Start state: `Reset demo` pressed, page at the top (opening scene), guardian input empty.
- Voice: record voiceover separately after the screen capture if timing is tight. QuickTime or OBS both fine.
- Total runtime target 4:30, hard cap 5:00. Rehearse with a stopwatch; cut the gate-illustration beat first if long.
- Title card: product name, one-line pitch, "Strands Agents SDK · Amazon Bedrock AgentCore". Closing card: repo URL, both names.

## Slides (only two)

1. Title card (5 s).
2. Architecture diagram (about 30 s of voiceover: engine, gate, ledger, model at three edges, Runtime deployed).

Everything else is the live app.

## Devpost page checklist

- Title: Immigration Status Guardian. Tagline: "One engine that reads the government so you don't have to."
- Description: paste from the draft; add one screenshot at the top.
- Public repo URL, video URL, Builder IDs, track: Everyday Agents.
- Optional live demo link: only if hosted without upload, or not at all.

## Risks and mitigations

- Bedrock blocked on Ani's account: record on the partner's account, or record in recorded mode and say so.
- The page has no CDN fonts, icons, or scripts since the 2026-09-14 redesign; nothing to preload. Reload once before recording anyway.
- Runtime invoke slow on cold start: run it once off-camera first.
- Video over 5 minutes: cut the decision-gate beat, then shorten the architecture voiceover.
