import json
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class CreateReviewTaskTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        creds = self.runtime.credentials
        base = (creds.get("base_url") or "https://loopquest.tomphillips.uk").rstrip("/")
        api_key = creds.get("api_key")

        module = tool_parameters.get("module") or "swiper"
        content = tool_parameters.get("content") or ""
        claim = tool_parameters.get("claim") or ""
        source_text = tool_parameters.get("source") or ""
        title = tool_parameters.get("title")

        # Build the payload in the shape each game expects, unless the advanced
        # payload_json overrides everything.
        payload_json = tool_parameters.get("payload_json")
        if payload_json:
            try:
                payload = json.loads(payload_json)
            except json.JSONDecodeError:
                yield self.create_text_message("payload_json is not valid JSON.")
                return
        elif module == "grounding":
            payload = {"claim": claim or content, "source": source_text}
        elif module in ("redact", "detective"):
            payload = {"body": content}
        else:
            # swiper / sorter / versus / fixer: keep the content; card hints + the
            # advanced payload handle the richer shapes.
            payload = {"content": content}

        body: dict[str, Any] = {"module": module, "payload": payload}

        # Card display hints. Sorter's buckets live here (card.choices).
        card: dict[str, Any] = {}
        if title:
            card["title"] = title
        if content and module == "swiper":
            card["body"] = content
        if module == "sorter":
            choices = tool_parameters.get("choices") or ""
            buckets = [c.strip() for c in choices.split(",") if c.strip()]
            if buckets:
                card["choices"] = buckets
        if card:
            body["card"] = card

        # Gating + routing fields.
        mode = tool_parameters.get("mode")
        if mode:
            body["mode"] = mode
        timeout_seconds = tool_parameters.get("timeout_seconds")
        if timeout_seconds:
            body["timeout_seconds"] = int(timeout_seconds)
        on_timeout = tool_parameters.get("on_timeout")
        if on_timeout:
            body["on_timeout"] = on_timeout

        source_name = tool_parameters.get("source_name")
        if source_name:
            body["source"] = source_name
        for key in ("external_id", "callback_url"):
            value = tool_parameters.get(key)
            if value:
                body[key] = value
        reviews_required = tool_parameters.get("reviews_required")
        if reviews_required:
            body["reviews_required"] = int(reviews_required)

        headers = {"authorization": f"Bearer {api_key}", "content-type": "application/json"}
        try:
            res = requests.post(f"{base}/api/v1/tasks", headers=headers, json=body, timeout=20)
        except requests.RequestException as exc:
            yield self.create_text_message(f"Request to LoopQuest failed: {exc}")
            return

        data = res.json() if res.content else {}
        if res.status_code >= 400:
            yield self.create_text_message(f"LoopQuest error {res.status_code}: {json.dumps(data)}")
            return

        yield self.create_json_message(data)
        yield self.create_text_message(f"Submitted task {data.get('id')} (status: {data.get('status')}).")
