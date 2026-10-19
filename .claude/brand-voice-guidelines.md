# Energy 4.0 Harness — Team Docs Voice Guidelines

## Generation Metadata
- Version: 1
- Sources: lead's review feedback ("too much extra information", "give developers very straightforward 1-by-1 steps", "do this after this", "links to files they will use", "hard to understand the flow"); review of the v0 portal and Markdown artifacts in this repo
- Documents processed: 12 (docs/*.html, root *.md)
- Conversations analyzed: 1 (lead review)
- Discovery report used: No
- Overall confidence: Medium (one authoritative source — the lead — with clear, explicit direction)

Applies to: everything a team member reads to get work done — `docs/` pages, READMEs, PR descriptions, CLAUDE.md. Reference documents (intent, ARCHITECTURE, EVALS) may be denser, but nobody should need to read them to know what to do next.

---

## Executive Summary

Our docs are a route, not a library. A developer opens their page and follows numbered steps from top to bottom; each step is one action, names the file they will touch, and says how they know it worked. Background and reasoning live in the reference documents, linked only from the step that needs them.

The reader is a busy engineer building live during a short hackathon session. Every sentence must either tell them what to do or how to check it. If it does neither, cut it.

---

## We Are / We Are Not

| We Are | We Are Not |
|--------|------------|
| **Sequential** — numbered steps, one action each, in the order they happen | **Encyclopedic** — sections to read "for context" before you can act |
| **Concrete** — every step names the exact file, command or message | **Abstract** — "align on contracts", "ensure integration" |
| **Brief** — one sentence per step, plus a link or command | **Explanatory** — why-it-matters paragraphs on working pages |
| **Checkable** — each step or task ends with how you know it is done | **Aspirational** — goals without a test |
| **Single-sourced** — one place for each fact; others link to it | **Repetitive** — the same rule restated on five pages |

### Voice Attributes Detail

#### Sequential
- **What it means**: The page reads as "do this, then this". Numbering is continuous across a page.
- **How it shows up**: Groups by moment (set up → build tasks → finish each task). Hand-offs to other people are steps too ("Send Dev 4 the golden number").
- **What to avoid**: Unordered section lists (mission, why, inputs, handoff) that the reader must assemble into a plan.
- **Evidence**: Lead: "very straightforward 1 by 1 steps, do this after this".
- **Confidence**: High

#### Concrete
- **What it means**: Each step links the files the person will open or create.
- **How it shows up**: "Open `mcp/energy-data/README.md`. Paste this into Claude Code: …". Copyable prompts, not shell commands.
- **What to avoid**: Pointing to whole documents when one section is needed.
- **Evidence**: Lead: "links to files that they will use".
- **Confidence**: High

#### Brief
- **What it means**: Working pages contain only what is needed to act.
- **How it shows up**: Max one sentence of explanation per step. No "why it matters" on working pages.
- **What to avoid**: Repeating SPEC/ARCHITECTURE content on working pages.
- **Evidence**: Lead: "too much extra information".
- **Confidence**: High

#### Checkable
- **What it means**: Every task ends in an observable result.
- **How it shows up**: "You should see: …", short "Done when" list at the end of a page.
- **Confidence**: Medium (inferred from the plan's "evidence before done" principle)

---

## Tone-by-Context Matrix

| Context | Formality | Energy | Technical Depth | Key Principle |
|---------|-----------|--------|-----------------|---------------|
| Developer / lead step pages (`docs/`) | Low | Medium | Low–Medium | One action per step, link the file |
| Prompts on the pages | Medium | Low | High | Complete and precise: Claude reads it, not the human |
| Component READMEs | Low | Low | Medium | Contract first: interface, rules, owner |
| Reference docs (SPEC, ARCHITECTURE, EVALS) | Medium | Low | High | Single source of truth; linked, not repeated |
| PR descriptions | Low | Low | Medium | Task, files, evidence |

---

## Writing Rules

1. Start each step with a verb: Open, Run, Tell Claude, Send, Check.
2. One step = one action. If a step has "and then", split it.
3. Link every file the step touches. Use the repo path as the link text.
4. Put Claude prompts in copyable blocks. Developers do not type shell commands; the prompt tells Claude to run them.
5. Each task has one prompt to start and one to finish. The prompt carries the rules, so nobody has to remember them.
6. No "why" on working pages. Link the reference doc if someone needs it.
7. End each page with "Done when" — five items or fewer.
8. Never repeat a rule that lives in another document; link it.

### Before / after

| Before | After |
|---|---|
| "Inputs you depend on: schemas/market-price.schema.json (Dev 3 + Dev 4, draft now; build against it)" | "4. Open `schemas/market-price.schema.json`. Tell Claude: 'Build get_day_ahead_prices against this schema, tests first.'" |
| "Why your part matters: the skill turns a generic model into an energy assistant that quotes numbers…" | *(removed from the working page: lives in INTENT.md)* |

---

## Open Questions for Team Discussion

### Medium priority
1. **Should reference docs (intent, ARCHITECTURE) also be shortened?**
   - What was found: Feedback targeted the working flow; reference docs are long but only linked when needed.
   - Agent recommendation: Leave them as reference for now; revisit at Milestone D if people still get lost.
   - Need from you: Confirm or override.
2. **Are the Architecture / Workflow / Team / Checklist portal pages needed?**
   - What was found: They duplicated Markdown content and made the flow harder to follow.
   - Agent recommendation: Removed in v1; the step pages plus the Markdown files cover them.
   - Need from you: Confirm or ask to restore any page.
