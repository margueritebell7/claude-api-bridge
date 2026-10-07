"""Rebuild the protocol matrix in endpoints.json from public pages, or check it.

Standard library only (Python 3.9+). No API key is needed: the catalog
endpoint and the model pages it reads are public.

    python check_endpoints.py            # print what changed, exit 1 on drift
    python check_endpoints.py --write    # refresh endpoints.json in place
    python check_endpoints.py --table    # print the README table from the file
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as _dt
import html
import json
import os
import re
import sys
import urllib.request

SITE = os.environ.get("MATRIX_SITE", "https://argolink.io").rstrip("/")
CATALOG_PATH = "/api/catalog/v1/models?category=chat&sort=provider&page_size=100"
PROTOCOLS = ("/v1/messages", "/v1/chat/completions", "/v1/responses")
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "endpoints.json")
USER_AGENT = "claude-api-bridge/1.0"  # some edges refuse urllib's default agent string

_BLOCK = re.compile(r'<div class="model-api-endpoints".*?</ul>', re.S)
_ITEM = re.compile(
    r"<strong>(?P<label>.*?)</strong>\s*<code>(?P<path>/v1/[a-z_/]+)</code>\s*<small>(?P<note>.*?)</small>",
    re.S,
)


def fetch(url: str, timeout: float = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_endpoints(page: str) -> dict:
    """Return {path: "native" | "converted"} from one model page.

    The page lists each accepted endpoint with a label; the one marked
    "Recommended" is the model's own format, the rest are converted to it."""
    block = _BLOCK.search(page)
    if not block:
        return {}
    found = {}
    for match in _ITEM.finditer(block.group(0)):
        label = html.unescape(match.group("label")).strip().lower()
        found[match.group("path")] = "native" if label == "recommended" else "converted"
    return found


def build(items: list, pages: dict, checked: str) -> dict:
    """Combine catalog items (prices, limits) with parsed pages (protocols)."""
    models = {}
    for item in items:
        model_id = item["id"]
        text = item.get("text", {})
        price = item.get("pricing", {}).get("effective", {})
        accepted = parse_endpoints(pages.get(model_id, ""))
        models[model_id] = {
            "vendor": item.get("provider_id"),
            "native": item.get("endpoint"),
            "protocols": {path: accepted.get(path) for path in PROTOCOLS},
            "context_tokens": text.get("context_tokens"),
            "max_output_tokens": text.get("max_output_tokens"),
            "efforts": text.get("efforts", []),
            "input_per_million": price.get("input_per_million"),
            "output_per_million": price.get("output_per_million"),
        }
    return {"checked": checked, "source": SITE, "models": models}


def diff(old: dict, new: dict) -> list:
    lines = []
    old_models, new_models = old.get("models", {}), new.get("models", {})
    for model_id in sorted(set(old_models) | set(new_models)):
        before, after = old_models.get(model_id), new_models.get(model_id)
        if before is None:
            lines.append(f"+ {model_id} (new model)")
        elif after is None:
            lines.append(f"- {model_id} (no longer listed)")
        else:
            for key in sorted(set(before) | set(after)):
                if before.get(key) != after.get(key):
                    lines.append(f"~ {model_id}.{key}: {before.get(key)!r} -> {after.get(key)!r}")
    return lines


def table(data: dict) -> str:
    mark = {"native": "native", "converted": "converted", None: "—"}
    rows = [
        "| Model ID | Vendor | `/v1/messages` | `/v1/chat/completions` | `/v1/responses` | Context | Input / output per 1M |",
        "|---|---|---|---|---|---:|---:|",
    ]
    for model_id, m in data["models"].items():
        p = m["protocols"]
        context = f"{m['context_tokens']:,}" if m.get("context_tokens") else "—"
        rows.append(
            f"| `{model_id}` | {m['vendor']} | {mark[p['/v1/messages']]} | {mark[p['/v1/chat/completions']]}"
            f" | {mark[p['/v1/responses']]} | {context} | ${m['input_per_million']:g} / ${m['output_per_million']:g} |"
        )
    return "\n".join(rows)


def collect(workers: int = 4) -> dict:
    items = json.loads(fetch(SITE + CATALOG_PATH))["items"]
    ids = [item["id"] for item in items]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        pages = dict(zip(ids, pool.map(lambda model_id: fetch(f"{SITE}/en/models/{model_id}"), ids)))
    return build(items, pages, _dt.date.today().isoformat())


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="overwrite endpoints.json")
    parser.add_argument("--table", action="store_true", help="print the Markdown table from endpoints.json")
    parser.add_argument("--file", default=DATA_FILE)
    args = parser.parse_args(argv)

    if args.table:
        with open(args.file, encoding="utf-8") as handle:
            print(table(json.load(handle)))
        return 0

    fresh = collect()
    if args.write:
        with open(args.file, "w", encoding="utf-8") as handle:
            json.dump(fresh, handle, indent=2)
            handle.write("\n")
        print(f"wrote {len(fresh['models'])} models to {args.file}")
        return 0

    with open(args.file, encoding="utf-8") as handle:
        changes = diff(json.load(handle), fresh)
    print("\n".join(changes) if changes else "endpoints.json matches the live pages")
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
