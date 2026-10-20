# DEMO.md: the three-minute story

**Owner:** Lead · **Role:** the acceptance test for the POC. If this demo works, the POC works.

**Setup:** the chat page, synthetic data (2 parks, 1 battery, June 2026), server running. Offline fallback: `MODEL_PROFILE=offline` once Dev 3's replay is merged.

## One-line pitch
Ask your portfolio a question, get a number you can trust, and approve the next step yourself.

## 30-second problem
Managers have the data, but a generic AI assistant raises three questions: *Can I trust the number? Where did my data go? Can it act without me?* Here, code owns the number, tools own the data, the model owns the words, and a person owns the action.

## The demo

| Time | Do | Say |
|---|---|---|
| 0:00 | Click the question *Which park lost most energy in June?* | "A manager asks in plain words." |
| 0:30 | Point at the chart and the answer. Open **Tools used** | "The AI chose these tools. It can call nothing else." |
| 1:00 | Ask *What is our battery round-trip efficiency?* | "Every number comes from tested code, not from the model." |
| 1:30 | Ask for something the data cannot answer, such as incident resolution | "It says unavailable and why. It does not guess." |
| 2:00 | Ask *Should we change anything about negative prices?* A proposal appears | "The assistant proposes. It cannot approve." |
| 2:20 | Type your name and press **Approve** | "A person approves. The decision is logged." |
| 2:40 | Show the audit line | "Every step is traceable." |
| 2:50 | Close | "First proof of concept on synthetic data. Next: a real data source and a second workflow." |

The exact numbers on screen come from the golden cases in [EVALS.md](EVALS.md). Fill them in here after Dev 4's first task.

## Fallback ladder
1. **No internet:** run with `MODEL_PROFILE=offline`. Same loop, recorded model turns, same numbers.
2. **Server unreachable:** run it on the presenter's laptop.
3. **Page fails:** the screenshots the lead saved during rehearsal.

## Rehearsal checklist
- [ ] Under three minutes
- [ ] No terminal in the story
- [ ] Run once with Wi-Fi off
- [ ] Every number is quoted from the screen
- [ ] A refused approval is shown or explained
