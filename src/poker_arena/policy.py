"""Debugging baseline: uniform over distinct offered exact actions."""

from random import Random

from .contracts import Action, Observation


class RandomPolicy:
    def __init__(self, seed: int):
        if type(seed) is not int:
            raise ValueError("Policy seed must be an integer")
        self._rng = Random(seed)

    def reset_hand(self) -> None:
        # Stateless across hands except for its independent RNG stream.
        pass

    def choose(self, observation: Observation) -> Action:
        if observation.actor != observation.seat or not observation.legal_actions:
            raise ValueError("No decision for this seat")
        return self._rng.choice(observation.legal_actions).action
