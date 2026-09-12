"""FastAPI backend for the local demo. No AgentCore dependency — this is
the "local-first" surface from the plan; AgentCore Runtime deployment
wraps the same pipeline functions later (deploy/agentcore_entrypoint.py)
without changing any of this logic.
"""

import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from strands.models import Model

from agent.config import BEDROCK_MODEL_ID, RULE_VERSION
from agent.engine.decision_gate import GateInputs, evaluate_gate
from agent.engine.store import ResetEpochMismatch, Store
from agent.llm.document_client import FailoverExtractionClient, build_extraction_client
from agent.llm.draft import build_bedrock_agent
from agent.llm.guardian import ask_in_session, build_guardian_agent, build_guardian_model, build_guardian_tools, tool_names
from agent.notify import send_email
from agent.packs.immigration.bulletin import PRIOR_CAPTURED_MONTH, load_seeded_case, run_bulletin_poll
from agent.packs.immigration.pipeline import SPECIMENS_DIR, run_case_from_documents
from agent.packs.immigration.scenarios import coherent_recorded_scenario, get_scenario, known_specimen_hashes, scenario_summaries, sha256_bytes
from agent.packs.recalls.feed import get_recall_item
from agent.packs.recalls.pipeline import run_recall_check

REPO_ROOT = Path(__file__).resolve().parent.parent
RECALLS_FIXTURES_DIR = REPO_ROOT / "fixtures" / "recalls"

IMMIGRATION_CLOCK_ID = "immigration-demo-user"
_SAMPLE_DOCUMENT_KEYS = {"i94", "i797", "passport"}

APPROVE_ACTION = "approve_for_attorney_review"
SESSION_TTL_SECONDS = 30 * 60
SESSION_CAP = 50


def _load_receipts() -> dict:
    return json.loads((RECALLS_FIXTURES_DIR / "receipts.json").read_text())


class RecallCheckRequest(BaseModel):
    receipt: str  # "seeded" or "unmatched" — picks a fixture receipt for the demo


class BulletinPollRequest(BaseModel):
    month: str  # "2025-09" or "2025-10" — which captured bulletin month to simulate polling


class SubmissionRef(BaseModel):
    clock_id: str
    event_id: str
    rule_version: str


class AskRequest(BaseModel):
    question: str  # free text for the guardian agent (agent/llm/guardian.py)
    # The {clock_id, event_id, rule_version} from a prior /api/process-documents
    # response, so check_uploaded_case can discuss that specific case instead
    # of only the bundled sample. Omit if no case has been uploaded yet.
    submission_ref: SubmissionRef | None = None
    session_id: str | None = None  # keep the conversation across questions (per page load)


class ApproveDraftRequest(BaseModel):
    clock_id: str
    event_id: str
    rule_version: str
    send_to: str | None = None  # optional attorney address; only used when SES is configured


def _public_demo() -> bool:
    return os.environ.get("GUARDIAN_PUBLIC_DEMO", "") not in ("", "0", "false", "False")


def _ses_sender() -> str | None:
    return os.environ.get("GUARDIAN_SES_SENDER") or None


