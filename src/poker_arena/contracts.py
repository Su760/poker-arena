"""Immutable, JSON-safe contracts. This module never imports the engine."""

from dataclasses import asdict, dataclass
import json
from typing import Literal, Protocol

SCHEMA_VERSION = 1
ACTION_SLOTS = ("fold", "check_call", "min_raise", "half_pot", "pot", "all_in")


def json_value(value):
    """Return an independent JSON value, with tuples normalized to arrays."""
    return json.loads(json.dumps(asdict(value), allow_nan=False))


@dataclass(frozen=True)
class GameConfig:
    starting_stacks: tuple[int, int] = (200, 200)
    small_blind: int = 1
    big_blind: int = 2

    def __post_init__(self):
        if type(self.starting_stacks) is not tuple or len(self.starting_stacks) != 2:
            raise ValueError("Require two positive integer stacks and 0 < SB < BB")
        values = (*self.starting_stacks, self.small_blind, self.big_blind)
        if (any(type(x) is not int or x <= 0 for x in values)
                or self.small_blind >= self.big_blind):
            raise ValueError("Require two positive integer stacks and 0 < SB < BB")


@dataclass(frozen=True)
class Action:
    kind: Literal["fold", "check_call", "raise_to"]
    amount: int = 0  # Only raise_to uses this field; calls use the quoted call amount.


@dataclass(frozen=True)
class LegalAction:
    action: Action
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class PublicEvent:
    kind: str
    street: str
    seat: int | None = None
    amount: int = 0
    cards: tuple[str, ...] = ()
    stacks: tuple[int, ...] = ()
    payouts: tuple[int, ...] = ()
    payoffs: tuple[int, ...] = ()


@dataclass(frozen=True)
class Observation:
    schema_version: int
    action_version: int
    hand_id: str
    state_version: int
    seat: int
    button: int
    actor: int | None
    street: str
    hole_cards: tuple[str, ...]
    board: tuple[str, ...]
    stacks: tuple[int, int]
    street_bets: tuple[int, int]
    contributions: tuple[int, int]
    pot: int
    to_call: int
    min_raise_to: int | None
    max_raise_to: int | None
    legal_actions: tuple[LegalAction, ...]
    action_mask: tuple[bool, ...]
    history: tuple[PublicEvent, ...]
    terminal: bool
    payoffs: tuple[int, ...]


@dataclass(frozen=True)
class ActionRequest:
    hand_id: str
    state_version: int
    seat: int
    action: Action
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class DecisionEvent:
    schema_version: int
    seat: int
    state_version: int
    observation: Observation
    legal_actions: tuple[LegalAction, ...]
    action: Action
    public_events: tuple[PublicEvent, ...]


class Policy(Protocol):
    def reset_hand(self) -> None: ...
    def choose(self, observation: Observation) -> Action: ...
