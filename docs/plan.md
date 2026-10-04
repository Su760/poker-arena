# Implementation plan

Status: P0 acceptance checklist passed again on 2026-10-03. Git recovery is verified; review-branch commit/push and the separately requested global hook repair remain blocked by session permissions. No P1 work started.

The specification is authoritative for detailed requirements. This file tracks execution; check boxes only after verifying the corresponding result.

## P0: correct, reproducible core

- [x] Inspect repository instructions and local environment; preserve unrelated work.
- [x] Verify PokerKit's installed API, heads-up seat mapping, automation settings, and deterministic dealing approach.
- [x] Create a Python package, reproducible dependency configuration, developer checks, and appropriate ignore rules.
- [x] Implement fixed-stack heads-up Hold'em with integer chips, no rake, alternating button, and cumulative results separate from stacks.
- [x] Implement typed/versioned seat observations and a policy interface that never exposes engine truth.
- [x] Translate fold, check/call, minimum raise, half-pot raise, pot raise, and all-in into exact legal actions; deduplicate sizes.
- [x] Add a uniformly random legal-action policy with RNG independent of dealing.
- [x] Add a runnable seeded CLI hand and versioned decision/replay records.
- [x] Cover betting order, minimum raises, short all-ins/reopening, refunds, folds, showdown, ties, board-playing hands, and chip accounting.
- [x] Check hidden-state invariance and serialized policy payloads; changing an opponent label or hidden deal must not change a fixed visible observation.
- [x] Verify stale/illegal action rejection, reproducibility, and replay; replay source must not be exposed through policy inputs.
- [x] Run at least 10,000 seeded random legal hands with card, stack, termination, and payout invariants. Preserve reproducible failure details.
- [x] Self-review, run documented commands, and complete an evidence-based review handoff.

- [x] Verify manually recovered Git metadata: `main` tracks `origin/main`, both at `6f5d69e`; inspect the actual diff and preserve all local files. No bootstrap documents needed restoration.
- [ ] Publish reviewed P0 files on `review/p0-verification`; `.git` writes are denied and sandbox escalation is disabled.
- [ ] Apply the separately requested global Stop-hook repair; backup and JSON validation are complete, active configuration is unchanged.

Evidence: 28 focused tests on Python 3.13 and 3.11; 10,000 standard seeded hands and replays; 1,000 varied-stack seeded hands and replays; independent payouts, CLI and bytecode checks. Both stress hashes exactly match the prior runs. The original wheel build/install remains valid because runtime source is unchanged. The failure-artifact regression was observed failing before the harness fix. Exact commands, results, current Git state and remaining delivery blockers are in `docs/review-handoff.md`.

P0 does not require API endpoints, a database, a web UI, opponent personalities, neural training, or coaching scores. Later checkpoint and API gates apply when those components exist.

## Subsequent milestones

| Milestone | Deliverable                                      | Main gate                                                        |
| --------- | ------------------------------------------------ | ---------------------------------------------------------------- |
| P1        | Opponent factory and headless sessions           | Every preset runs and measured behaviors differ as intended      |
| P2        | Human-play UI, bookmarks, replay, basic feedback | Complete and review a session without future-information leakage |
| P3        | Evaluation, Leduc lab, first objective drills    | Reproducible benchmarks and separate bot/human metrics           |
| P4        | Learned Hold'em candidate                        | Honest held-out report, including if the baseline wins           |
| P5        | Local autonomous policy export                   | Unattended play through the same observation/action contract     |
| P6        | Advanced opponents and possible external adapter | Explicit venue compatibility and the spec's operational gates    |

## Ideas to revisit

- Unknown-style practice and repeated decision drills at P2/P3.
- Six-player practice after core correctness if that matches the user's usual poker games.
- Branching replay after simulation-based evaluation can state its opponent and continuation assumptions.

Stop after P0 and bring the handoff back for review before starting P1.

## Bounded P1 recommendation after P0 review

- Freeze a parameter/config schema for scripted opponent styles using the existing seat-only policy protocol.
- Add separately testable style policies and a headless diagnostic run reporting entry/raise/fold rates with denominators.
- Continue fixed-stack and alternating-button sessions; preserve P0 tests and replay compatibility.
- Defer UI and coaching to P2; do not interpret style labels or random-baseline winnings as evidence of poker strength.
