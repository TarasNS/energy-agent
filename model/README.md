# model/: model gateway (model-agnostic)

**Owner:** Dev 3 · **Status:** live calls work; offline replay not built · **Default model:** Claude Haiku 5.5

The rest of the code never knows which model or vendor it talks to. Swapping the model is a config change; adding a vendor is one new file here.

## Interface (what exists)
```python
from model.model_gateway import run_turn, explain, ModelTurn, ModelUnavailable

turn = run_turn(system, messages, tools, max_tokens=600)
turn.text         # str | None: the answer when no tool is requested
turn.tool_calls   # list of ToolCall(id, name, input); empty means the loop stops
```
`run_turn` takes tool schemas in OpenAI style (from `harness/registry.py`) and converts them to Anthropic `input_schema`. Calls use the standard library (`urllib`); no provider SDK is installed.

## Layout
```text
model/
├── profiles.json            profile name → provider + model id (config, no code)
├── recorded/                recorded model turns for offline demos (Dev 3 fills it)
└── model_gateway/
    ├── __init__.py          run_turn, explain, ModelTurn, ModelUnavailable
    └── anthropic_client.py  the only file that talks to Anthropic
```

## Rules
1. **Only `model/model_gateway/` may import or call a provider SDK.** `make check` fails if `anthropic` or `openai` is imported elsewhere.
2. The model gets only the tools the harness passes in. None writes data or approves; `propose_action` only proposes.
3. Numbers shown to the user come from tool results, never from model text.
4. Any provider error raises `ModelUnavailable`. The agent returns a clear note and the page stays up.
5. The key comes from `ANTHROPIC_API_KEY` in `.env` (git-ignored) or the environment. Never in code, prompts, fixtures or logs. Override the model with `ANTHROPIC_MODEL`.

## Still to build (Dev 3)
`MODEL_PROFILE=offline` replays recorded turns from `model/recorded/` in order, with no network. See the [Dev 3 page](../docs/developer-3.html).

## Adding another vendor later
Add `<vendor>_client.py` with the same `run_turn` shape and a profile in `profiles.json`. No other file changes.
