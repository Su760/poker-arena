# Implementation plan

Status: P0 not started. Documentation bootstrap prepared on 2026-10-02.

The specification is authoritative for detailed requirements. This file tracks execution; check boxes only after verifying the corresponding result.

## P0: correct, reproducible core

- [ ] Inspect repository instructions and local environment; preserve unrelated work.
- [ ] Verify PokerKit's installed API, heads-up seat mapping, automation settings, and deterministic dealing approach.
- [ ] Create a Python package, reproducible dependency configuration, developer checks, and appropriate ignore rules.
- [ ] Implement fixed-stack heads-up Hold'em with integer chips, no rake, alternating button, and cumulative results separate from stacks.
- [ ] Implement typed/versioned seat observations and a policy interface that never exposes engine truth.
- [ ] Translate fold, check/call, minimum raise, half-pot raise, pot raise, and all-in into exact legal actions; deduplicate sizes.
- [ ] Add a uniformly random legal-action policy with RNG independent of dealing.
- [ ] Add a runnable seeded CLI hand and versioned decision/replay records.
- [ ] Cover betting order, minimum raises, short all-ins/reopening, refunds, folds, showdown, ties, board-playing hands, and chip accounting.
- [ ] Check hidden-state invariance and serialized policy payloads; changing an opponent label or hidden deal must not change a fixed visible observation.
- [ ] Verify stale/illegal action rejection, reproducibility, and replay; replay source must not be exposed through policy inputs.
- [ ] Run at least 10,000 seeded random legal hands with card, stack, termination, and payout invariants. Preserve reproducible failure details.
- [ ] Self-review, run documented commands, and complete an evidence-based review handoff.

P0 does not require API endpoints, a database, a web UI, opponent personalities, neural training, or coaching scores. Later checkpoint and API gates apply when those components exist.

## Subsequent milestones

| Milestone | Deliverable | Main gate |
| --- | --- | --- |
| P1 | Opponent factory and headless sessions | Every preset runs and measured behaviors differ as intended |
| P2 | Human-play UI, bookmarks, replay, basic feedback | Complete and review a session without future-information leakage |
| P3 | Evaluation, Leduc lab, first objective drills | Reproducible benchmarks and separate bot/human metrics |
| P4 | Learned Hold'em candidate | Honest held-out report, including if the baseline wins |
| P5 | Local autonomous policy export | Unattended play through the same observation/action contract |
| P6 | Advanced opponents and possible external adapter | Explicit venue compatibility and the spec's operational gates |

## Ideas to revisit

- Unknown-style practice and repeated decision drills at P2/P3.
- Six-player practice after core correctness if that matches the user's usual poker games.
- Branching replay after simulation-based evaluation can state its opponent and continuation assumptions.

Stop after P0 and bring the handoff back for review before starting P1.
