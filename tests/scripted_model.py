"""A Strands Model double for offline agent tests.

Plays a script: each entry is either ("tool", name, input_dict) or
("text", string). The agent loop sees real tool-use events, executes the real
tools, and feeds results back exactly as it would with Bedrock, so the tests
exercise Strands' actual tool registration and loop, not a mock of it.
"""

import json

from strands.models import Model


class ScriptedModel(Model):
    def __init__(self, script):
        self.script = list(script)
        self.calls = []  # one entry per model invocation: {"tools": [...], "system_prompt": ..., "messages": [...]}
        self.config = {}

    def update_config(self, **config):
        self.config.update(config)

    def get_config(self):
        return self.config

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError("not used by the guardian")

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.calls.append(
            {
                "tools": [spec["name"] for spec in (tool_specs or [])],
                "system_prompt": system_prompt,
                "messages": [json.loads(json.dumps(m, default=str)) for m in messages],
            }
        )
        step = self.script.pop(0) if self.script else ("text", "(script exhausted)")
        yield {"messageStart": {"role": "assistant"}}
        if step[0] == "tool":
            _, name, tool_input = step
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"use-{len(self.calls)}", "name": name}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(tool_input)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockDelta": {"delta": {"text": step[1]}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}, "metrics": {"latencyMs": 1}}}

    def last_tool_result(self):
        """The toolResult block the agent fed back on the most recent call."""
        for message in reversed(self.calls[-1]["messages"]):
            for block in message.get("content", []):
                if "toolResult" in block:
                    return block["toolResult"]
        return None
