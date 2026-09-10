"""AgentCore Runtime entrypoint — Day-3 bonus, time-boxed (see
docs/architecture-spec.md §4.1 and §9). Wraps the same deterministic
pipeline used locally; does not change any engine/pack logic.

UNVERIFIED: written from Strands' documented deploy contract
(strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python/)
but not yet run against a live AgentCore Runtime or the `bedrock-agentcore`
package in this environment (no AWS/AgentCore CLI access here). Verify the
`BedrockAgentCoreApp` import path and the exact CLI commands
(`agentcore configure/launch/invoke` vs. newer `agentcore create/dev/deploy`)
against current docs before relying on this — both surfaces exist and are
evolving. Local dev/test: `python deploy/agentcore_entrypoint.py`, then
`curl -X POST http://localhost:8080/invocations -d '{"prompt": "..."}'`.
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent.engine.store import Store
from agent.packs.immigration.pipeline import run_discrepancy_check

app = BedrockAgentCoreApp()
_store = Store("data/agentcore_demo.db")


@app.entrypoint
def invoke(payload: dict) -> dict:
    fields = payload["fields"]
    clock_id = payload.get("clock_id", "demo-clock")
    event_id = payload.get("event_id", "demo-event")

    result = run_discrepancy_check(_store, clock_id=clock_id, event_id=event_id, fields=fields)

    return {
        "alert": {"decision": result.alert.decision, "reason": result.alert.reason},
        "draft": {"subject": result.draft.subject, "body": result.draft.body} if result.draft else None,
    }


if __name__ == "__main__":
    app.run()
