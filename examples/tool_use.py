"""Tool use over the Anthropic Messages format with a non-Claude model.

    pip install anthropic
    export ANTHROPIC_BASE_URL=https://argolink.io   # root origin: the SDK adds /v1/messages
    export ANTHROPIC_API_KEY=your-key
    python examples/tool_use.py glm-5.3 "Which of our services are on a Node version past end of life?"

The model asks for the tool, the script runs it and returns a tool_result, and the
loop ends when the model answers in text. Works the same with claude-sonnet-5,
deepseek-v4-pro, kimi-k2.7-code or grok-4.7.
"""
import json
import sys

import anthropic

# A local, deterministic "tool": the data a real one would fetch from your inventory.
SERVICES = {
    "billing-api": {"runtime": "node", "version": "18.20"},
    "search-indexer": {"runtime": "node", "version": "22.11"},
    "auth-gateway": {"runtime": "node", "version": "16.20"},
    "report-worker": {"runtime": "python", "version": "3.12"},
}

TOOLS = [
    {
        "name": "list_services",
        "description": "List deployed services with their runtime and runtime version.",
        "input_schema": {
            "type": "object",
            "properties": {"runtime": {"type": "string", "description": "Filter by runtime, e.g. node"}},
            "required": [],
        },
    }
]


def list_services(runtime=None):
    return {name: info for name, info in SERVICES.items() if runtime in (None, info["runtime"])}


def run(model: str, question: str, max_rounds: int = 6) -> str:
    client = anthropic.Anthropic()  # reads ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY
    messages = [{"role": "user", "content": question}]
    for _ in range(max_rounds):
        reply = client.messages.create(model=model, max_tokens=4096, tools=TOOLS, messages=messages)
        # Send the assistant turn back exactly as received (thinking blocks included).
        messages.append({"role": "assistant", "content": reply.content})
        calls = [block for block in reply.content if block.type == "tool_use"]
        if reply.stop_reason != "tool_use" or not calls:
            print(f"usage: {reply.usage.input_tokens} in / {reply.usage.output_tokens} out", file=sys.stderr)
            return "".join(block.text for block in reply.content if block.type == "text")
        results = []
        for call in calls:
            output = list_services(**call.input) if call.name == "list_services" else {"error": "unknown tool"}
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(output)})
        messages.append({"role": "user", "content": results})
    raise RuntimeError(f"no final answer after {max_rounds} rounds")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit('usage: python examples/tool_use.py MODEL_ID "question"')
    print(run(sys.argv[1], sys.argv[2]))
