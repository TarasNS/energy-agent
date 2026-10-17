# model/recorded — offline replies

One JSON file per review the demo uses (`G-07.json` for `demo-solar-dk`, DK1, 2026-06), shaped like `ModelReply`:
`{"explanation": "...", "recommendation": "...", "model": "recorded"}`.

Dev 3 creates `G-07.json` during the session: run the review once with `MODEL_PROFILE=default`, save the reply, and check that every number in it appears in the calc result. With `MODEL_PROFILE=offline` the demo then runs with no internet.
