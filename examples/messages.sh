#!/usr/bin/env bash
# Send one Anthropic Messages request to three model families and print the text.
# Only the "model" field changes; the request and response shapes stay Anthropic's.
set -euo pipefail
: "${ANTHROPIC_API_KEY:?export ANTHROPIC_API_KEY first}"
BASE="${ANTHROPIC_BASE_URL:-https://argolink.io}"

for MODEL in claude-sonnet-5 glm-5.3 deepseek-v4.1-flash; do
  echo "== $MODEL"
  curl -fsS "$BASE/v1/messages" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "{
      \"model\": \"$MODEL\",
      \"max_tokens\": 1024,
      \"system\": \"Answer in two sentences.\",
      \"messages\": [{\"role\": \"user\", \"content\": \"What does an idempotency key protect against?\"}]
    }" | jq -r '(.content[] | select(.type == "text") | .text), "usage: \(.usage.input_tokens) in / \(.usage.output_tokens) out"'
done
