# Prompt 6 — Integration review

**Owner:** Dev 3 (runs it), lead (decides) · **Use:** run `claude` from the repo root, then paste the prompt below (or say "Follow prompts/06-integration-review.md").

```text
Review the integrated dev branch against intent.md, SPEC.md, ARCHITECTURE.md
and PLAN.md.

Do not implement anything.

Run:
- make check
- make test (unit, golden and approval tests)
- offline demo (network disabled, MODEL_PROFILE=offline)
- make demo-smoke

Then report only:
1. blockers to the three-minute demo,
2. safety invariant failures,
3. integration contract mismatches,
4. unnecessary complexity that can be removed.

Rank findings P0/P1/P2.
P0 = demo or safety is broken.
P1 = likely demo failure or confusing audience experience.
P2 = improvement only.

Attach the command and output for every finding.
Do not create new scope.
```
