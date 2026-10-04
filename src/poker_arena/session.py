"""Fixed-stack hands; button alternation and cumulative results stay separate."""

from random import Random
from typing import Callable

from .contracts import ActionRequest, GameConfig, Observation, Policy
from .engine import Hand


class Session:
    def __init__(self, policies: tuple[Policy, Policy], *, config=GameConfig(),
                 deck_seed: int = 0, first_button: int = 0, max_actions: int = 1000):
        if len(policies) != 2:
            raise ValueError("Require two seat policies")
        if type(first_button) is not int or first_button not in (0, 1):
            raise ValueError("Button must be 0 or 1")
        if type(deck_seed) is not int or type(max_actions) is not int or max_actions <= 0:
            raise ValueError("Require integer seed and positive action limit")
        self.config = config
        self._policies = policies
        self._deck_rng = Random(deck_seed)
        self._first_button = first_button
        self.max_actions = max_actions
        self.hands_played = 0
        self.cumulative_payoffs = (0, 0)

    def play_hand(self, *, view_seat: int = 0,
                  on_view: Callable[[Observation], None] | None = None) -> Hand:
        if type(view_seat) is not int or view_seat not in (0, 1):
            raise ValueError("View seat must be 0 or 1")
        hand = Hand(self.config, button=(self._first_button + self.hands_played) % 2,
                    deck_seed=self._deck_rng.getrandbits(128))
        for policy in self._policies:
            policy.reset_hand()
        actions = 0
        while True:
            view = hand.observe(view_seat)
            if on_view is not None:
                on_view(view)
            if view.terminal:
                break
            if actions >= self.max_actions:
                raise RuntimeError("Hand action limit exceeded; session sample invalid")
            observation = hand.observe(view.actor)
            action = self._policies[view.actor].choose(observation)
            hand.apply(ActionRequest(observation.hand_id, observation.state_version,
                                     observation.seat, action))
            actions += 1
        self.hands_played += 1
        self.cumulative_payoffs = tuple(a + b for a, b in zip(self.cumulative_payoffs, view.payoffs))
        return hand
