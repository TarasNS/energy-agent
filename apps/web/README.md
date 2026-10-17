# apps/web — demo screen and local API

**Owner:** Dev 5 · **Status:** not implemented · **Acceptance test:** [DEMO.md](../../DEMO.md)

POC runtime: one HTML page served by a small FastAPI server on `localhost`. Everything runs offline with `MODEL_PROFILE=offline`. Lovable polish only after the POC works.

## Files
```text
apps/web/
├── server.py         FastAPI app: serves the page and the three endpoints
├── static/index.html the single screen (plain HTML + JS)
├── recorded.json     a review result for building before the workflow exists
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

[Create proposal: enable negative-price curtailment on Engbakke]
Proposal #…   Approver [name]  [Approve]
Audit: proposed · approved · executed (simulated)
```
- An energy workflow screen, not a chat window.
- Every number renders from `calculation` fields, never from model text.
