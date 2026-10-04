"""Explicitly privileged replay; seat files are separate from truth storage."""

import json
import os
from pathlib import Path

from .contracts import SCHEMA_VERSION, Action, ActionRequest, GameConfig
from .engine import ENGINE_VERSION, Hand


def replay(record: dict) -> Hand:
    """Re-execute every exact action and verify all recorded views and payouts."""
    try:
        if (type(record["schema_version"]) is not int
                or record["schema_version"] != SCHEMA_VERSION
                or record["engine_version"] != ENGINE_VERSION):
            raise ValueError("Incompatible replay version")
        config = record["config"].copy()
        config["starting_stacks"] = tuple(config["starting_stacks"])
        hand = Hand(GameConfig(**config), button=record["button"],
                    deck=tuple(record["deck"]), hand_id=record["hand_id"])
        for event in record["decisions"]:
            hand.apply(ActionRequest(hand.hand_id, event["state_version"], event["seat"],
                                     Action(**event["action"])))
        # Canonical JSON comparison distinguishes 1, 1.0 and True too.
        if json.dumps(hand.private_record(), sort_keys=True) != json.dumps(record, sort_keys=True):
            raise ValueError("Replay diverged from recorded decisions or payouts")
        return hand
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid or divergent private replay") from exc


def save_replay(hand: Hand, directory: Path) -> None:
    record = hand.private_record()
    # New directories/files only: never overwrite an existing record.
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    private_dir = directory / "private"
    private_dir.mkdir(mode=0o700)
    entries = [(private_dir / "truth.json", record)] + [
        (directory / f"seat-{i}.json", hand.seat_record(i)) for i in (0, 1)
    ]
    for path, value in entries:
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
            json.dump(value, f, indent=2, allow_nan=False)
            f.write("\n")


def load_replay(path: Path) -> Hand:
    return replay(json.loads(path.read_text()))
