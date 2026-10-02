# Repository instructions

## Context and scope

Read `Poker-Arena-Project-Spec.md`, `docs/plan.md`, and the latest `docs/review-handoff.md` before implementation. The spec defines the product; the plan records the active task. Current implementation scope is P0 only.

Keep instructions concise and maintain the existing documents instead of creating competing specs or status files. The user is learning: explain consequential design choices and the poker concepts behind them in plain English.

## Research and execution

At each milestone, and before dependency changes or uncertain API/rule decisions, consult relevant primary sources: official documentation, upstream source/tests, and original research papers. Verify behavior against the installed version. Record the date, source URL, finding, decision, and remaining uncertainty in `docs/research.md`. A documentation example does not prove our adapter is correct.

Research should resolve a concrete question. Reuse still-applicable findings; record useful future ideas in the plan without silently expanding the current task. If browsing is unavailable, inspect installed source and state the limitation honestly.

Inspect repository state and preserve unrelated changes. Write a short implementation plan, then implement the bounded task. Work on one reviewable milestone at a time. Build the smallest complete path before adding abstractions.

## Core invariants

- Python 3.11+ and PokerKit behind a thin adapter. Install only dependencies needed for the active milestone and lock their resolved versions.
- Integer chips: 2 units per BB; default stacks 200 units each; blinds 1/2.
- Engine truth stays private. Policies and live human views receive only their own cards and public information; no opponent configuration, future cards, deck seeds, or raw engine objects.
- Separate deck and policy RNG streams. A policy's extra random draw must not change the deal.
- Preserve chip totals, betting legality, action order, and uncalled-bet refunds. Reject illegal or stale actions without partial mutation.
- Store versioned decision events for replay. Keep private truth records separate from seat-visible output.
- Heuristics are not GTO. Hand outcomes alone do not grade decisions. Leduc results are not Hold'em results.
- External poker-site automation is outside P0. Follow the spec's later venue-compatibility scope.

## Verification and handoff

Test poker rules and information boundaries with independent expected outcomes, plus the spec's seeded stress run. Replay must reproduce actions and payouts. Review the diff for correctness after checks pass.

Report exact commands, actual results, failures, and untested behavior. Never mark a gate complete from assumptions or fabricated output. Update README commands, the plan checklist, architecture decisions, and review handoff when behavior changes. The handoff must include the reviewed code revision/worktree state and next bounded task.

## Code Review Rules

Prioritize hidden-information leaks, seed leakage, RNG coupling, incorrect raise-to amounts, all-in reopening, payout errors, and result claims unsupported by tests. Flag any reduction of correctness gates used only to make tests pass.
