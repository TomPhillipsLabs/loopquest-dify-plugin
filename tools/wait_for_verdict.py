import json
import time
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


def _shape_payload(module: str, params: dict[str, Any]) -> dict[str, Any]:
    """Build the payload the way each game expects (mirrors create_review_task)."""
    content = params.get("content") or ""
    payload_json = params.get("payload_json")
    if payload_json:
        return json.loads(payload_json)
    if module == "grounding":
        return {"claim": params.get("claim") or content, "source": params.get("source") or ""}
    if module in ("redact", "detective"):
        return {"body": content}
    return {"content": content}


class WaitForVerdictTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        creds = self.runtime.credentials
        base = (creds.get("base_url") or "https://loopquest.tomphillips.uk").rstrip("/")
        api_key = creds.get("api_key")
        headers = {"authorization": f"Bearer {api_key}", "content-type": "application/json"}

        module = tool_parameters.get("module") or "swiper"
        content = tool_parameters.get("content") or ""

        # Build the gate task body.
        body: dict[str, Any] = {"module": module, "payload": _shape_payload(module, tool_parameters), "mode": "gate"}

        card: dict[str, Any] = {}
        if tool_parameters.get("title"):
            card["title"] = tool_parameters["title"]
        if content and module == "swiper":
            card["body"] = content
        if module == "sorter":
            buckets = [c.strip() for c in (tool_parameters.get("choices") or "").split(",") if c.strip()]
            if buckets:
                card["choices"] = buckets
        if card:
            body["card"] = card

        timeout_seconds = tool_parameters.get("timeout_seconds")
        if timeout_seconds:
            body["timeout_seconds"] = int(timeout_seconds)
        on_timeout = tool_parameters.get("on_timeout")
        if on_timeout:
            body["on_timeout"] = on_timeout
        if tool_parameters.get("source_name"):
            body["source"] = tool_parameters["source_name"]
        if tool_parameters.get("external_id"):
            body["external_id"] = tool_parameters["external_id"]
        if tool_parameters.get("reviews_required"):
            body["reviews_required"] = int(tool_parameters["reviews_required"])

        # 1. Create the gate task.
        try:
            res = requests.post(f"{base}/api/v1/tasks", headers=headers, json=body, timeout=20)
        except requests.RequestException as exc:
            yield self.create_text_message(f"Request to LoopQuest failed: {exc}")
            return
        data = res.json() if res.content else {}
        if res.status_code >= 400:
            yield self.create_text_message(f"LoopQuest error {res.status_code}: {json.dumps(data)}")
            return
        task_id = data.get("id")
        if not task_id:
            yield self.create_json_message(data)
            return

        # 2. Poll until the task is resolved (or we hit max_wait).
        max_wait = int(tool_parameters.get("max_wait_seconds") or 300)
        interval = max(1, int(tool_parameters.get("poll_interval_seconds") or 3))
        deadline = time.monotonic() + max_wait
        status = data.get("status", "pending")
        latest: dict[str, Any] = data

        while status == "pending" and time.monotonic() < deadline:
            time.sleep(interval)
            try:
                poll = requests.get(f"{base}/api/v1/tasks/{task_id}", headers=headers, timeout=20)
            except requests.RequestException:
                continue
            if poll.status_code >= 400:
                continue
            latest = poll.json() if poll.content else latest
            status = latest.get("status", status)

        # 3. Return the outcome.
        verdict = latest.get("verdict")
        approved = verdict is True
        if status == "pending":
            summary = f"Still pending after {max_wait}s — no verdict yet (task {task_id})."
        elif latest.get("timed_out"):
            summary = f"Timed out and resolved to '{latest.get('verdict_choice') or ('approve' if approved else 'escalate/reject')}'."
        else:
            summary = "Approved by a human." if approved else f"Flagged by a human ({latest.get('verdict_choice') or latest.get('verdict_reason') or 'flagged'})."

        yield self.create_json_message({**latest, "approved": approved})
        yield self.create_text_message(summary)
