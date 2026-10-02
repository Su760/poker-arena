# Architecture and decisions

Status: proposed architecture; implementation pending.

## Boundaries

| Component | Responsibility | Permitted information |
| --- | --- | --- |
| Game adapter | PokerKit integration, legal transitions, payouts | Full private engine state |
| Observation builder | Produce a seat-specific immutable snapshot | Full input state internally; filtered output only |
| Action translator | Resolve abstract choices to exact legal engine actions | Public betting data and engine legality queries |
| Policy | Choose from supplied legal actions | Seat observation and independent policy RNG |
| Session runner / CLI | Alternate seats, run hands, collect results | Control data; printed views must remain seat-filtered |
| Replay storage | Reconstruct completed hands | Private truth stored separately from seat-visible events |
| Future review layer | Explain past decisions | Decision-time information; separately labeled showdown reveal |

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
