// Stream a Messages response from any model ID with the official Anthropic SDK.
//
//   npm install @anthropic-ai/sdk
//   export ANTHROPIC_BASE_URL=https://argolink.io   # root origin, no /v1
//   export ANTHROPIC_API_KEY=your-key
//   node examples/stream.mjs deepseek-v4-pro "Explain write-ahead logging in five sentences"

import Anthropic from "@anthropic-ai/sdk";

const [model = "deepseek-v4-pro", prompt = "Explain write-ahead logging in five sentences"] = process.argv.slice(2);

const client = new Anthropic(); // reads ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY

const stream = client.messages.stream({
  model,
  max_tokens: 2048,
  // Converted models map this to their own reasoning_effort; left out, it is sent as medium.
  output_config: { effort: "low" },
  messages: [{ role: "user", content: prompt }],
});

stream.on("text", (text) => process.stdout.write(text));

const message = await stream.finalMessage();
console.error(`\n${message.usage.input_tokens} in / ${message.usage.output_tokens} out, stop: ${message.stop_reason}`);
