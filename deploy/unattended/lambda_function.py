"""Scheduled invoker for the AgentCore Runtime (the "unattended run").

EventBridge Scheduler -> this Lambda -> InvokeAgentRuntime with
{"check": "bulletin", "month": ..., "notify_topic_arn": ...}. The Runtime
runs the same engine/gate/ledger as the UI and publishes one SNS ping only
if the gate surfaces. Environment: AGENT_RUNTIME_ARN, TOPIC_ARN, optional
MONTH (default 2025-10). The event may override "month".
"""

import json
import os
import uuid

import boto3

_client = None


def _runtime_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _client


def build_payload(event: dict | None) -> dict:
    event = event or {}
    return {
        "check": "bulletin",
        "month": str(event.get("month") or os.environ.get("MONTH", "2025-10")),
        "notify_topic_arn": os.environ["TOPIC_ARN"],
    }


def handler(event, context):
    payload = build_payload(event)
    response = _runtime_client().invoke_agent_runtime(
        agentRuntimeArn=os.environ["AGENT_RUNTIME_ARN"],
        runtimeSessionId=f"scheduled-{uuid.uuid4()}",  # >= 33 chars, unique per run
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(payload).encode("utf-8"),
    )
    body = response["response"].read() if hasattr(response.get("response"), "read") else response.get("response")
    try:
        result = json.loads(body)
    except (TypeError, ValueError):
        result = {"raw": body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else str(body)}
    print(json.dumps({"scheduled_check": payload, "result": result}))
    return result
