# apps/web — demo screen and local API

**Owner:** Dev 5 · **Status:** not implemented · **Acceptance test:** [DEMO.md](../../DEMO.md)

POC runtime: a small FastAPI server on `localhost` that runs `harness.agent.run_review`. The main screen is built in Lovable and calls this API ([brief](../../presentation/lovable-brief.md)). This folder also serves one plain HTML page as the offline fallback (`MODEL_PROFILE=offline`).

## Files
```text
apps/web/
├── server.py         FastAPI app: serves the page and the three endpoints
├── static/index.html the fallback screen (plain HTML + JS)
├── recorded.json     a review result for building before the harness runs
├── tests/            endpoint tests with FastAPI's TestClient
└── run.sh            uvicorn apps.web.server:app --port 8000  (used by make run)
```

## API
| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/api/review` | `{portfolio, zone, month, threshold_eur}` | review result (`schemas/review-result.schema.json`) |
| `POST` | `/api/proposals` | `{input_hash, asset_id}` | proposal (`schemas/action-proposal.schema.json`) |
| `POST` | `/api/proposals/{id}/approve` | `{approver}` | `{proposal, audit_record}` |

The approve endpoint is the only place that calls `actions.issue_approval_token` and `actions.approve_action` (see `mcp/actions/README.md`).

## Screen
```text
Portfolio   Zone   Month      [Run review]

Negative-price exposure  € …       ← headline, from calculation.economic_value_eur
Avoided by self-curtailment  € …   Grid operator (may be compensated)  € …
Per asset table · Assumptions · Recommendation
Tools the AI used: list_assets → get_production → get_day_ahead_prices → calculate_curtailment_value

[Create proposal: enable negative-price curtailment on Engbakke]
Proposal #…   Approver [name]  [Approve]
Audit: proposed · approved · executed (simulated)
```
- An energy workflow screen, not a chat window.
- Every number renders from `calculation` fields, never from model text.
- The tool trace renders from `tool_trace` (T3.5), in call order.
