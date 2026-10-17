# model/recorded — offline model turns

One JSON file per review the demo uses (`G-07.json` for `demo-solar-dk`, DK1, 2026-06): the list of `ModelTurn`s the model produced, in order.
`[{"tool_calls": [{"name": "list_assets", "arguments": {...}}], "text": ""}, ..., {"tool_calls": [], "text": "explanation + recommendation"}]`

Dev 3 creates `G-07.json` during the session (T3.3): run the review once with `MODEL_PROFILE=default`, save the turns, and check that every number in the final text appears in the calc result. With `MODEL_PROFILE=offline` the recorded client replays the turns, the harness still dispatches the real tools, and the demo runs with no internet.
