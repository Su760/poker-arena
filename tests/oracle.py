"""Independent five-card rank enumeration and public chip ledger for checks."""

from collections import Counter
from itertools import combinations

CARDS = tuple(r + s for r in "23456789TJQKA" for s in "cdhs")


def rank_five(cards):
    ranks = sorted(("23456789TJQKA".index(c[0]) + 2 for c in cards), reverse=True)
    groups = sorted(((count, rank) for rank, count in Counter(ranks).items()), reverse=True)
    flush = len({c[1] for c in cards}) == 1
    straight = (5 if ranks == [14, 5, 4, 3, 2] else
                ranks[0] if len(set(ranks)) == 5 and ranks[0] - ranks[-1] == 4 else 0)
    if straight and flush:
        return (8, straight)
    if groups[0][0] == 4:
        return (7, groups[0][1], groups[1][1])
    if [g[0] for g in groups] == [3, 2]:
        return (6, groups[0][1], groups[1][1])
    if flush:
        return (5, *ranks)
    if straight:
        return (4, straight)
    if groups[0][0] == 3:
        return (3, *(g[1] for g in groups))
    if [g[0] for g in groups[:2]] == [2, 2]:
        return (2, *(g[1] for g in groups))
    if groups[0][0] == 2:
        return (1, *(g[1] for g in groups))
    return (0, *ranks)


def rank_seven(cards):
    return max(rank_five(c) for c in combinations(cards, 5))


def rigged(bb="AsAh", sb="KsKh", board="2c3d4h5s9c"):
    split = lambda s: [s[i:i + 2] for i in range(0, len(s), 2)]
    a, b, board = split(bb), split(sb), split(board)
    used = a + b + board
    assert len(set(used)) == 9
    burns = [c for c in CARDS if c not in used][:3]
    first = [a[0], b[0], a[1], b[1], burns[0], *board[:3], burns[1], board[3], burns[2], board[4]]
    return tuple(first + [c for c in CARDS if c not in first])


def verify_record(record):
    deck = record["deck"]
    assert len(deck) == len(set(deck)) == 52 and set(deck) == set(CARDS)
    view = record["seats"][0]["observation"]
    history = view["history"]
    initial = record["config"]["starting_stacks"]
    paid, bets = [0, 0], [0, 0]
    street = "preflop"
    fold = None
    board = []
    for e in history:
        if e["street"] != street:
            bets = [0, 0]
            street = e["street"]
        i, amount, kind = e["seat"], e["amount"], e["kind"]
        if kind in ("blind", "call"):
            paid[i] += amount
            bets[i] += amount
        elif kind == "raise_to":
            assert amount > max(bets)
            paid[i] += amount - bets[i]
            bets[i] = amount
        elif kind == "refund":
            assert amount == bets[i] - bets[1 - i]
            paid[i] -= amount
            bets[i] -= amount
        elif kind == "fold":
            fold = i
        elif kind == "board":
            board.extend(e["cards"])
        assert all(0 <= paid[i] <= initial[i] for i in (0, 1))
    assert paid[0] == paid[1]
    expected_board = [deck[i] for i in (5, 6, 7, 9, 11)][:len(board)]
    assert board == expected_board == view["board"]
    if fold is not None:
        winners = [1 - fold]
    else:
        assert len(board) == 5
        button = record["button"]
        holes = [None, None]
        holes[button] = [deck[1], deck[3]]
        holes[1 - button] = [deck[0], deck[2]]
        ranks = [rank_seven(cards + board) for cards in holes]
        winners = [i for i in (0, 1) if ranks[i] == max(ranks)]
    pot = sum(paid)
    # HU matched contributions make a tied pot even: no fractional chips.
    assert pot % len(winners) == 0
    payouts = [pot // len(winners) if i in winners else 0 for i in (0, 1)]
    expected = [initial[i] - paid[i] + payouts[i] for i in (0, 1)]
    assert view["stacks"] == expected, (view["stacks"], expected)
    assert view["payoffs"] == [expected[i] - initial[i] for i in (0, 1)]
    assert history[-1]["payouts"] == payouts
    assert view["contributions"] == paid
    return "fold" if fold is not None else "tie" if len(winners) == 2 else "showdown"
