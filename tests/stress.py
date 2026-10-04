"""Seeded P0 gate; failures are written only to a private local artifact."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

from poker_arena.contracts import ActionRequest, GameConfig
from poker_arena.engine import Hand
from poker_arena.policy import RandomPolicy
from poker_arena.replay import replay
from oracle import verify_record


def run(hands, seed, varied):
    counts = Counter()
    digest = hashlib.sha256()
    started = perf_counter()
    for index in range(hands):
        stacks = ((200, 200), (200, 5), (17, 200), (1, 200), (201, 200))[index % 5] if varied else (200, 200)
        deck_seed = seed + index
        policy_seeds = (seed + hands + 2 * index, seed + hands + 2 * index + 1)
        requests = []
        try:
            hand = Hand(GameConfig(stacks), button=index % 2, deck_seed=deck_seed,
                        hand_id=f"stress-hand-{index}")  # Public index, never a seed/hash.
            policies = tuple(RandomPolicy(value) for value in policy_seeds)
            for policy in policies:
                policy.reset_hand()
            while not hand.terminal:
                view = hand.observe(0)
                for seat in (0, 1):
                    o = hand.observe(seat)
                    assert sum(o.stacks) + o.pot == sum(stacks)
                    assert all(type(x) is int and x >= 0 for x in (*o.stacks, *o.street_bets, o.pot))
                    assert len(set(o.hole_cards + o.board)) == len(o.hole_cards + o.board)
                assert len(requests) < 1000, "Stuck hand"
                o = hand.observe(view.actor)
                action = policies[o.seat].choose(o)
                requests.append({"seat": o.seat, "kind": action.kind, "amount": action.amount})
                hand.apply(ActionRequest(o.hand_id, o.state_version, o.seat, action))
                hand._assert_invariants()
            record = hand.private_record()
            counts[verify_record(record)] += 1
            assert replay(record).private_record() == record
            digest.update(json.dumps(record, sort_keys=True).encode())
            counts["hands"] += 1
            counts["actions"] += len(requests)
            counts["replays"] += 1
        except Exception:
            directory = Path("artifacts/private")
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = directory / f"stress-failure-{seed}-{index}.json"
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
                json.dump({"seed": seed, "hands": hands, "varied": varied,
                           "deck_seed": deck_seed, "policy_seeds": policy_seeds,
                           "index": index, "stacks": stacks,
                           "button": index % 2, "actions": requests}, f)
            print(f"Failure details saved to {path}", flush=True)
            raise
        if (index + 1) % 1000 == 0:
            print(json.dumps({"progress": index + 1, "seconds": round(perf_counter() - started, 2)}), flush=True)
    print(json.dumps({"result": "passed", **counts, "seed": seed, "varied": varied,
                      "sha256": digest.hexdigest(), "seconds": round(perf_counter() - started, 2)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hands", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20261002)
    parser.add_argument("--varied", action="store_true")
    args = parser.parse_args()
    if args.hands <= 0:
        parser.error("--hands must be positive")
    run(args.hands, args.seed, args.varied)
