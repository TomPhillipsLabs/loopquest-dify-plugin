# LoopQuest for Dify

Send your workflow's AI output to **LoopQuest** for gamified human-in-the-loop review, and get a verdict back. Two tools:

- **Create review task** — submit content; a human approves or flags it in LoopQuest.
- **Get task status** — poll a task's status / verdict.

The review is **asynchronous** (a human takes time), so `create_review_task` returns immediately with a task id. The verdict arrives later via the **signed webhook** to your `callback_url`, or by calling `get_task_status`.

## Configure

When you add the tool in Dify, set:

- **API key** — a LoopQuest workspace API key (Workspaces → API keys) or your public ingest secret.
- **Base URL** — your LoopQuest deployment (defaults to `https://loopquest.tomphillips.uk`).

## Use it in a workflow

After your LLM node, add the **Create review task** tool and map the model output into **Content**. Optionally set a **Title**, **External id** (echoed back in the webhook so you can correlate), and a **Callback URL**.

## Test / record a demo

```bash
cd packages/dify-plugin
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Local debugging against a Dify instance:
#   set REMOTE_INSTALL_KEY + REMOTE_INSTALL_HOST from Dify → Plugins → "Debug plugin"
python -m main          # connects to Dify for live testing

# Or package and install:
#   dify plugin package ./ -o loopquest.difypkg
#   then upload loopquest.difypkg in Dify → Plugins → Install from local
```

Then in Dify: add the **LoopQuest** tool, run a workflow that calls **Create review task**, open the LoopQuest **Review** tab, approve/flag, and (if you set a `callback_url`) watch the signed verdict arrive.

## API

Backed by the public LoopQuest API — see `https://<your-app>/docs` and `/openapi.json`.
