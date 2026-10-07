# Anthropic Messages API for any model — `/v1/messages` with GLM, DeepSeek, Kimi, Grok and Claude

Call non-Claude models in the Anthropic Messages format without running a local proxy: which models answer on `/v1/messages`, what changes in the conversion, and examples you can run with the official Anthropic SDKs. The hosted endpoint used here is [ArgoLink](https://argolink.io/gh-claude-api-bridge)'s, which accepts the Messages shape for every text model except OpenAI's.

[Model matrix](#which-models-answer-on-v1messages) · [Setup](#setup) · [Effort mapping](#effort-and-thinking) · [Tool use](#tool-use) · [Prices](#price-per-1m-tokens) · [FAQ](#faq)

<sub>Checked 2026-10-07 against the public model pages and catalog. `python check_endpoints.py` re-checks them and prints what changed. Unofficial; not affiliated with Anthropic.</sub>

## What you get

- **One request shape for 19 of the 28 text models**: Claude answers in its own format; DeepSeek, GLM and Kimi requests are converted to Chat Completions, Grok requests to Responses.
- **JSON by default, SSE with `"stream": true`**: the stream emits `message_start`, content-block events, `message_delta` and `message_stop`.
- **Tool use**: `tools`, `tool_use` and `tool_result` blocks work on every converted model.
- **Effort**: `output_config.effort` is passed to each model's own reasoning control.
- **Either header**: `x-api-key` or `Authorization: Bearer`, plus `anthropic-version: 2023-06-01`. The model ID does not have to start with `claude-`.

## Which models answer on /v1/messages

`native` is the model's own protocol. `converted` means the gateway translates the request and the response. `—` means the endpoint is not open for that model: OpenAI models take `/v1/responses` and `/v1/chat/completions` only.

| Model ID | Vendor | `/v1/messages` | `/v1/chat/completions` | `/v1/responses` | Context | Input / output per 1M |
|---|---|---|---|---|---:|---:|
| `claude-fable-5` | anthropic | native | converted | converted | 1,000,000 | $4 / $20 |
| `claude-fable-5-1` | anthropic | native | converted | converted | 1,000,000 | $4 / $20 |
| `claude-opus-4-8` | anthropic | native | converted | converted | 1,000,000 | $2 / $10 |
| `claude-opus-5` | anthropic | native | converted | converted | 1,000,000 | $2 / $10 |
| `claude-opus-5-5` | anthropic | native | converted | converted | 1,000,000 | $1.6 / $8 |
| `claude-sonnet-5` | anthropic | native | converted | converted | 1,000,000 | $0.8 / $4 |
| `deepseek-v4-pro` | deepseek | converted | native | converted | 1,048,576 | $0.528 / $1.584 |
| `deepseek-v4.1-flash` | deepseek | converted | native | converted | 1,048,576 | $0.12 / $0.48 |
| `kimi-k2.6` | kimi | converted | native | converted | 262,144 | $0.76 / $3.2 |
| `kimi-k2.7-code` | kimi | converted | native | converted | 262,144 | $0.76 / $3.2 |
| `kimi-k3` | kimi | converted | native | converted | 1,048,576 | $2.4 / $12 |
| `gpt-5.4` | openai | — | converted | native | 1,050,000 | $0.75 / $4.5 |
| `gpt-5.4-mini` | openai | — | converted | native | 400,000 | $0.225 / $1.35 |
| `gpt-5.5` | openai | — | converted | native | 1,050,000 | $1.5 / $9 |
| `gpt-5.6-luna` | openai | — | converted | native | 1,050,000 | $0.06 / $0.36 |
| `gpt-5.6-sol` | openai | — | converted | native | 1,050,000 | $1.5 / $9 |
| `gpt-5.6-terra` | openai | — | converted | native | 1,050,000 | $0.6 / $3.6 |
| `gpt-6-astra` | openai | — | converted | native | 1,050,000 | $3 / $15 |
| `gpt-6-sol` | openai | — | converted | native | 1,050,000 | $0.6 / $3 |
| `gpt-6.1-sol` | openai | — | converted | native | 1,050,000 | $0.6 / $3 |
| `glm-5.1` | zhipu | converted | native | converted | 200,000 | $1.12 / $3.52 |
| `glm-5.2` | zhipu | converted | native | converted | 1,000,000 | $1.12 / $3.52 |
| `glm-5.3` | zhipu | converted | native | converted | 1,000,000 | $1.12 / $3.52 |
| `glm-5.3-flash` | zhipu | converted | native | converted | 1,000,000 | $0.12 / $0.4 |
| `glm-5.3-flashx` | zhipu | converted | native | converted | 1,000,000 | $0.296 / $1 |
| `grok-4.5` | xai | converted | converted | native | 500,000 | $0.6 / $1.8 |
| `grok-4.6` | xai | converted | converted | native | 500,000 | $0.6 / $1.8 |
| `grok-4.7` | xai | converted | converted | native | 500,000 | $0.6 / $1.8 |

The same data is in [`endpoints.json`](./endpoints.json) with output caps and effort levels, so a script can read it instead of this table.

## Setup

The Anthropic SDKs add `/v1/messages` to the base URL themselves, so the base URL is the bare origin `https://argolink.io`, not `.../v1`.

| Variable | Read by | Sent as |
|---|---|---|
| `ANTHROPIC_BASE_URL` | Python and TypeScript SDKs, Claude Code | request origin |
| `ANTHROPIC_API_KEY` | same | `x-api-key` header |
| `ANTHROPIC_AUTH_TOKEN` | same | `Authorization: Bearer` header |

```bash
export ANTHROPIC_BASE_URL=https://argolink.io
export ANTHROPIC_API_KEY=your-key      # create one in the console at argolink.io
```

### Python

```python
import anthropic

client = anthropic.Anthropic()  # picks up both variables
message = client.messages.create(
    model="glm-5.3",
    max_tokens=2048,
    system="You review SQL migrations.",
    messages=[{"role": "user", "content": "Is adding a NOT NULL column with a default safe on a 50M-row table?"}],
)
print("".join(block.text for block in message.content if block.type == "text"))
```

Read text by block `type`, not by position: Claude and the always-thinking models can return `thinking` blocks before the first `text` block.

### TypeScript

[`examples/stream.mjs`](./examples/stream.mjs) streams from `deepseek-v4-pro` with `@anthropic-ai/sdk`:

```js
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const stream = client.messages.stream({
  model: "deepseek-v4-pro",
  max_tokens: 2048,
  output_config: { effort: "low" },
  messages: [{ role: "user", content: "Explain write-ahead logging in five sentences" }],
});
stream.on("text", (text) => process.stdout.write(text));
console.error((await stream.finalMessage()).usage);
```

### cURL

[`examples/messages.sh`](./examples/messages.sh) sends one request to `claude-sonnet-5`, `glm-5.3` and `deepseek-v4.1-flash`; only `model` changes.

```bash
curl https://argolink.io/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "kimi-k2.7-code", "max_tokens": 1024,
       "messages": [{"role": "user", "content": "Refactor this Go loop to use a worker pool"}]}'
```

Without a key the endpoint answers `401 API_KEY_REQUIRED`, which is a quick way to confirm the URL before you add credentials.

## What survives the conversion

What the model pages document for each converted family:

| Messages feature | Claude (native) | DeepSeek, GLM, Kimi (to Chat Completions) | Grok (to Responses) |
|---|---|---|---|
| `system`, `messages`, `max_tokens`, `stream` | yes | yes | yes |
| `tools`, `tool_use`, `tool_result` | yes | yes | yes |
| Image blocks | `url` or `base64` source | `base64` only, and only on models that read images (`deepseek-v4.1-flash`, `glm-5.3-flash`, `glm-5.3-flashx`, `kimi-k3`); image URLs are dropped | `base64` only; image URLs are dropped |
| `output_config.effort` | the model's own levels | mapped to `reasoning_effort`; sent as `medium` when left out | same as the column on the left |
| `cache_control` | 5 minutes, or 1 hour with `"ttl": "1h"` | not documented | not documented |
| Server-side tools such as web search | not documented | dropped | dropped |

`deepseek-v4-pro`, `glm-5.1`, `glm-5.2`, `glm-5.3`, `kimi-k2.6` and `kimi-k2.7-code` read no images on any endpoint.

## Effort and thinking

On converted models, the effort you send in `output_config.effort` lands on the model's `reasoning_effort`. When you leave it out, the gateway sends `medium`, which several models round to `high`. That differs from their Chat Completions default, so a Messages request to `glm-5.3` runs at `high` while the same prompt on Chat Completions runs at `max`.

| Model | Levels that reach the model | Rounding | Left out on `/v1/messages` |
|---|---|---|---|
| `deepseek-v4-pro` | low, high, max | minimal→low; medium, xhigh→high | `high` (always thinks) |
| `deepseek-v4.1-flash` | low, high, max | minimal→low; medium, xhigh→high | `high` |
| `glm-5.3` | low, high, max | medium→high; xhigh→max | `high` (always thinks) |
| `glm-5.3-flash`, `glm-5.3-flashx` | high, max | low, medium→high; xhigh→max | `high` |
| `glm-5.2` | high, max | low, medium→high; xhigh→max | `high` |
| `grok-4.6`, `grok-4.7` | low, medium, high, xhigh | max→high | `medium` |
| `grok-4.5` | low, medium, high | xhigh, max→high | `medium` |
| `kimi-k2.7-code` | none | leave effort out | always thinks |

Claude models keep their own defaults: `high` on Opus 5, Opus 4.8, Sonnet 5 and both Fable models, `medium` on Opus 5.5. Claude rejects manual `thinking.budget_tokens`; set the depth with effort.

Turning thinking off on `deepseek-v4.1-flash`, `glm-5.1` or `glm-5.2` takes `reasoning_effort: "none"` on `/v1/chat/completions`. The docs verified the thinking controls on Chat Completions only, so send them there when they must take effect.

## Tool use

[`examples/tool_use.py`](./examples/tool_use.py) runs a complete loop against any model ID:

```bash
pip install anthropic
python examples/tool_use.py glm-5.3 "Which of our services are on a Node version past end of life?"
```

The loop follows three rules that hold for Claude and for converted models:

1. Append the assistant turn exactly as received, `thinking` blocks included. Claude rejects edited or dropped thinking blocks with a 400.
2. Answer every `tool_use` block with a `tool_result` carrying its `tool_use_id`, all in the next user turn.
3. Stop when `stop_reason` is not `tool_use`, and cap the number of rounds.

Forcing a tool with `tool_choice` `any` or `tool` returns an error on `claude-opus-5-5` and `claude-fable-5-1`; use `auto` there.

## Clients that only speak Messages

Some coding tools build their requests with the Anthropic SDK, others with the Vercel AI SDK, and the two expect different base URLs:

| Client | Base URL to enter | Why |
|---|---|---|
| Claude Code | `https://argolink.io` | appends `/v1/messages` itself |
| Claude Agent SDK | `https://argolink.io` in `env` | passes the variables to the Claude Code process it starts |
| Qwen Code, `anthropic` provider | `https://argolink.io` | uses `@anthropic-ai/sdk` |
| Cline, Anthropic provider with custom base URL | `https://argolink.io/v1` | uses `@ai-sdk/anthropic`, whose base already ends in `/v1` |
| OpenCode, `anthropic` provider `baseURL` | `https://argolink.io/v1` | same AI SDK package |

Anthropic's Claude Code documentation says it does not support routing Claude Code to non-Claude models through any gateway. Requests to `glm-5.3` or `deepseek-v4-pro` reach the model through the conversion above, but Claude Code features that depend on Claude behavior may not work.

## Price per 1M tokens

Rates for the models people most often move to the Messages format. Each vendor's own figure, checked on the date shown.

| Model | ArgoLink input / output | Vendor list input / output | Vendor source |
|---|---:|---:|---|
| `glm-5.3` | $1.12 / $3.52 | $1.40 / $4.40 | [Z.ai pricing](https://docs.z.ai/guides/overview/pricing) |
| `deepseek-v4-pro` | $0.528 / $1.584 | $0.66 / $1.98 | [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing) |
| `deepseek-v4.1-flash` | $0.12 / $0.48 | $0.15 / $0.60 | same |
| `grok-4.7` | $0.60 / $1.80 | $2.00 / $6.00 | [xAI models](https://docs.x.ai/docs/models) |
| `claude-sonnet-5` | $0.80 / $4 | $2 / $10 | [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| `claude-opus-5-5` | $1.60 / $8 | $4 / $20 | same |

<sub>All checked 2026-10-07. DeepSeek bills twice its off-peak rate on weekdays 01:00–04:00 and 06:00–10:00 UTC; the ArgoLink DeepSeek rates double in the same hours (09:00–12:00 and 14:00–18:00 Beijing time). Reasoning tokens are billed as output tokens everywhere.</sub>

## Keeping the matrix current

```bash
python check_endpoints.py           # exit 1 and list the drift if a page changed
python check_endpoints.py --write   # rewrite endpoints.json
python check_endpoints.py --table   # print the Markdown table above
```

The script reads the public catalog at `/api/catalog/v1/models` and each model page, so it needs no key. Run it in CI on a schedule to catch a model that gains or loses an endpoint.

## FAQ

**Can I call GPT-6 Sol through `/v1/messages`?**
No. The Messages endpoint is not open for OpenAI models. Use `/v1/responses`, their own format, or `/v1/chat/completions`.

**Which base URL does the Anthropic Python SDK need?**
The origin without a path: `https://argolink.io`. With `https://argolink.io/v1` the SDK requests `/v1/v1/messages`, which returns 404.

**Why was my image ignored by a converted model?**
Converted models drop image URLs. Send the image as a `base64` source, and pick a model that reads images.

**Why does `deepseek-v4-pro` keep thinking when I send `thinking: {"type": "disabled"}`?**
DeepSeek V4 Pro always thinks; the setting is ignored. Lower `output_config.effort` to `low` to spend fewer reasoning tokens.

**Does a Messages request cost more than the same request on Chat Completions?**
Prices are per model, not per endpoint. The bill can still differ when the protocol changes the default effort, because that changes how many reasoning tokens the model produces.

**Is there a bridge process to install?**
No. The conversion happens on the hosted endpoint; this repository holds the matrix, the examples and the checker.

## Run the tests

```bash
pip install pytest
pytest tests/
```

The tests parse page fragments in memory and make no network calls.

## License

MIT
