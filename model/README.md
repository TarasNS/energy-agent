# model/: model gateway (model-agnostic)

**Owner:** Dev 1 · **Status:** gateway built; offline replay is the next task · **Default model:** Claude Haiku 5.5 (`claude-haiku-5-5`)

`model/model_gateway/` is the only place that calls a model. The rest of the code calls one function and never knows which model or vendor it talks to. Swapping the model is a change in `model/profiles.json`; adding a vendor is one new file in `model_gateway/`.

## Use it

```python
from model.model_gateway import run_turn, ModelTurn, ToolCall, ModelUnavailable

turn = run_turn(system, messages, tools, max_tokens=600)   # -> ModelTurn(text, tool_calls)
```

- `messages` are OpenAI style: `{"role": "user" | "assistant" | "tool", ...}`. An assistant message may carry `tool_calls`; a tool result is `{"role": "tool", "tool_call_id", "content"}`.
- `tools` are OpenAI style: `{"type": "function", "function": {name, description, parameters}}`. The gateway converts them to the provider's format.
- A turn with no `tool_calls` means the model has finished.
- A missing key, an unknown profile, a malformed message, a failed call or an unreadable reply all raise `ModelUnavailable`. Callers catch that one error, never a raw HTTP or parsing error.

## Profiles and keys

- `MODEL_PROFILE` picks a profile from `model/profiles.json`: `default` (used when unset), `fast` (same model for now) or `offline` (replay, not built yet; raises `ModelUnavailable`).
- The key is `ANTHROPIC_API_KEY`, read from the environment or from `.env` at the repo root. It is never printed or logged.

## Tests (no network)

```text
python scripts/dev.py test        # runs every test, including model/tests/test_gateway.py (fake transport)
```

The tests cover tool conversion, message conversion for a tool round trip, a text reply, a tool-call reply, the request sent, a missing key, a failed call, profile selection, and a scan that no file outside `model/model_gateway/` imports `anthropic` or `openai`. `python scripts/dev.py check` (or `make check`) runs the same scan.

## Rules

- Only `model/model_gateway/` may import a provider SDK. This gateway imports none: it uses the standard library for HTTP.
- No test makes a live call. A live call needs the developer's go.
- `MODEL_PROFILE=offline` must replay recorded turns from `model/recorded/*.json` with no network. Not built yet.
