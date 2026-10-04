# Research log

Research supports project decisions; it does not establish playing strength. Entries below distinguish checked sources from implementation questions.

## 2026-10-02: repository workflow

Sources:

- [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [OpenAI: best practices](https://learn.chatgpt.com/guides/best-practices)

Checked findings: Codex discovers repository instructions at session startup. OpenAI recommends practical repository guidance, concrete task goals, and verification. Restarting after pulling new instructions avoids relying on a session created before those instructions existed.

Project decision: maintain a concise root AGENTS.md and link the spec, current plan, and latest handoff. Keep research attached to active engineering questions. These are workflow choices, not a guarantee of optimal output.

## 2026-10-02: poker engine suitability

Source: [PokerKit stable documentation](https://pokerkit.readthedocs.io/en/stable/)

Checked findings: the retrieved documentation identifies itself as version 0.7.6, requires Python 3.11+, and provides NoLimitTexasHoldem examples using explicit dealing, betting, and automation settings.

Project decision: retain PokerKit behind an adapter. The retrieved stable-documentation version is not yet an installed dependency pin. Resolve and lock a compatible version during P0 and check that version's API.

Original P0 questions (resolved in the entry below):

- How do PokerKit seat indices map to the heads-up button/small blind and postflop action order?
- Which automations are needed, and when do collection, refunds, and payouts occur?
- How can a deterministic complete deal be supplied without coupling deck randomness to policy randomness?
- How are short all-ins, minimum raises, and reopening represented?
- What public/pot quantities must the adapter expose without double counting chips?
- Which completed-hand fields are safe for seat replay, and which must remain private?

Resolve each question through version-matched documentation/source and focused executable examples/tests. Record actual findings; do not infer a passing adapter from library examples.

## Entry format for future work

Date; milestone/question; primary-source URLs; installed version or paper version; checked finding; proposed project decision; implementation evidence; unresolved limitations.

Future algorithm comparisons belong to P3/P4. The original spec's training references are research leads until checked for the selected implementation.

## 2026-10-02: P0 engine decisions, verified against PokerKit 0.7.6

Primary sources retrieved: [tagged simulation documentation](https://github.com/uoftcprg/pokerkit/blob/v0.7.6/docs/simulation.rst), [examples](https://github.com/uoftcprg/pokerkit/blob/v0.7.6/docs/examples.rst), [state implementation](https://github.com/uoftcprg/pokerkit/blob/v0.7.6/pokerkit/state.py), [card/chip utilities](https://github.com/uoftcprg/pokerkit/blob/v0.7.6/pokerkit/utilities.py), [upstream state tests](https://github.com/uoftcprg/pokerkit/blob/v0.7.6/pokerkit/tests/test_state.py), and [release metadata](https://pypi.org/pypi/pokerkit/0.7.6/json).

The browser could not retrieve the versioned ReadTheDocs page. Fallback: downloaded the official GitHub `v0.7.6` archive, read its documentation/source/tests, and compared installed `state.py`, `games.py`, and `utilities.py` byte-for-byte with that tag; all matched. The initial unprefixed `0.7.6` GitHub archive URL returned 404; `v0.7.6` succeeded. PyPI metadata says Python >=3.11 and no runtime dependencies. Installed and pinned PokerKit 0.7.6. Only PokerKit is a runtime dependency; standard-library unittest supplies our tests. Hatchling 1.27.0 and its resolved build dependencies are recorded in the lockfile's optional build group.

| Question                | Verified finding                                                                                                                                                                                                                               | Adapter decision and executable evidence                                                                                                                                                                                                                                                                                                                                      |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Heads-up positions      | `State._begin_betting` reverses blind positions for two players; with raw blinds `(1,2)`, position 0 posts 2 and position 1 posts 1. Position 1 opens preflop, position 0 opens later streets.                                                 | Engine positions map to `(nonbutton, button)`. Tests cover both button assignments, the BB option after a limp, and all streets.                                                                                                                                                                                                                                              |
| Automations and refunds | `collect_bets` caps unmatched contributions and returns excess. On folds, the winner's outstanding bet can be retained through chip pushing. `CHIPS_PULLING` completes settlement.                                                             | Automate posting, collection, single-runout selection, showing/mucking, killing, pushing and pulling. Manually deal/burn. Public ledger normalizes refunds separately from matched-pot payouts. Tests verify 200 vs 17 all-in, raise/fold, blind folds, and known winners.                                                                                                    |
| Deterministic dealing   | `_setup` globally shuffles `deck_cards`. Dealing methods consume this deque; with no dealing/burning automations, no card is consumed on construction.                                                                                         | Shuffle all 52 cards using a private `Random(deck_seed)` and replace the deque before the first deal. Deal round-robin, with real burn cards. Do not seed or monkeypatch global randomness. Extra policy draws do not change deals; replay stores the full private deck for independence from future RNG implementation changes.                                              |
| Raises and reopening    | Minimum/maximum raise-to queries and `can_complete_bet_or_raise_to` encode short-stack exceptions. `_verify_completion_betting_or_raising` bars previously acting players after a non-full raise, and bars raising against an all-in opponent. | Offer only validated exact raises. A short all-in may be below a full raise; calls consume only the remaining difference. In HU, the opponent of an all-in player cannot reraise even if the all-in was full. Adapter tests plus upstream `test_full_and_short_all_ins` and `test_all_ins` passed. Multiway reopening is upstream evidence, not an implemented arena variant. |
| Pot accounting          | `total_pot_amount` includes outstanding bets; stacks exclude them.                                                                                                                                                                             | Use it once. Pot-based target = largest street bet + fraction of `(pot + call)`, rounded half-up in integer units and clamped to engine limits. Starting 1/2 blinds yield min/half-pot 4, pot 6, all-in 200. Independent ledger checks validate every completed stress hand.                                                                                                  |
| Safe history/replay     | Raw operations contain dealt cards, burns, and show/muck data. `str(Card)` produces prose; `repr(Card)` produces the parseable two-character code.                                                                                             | Whitelist public blind/check/call/raise/fold/board/refund/settlement events. Keep own cards cached across mucking. Seat records include only that seat's decision observations. Truth and both seats' decisions go only in the private record. Card-code regression and hidden-state invariance tests pass.                                                                   |

Additional resolved details:

- PokerKit cash mode allows a free fold with a warning. P0 deliberately masks folds when checking is free. Tests run with warnings treated as errors.
- `all_in` is an alias of `check_call` when calling consumes the remaining stack, and of `raise_to` when aggressive. Aliases resolving to the same action do not receive extra random-policy weight.
- Chips remain integers. PokerKit's integer `divmod` preserves integer quotient/remainder and assigns a remainder to the first eligible position. Under P0's two-player, no-ante/no-rake rules, matched contributions make every tied pot even; an odd-chip split is unreachable. A test with starting stacks 201/200 verifies a one-chip refund and exact 200/200 tie payout. Odd multiway splits are not claimed tested.
- Identity is independent of hidden truth: default hand IDs are UUID4 values, not deck hashes or seeds. Identical seeded runs reproduce deals/actions/results; UUIDs intentionally differ. Replays preserve the recorded ID. Test fixtures use a fixed public ID when comparing identical visible situations.
- No open engine question remains for the P0 variant. The full record is privileged and Python policies are trusted local code, not sandboxed arbitrary uploads. Human reveal views, deadlines/fallback accounting, checkpoints, API endpoints and training remain later work.

## 2026-10-02: global Stop-hook JSON warning

Installed CLI: `codex-cli 0.160.0`. Primary contract: [version-matched stop handler](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/hooks/src/events/stop.rs#L279) and [output schema](https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/hooks/src/schema.rs#L455).

Confirmed source: `/Users/supashramesha/.codex/hooks.json:41`, `hooks.Stop[0].hooks[0]`. This global command is an `echo` of a memory reminder. Re-executing that exact, side-effect-free command returned exit 0, empty stderr, and this stdout (with a trailing newline):

```text
Session complete. Update ~/claude-workspace/MEMORY.md with what changed this session. Mark any completed kalshi-bot phases. Remove resolved blockers.
```

JSON parsing fails with `Expecting value: line 1 column 1 (char 0)`. The tagged Codex Stop handler parses nonempty successful output as JSON and emits the exact warning at `stop.rs:333` if parsing fails for a control-capable hook. This is a reproduced formatting defect, not evidence that the reminder's memory work ran. The local SQLite logs searched did not contain a retained runtime warning event for this thread, so attribution is based on the exact configured command, captured output, and version-matched handler.

Proposed global fix: preserve the exact reminder text under a JSON `systemMessage` key (exit 0), using a JSON encoder. That preserves its nonblocking reminder behavior. Do not change it into a blocking hook, silence it, or disable other hooks. `hooks.Stop[1]` invokes `hooks/on-stop.js` for session-learning writes; it was inspected but not executed or changed. The claude-mem plugin Stop hook is separate. No hook configuration, permissions, or memory files were modified.


## 2026-10-03: P0 verification and Stop-hook repair validation

The installed PokerKit version and runtime source are unchanged. Reused the version-matched primary-source findings above; both selected upstream all-in tests pass again. No new engine assumptions or dependencies were introduced. Repeated 10,000-hand and 1,000 varied-stack runs reproduce the previous full-record hashes exactly. All 28 focused tests pass on Python 3.13.11 and on the previously installed wheel with Python 3.11.14.

Concrete harness gap: `tests/stress.py` created the hand before its exception handler, so initialization failures escaped without a failure artifact. A regression first failed at `assertTrue(path.exists())`; moving initialization inside the handler and recording the hand budget, run variant, deck seed and both policy seeds fixes reproduction inputs. The regression also checks private file mode 0600. No game behavior changed.

The first global Stop hook remains the plain-text command identified above. A reviewed replacement uses `printf` with JSON encoded by Python, emitting only `{"systemMessage": "<unchanged reminder>"}` and a newline. Executing the candidate returned exit 0, empty stderr and valid JSON with the exact original reminder. Parsed-config comparison verified every other hook is unchanged. Applying it via normal escalation was rejected because `sandbox_approval` is disabled; the active file was not modified. A byte-identical mode-0600 backup and reviewed repair script are preserved under ignored `artifacts/private/p0-verification-20261003/`. No approval settings changed.

Separate scoping issue: the global reminder names `kalshi-bot` and `~/claude-workspace/MEMORY.md` for every project. JSON repair alone deliberately retains that wording; deciding its project scope is a separate global-configuration task. No Kalshi or memory files were modified.
