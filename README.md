# LoopQuest for Dify

Send your workflow's AI output to **LoopQuest** for gamified human-in-the-loop review, and get a verdict back. Three tools:

- **Create review task** — submit content for review and **keep going** (non-blocking, "monitor"). Returns a task id immediately; the verdict arrives later via the signed webhook to your `callback_url`, or by calling `get_task_status`.
- **Wait for verdict** — submit content and **block this node until a human decides** (a "gate"). Returns the verdict so you can branch on approve vs flag.
- **Get task status** — poll a task's status / verdict by id.

## Two ways to use it: monitor vs gate

- **Monitor (non-blocking):** use **Create review task**. Your workflow proceeds immediately; a human reviews a copy for quality in the background. Great for QA, drift and accuracy metrics.
- **Gate (blocking):** use **Wait for verdict**. Nothing downstream happens until a person approves. Use it for decisions that must have a human answerable — refunds, sign-offs, sends, deletions.

> **Why a dedicated Wait tool?** A Dify chatflow can't natively pause a turn and resume on an external callback. **Wait for verdict** solves this by creating a gate task and **polling server-side inside the tool call** until the human decides (or the fail-closed timeout is applied), so the node itself blocks — no loop wiring needed. Keep **Max wait** at or below your Dify request timeout, and set a **Fail-closed timeout** so a missing decision never hangs the flow (it escalates by default).

## Configure

When you add the tool in Dify, set:

- **API key** — a LoopQuest workspace API key (Workspaces → API keys) or your public ingest secret.
- **Base URL** — your LoopQuest deployment (defaults to `https://loopquest.tomphillips.uk`).

## Use it in a workflow

**Monitor:** after your LLM node, add **Create review task**, map the output into **Content**, pick a **Module**, and carry on. Optionally set **Title**, **External id** and a **Callback URL**.

**Gate:** after your LLM node, add **Wait for verdict**, map the output into **Content** (or **Claim** + **Source** for Grounding). The node blocks until the verdict, then wire an **IF/ELSE** on the returned `approved` — true → send the answer, false → send a fallback or escalate.

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
