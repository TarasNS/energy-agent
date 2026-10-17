# Prompt 7 — Final simplification pass

**Owner:** Dev 2 (runs simplifier), lead (approves) · **Use:** run `claude` from the repo root, then paste the prompt below (or say "Follow prompts/07-final-simplification.md").

```text
The POC is feature-frozen.

Use the simplifier subagent to inspect the repository for anything that can be
removed or simplified without reducing the approved demo, tests, controls or
clarity.

Prioritise:
- dead code,
- duplicate abstractions,
- unused agents/skills,
- unnecessary configuration,
- live dependencies that can use fixtures,
- demo steps that can be eliminated.

Do not change business behaviour.
Do not weaken tests, golden values or approval controls.
Propose deletions first; implement only after I approve each one.
After each approved change run make test, make eval and make demo-smoke.
```
