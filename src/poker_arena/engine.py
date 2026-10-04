"""Privileged PokerKit adapter. Never pass a Hand to a policy or live client."""

from collections import deque
from copy import copy, deepcopy
from random import Random
from threading import RLock
from uuid import uuid4

from pokerkit import (
    Automation, BetCollection, BlindOrStraddlePosting, BoardDealing, Card,
    CheckingOrCalling, CompletionBettingOrRaisingTo, Deck, Folding, Mode,
    NoLimitTexasHoldem,
)

from .actions import legal_actions
from .contracts import (
    ACTION_SLOTS, SCHEMA_VERSION, Action, ActionRequest, DecisionEvent,
    GameConfig, Observation, PublicEvent, json_value,
)

ENGINE_VERSION = "0.7.6"
AUTOMATIONS = (
    Automation.ANTE_POSTING, Automation.BET_COLLECTION,
    Automation.BLIND_OR_STRADDLE_POSTING, Automation.RUNOUT_COUNT_SELECTION,
    Automation.HOLE_CARDS_SHOWING_OR_MUCKING, Automation.HAND_KILLING,
    Automation.CHIPS_PUSHING, Automation.CHIPS_PULLING,
)
STREETS = ("preflop", "flop", "turn", "river")


class ActionRejected(ValueError):
    """Invalid, stale, or out-of-turn request; no state was changed."""


