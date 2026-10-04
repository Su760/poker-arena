"""Translate P0's action abstraction to deduplicated exact legal actions."""

from .contracts import Action, LegalAction


def legal_actions(state) -> tuple[LegalAction, ...]:
    if state.actor_index is None:
        return ()
    choices: dict[Action, list[str]] = {}

    def add(action, alias):
        choices.setdefault(action, []).append(alias)

    if state.checking_or_calling_amount > 0 and state.can_fold():
        add(Action("fold"), "fold")
    if state.can_check_or_call():
        add(Action("check_call"), "check_call")
        if state.checking_or_calling_amount == state.stacks[state.actor_index]:
            add(Action("check_call"), "all_in")
    minimum = state.min_completion_betting_or_raising_to_amount
    maximum = state.max_completion_betting_or_raising_to_amount
    if minimum is not None and maximum is not None:
        call = state.checking_or_calling_amount
        target = max(state.bets)
        # Pot already includes outstanding bets. Round half chips upward.
        pot_after_call = state.total_pot_amount + call
        candidates = (
            ("min_raise", minimum),
            ("half_pot", target + (pot_after_call + 1) // 2),
            ("pot", target + pot_after_call),
            ("all_in", maximum),
        )
        for label, amount in candidates:
            amount = min(maximum, max(minimum, amount))
            if state.can_complete_bet_or_raise_to(amount):
                add(Action("raise_to", amount), label)
    return tuple(LegalAction(action, tuple(labels)) for action, labels in choices.items())
