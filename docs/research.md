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

Unresolved P0 questions:
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