class _RateLimiter:
    """Small in-memory per-client limiter for the public demo: `limit`
    requests per `window` seconds, keyed by client address."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


_PRIOR_BULLETIN_MONTH = PRIOR_CAPTURED_MONTH


def create_app(
    db_path: str = "data/demo.db",
    attempt_live_recall_feed: bool = False,
    guardian_model: Model | None = None,
    auto_guardian_model: bool = True,
    extraction_client=None,
    ses_client=None,
    public_demo: bool | None = None,
) -> FastAPI:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    store = Store(db_path)
    public_demo = _public_demo() if public_demo is None else public_demo
    limiter = _RateLimiter(limit=int(os.environ.get("GUARDIAN_RATE_LIMIT", "40")), window=60.0)
    sessions: dict[str, dict] = {}
    upload_limiter = _RateLimiter(limit=int(os.environ.get("GUARDIAN_UPLOAD_RATE_LIMIT", "8")), window=60.0)
    # None when no AWS credentials are configured (e.g. this sandbox) — the
    # pipeline's deterministic core is a fully correct draft either way; a
    # real Agent only adds personalization when Bedrock is actually reachable.
    bedrock_agent = build_bedrock_agent(model_id=BEDROCK_MODEL_ID)
    # "live" only when real AWS credentials are configured; otherwise a
    # deterministic recorded replay of the same specimen images (C1) — the
    # mode is surfaced in every response below so the UI never presents a
    # recorded replay as a live parse.
    if extraction_client is None:
        extraction_client, extraction_mode = build_extraction_client()
    else:
        # Tests inject a "live" client that behaves like a denied account;
        # wrap it so the same failover path is exercised.
        if not isinstance(extraction_client, FailoverExtractionClient):
            extraction_client = FailoverExtractionClient(extraction_client)
        extraction_mode = extraction_client.mode
    # attempt_live_recall_feed defaults to False so create_app() (used
    # throughout the test suite) never makes a real network call — the
    # actual running app (bottom of this file) turns it on. Either way the
    # fetched-or-fallback recall is resolved once at startup, not per
    # request, and its mode is surfaced in every response (C4).
    recall_item, recall_mode = get_recall_item(attempt_live=attempt_live_recall_feed)

    def _build_guardian_tools(current_submission_ref: dict[str, str] | None = None) -> list:
        # The conversational front door: a Strands Agent whose only tools are
        # the engine's checks, bound to this app's store and clients. Built
        # fresh per /api/ask call so check_uploaded_case can be bound to that
        # request's specific submission reference (see agent/llm/guardian.py)
        # rather than stale server-side "last upload" state.
        return build_guardian_tools(
            store,
            extraction_client=extraction_client,
            extraction_mode=extraction_mode,
            model_id=BEDROCK_MODEL_ID,
            recall_item=recall_item,
            recall_mode=recall_mode,
            receipts_loader=_load_receipts,
            prior_bulletin_months=_PRIOR_BULLETIN_MONTH,
            draft_agent=bedrock_agent,
            current_submission_ref=current_submission_ref,
        )

    # Tool names are identical regardless of the ref (only check_uploaded_case's
    # *behavior* depends on it), so a single no-ref build is enough for the
    # tool-listing shown when the guardian model is unavailable.
    guardian_tools = _build_guardian_tools()
    if guardian_model is None and auto_guardian_model:
        guardian_model = build_guardian_model(BEDROCK_MODEL_ID)
    app = FastAPI(title="Immigration Status Guardian — demo backend")

    def draft_payload(draft, clock_id: str, event_id: str, rule_version: str, kind: str) -> dict | None:
        """Every draft carries the ledger key it belongs to (so the UI can
        act on it) and whether a human already approved it."""
        if draft is None:
            return None
        receipt = store.get_action(clock_id, event_id, rule_version, APPROVE_ACTION)
        return {
            "subject": draft.subject,
            "body": draft.body,
            "used_llm_personalization": bool(draft.used_llm_personalization),
            "kind": kind,
            "ref": {"clock_id": clock_id, "event_id": event_id, "rule_version": rule_version},
            "approved_at": receipt.created_at if receipt else None,
        }

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # Never a bare 500 with a text body: the UI's fetch helper shows
        # this message instead of failing silently.
        return JSONResponse(status_code=500, content={"error": f"{type(exc).__name__}: {exc}"})

    @app.middleware("http")
    async def _public_demo_guards(request: Request, call_next):
        # Public demo only: per-client request caps so a shared URL cannot
        # be turned into a Bedrock bill. Local runs are unlimited.
        if public_demo and request.url.path.startswith("/api/"):
            client_key = request.client.host if request.client else "unknown"
            active = upload_limiter if request.url.path == "/api/process-documents" else limiter
            if not active.allow(client_key):
                return JSONResponse(status_code=429, content={"error": "Too many requests for the public demo. Wait a minute and try again."})
        return await call_next(request)

    @app.get("/api/config")
    def config():
        """What this deployment can do, so the UI never offers an action
        the backend cannot honestly perform."""
        return {
            "public_demo": public_demo,
            "email_enabled": bool(_ses_sender()),
            "notice": (
                "Public demo: synthetic documents only. Uploads are limited to the bundled sample sets; "
                "do not upload real immigration papers here."
                if public_demo
                else None
            ),
        }

    @app.get("/api/scenarios")
    def scenarios():
        """The bundled sample scenarios (discrepant / matching / ambiguous)
        and whether each can run offline (has a recorded Bedrock response)."""
        return {"scenarios": scenario_summaries()}

    @app.get("/api/sample-documents/{key}")
    def sample_document(key: str, scenario: str = "discrepant"):
        """Serves the synthetic I-94/I-797/passport specimen images for
        download so a user can visibly select/upload them — the upload flow
        then processes exactly those selected bytes (R2/product feedback).
        `scenario` picks which bundled set (see agent/packs/immigration/scenarios.py)."""
        if key not in _SAMPLE_DOCUMENT_KEYS:
            raise HTTPException(status_code=404, detail="unknown sample document")
        try:
            chosen = get_scenario(scenario)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None
        path = chosen.specimen_path(key)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"scenario '{scenario}' has no {key} specimen")
        return FileResponse(path, media_type="image/png")

    @app.post("/api/process-documents")
    async def process_documents(i94: UploadFile, i797: UploadFile, passport: UploadFile):
        """Runs the real extraction path against the caller's actually-
        selected upload bytes, once, and returns evidence, the discrepancy
        decision, and the attorney draft from that single pass (R2) — never
        a second, independent extraction.

        The synchronous pipeline (Bedrock/Strands calls, SQLite writes) is
        offloaded to the threadpool (F4): this is an async handler only to
        `await` the upload reads, so a slow extraction never blocks other
        requests on the event loop. The epoch is captured before that slow
        work starts so a reset that happens while this request is in flight
        aborts it instead of letting it recreate rows just after the reset
        cleared them (see Store.reset/ResetEpochMismatch).
        """
        documents = {"i94": await i94.read(), "i797": await i797.read(), "passport": await passport.read()}
        if public_demo:
            known = known_specimen_hashes()
            provenance = {key: sha256_bytes(data) for key, data in documents.items()}
            if any(provenance[key] not in known for key in documents):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "This public demo only processes the bundled synthetic sample documents. "
                        "Use 'Download sample' or 'Load bundled sample & process', and never upload real papers here."
                    },
                )
        epoch = store.current_epoch()
        try:
            result = await run_in_threadpool(
                run_case_from_documents,
                store,
                clock_id=IMMIGRATION_CLOCK_ID,
                client=extraction_client,
                mode=extraction_mode,
                model_id=BEDROCK_MODEL_ID,
                documents=documents,
                agent=bedrock_agent,
                expected_epoch=epoch,
            )
        except ResetEpochMismatch:
            return {
                "mode": extraction_mode,
                "mode_reason": None,
                "fields": {},
                "evidence": {},
                "statuses": {},
                "needs_review": True,
                "error": "The demo was reset while this upload was still processing. Please upload and process again.",
                "alert": None,
                "draft": None,
            }
        draft = None
        if result.ref is not None:
            draft = draft_payload(result.draft, result.ref["clock_id"], result.ref["event_id"], result.ref["rule_version"], "attorney_review")
        return {
            "mode": result.extraction.mode,
            "mode_reason": result.extraction.mode_reason,
            "fields": result.extraction.fields,
            "evidence": result.extraction.evidence,
            "statuses": result.extraction.statuses,
            "needs_review": result.extraction.needs_review,
            "error": result.error,
            "alert": {"decision": result.alert.decision, "reason": result.alert.reason} if result.alert else None,
            "draft": draft,
            "ref": result.ref,
        }

    @app.get("/api/gate-demo")
    def gate_demo():
        """Illustrates the decision gate narration for the demo: several
        events processed, most staying silent, exactly one surfacing."""
        scenarios = [
            {"label": "discrepancy found", "material": True, "actionable": True, "window_open": True},
            {"label": "no discrepancy", "material": False, "actionable": False, "window_open": False},
            {"label": "discrepancy already reviewed", "material": True, "actionable": True, "window_open": False},
        ]
        results = []
        for i, s in enumerate(scenarios):
            inputs = GateInputs(
                clock_id="gate-demo",
                event_id=f"evt-{i}",
                rule_version="v1",
                material=s["material"],
                actionable=s["actionable"],
                window_open=s["window_open"],
                prior_alerts=[],
            )
            alert = evaluate_gate(inputs)
            results.append({"label": s["label"], "decision": alert.decision, "reason": alert.reason})
        return {"results": results}

    @app.post("/api/bulletin-poll")
    def bulletin_poll(req: BulletinPollRequest):
        """Simulates the unattended scheduled poll firing for one captured
        bulletin month (C3) — no user upload involved, same shared engine/
        gate/persistence/draft path as the discrepancy check. This is a
        separate seeded monitoring example (a different case than whatever
        was just uploaded above), not derived from the uploaded documents."""
        case = load_seeded_case()
        result = run_bulletin_poll(
            store,
            clock_id="bulletin-clock",
            month=req.month,
            case=case,
            agent=bedrock_agent,
            previous_month=_PRIOR_BULLETIN_MONTH.get(req.month),
        )
        return {
            "case_name": case.case_name,
            "priority_date": case.priority_date,
            "error": result.error,
            "cutoff_status": result.cutoff.status if result.cutoff else None,
            "alert": {"decision": result.alert.decision, "reason": result.alert.reason} if result.alert else None,
            "draft": draft_payload(
                result.draft, "bulletin-clock", f"bulletin-{req.month}-{case.category}", RULE_VERSION, "attorney_review"
            ),
        }

    @app.post("/api/recalls/check")
    def recalls_check(req: RecallCheckRequest):
        receipts = _load_receipts()
        receipt = receipts["seeded_receipt"] if req.receipt == "seeded" else receipts["unmatched_receipt"]
        result = run_recall_check(store, clock_id="recall-clock", recall_item=recall_item, receipt=receipt)
        return {
            "mode": recall_mode,
            "matched": result.match.matched,
            "message": result.match.message,
            "demo_scope": result.match.demo_scope,
            "alert": {"decision": result.alert.decision, "reason": result.alert.reason},
            "draft": draft_payload(
                result.draft,
                "recall-clock",
                f"recall-{recall_item.recall_id}-{receipt.get('receipt_id', 'unknown')}",
                RULE_VERSION,
                "recall_remedy",
            ),
        }

    @app.post("/api/reset")
    def reset_demo():
        """Demo control: clear the ledger so the sample case surfaces again.
        Bumps the store's epoch first, so any upload still processing when
        this runs aborts instead of writing its result back afterward."""
        store.reset()
        return {"reset": True}

    @app.post("/api/drafts/approve")
    def approve_draft(req: ApproveDraftRequest):
        """The one human action in the loop: approve a persisted draft for
        attorney review. Records an idempotent receipt; sends nothing (there
        is no mail transport in this build, and the UI never claims one)."""
        draft = store.get_draft(req.clock_id, req.event_id, req.rule_version)
        if draft is None or draft.status != "ready":
            return JSONResponse(status_code=404, content={"error": "No ready draft exists for that clock/event/rule version."})
        receipt = store.record_action(req.clock_id, req.event_id, req.rule_version, APPROVE_ACTION)
        delivery = None
        state = "Approved and ready to send"
        sender = _ses_sender()
        if req.send_to and sender:
            delivery = send_email(sender, req.send_to, draft.subject or "Document review needed", draft.body or "", client=ses_client).as_dict()
            state = f"Approved and sent to {req.send_to}" if delivery["sent"] else "Approved; email delivery failed"
        elif req.send_to and not sender:
            delivery = {"sent": False, "channel": "ses", "target": req.send_to, "message_id": None, "error": "email is not configured on this deployment (GUARDIAN_SES_SENDER unset)"}
            state = "Approved and ready to send"
        return {
            "approved": True,
            "already_approved": receipt.already_recorded,
            "state": state,
            "delivery": delivery,
            "receipt": {
                "clock_id": receipt.clock_id,
                "event_id": receipt.event_id,
                "rule_version": receipt.rule_version,
                "action_type": receipt.action_type,
                "created_at": receipt.created_at,
            },
        }

    @app.post("/api/ask")
    def ask(req: AskRequest):
        """One question, one fresh Strands agent run; the answer can only
        come from tool results (see agent/llm/guardian.py). If a submission
        reference is supplied, check_uploaded_case can discuss that specific
        upload instead of only the bundled sample."""
        names = tool_names(guardian_tools)
        if guardian_model is None:
            return {
                "available": False,
                "answer": None,
                "tools_called": [],
                "trace": [],
                "tools": names,
                "error": "The guardian agent needs a Bedrock model: configure AWS credentials with model access.",
            }
        ref = req.submission_ref.model_dump() if req.submission_ref else None
        tools = _build_guardian_tools(current_submission_ref=ref)
        # Multi-turn: one Strands Agent per session id (per page load) so a
        # follow-up question can build on the previous tool result. The
        # agent is rebuilt if the uploaded case changed, and sessions expire.
        now = time.monotonic()
        for stale in [sid for sid, s in sessions.items() if now - s["seen"] > SESSION_TTL_SECONDS]:
            sessions.pop(stale, None)
        session = sessions.get(req.session_id) if req.session_id else None
        if req.session_id and (session is None or session["ref"] != ref):
            if len(sessions) >= SESSION_CAP:
                sessions.pop(min(sessions, key=lambda sid: sessions[sid]["seen"]), None)
            session = {"agent": build_guardian_agent(guardian_model, tools), "ref": ref, "seen": now, "turns": 0}
            sessions[req.session_id] = session
        if session is not None:
            session["seen"] = now
            session["turns"] += 1
            result = ask_in_session(session["agent"], req.question)
        else:
            result = ask_in_session(build_guardian_agent(guardian_model, tools), req.question)
        return {
            "available": True,
            "question": req.question,
            "answer": result.answer,
            "tools_called": result.tools_called,
            "trace": result.trace_dicts(),
            "tools": tool_names(tools),
            "error": result.error,
            "session_id": req.session_id,
            "turn": session["turns"] if session is not None else 1,
        }

    ui_dir = REPO_ROOT / "ui"
    if ui_dir.exists():
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app


app = create_app(attempt_live_recall_feed=True)
