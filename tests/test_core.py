import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from contextlib import chdir, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
from random import Random
import tempfile
from unittest.mock import patch

from poker_arena.contracts import Action, ActionRequest, GameConfig, json_value
from poker_arena.engine import ActionRejected, Hand
from poker_arena.policy import RandomPolicy
from poker_arena.replay import load_replay, replay, save_replay
from poker_arena.session import Session
from oracle import rank_five, rigged, verify_record


def act(hand, kind="check_call", amount=0):
    seat = hand.observe(0).actor
    view = hand.observe(seat)
    return hand.apply(ActionRequest(view.hand_id, view.state_version, seat, Action(kind, amount)))


class CoreTests(unittest.TestCase):
    def test_stress_initialization_failure_preserves_reproduction_inputs(self):
        import stress
        with tempfile.TemporaryDirectory() as directory, chdir(directory), \
                patch.object(stress, "Hand", side_effect=RuntimeError("initialization failed")), \
                redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "initialization failed"):
                stress.run(10, 123, True)
            path = Path("artifacts/private/stress-failure-123-0.json")
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            record = json.loads(path.read_text())
            self.assertEqual(record["hands"], 10)
            self.assertEqual(record["seed"], 123)
            self.assertEqual(record["deck_seed"], 123)
            self.assertEqual(record["policy_seeds"], [133, 134])
            self.assertTrue(record["varied"])
            self.assertEqual(record["actions"], [])

    def finish_calling(self, hand):
        for _ in range(20):
            if hand.terminal:
                verify_record(hand.private_record())
                return
            act(hand)
        self.fail("Hand stuck")

    def test_heads_up_blinds_and_every_street_order(self):
        for button in (0, 1):
            hand = Hand(button=button)
            view = hand.observe(button)
            self.assertEqual(view.actor, button)
            self.assertEqual(view.stacks[button], 199)
            self.assertEqual(view.stacks[1 - button], 198)
            self.assertEqual(view.pot, 3)
            self.assertEqual(view.to_call, 1)
            act(hand)
            self.assertEqual(hand.observe(0).actor, 1 - button)
            for street in ("flop", "turn", "river"):
                act(hand)
                view = hand.observe(1 - button)
                self.assertEqual((view.street, view.actor, view.pot), (street, 1 - button, 4))
                self.assertEqual(view.to_call, 0)
                act(hand)
                self.assertEqual(hand.observe(0).actor, button)
            act(hand)
            self.assertTrue(hand.terminal)

    def test_raise_to_sizes_pot_after_call_and_deduplication(self):
        hand = Hand()
        choices = hand.observe(0).legal_actions
        self.assertEqual([x.action for x in choices], [Action("fold"), Action("check_call"),
                         Action("raise_to", 4), Action("raise_to", 6), Action("raise_to", 200)])
        self.assertEqual(choices[2].aliases, ("min_raise", "half_pot"))
        act(hand, "raise_to", 6)
        view = hand.observe(1)
        self.assertEqual((view.stacks, view.street_bets, view.pot, view.to_call),
                         ((194, 198), (6, 2), 8, 4))
        self.assertEqual(view.min_raise_to, 10)
        self.assertEqual([x.action.amount for x in view.legal_actions if x.action.kind == "raise_to"],
                         [10, 12, 18, 200])

    def test_custom_blinds_and_stack_clamping(self):
        hand = Hand(GameConfig((20, 20), 1, 3))
        # P=4, call=2, half raise = 3 + 3 = 6; pot raise = 9.
        self.assertEqual([x.action.amount for x in hand.observe(0).legal_actions[2:]], [6, 9, 20])
        short = Hand(GameConfig((3, 200)))
        raises = [x for x in short.observe(0).legal_actions if x.action.kind == "raise_to"]
        self.assertEqual(len(raises), 1)
        self.assertEqual(raises[0].action.amount, 3)
        self.assertEqual(raises[0].aliases, ("min_raise", "half_pot", "pot", "all_in"))

    def test_short_all_in_does_not_reopen_and_call_is_incremental(self):
        hand = Hand(GameConfig((200, 5)))
        act(hand, "raise_to", 4)
        act(hand, "raise_to", 5)
        view = hand.observe(0)
        self.assertEqual(view.to_call, 1)
        self.assertIsNone(view.min_raise_to)
        self.assertEqual([x.action for x in view.legal_actions], [Action("fold"), Action("check_call")])
        self.finish_calling(hand)
        self.assertEqual(hand.observe(0).contributions, (5, 5))

    def test_full_raise_reopens_when_both_have_chips(self):
        hand = Hand()
        act(hand, "raise_to", 4)
        act(hand, "raise_to", 6)
        self.assertEqual(hand.observe(0).min_raise_to, 8)
        act(hand, "raise_to", 8)
        self.finish_calling(hand)

    def test_fold_and_uncalled_overbet_refund(self):
        for amount, expected in ((0, (199, 201)), (200, (202, 198))):
            hand = Hand()
            if amount:
                act(hand, "raise_to", amount)
            act(hand, "fold")
            self.assertEqual(hand.observe(0).stacks, expected)
            refunds = [e.amount for e in hand.observe(0).history if e.kind == "refund"]
            self.assertEqual(refunds, [198 if amount else 1])
            verify_record(hand.private_record())

    def test_short_call_refund_and_known_showdown(self):
        hand = Hand(GameConfig((200, 17)), deck=rigged())
        act(hand, "raise_to", 200)
        self.assertEqual(hand.observe(1).to_call, 15)
        act(hand)
        # BB aces make a wheel and beat the button's kings.
        self.assertEqual(hand.observe(0).stacks, (183, 34))
        self.assertEqual(hand.observe(0).payoffs, (-17, 17))
        self.assertIn(183, [e.amount for e in hand.observe(0).history if e.kind == "refund"])
        verify_record(hand.private_record())

    def test_board_plays_tie_and_odd_starting_total_refund(self):
        hand = Hand(GameConfig((201, 200)), deck=rigged("2c3d", "4c5d", "AsKsQsJsTs"))
        act(hand, "raise_to", 201)
        act(hand)
        self.assertEqual(hand.observe(0).stacks, (201, 200))
        self.assertEqual(hand.observe(0).history[-1].payouts, (200, 200))
        self.assertEqual(verify_record(hand.private_record()), "tie")

    def test_equal_hand_tie_with_different_hole_suits(self):
        hand = Hand(deck=rigged("AsKd", "AhKc", "2c3d4h9sTc"))
        self.finish_calling(hand)
        self.assertEqual(hand.observe(0).stacks, (200, 200))

    def test_blind_all_ins_and_integer_conservation(self):
        for stacks in ((1, 1), (1, 200), (200, 1), (2, 3), (3, 2)):
            for button in (0, 1):
                hand = Hand(GameConfig(stacks), button=button)
                self.finish_calling(hand)
                self.assertEqual(sum(hand.observe(0).stacks), sum(stacks))
                self.assertTrue(all(type(x) is int for x in hand.observe(0).stacks))

    def test_invalid_requests_are_atomic(self):
        hand = Hand()
        view = hand.observe(0)
        request = ActionRequest(view.hand_id, view.state_version, 0, Action("check_call"))
        bad = [replace(request, hand_id="another-hand"), replace(request, state_version=1),
               replace(request, state_version=False), replace(request, seat=True),
               replace(request, seat=1), replace(request, seat=2),
               replace(request, schema_version=True), replace(request, schema_version=2),
               *[replace(request, action=a) for a in (Action("raise_to", 3), Action("raise_to", 201),
                 Action("raise_to", 5), Action("raise_to", 4.0), Action("fold", True),
                 Action("check_call", 1), Action("invalid"))]]
        before = deepcopy(hand._state.__dict__), hand.seat_record(0), hand.seat_record(1)
        for req in bad:
            with self.subTest(req=req), self.assertRaises(ActionRejected):
                hand.apply(req)
            self.assertEqual((hand._state.__dict__, hand.seat_record(0), hand.seat_record(1)), before)
        hand.apply(request)
        after = deepcopy(hand._state.__dict__)
        with self.assertRaises(ActionRejected):
            hand.apply(request)
        self.assertEqual(hand._state.__dict__, after)

    def test_internal_failure_rolls_back(self):
        hand = Hand()
        before = deepcopy(hand._state.__dict__), hand.seat_record(0)
        with patch.object(Hand, "_pump", side_effect=RuntimeError("injected failure")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                act(hand)
        self.assertEqual((hand._state.__dict__, hand.seat_record(0)), before)

    def test_concurrent_duplicate_applied_once(self):
        hand = Hand()
        req = ActionRequest(hand.hand_id, 0, 0, Action("check_call"))
        def submit():
            try:
                hand.apply(req)
                return "accepted"
            except ActionRejected:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(lambda _: submit(), range(2))), ["accepted", "rejected"])
        self.assertEqual(hand.observe(0).state_version, 1)

    def test_hidden_cards_labels_and_future_deck_cannot_affect_view(self):
        deck = rigged()
        other = list(deck)
        other[0], other[20] = other[20], other[0]  # Opponent hole.
        other[2], other[21] = other[21], other[2]
        other[9], other[22] = other[22], other[9]  # Future turn.
        a = Hand(deck=deck, hand_id="public-test-id")
        b = Hand(deck=tuple(other), hand_id="public-test-id")
        a._opponent_label, b._opponent_label = "nit", "maniac"
        for _ in range(3):
            self.assertEqual(json_value(a.observe(0)), json_value(b.observe(0)))
            self.assertEqual(a.seat_record(0), b.seat_record(0))
            if a.observe(0).street == "flop":
                break
            act(a)
            act(b)
        text = json.dumps(a.seat_record(0))
        for secret in ("As", "Ah", "nit", "maniac", "deck", "seed", "_state"):
            self.assertNotIn(secret, text)
        with self.assertRaises(FrozenInstanceError):
            a.observe(0).pot = 999
        serialized = a.seat_record(0)
        serialized["observation"]["stacks"][0] = 999
        self.assertNotEqual(a.observe(0).stacks[0], 999)

    def test_terminal_and_saved_seat_records_remain_filtered(self):
        hand = Hand(deck=rigged())
        self.finish_calling(hand)
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "record"
            save_replay(hand, dest)
            self.assertEqual(load_replay(dest / "private/truth.json").private_record(), hand.private_record())
            for seat, hidden in ((0, ("As", "Ah")), (1, ("Ks", "Kh"))):
                text = (dest / f"seat-{seat}.json").read_text()
                for card in hidden:
                    self.assertNotIn('"' + card + '"', text)
                for e in json.loads(text)["decisions"]:
                    self.assertEqual(e["seat"], seat)
            with self.assertRaises(FileExistsError):
                save_replay(hand, dest)

    def test_policy_rng_draws_do_not_change_deals(self):
        class CallingPolicy:
            def __init__(self, extra):
                self.rng, self.extra, self.resets = Random(2), extra, 0
            def reset_hand(self):
                self.resets += 1
            def choose(self, observation):
                for _ in range(self.extra):
                    self.rng.random()
                return Action("check_call")
        policies_a = (CallingPolicy(0), CallingPolicy(0))
        policies_b = (CallingPolicy(100), CallingPolicy(200))
        a, b = Session(policies_a, deck_seed=871), Session(policies_b, deck_seed=871)
        for _ in range(4):
            ra, rb = a.play_hand().private_record(), b.play_hand().private_record()
            self.assertEqual(ra["deck"], rb["deck"])
            self.assertEqual(ra["seats"][0]["observation"]["board"], rb["seats"][0]["observation"]["board"])
        self.assertEqual(policies_b[0].resets, 4)

    def test_reproducible_policies_stacks_reset_button_and_totals(self):
        a = Session((RandomPolicy(4), RandomPolicy(5)), deck_seed=8)
        b = Session((RandomPolicy(4), RandomPolicy(5)), deck_seed=8)
        payoffs = [0, 0]
        for i in range(10):
            ha, hb = a.play_hand(), b.play_hand()
            ra, rb = ha.private_record(), hb.private_record()
            self.assertEqual(ha.button, i % 2)
            self.assertEqual(ra["config"]["starting_stacks"], [200, 200])
            self.assertEqual(ra["deck"], rb["deck"])
            self.assertEqual([d["action"] for d in ra["decisions"]], [d["action"] for d in rb["decisions"]])
            self.assertEqual(ha.observe(0).payoffs, hb.observe(0).payoffs)
            payoffs = [x + y for x, y in zip(payoffs, ha.observe(0).payoffs)]
        self.assertEqual(a.cumulative_payoffs, tuple(payoffs))

    def test_random_policy_uniform_over_unique_actions(self):
        view = Hand().observe(0)
        policy = RandomPolicy(731)
        actions = [x.action for x in view.legal_actions]
        counts = {a: 0 for a in actions}
        for _ in range(20000):
            counts[policy.choose(view)] += 1
        self.assertTrue(all(3700 < n < 4300 for n in counts.values()), counts)

    def test_replay_tampering_and_incompatible_versions_rejected(self):
        hand = Hand()
        act(hand, "fold")
        record = hand.private_record()
        mutations = [lambda r: r.update(schema_version=2), lambda r: r.update(schema_version=True),
                     lambda r: r.update(engine_version="0.0.0"),
                     lambda r: r["decisions"][0]["action"].update(kind="check_call"),
                     lambda r: r["decisions"][0]["observation"].update(pot=9),
                     lambda r: r["seats"][0]["observation"].update(payoffs=[0, 0]),
                     lambda r: r["deck"].__setitem__(0, r["deck"][1])]
        for mutate in mutations:
            bad = deepcopy(record)
            mutate(bad)
            with self.assertRaises(ValueError):
                replay(bad)

    def test_config_validation(self):
        for stacks in (None, 200, (0, 200), (-1, 200), (True, 200), (200.0, 200), (1,), (1, 2, 3)):
            with self.assertRaises(ValueError):
                GameConfig(stacks)
        for sb, bb in ((0, 2), (2, 2), (3, 2), (1, float("inf")), (True, 2)):
            with self.assertRaises(ValueError):
                GameConfig(small_blind=sb, big_blind=bb)

    def test_own_holes_seat_mapping_and_deck_validation(self):
        for button in (0, 1):
            hand = Hand(button=button, deck=rigged())
            self.assertEqual(hand.observe(button).hole_cards, ("Ks", "Kh"))
            self.assertEqual(hand.observe(1 - button).hole_cards, ("As", "Ah"))
        bad = list(rigged())
        bad[0] = bad[1]
        for deck in (tuple(bad), rigged()[:-1], ("??",) * 52):
            with self.assertRaises(ValueError):
                Hand(deck=deck)

    def test_all_in_call_alias_deduplicates(self):
        hand = Hand(GameConfig((200, 17)))
        act(hand, "raise_to", 200)
        choices = hand.observe(1).legal_actions
        self.assertEqual([x.action for x in choices], [Action("fold"), Action("check_call")])
        self.assertEqual(choices[1].aliases, ("check_call", "all_in"))

    def test_action_limit_is_failure_not_scored_result(self):
        class CallingPolicy:
            def reset_hand(self):
                pass
            def choose(self, observation):
                return Action("check_call")
        session = Session((CallingPolicy(), CallingPolicy()), max_actions=1)
        with self.assertRaisesRegex(RuntimeError, "sample invalid"):
            session.play_hand()
        self.assertEqual(session.hands_played, 0)
        self.assertEqual(session.cumulative_payoffs, (0, 0))

    def test_independent_rank_oracle_known_categories(self):
        fixtures = ("AsKsQsJsTs", "AsAhAdAc2s", "KsKhKd2c2s", "AsJs8s4s2s",
                    "As2c3d4h5s", "QsQdQh9s2c", "AsAdKsKd2c", "JsJd9c5c2h", "AsJd9c5c2h")
        for category, s in zip(range(8, -1, -1), fixtures):
            self.assertEqual(rank_five([s[i:i + 2] for i in range(0, 10, 2)])[0], category)

    def test_cli_stdout_and_stderr_are_seat_filtered(self):
        from poker_arena.cli import main
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["poker-arena", "--deck-seed", "12", "--seat", "0"]), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            main()
        lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(lines[-1]["hands"], 1)
        for view in lines[:-1]:
            self.assertEqual(view["seat"], 0)
            self.assertNotIn("deck", view)
            self.assertNotIn("decisions", view)
            self.assertNotIn("seed", view)
            self.assertEqual(len(view["hole_cards"]), 2)
        self.assertEqual(stderr.getvalue(), "")

    def test_replay_uses_parseable_cards(self):
        hand = Hand()
        act(hand, "fold")
        record = hand.private_record()
        self.assertTrue(all(len(card) == 2 for card in record["deck"]))
        self.assertEqual(replay(record).private_record(), record)

    def test_free_fold_is_masked(self):
        hand = Hand()
        act(hand)
        view = hand.observe(1)
        self.assertEqual(view.to_call, 0)
        self.assertNotIn(Action("fold"), [x.action for x in view.legal_actions])
