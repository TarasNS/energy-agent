# model/: model gateway (model-agnostic)

**Owner:** Dev 1 · **Status:** gateway and offline replay built; recorded runs with the real model still to make · **Default model:** Claude Haiku 5.5 (`claude-haiku-5-5`)

`model/model_gateway/` is the only place that calls a model. The rest of the code calls one function and never knows which model or vendor it talks to. Swapping the model is a change in `model/profiles.json`; adding a vendor is one new file in `model_gateway/`.

## Use it

```python
from model.model_gateway import run_turn, ModelTurn, ToolCall, ModelUnavailable
from model.model_gateway.gateway import reset_recordings   # offline replay only

turn = run_turn(system, messages, tools, max_tokens=600)   # -> ModelTurn(text, tool_calls)
```

- `messages` are OpenAI style: `{"role": "user" | "assistant" | "tool", ...}`. An assistant message may carry `tool_calls`; a tool result is `{"role": "tool", "tool_call_id", "content"}`.
- `tools` are OpenAI style: `{"type": "function", "function": {name, description, parameters}}`. The gateway converts them to the provider's format.
- A turn with no `tool_calls` means the model has finished.
- A missing key, an unknown profile, a malformed message, a failed call or an unreadable reply all raise `ModelUnavailable`. Callers catch that one error, never a raw HTTP or parsing error.

## Profiles and keys

- `MODEL_PROFILE` picks a profile from `model/profiles.json`: `default` (used when unset), `fast` (same model for now) or `offline` (replay, no key, no network).
- The key is `ANTHROPIC_API_KEY`, read from the environment or from `.env` at the repo root. It is never printed or logged.

## Tests (no network)

```text
python scripts/dev.py test        # runs every test, including model/tests/test_gateway.py (fake transport)
```

The tests cover tool conversion, message conversion for a tool round trip, a text reply, a tool-call reply, the request sent, a missing key, a failed call, profile selection, and a scan that no file outside `model/model_gateway/` imports `anthropic` or `openai`. `python scripts/dev.py check` (or `make check`) runs the same scan.

## Rules

- Only `model/model_gateway/` may import a provider SDK. This gateway imports none: it uses the standard library for HTTP.
- No test makes a live call. A live call needs the developer's go.

## Offline replay

- `MODEL_PROFILE=offline` and `MODEL_RECORDING=<file>` replay one recording: a JSON list of turns, `[{"text": ..., "tool_calls": [{"id", "name", "input"}]}, ...]`, returned in order.
- Each `run_turn` call returns the next turn. The `system`, `messages` and `tools` are not sent anywhere. No key and no network are needed.
- When the turns run out, or the file is missing or malformed, `run_turn` raises `ModelUnavailable`.
- The position is kept per file. Call `reset_recordings()` before each replayed question so it starts from the first turn.
- `MODEL_RECORDING` is required for the offline profile. Point it at a file, for example one in `model/recorded/`. Real recordings are made with the real model and need the developer's go, because recording uses a live call; `model/recorded/` is empty until then. `model/tests/fixtures/` holds hand-written fixtures for tests only.
