"""Offline tests for check_endpoints.py: page fragments stand in for the network."""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import check_endpoints  # noqa: E402

GLM_PAGE = """
<div class="model-api-endpoints" aria-labelledby="model-endpoints-title">
  <h3 id="model-endpoints-title">Endpoints</h3>
  <ul>
    <li><span class="model-method">POST</span><span class="model-endpoint-body"><strong>Recommended</strong><code>/v1/chat/completions</code><small>Z.ai&#39;s own format.</small></span></li>
    <li><span class="model-method">POST</span><span class="model-endpoint-body"><strong>Responses</strong><code>/v1/responses</code><small>Converted to Chat Completions.</small></span></li>
    <li><span class="model-method">POST</span><span class="model-endpoint-body"><strong>Anthropic Messages</strong><code>/v1/messages</code><small>Converted to Chat Completions.</small></span></li>
  </ul>
</div>
"""

GPT_PAGE = """
<div class="model-api-endpoints">
  <ul>
    <li><strong>Recommended</strong><code>/v1/responses</code><small>OpenAI&#39;s own format.</small></li>
    <li><strong>Chat Completions</strong><code>/v1/chat/completions</code><small>The messages format.</small></li>
  </ul>
</div>
"""

ITEMS = [
    {"id": "glm-5.3", "provider_id": "zhipu", "endpoint": "/v1/chat/completions",
     "text": {"context_tokens": 1000000, "max_output_tokens": 128000, "efforts": ["low", "high", "max"]},
     "pricing": {"effective": {"input_per_million": 1.12, "output_per_million": 3.52}}},
    {"id": "gpt-6-sol", "provider_id": "openai", "endpoint": "/v1/responses",
     "text": {"context_tokens": 1050000, "max_output_tokens": 128000},
     "pricing": {"effective": {"input_per_million": 0.6, "output_per_million": 3}}},
]


def test_recommended_endpoint_is_native_and_the_rest_converted():
    assert check_endpoints.parse_endpoints(GLM_PAGE) == {
        "/v1/chat/completions": "native",
        "/v1/responses": "converted",
        "/v1/messages": "converted",
    }


def test_missing_endpoint_block_yields_nothing():
    assert check_endpoints.parse_endpoints("<html><body>no api section</body></html>") == {}


def test_build_marks_protocols_a_model_does_not_accept_as_none():
    data = check_endpoints.build(ITEMS, {"glm-5.3": GLM_PAGE, "gpt-6-sol": GPT_PAGE}, "2026-10-07")
    gpt = data["models"]["gpt-6-sol"]
    assert gpt["protocols"]["/v1/messages"] is None
    assert gpt["protocols"]["/v1/responses"] == "native"
    assert data["models"]["glm-5.3"]["efforts"] == ["low", "high", "max"]
    assert data["checked"] == "2026-10-07"


def test_diff_reports_added_removed_and_changed_fields():
    old = check_endpoints.build(ITEMS, {"glm-5.3": GLM_PAGE, "gpt-6-sol": GPT_PAGE}, "2026-10-07")
    new = json.loads(json.dumps(old))
    new["models"]["glm-5.3"]["input_per_million"] = 1.0
    del new["models"]["gpt-6-sol"]
    new["models"]["glm-6"] = dict(old["models"]["glm-5.3"])
    lines = check_endpoints.diff(old, new)
    assert "~ glm-5.3.input_per_million: 1.12 -> 1.0" in lines
    assert "- gpt-6-sol (no longer listed)" in lines
    assert "+ glm-6 (new model)" in lines


def test_table_renders_dash_for_closed_protocols():
    data = check_endpoints.build(ITEMS, {"glm-5.3": GLM_PAGE, "gpt-6-sol": GPT_PAGE}, "2026-10-07")
    rendered = check_endpoints.table(data)
    assert "| `gpt-6-sol` | openai | — | converted | native | 1,050,000 | $0.6 / $3 |" in rendered
    assert "| `glm-5.3` | zhipu | converted | native | converted | 1,000,000 | $1.12 / $3.52 |" in rendered


def test_shipped_data_file_is_consistent():
    with open(check_endpoints.DATA_FILE, encoding="utf-8") as handle:
        data = json.load(handle)
    for model_id, model in data["models"].items():
        natives = [p for p, kind in model["protocols"].items() if kind == "native"]
        assert natives == [model["native"]], model_id
        if model["vendor"] == "openai":
            assert model["protocols"]["/v1/messages"] is None, model_id


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def test_fetch_sends_an_explicit_user_agent(monkeypatch):
    seen = {}

    def urlopen(request, timeout=None):
        seen["agent"] = request.get_header("User-agent")
        seen["url"] = request.full_url
        return FakeResponse(b"<html></html>")

    monkeypatch.setattr(check_endpoints.urllib.request, "urlopen", urlopen)
    check_endpoints.fetch("https://argolink.io/en/models/glm-5.3")
    assert seen["agent"] == "claude-api-bridge/1.0"
    assert seen["url"] == "https://argolink.io/en/models/glm-5.3"
