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

        content = tool_parameters.get("content") or ""

        payload_json = tool_parameters.get("payload_json")
        if payload_json:
            try:
                payload = json.loads(payload_json)
            except json.JSONDecodeError:
                yield self.create_text_message("payload_json is not valid JSON.")
                return
        else:
            payload = {"content": content}

        body: dict[str, Any] = {
            "module": tool_parameters.get("module") or "swiper",
            "payload": payload,
        }
        title = tool_parameters.get("title")
        if title or content:
            body["card"] = {"title": title or "Review", "body": content}
        for key in ("source", "external_id", "callback_url"):
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
