# Architecture and decisions

Status: P0 core implemented and reverified on 2026-10-03; Git recovery is complete, but review-branch publication remains blocked by the session sandbox. See review-handoff.md for the gate and exact evidence.

## Boundaries

| Component            | Responsibility                                         | Permitted information                                         |
| -------------------- | ------------------------------------------------------ | ------------------------------------------------------------- |
| Game adapter         | PokerKit integration, legal transitions, payouts       | Full private engine state                                     |
| Observation builder  | Produce a seat-specific immutable snapshot             | Full input state internally; filtered output only             |
| Action translator    | Resolve abstract choices to exact legal engine actions | Public betting data and engine legality queries               |
| Policy               | Choose from supplied legal actions                     | Seat observation and independent policy RNG                   |
| Session runner / CLI | Alternate seats, run hands, collect results            | Control data; printed views must remain seat-filtered         |
| Replay storage       | Reconstruct completed hands                            | Private truth stored separately from seat-visible events      |
| Future review layer  | Explain past decisions                                 | Decision-time information; separately labeled showdown reveal |

No module may give a policy the adapter itself as a shortcut. Public history must be filtered too; filtering only top-level hole-card fields is insufficient.

## Initial choices

- Use PokerKit as the rules engine and test our wrapper independently.
- Use 200 integer units per starting stack, with blinds 1 and 2.
- Keep fixed-stack hand returns separate from a future carryover-stack mode.
- Keep engine and policy randomness independent. Verify the actual library dealing behavior before choosing an implementation.
- Record observation/action schema versions and define raise amounts as total contribution on the current street.
- Preserve replay data now so human review can be added without reconstructing missing history.
- Keep game code runnable without FastAPI, Next.js, or training packages.

Implementation should document the selected seat mapping, RNG/deck injection method, rounding rule, engine automations, and event format here, together with their verification.

## Implemented P0 choices

- `contracts.py` defines frozen version-1 dataclasses for configuration, observations, exact actions, requests, public events, and decision events. It does not import PokerKit. The policy protocol accepts only an observation and returns an action; legal choices and the mask are part of the observation. Optional probabilities/timing are deferred.
- `engine.py` owns private PokerKit state, the complete deck, cached own-hole-card data and both seats' decisions. Position 0 maps to the nonbutton/BB and position 1 to the button/SB. Street order comes from PokerKit. `session.py` alternates the external button, resets stacks every hand, and maintains cumulative net returns separately.
- Blind units default to 1/2 and starting stacks to 200/200. `GameConfig` also permits positive integer short/unequal stacks and blind amounts for correctness fixtures. No antes, rake, extra boards or more than two seats are supported.
- Engine bookkeeping is automated, including one-runout cash-game selection and settlement. Dealing/burning are explicit. A separate local RNG shuffles a canonical 52-card deck, replacing PokerKit's construction-time shuffle before the first deal. Policy RNG objects and the session deck RNG are independent. Private replay stores deck order, not just a seed.
- `actions.py` translates six abstract slots into distinct exact actions. Raise-to is the total street commitment. Compute the pot after calling, multiply by the fraction, round half units upward, add the current largest street bet, clamp to PokerKit's legal min/max, then validate. Duplicate amounts share aliases. An all-in call shares the call action. The mask uses the order in `ACTION_SLOTS`; policies sample distinct choices, not aliases. P0 intentionally omits the cash-mode free-fold option.
- `Observation.to_call` is the actual capped amount this seat can call and is zero when it is not that seat's turn. Only the actor gets legal actions/min/max; another seat's view still shows public board, bets, stacks and history. `pot` already includes street bets. `contributions` means chips paid net of refunds, distinct from outstanding street bets and terminal net profit.
- Every accepted request must match the hand ID, state version, acting seat, schema version and an offered exact action. A per-hand lock serializes duplicate/concurrent requests. Apply on a private copy, advance automatic dealing/settlement, validate invariants, then commit. An illegal/stale request or a transition exception leaves the original state and history unchanged. Repeated requests are rejected after the first application; they do not act twice.
- A public history whitelist excludes hole deals, burns, show/muck operations, engine commentary and internal identifiers. Even terminal views hide the opponent's cards. A fold refund is represented explicitly; payout means chips awarded from the matched pot, excluding the separately returned uncalled wager. Payoff means final stack minus starting stack.
- Default hand IDs are random opaque UUIDs with no relation to the deck or any policy seed. Privileged constructors/replay can supply an existing public ID. Seeded simulations reproduce cards/actions/results rather than fresh UUIDs; replay reproduces the full recorded payload.

## Persistence and trust boundary

`replay.py` writes a new hand directory containing `seat-0.json`, `seat-1.json`, and `private/truth.json`. Each seat file contains only that seat's historical decisions and current filtered observation. Neither seat file is suitable for the other seat. The private file contains the deck and both seats' decision records, including their own-card observations. All files are created with mode 0600, hand/private directories with mode 0700; existing destinations are refused. These evaluator-only artifacts are ignored by Git.

Replay re-executes exact actions from the stored deck/config/button, then compares every decision observation, legal-action set, public event, final view and payoff. Unknown schema/engine versions or altered records fail. The CLI can verify a private replay, but prints only the selected seat's record.

A decision event records the pre-action view and resulting public events separately. Future board cards can appear in the resulting board events, never in the earlier observation used to make the decision. Later review must preserve that temporal distinction.

This is a local code boundary, not a security sandbox for malicious Python policies. Trusted policies get immutable snapshots, never the `Hand`, replay truth or another policy's configuration. There is no network/API service yet. The CLI prints one fixed seat throughout a hand, including while the opponent acts; switching to the actor's observation in stdout would leak both hands and is prohibited.

## Verification limits

Tests include an independent rank oracle (enumerating five-card combinations) and independent public-ledger reconciliation, not just comparisons with PokerKit. Stress checks run at every adapter decision transition, count all actually dealt/burned cards for uniqueness, check terminal settlement and replay all hands. Bounds invalidate a stuck sample rather than score it. There is no live policy deadline or fallback system in P0.

The transactional deepcopy favors clarity and atomicity over maximum simulation throughput. Performance optimization needs measurement in a later task. No P1 opponent factory, web UI, coaching, neural model, checkpoint or external-site adapter is implemented.
