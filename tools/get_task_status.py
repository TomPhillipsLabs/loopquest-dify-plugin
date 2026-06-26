import json
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class GetTaskStatusTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        creds = self.runtime.credentials
        base = (creds.get("base_url") or "https://loopquest.tomphillips.uk").rstrip("/")
        api_key = creds.get("api_key")
        task_id = tool_parameters.get("task_id")

        if not task_id:
            yield self.create_text_message("task_id is required.")
            return

        headers = {"authorization": f"Bearer {api_key}"}
        try:
            res = requests.get(f"{base}/api/v1/tasks/{task_id}", headers=headers, timeout=20)
        except requests.RequestException as exc:
            yield self.create_text_message(f"Request to LoopQuest failed: {exc}")
            return

        data = res.json() if res.content else {}
        if res.status_code >= 400:
            yield self.create_text_message(f"LoopQuest error {res.status_code}: {json.dumps(data)}")
            return

        yield self.create_json_message(data)
        yield self.create_text_message(f"Task {data.get('id')} is {data.get('status')}.")
