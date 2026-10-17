# Lovable challenge brief

**Owner:** Lead + Dev 5 · Paste the sections below into the Lovable workspace. Upload only the files listed under Data.

## Problem
Solar parks in DK1 sometimes keep producing while day-ahead prices are negative. That costs money, but nobody sees the cost month by month. Teams also do not trust AI numbers, and do not want AI to act without approval.

## Context
- Portfolio: `demo-solar-dk`, synthetic, three solar parks in DK1 (Vestmark, Lindholm, Engbakke).
- Month: June 2026, 15-minute intervals.
- One park, Engbakke Solar, does not curtail at negative prices. The others do.
- The EUR numbers come from our own calculator through an API. The screen must show them exactly as received and never compute them.

## Who it affects
- **Primary:** portfolio and asset managers, who decide what to change.
- **Secondary:** energy analysts, operations, trading, risk and compliance.

## What the screen must do
1. Select portfolio, zone and month, then click **Run review**.
2. Show the headline EUR and the split by cause and by asset.
3. Show the explanation, the recommendation and the assumptions.
4. Show which tools the AI used, in order.
5. **Create proposal**, enter the approver's name, **Approve**.
6. Show the audit line.

Keep it to one screen. It is an energy decision screen, not a chat window. Use Nordic Solar colours (`#1A5C00`, `#1C1C1C`, `#F4F2EB`, `#FFFFFF`) and the Aptos font.

## Data to upload
- `data/synthetic/demo-solar-dk/assets.json`
- `data/synthetic/demo-solar-dk/production-2026-06.jsonl`
- `data/synthetic/demo-solar-dk/prices-DK1-2026-06.jsonl`
- `apps/web/recorded.json` (a recorded review result, once Dev 5 has made it)

Do not upload real company data, API keys or `.env`.

## API the screen calls
| Method | Path | Returns |
|---|---|---|
| `POST` | `/api/review` | review result ([schema](../schemas/review-result.schema.json)) |
| `POST` | `/api/proposals` | proposal |
| `POST` | `/api/proposals/{id}/approve` | proposal + audit record |

Until the harness runs, build the screen against `recorded.json`.