class Hand:
    def __init__(self, config: GameConfig = GameConfig(), *, button: int = 0,
                 deck_seed: int = 0, deck: tuple[str, ...] | None = None,
                 hand_id: str | None = None):
        if type(button) is not int or button not in (0, 1):
            raise ValueError("Button must be seat 0 or 1")
        if type(deck_seed) is not int:
            raise ValueError("Deck seed must be an integer")
        if hand_id is not None and (type(hand_id) is not str or not hand_id):
            raise ValueError("Hand ID must be a nonempty public identifier")
        self.config = config
        self.button = button
        # This identifier must never encode a seed, deck hash, or hidden cards.
        self.hand_id = hand_id if hand_id is not None else uuid4().hex
        self._lock = RLock()
        self._seats = (1 - button, button)  # engine 0 = BB, engine 1 = SB/button
        cards = list(Deck.STANDARD)
        if deck is None:
            Random(deck_seed).shuffle(cards)
        else:
            try:
                cards = list(Card.parse("".join(deck)))
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid private deck") from exc
            if (len(deck) != 52 or len(cards) != 52
                    or set(cards) != set(Deck.STANDARD)
                    or any(repr(c) != s for c, s in zip(cards, deck))):
                raise ValueError("Private deck must be a permutation of 52 cards")
        self._deck = tuple(repr(c) for c in cards)
        self._state = NoLimitTexasHoldem.create_state(
            AUTOMATIONS, True, 0, (config.small_blind, config.big_blind),
            config.big_blind, tuple(config.starting_stacks[i] for i in self._seats),
            2, mode=Mode.CASH_GAME,
        )
        # PokerKit shuffles during construction. No card operation is automated:
        # replace the entire deck before any deal/burn, without global reseeding.
        self._state.deck_cards = deque(cards)
        self._holes = (tuple(self._deck[i] for i in (0, 2)),
                       tuple(self._deck[i] for i in (1, 3)))
        self._version = 0
        self._history: tuple[PublicEvent, ...] = ()
        self._decisions: tuple[DecisionEvent, ...] = ()
        self._paid = [0, 0]
        self._round_bets = [0, 0]
        self._event_street = "preflop"
        self._operation_cursor = 0
        self._pump()
        self._collect_public_events()
        self._assert_invariants()

    def _seat_order(self, values):
        return tuple(values[self._seats.index(seat)] for seat in (0, 1))

    def _pump(self):
        while self._state.status and self._state.actor_index is None:
            if self._state.can_deal_hole():
                self._state.deal_hole(1)
            elif self._state.can_burn_card():
                self._state.burn_card()
            elif self._state.can_deal_board():
                self._state.deal_board()
            else:
                raise RuntimeError("Engine stalled outside a decision")

    def _collect_public_events(self):
        events = []
        for op in self._state.operations[self._operation_cursor:]:
            seat = self._seats[op.player_index] if hasattr(op, "player_index") else None
            if isinstance(op, (BlindOrStraddlePosting, CheckingOrCalling,
                               CompletionBettingOrRaisingTo)):
                i = op.player_index
                delta = op.amount
                if isinstance(op, CompletionBettingOrRaisingTo):
                    delta -= self._round_bets[i]
                    kind = "raise_to"
                else:
                    kind = "blind" if isinstance(op, BlindOrStraddlePosting) else (
                        "check" if op.amount == 0 else "call")
                self._round_bets[i] += delta
                self._paid[i] += delta
                events.append(PublicEvent(kind, self._event_street, seat, op.amount))
            elif isinstance(op, Folding):
                events.append(PublicEvent("fold", self._event_street, seat))
            elif isinstance(op, BetCollection):
                # In HU, excess above the smaller wager cannot be contested.
                # Normalize PokerKit's fold path (which retains the winner's bet)
                # to an explicit public refund and matched-pot payout.
                cutoff = min(self._round_bets)
                for i in (0, 1):
                    excess = self._round_bets[i] - cutoff
                    if excess:
                        self._paid[i] -= excess
                        events.append(PublicEvent("refund", self._event_street,
                                                  self._seats[i], excess))
                self._round_bets = [0, 0]
            elif isinstance(op, BoardDealing):
                self._event_street = STREETS[STREETS.index(self._event_street) + 1]
                events.append(PublicEvent("board", self._event_street,
                                          cards=tuple(repr(c) for c in op.cards)))
            # Hole dealing, burns, showing/mucking, and engine commentary are
            # deliberately excluded, including at terminal states.
        self._operation_cursor = len(self._state.operations)
        if not self._state.status:
            payouts = tuple(self._state.payoffs[i] + self._paid[i] for i in (0, 1))
            events.append(PublicEvent("settlement", self._event_street,
                                      stacks=self._seat_order(self._state.stacks),
                                      payouts=self._seat_order(payouts),
                                      payoffs=self._seat_order(self._state.payoffs)))
        self._history += tuple(events)

    def _assert_invariants(self):
        s = self._state
        if any(type(x) is not int or x < 0 for x in (*s.stacks, *s.bets, s.total_pot_amount)):
            raise RuntimeError("Noninteger or negative chip accounting")
        if sum(s.stacks) + s.total_pot_amount != sum(self.config.starting_stacks):
            raise RuntimeError("Chip conservation failed")
        dealt = []
        for op in s.operations:
            # Count actual deals, not later reveal operations, to catch duplicates.
            if type(op).__name__ in ("HoleDealing", "BoardDealing"):
                dealt.extend(op.cards)
            elif type(op).__name__ == "CardBurning":
                dealt.append(op.card)
        if len(dealt) != len(set(dealt)):
            raise RuntimeError("Duplicate card in deal")
        if s.status and (s.actor_index is None or not legal_actions(s)):
            raise RuntimeError("Hand has no legal continuation")
        if not s.status:
            final = self._history[-1]
            if (sum(s.payoffs) != 0 or sum(final.payouts) != sum(self._paid)
                    or any(x < 0 for x in final.payouts)):
                raise RuntimeError("Payout accounting failed")

    @property
    def terminal(self):
        return not self._state.status

    def observe(self, seat: int) -> Observation:
        with self._lock:
            if type(seat) is not int or seat not in (0, 1):
                raise ValueError("Seat must be 0 or 1")
            s = self._state
            actor = self._seats[s.actor_index] if s.actor_index is not None else None
            choices = legal_actions(s) if actor == seat else ()
            aliases = {alias for choice in choices for alias in choice.aliases}
            return Observation(
                SCHEMA_VERSION, SCHEMA_VERSION, self.hand_id, self._version,
                seat, self.button, actor, "terminal" if self.terminal else STREETS[s.street_index],
                self._holes[self._seats.index(seat)],
                tuple(repr(card) for group in s.board_cards for card in group),
                self._seat_order(s.stacks), self._seat_order(s.bets),
                self._seat_order(self._paid), s.total_pot_amount,
                s.checking_or_calling_amount if actor == seat else 0,
                s.min_completion_betting_or_raising_to_amount if actor == seat else None,
                s.max_completion_betting_or_raising_to_amount if actor == seat else None,
                choices, tuple(alias in aliases for alias in ACTION_SLOTS),
                self._history, self.terminal,
                self._seat_order(s.payoffs) if self.terminal else (),
            )

    def apply(self, request: ActionRequest) -> DecisionEvent:
        with self._lock:
            if (type(request) is not ActionRequest
                    or type(request.schema_version) is not int
                    or request.schema_version != SCHEMA_VERSION
                    or type(request.state_version) is not int
                    or request.hand_id != self.hand_id
                    or request.state_version != self._version
                    or type(request.seat) is not int or request.seat not in (0, 1)):
                raise ActionRejected("Invalid or stale action request")
            observation = self.observe(request.seat)
            action = request.action
            if (type(action) is not Action or type(action.amount) is not int
                    or action not in tuple(x.action for x in observation.legal_actions)):
                raise ActionRejected("Action is not offered to this seat")
            # Transition on a candidate state. Commit only after dealing,
            # settlement and accounting validation succeed.
            candidate = copy(self)
            candidate._state = deepcopy(self._state)
            candidate._paid = self._paid.copy()
            candidate._round_bets = self._round_bets.copy()
            if action.kind == "fold":
                candidate._state.fold()
            elif action.kind == "check_call":
                candidate._state.check_or_call()
            else:
                candidate._state.complete_bet_or_raise_to(action.amount)
            candidate._pump()
            candidate._collect_public_events()
            candidate._version += 1
            candidate._assert_invariants()
            decision = DecisionEvent(SCHEMA_VERSION, request.seat, self._version,
                                     observation, observation.legal_actions, action,
                                     candidate._history[len(self._history):])
            candidate._decisions += (decision,)
            self.__dict__.update(candidate.__dict__)
            return decision

    def seat_record(self, seat: int) -> dict:
        """Seat-scoped review: never include the other seat's decisions."""
        with self._lock:
            view = self.observe(seat)
            return {"schema_version": SCHEMA_VERSION,
                    "decisions": [json_value(d) for d in self._decisions if d.seat == seat],
                    "observation": json_value(view)}

    def private_record(self) -> dict:
        """Evaluator-only truth. No live client or policy may receive this."""
        with self._lock:
            if not self.terminal:
                raise ValueError("Private replay export requires a completed hand")
            return {"schema_version": SCHEMA_VERSION, "engine_version": ENGINE_VERSION,
                    "config": json_value(self.config), "button": self.button,
                    "hand_id": self.hand_id, "deck": list(self._deck),
                    "decisions": [json_value(d) for d in self._decisions],
                    "seats": [self.seat_record(i) for i in (0, 1)]}
