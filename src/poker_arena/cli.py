"""Seeded debugging demo; stdout contains one seat's views only."""

import argparse
import json
from pathlib import Path

from .contracts import json_value
from .policy import RandomPolicy
from .replay import load_replay, save_replay
from .session import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck-seed", type=int, default=0)
    parser.add_argument("--policy-seeds", type=int, nargs=2, default=(1, 2))
    parser.add_argument("--seat", type=int, choices=(0, 1), default=0)
    parser.add_argument("--hands", type=int, default=1)
    parser.add_argument("--save", type=Path, help="New evaluator-only replay directory")
    parser.add_argument("--replay", type=Path, help="Verify a private truth.json locally")
    args = parser.parse_args()
    if args.hands <= 0:
        parser.error("--hands must be positive")
    if args.replay:
        hand = load_replay(args.replay)
        print(json.dumps({"replay_verified": True, "seat_record": hand.seat_record(args.seat)}))
        return
    if args.save and args.save.exists():
        parser.error("--save directory already exists; choose a new path")
    session = Session(tuple(RandomPolicy(seed) for seed in args.policy_seeds), deck_seed=args.deck_seed)
    for i in range(args.hands):
        hand = session.play_hand(view_seat=args.seat,
                                 on_view=lambda view: print(json.dumps(json_value(view))))
        if args.save:
            save_replay(hand, args.save / f"hand-{i + 1}")
    print(json.dumps({"hands": session.hands_played,
                      "cumulative_payoffs": session.cumulative_payoffs}))


if __name__ == "__main__":
    main()
