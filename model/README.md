# model/: model gateway (model-agnostic)

**Owner:** Dev 1 (gateway, task #2) and Dev 4 (`model/recorded/`, task #21) · **Status:** not built · **Default model:** Claude Haiku 5.5 (`claude-haiku-5-5`)

Build `model/model_gateway/` as described in [SPEC.md §4](../SPEC.md): `run_turn(system, messages, tools, max_tokens)` returns `ModelTurn(text, tool_calls)`. The rest of the code never knows which model or vendor it talks to. Swapping the model is a change in `model/profiles.json`; adding a vendor is one new file here.

Rules: only `model/model_gateway/` may import a provider SDK (`make check` fails otherwise); the key is `ANTHROPIC_API_KEY` from `.env`; `MODEL_PROFILE=offline` replays recorded turns from `MODEL_RECORDED_PATH` (default `model/recorded/`) with no network.
