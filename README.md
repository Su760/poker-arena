# Poker Arena

A local poker practice arena and bot-training project.

Play against configurable opponent styles, review your decisions, and eventually train and evaluate your own agents.

**Status:** P0 core implemented: PokerKit heads-up Hold'em, private/seat observations, exact legal actions, random baseline, replay and CLI. P0 correctness was reverified on 2026-10-03. Git recovery is complete; review-branch publication is blocked by this session's read-only Git metadata. See [review handoff](docs/review-handoff.md). No UI, coaching or trained model is implemented.

## Start here

- [Project specification](Poker-Arena-Project-Spec.md): product goals, game rules, privacy boundaries, and milestone gates.
- [Agent instructions](AGENTS.md): how to work in this repository.
- [Implementation plan](docs/plan.md): current task and completion checklist.
- [Architecture](docs/architecture.md): proposed boundaries and decisions.
- [Research log](docs/research.md): sources, findings, and unresolved questions.
- [Review handoff](docs/review-handoff.md): verified progress for the next session.

## Run P0

Python 3.11+ and uv are required. Tested with Python 3.11.14 and 3.13.11, uv 0.9.18. From this directory:

```sh
uv run --cache-dir /tmp/poker-arena-uv-cache --locked python -c 'import poker_arena; print(poker_arena.__version__)'
.venv/bin/python -W error -m unittest discover -s tests -v
.venv/bin/python -W error tests/stress.py --hands 10000 --seed 20261002
.venv/bin/python -m poker_arena --deck-seed 12 --policy-seeds 34 56 --seat 0 --hands 2
```

The demo prints JSON views for seat 0 only, then cumulative chip results. For those seeds the two payoffs are `[2, -2]` and `[-10, 10]`, with cumulative `[-8, 8]`. One BB equals two chip units. Stacks reset to 200/200 each hand; the button alternates. Fresh hand IDs vary independently of the deal.

Save and verify replay using a **new** directory:

```sh
.venv/bin/python -m poker_arena --deck-seed 12 --policy-seeds 34 56 --seat 0 --hands 2 --save artifacts/p0-demo
.venv/bin/python -m poker_arena --replay artifacts/p0-demo/hand-1/private/truth.json --seat 0
```

The recorded demo directory may already exist in this workspace; use a different `--save` destination for another run. Existing files are refused, never overwritten. `private/truth.json` contains the full deal and both players' decisions: keep it with the local evaluator. `seat-0.json` and `seat-1.json` are separate seat-scoped review records. CLI replay prints only the selected seat's view, even after showdown.

Additional checks and an optional wheel build:

```sh
.venv/bin/python -W error tests/stress.py --hands 1000 --seed 20262002 --varied
.venv/bin/python -m compileall -q src tests
uv run --cache-dir /tmp/poker-arena-uv-cache --locked --group build python -m hatchling build -t wheel
```

PokerKit 0.7.6 is the only runtime dependency. The lockfile also pins the optional packaging group. unittest is part of Python; no web, numerical, or training framework is installed for P0. The explicit cache location avoids a local sandbox denial on the default uv cache; application commands use the installed environment directly because uv 0.9.18 also panicked under some sandboxed shell invocations.

The random baseline is for debugging. This project makes no claims about playing strength or profitability. Stop at P0; P1 requires a separate review/task.
