# model/ — model gateway (model-agnostic)

**Owner:** Dev 3 · **Status:** not implemented · **Provider for the hackathon:** Anthropic Python SDK (`pip install anthropic`)

The rest of the code never knows which model or vendor it talks to. It calls one function and gets text back. Swapping the model is a config change; adding a vendor is one new class here.

## Interface (proposed)
```python
from model_gateway import get_client, ModelUnavailable

client = get_client()            # reads MODEL_PROFILE from .env; default "default"
turn = client.run_turn(
    system=system_text,          # harness/prompts/system.txt + curtailment-advisor skill
    messages=messages,           # conversation so far, incl. tool results
    tools=tool_schemas,          # from harness/tools/registry.py
)
turn.text              # str, final explanation + recommendation when no tool calls
turn.tool_calls        # list of {id, name, arguments}; empty means the loop stops
turn.model             # e.g. "claude-sonnet-5-5" or "recorded"
```

## Layout
```text
model/
├── profiles.json            profile name → provider + model id (config, no code)
├── recorded/                recorded model turns per golden case, for offline demos
└── model_gateway/
    ├── __init__.py          get_client(), ModelTurn, ModelUnavailable
    ├── anthropic_client.py  the only file that imports the Anthropic SDK
    └── recorded_client.py   replays recorded/ turns in order — no network
```

## Rules
1. **Only `model/model_gateway/` may import a provider SDK.** `make check` fails if `anthropic` (or `openai`) is imported anywhere else.
2. The model gets only the tools the harness registry passes in. None of them writes data or approves; `propose_action` only proposes.
3. Numbers shown to the user come from the calc result, never from model text.
4. Any provider error raises `ModelUnavailable`. The harness then uses the `offline` profile, so the demo never stops.
5. The API key comes from `ANTHROPIC_API_KEY` in `.env` (git-ignored). Never in code, prompts, fixtures or logs.

## Adding another vendor later
Add `<vendor>_client.py` implementing `run_turn(...)`, add a profile in `profiles.json`. No other file changes. The Anthropic SDK also supports Claude on AWS Bedrock and Google Vertex, which covers "enterprise cloud" profiles without a new vendor.

Check current model IDs on the Anthropic models overview page before the hackathon; update `profiles.json` only.
