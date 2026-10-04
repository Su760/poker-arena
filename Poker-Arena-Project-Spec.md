# Poker Arena Project Specification

Build a poker training arena where you can create opponents, train agents, inspect their decisions, and play against them. The arena also helps its human player practice poker fundamentals, review decisions, and track recurring mistakes. The long-term deliverable is an autonomous poker bot with a clean interface for environments that explicitly permit automated play.

This specification defines proposed implementation choices and acceptance gates. It does not claim that a model has been trained or that an agent has a profitable edge. Version 1.1, October 2, 2026. This revision adds the human-practice track and its delivery sequence; implementation has not yet been verified.

## Product goal

The core experience is straightforward: choose an opponent style, run a match, inspect the hands, train a candidate, and compare it with earlier versions on opponents it has not trained against.

The project should answer three questions: Does the bot make legal decisions using only information available to its seat? Does it improve against a diverse set of opponents? Does its behavior hold up when the opponent changes?

For the human player, the goal is a useful practice loop: play a short session, bookmark uncertain decisions, review the reasoning, and retry related situations. Measure learning separately from the bot's performance and from the player's short-term winnings.

## Scope and release sequence

| Release               | Deliverable                                                                                                  | Completion condition                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| Arena MVP             | Heads-up no-limit Texas Hold’em with scripted opponents, a playable table, hand replay, and batch evaluation | Games are correct and reproducible; a human can complete a session against every opponent preset |
| Learning lab          | Small Leduc Hold’em environment with a random baseline and CFR agent                                         | Training, checkpoints, and independent evaluation work in a tractable poker game                 |
| Learned Hold’em agent | Discrete-action Hold’em policy trained against a frozen opponent mixture                                     | Produces a reproducible benchmark report with held-out opponents and uncertainty                 |
| Autonomous bot        | Exportable policy and adapter for the local arena or a specifically approved bot venue                       | Runs unattended through the same observation and legal-action contract                           |

The Hold’em arena is the main product. Leduc is a separate learning benchmark; its results and checkpoints must never be presented as Hold’em performance. Six-player tables, tournaments, arbitrary bet sizing, and opponent adaptation across long sessions are later milestones.

## Initial game configuration

Use two players, 100 big blinds per player, blinds of 0.5 and 1 big blind, no ante, one board, and no rake. Represent chips as integers with two units per big blind. Alternate the button. Reset stacks each hand while keeping cumulative results separately; this makes the first benchmark a sequence of independent fixed-stack hands.

Later, add sessions where stacks carry over, with explicit buy-in and rebuy rules. Keep those results separate from fixed-stack results. Introduce a configurable, clearly labeled rake model before making any claims about performance after fees.

Use PokerKit behind an adapter for dealing, betting legality, hand resolution, and payouts. PokerKit is a Python poker simulation library with no-limit Hold’em examples; its documentation is the implementation reference, not a substitute for testing the adapter. [S1]

## Opponent factory

Styles are parameterized policies, not random-action percentages pasted onto labels. Every policy conditions on its own cards, public cards, position, pot odds, stack depth, street, and observed betting history.

| Preset           | Intended behavior                                               | Parameters that distinguish it                                       |
| ---------------- | --------------------------------------------------------------- | -------------------------------------------------------------------- |
| Nit              | Enters few marginal hands and folds readily to pressure         | Narrow entry range, high continuation threshold, low bluff frequency |
| Tight aggressive | Selective entry with assertive value betting and some bluffs    | Narrower entry range, higher raise frequency, disciplined calls      |
| Loose aggressive | Enters more hands and applies frequent pressure                 | Wider entry range, more continuation bets and reraises               |
| Calling station  | Enters widely, calls too often, rarely raises without strength  | Wide calling range, low fold tendency, low bluff aggression          |
| Maniac           | Applies excessive pressure with weak as well as strong hands    | Very wide entry, frequent reraises, large bet-size preference        |
| Fit or fold      | Continues strongly connected hands and gives up often otherwise | High dependence on board connection, high fold-to-pressure tendency  |
| Mixed reference  | Uses a configurable mix of sensible heuristic behaviors         | Moderate ranges, pot-odds sensitivity, varied sizing                 |

Also provide a uniformly random legal-action agent as a debugging baseline. Do not call the mixed reference balanced in the game-theoretic sense or label any heuristic GTO.

Expose sliders for entry looseness, aggression, bluff tendency, calling tolerance, bet-size preference, and decision randomness. Freeze each generated opponent to a config and seed. Add tilt and within-session style changes only after stationary opponents work.

Validate the presets with measured behavior: voluntary preflop participation, preflop raises, aggression by street, fold-to-bet rates, and bet sizes. Show denominators and sample counts. These are diagnostics for synthetic agents, not universal human-player thresholds. Distinguish successful bluffs from simply winning a hand; any bluff annotation based on hidden cards belongs in post-hand analysis only.

## Observation and action contract

The policy receives its own hole cards, revealed board cards, public stacks and contributions, position, street, pot, amount to call, observed action history, and a legal-action mask. Future opponent models may add statistics computed from prior observed hands, with sample counts and uncertainty.

The policy never receives opponent hole cards, the future board, deck order, deal seeds, full engine state, opponent preset name, or opponent policy parameters. The same boundary applies to scripted opponents. Spectator replay may reveal all cards after a hand; live human play may not.

Expose a versioned policy interface: observation and legal actions go in; a legal action, optional action probabilities, and timing diagnostics come out. Reset per-hand memory explicitly. Full truth stays in the engine and evaluator, outside the policy payload and client-visible API.

Start with fold, check or call, minimum legal raise, half-pot raise, pot-sized raise, and all-in. The adapter translates each abstract choice into an exact engine action. A raise-to amount means the player's total contribution on the current street, not extra chips added. Calculate pot-based raises after calling, round to chip units, enforce minimum-raise and stack rules, and deduplicate choices that resolve to the same amount. An all-in below a full raise must preserve the engine's reopening rules.

Mask unavailable choices. Reject stale or illegal API actions without mutating the game. An autonomous agent timeout defaults to check when legal, otherwise fold; count every fallback separately so benchmark scores cannot conceal policy failures.

## Application screens

| Screen      | User can do                                       | Information shown                                                         |
| ----------- | ------------------------------------------------- | ------------------------------------------------------------------------- |
| Arena       | Play a session against a preset or checkpoint     | Cards visible to the player, pot, stacks, legal actions, action log       |
| Opponents   | Create, edit, and preview an opponent             | Parameters and measured behavior over sample hands                        |
| Training    | Start a bounded job, stop it, inspect checkpoints | Steps, runtime, training configuration, validation results                |
| Tournaments | Compare a chosen set of policies                  | Matchup matrix, big blinds per 100 hands, confidence intervals            |
| Replay      | Step through a completed hand                     | Actions, board progression, policy probabilities, optional revealed cards |
| Models      | Compare or promote checkpoints                    | Game variant, training population, data split, metrics, known weaknesses  |

A running job must show whether it is queued, running, completed, failed, or cancelled. Stopping a job should preserve its latest valid checkpoint. Charts must distinguish training rewards from independent evaluation results.

## Human practice and coaching

Ship useful human practice with P2, before neural training. The first practice release needs a playable table, bookmarked hands, replay from the player's perspective, and a small post-hand review. It does not need a solver, an LLM, or a complete lesson system.

| Feature                 | Intended experience                                                                                                                                                      | Delivery                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| Play mode               | Complete hands without action recommendations; optionally hide the opponent's preset label for practice against an unknown style                                         | P2                                               |
| Review mode             | Revisit a decision with future cards and unrevealed opponent cards hidden by default; record the player's reasoning before revealing the result                          | P2                                               |
| Basic decision feedback | Explain position, amount to call, pot odds, effective stack, and available actions; show an equity estimate only when its assumed opponent range and method are explicit | P2                                               |
| Focused drills          | Practice pot-odds arithmetic, position, value betting, bluff selection, and responses to different opponent behaviors                                                    | P3, starting with objective arithmetic exercises |
| Progress view           | Track hands reviewed, arithmetic accuracy, and repeated decision patterns with sample counts; keep assisted and unassisted sessions separate                             | P3                                               |
| Branching replay        | Retry a saved decision under alternative actions and compare repeated simulated continuations                                                                            | Later, after evaluation is reliable              |

Keep observed facts, estimates, and advice distinct. A pot-odds calculation can be exact for the displayed state; an equity estimate depends on the assumed range; strategic advice depends on that range, future play, and the reference policy. Do not present raw equity as a complete call/fold rule when future betting remains. Do not call a heuristic action optimal, GTO, or a solver answer.

Evaluate the decision using only information available when it was made. The actual opponent cards and future runout may explain the completed hand, but cannot serve as inputs to its strategic grade. Show showdown truth in a separately labeled reveal view. Losing a hand is not itself evidence of a mistake. Early reviews should identify questions and explain tradeoffs rather than invent precise EV-loss scores.

Any later action-EV comparison must document the assumed opponent strategy, continuation policies, simulation budget, and uncertainty. Alternative actions change later play; comparing two actions against one fixed future action script is not a sound general EV estimate. Human benchmark sessions must be separate from drill scenarios and from the bot's frozen final-test deals.

Start with heads-up practice and clearly label the game format. Six-player and full-ring advice require their own validated configurations and strategy references; do not silently reuse heads-up opening ranges. If the user's main target is multi-player cash poker, prioritize a six-player practice milestone after the two-player core and evaluation pass.

Prepare for review in P0 by recording versioned decision events: acting seat, state version, seat-filtered observation, legal actions, chosen action, and resulting public events. Keep any private replay/deck data in a separate engine-only record. Human notes and review annotations must not alter the underlying hand history. An optional language-model explanation layer can come later, grounded in verified calculations and explicit assumptions.

## Training plan

Begin with tabular counterfactual regret minimization in Leduc, a small poker variant. RLCard documents Leduc and examples of CFR and other learning algorithms. Use it as an isolated learning-lab dependency, keeping its game rules and metrics separate from PokerKit Hold’em. [S2]

For Hold’em, first build an equity-and-pot-odds heuristic. Any equity estimate must sample unknown cards using only the player's information, never the actual hidden engine cards.

The first learned Hold’em candidate is a feedforward policy using card encodings, public numeric features, and a bounded history representation. A proposed starting algorithm is MaskablePPO through a Gymnasium wrapper. Treat this as an experiment in exploiting a defined opponent population; it is not an equilibrium solver. Use mask-aware evaluation utilities and pin dependency versions. [S3]

Each learner step advances its legal action and scripted opponent actions until the learner acts again or the hand ends. Terminal reward is net chips won or lost divided by the big blind; use an undiscounted episodic objective. Avoid rewards for aggression, bluffing, or winning an individual pot because they can conflict with net returns. A safety timeout invalidates the sample and is logged; it must not erase losses.

Train first against a frozen, documented mixture of presets. Later add snapshots of older policies and population-based self-play. Keep a portion of the fixed reference opponents so the population does not collapse into a narrow counterstrategy. Benchmark one short CPU run before allocating longer runs or paid compute; record hands per second, wall time, and memory.

## Evaluation and model promotion

Freeze separate training, validation, and final-test manifests. Separate deal seeds, opponent parameter sets, and policy checkpoints. Sample test opponents from held-out parameter combinations; include a separately authored heuristic and style-switching sessions when that feature exists.

Evaluate competing candidates on matched deals and both seat assignments. Keep each matched-deal group together in resampling. Report net big blinds per 100 hands, a 95 percent confidence interval, per-opponent results, worst-matchup performance, illegal-action count, fallback count, and decision latency. Use independent training seeds and distinguish uncertainty from deal randomness from variability across training runs.

Proposed starting budget: 20,000 matched-deal pairs per opponent for a frozen final evaluation, plus at least three independently trained candidates when assessing the learning method. These are resource defaults, not a guarantee of statistical precision. Choose any expanded sample size using validation variance before opening the final test; do not keep sampling until a favorable result appears.

Compare with random play, the strongest validation-selected heuristic, and the previous promoted checkpoint. Promote a learned checkpoint only when its paired aggregate improvement over the chosen reference has a confidence interval above zero, it passes all correctness gates, and it meets predeclared per-opponent regression limits. Set those limits before final evaluation. An inconclusive or negative result remains an honest experiment; the arena can ship with its stronger heuristic.

Exact exploitability is a small-game metric only when a verified best-response evaluator exists. Sampled tournament winnings in Hold’em do not establish equilibrium play or profitability against humans. A Leduc result cannot justify either claim.

## Architecture and persistence

Use Python 3.11 or later, PokerKit, NumPy, Gymnasium, PyTorch and sb3-contrib for the core and training. Use FastAPI for the service and Next.js with TypeScript for the interface. Start with SQLite for metadata and local compressed event logs and model files. Training runs in a separate process so the API stays responsive. Begin with CLI training; add a UI job launcher after checkpoint recovery works.

Keep modules separate: game adapter, seat observation builder, action translator, opponent policies, learner wrapper, evaluator, replay serializer, API, and UI. The game core must run without the web application. Use a synchronous action endpoint for turn-based play and SSE for training progress; multiplayer networking is unnecessary for the first release.

Persist opponent configs, hand events, policy versions, training jobs, tournament manifests, and metrics. Every experiment records its code commit, environment version, game configuration, observation and action versions, checkpoint hash, training seed, opponent population, and evaluation split. A saved checkpoint must include preprocessing metadata and reject incompatible environments.

Live endpoints return seat-filtered state. Completed replay endpoints must enforce the chosen reveal mode. Keep privileged truth logs local to the evaluator. Arbitrary uploaded executable agents and public multi-user hosting are outside the MVP.

## Correctness gates

- Validate heads-up blind and action order, folds, checks, calls, raises, short all-ins, uncalled-bet refunds, ties, board-playing hands, and split-pot rounding.
- Preserve chip totals through every transition; account for explicit rake only in a later fee-enabled configuration.
- Run at least 10,000 seeded random legal hands without duplicate cards, negative stacks, stuck states, or payout inconsistencies. This supplements targeted edge-case tests rather than replacing them.
- Replay a saved hand to the same actions and payouts. Verify a checkpoint round trip preserves outputs for fixed observations and RNG state.
- Hold visible information constant while changing hidden cards and opponent labels; the serialized observation must remain identical. Inspect live API payloads as well as training inputs.
- Apply a repeated action request only once, reject old state versions, and surface interrupted training as an explicit failure or cancellation.

## Milestones

| Milestone | Build                                                           | Exit gate                                                                                                                                                          |
| --------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| P0        | Repository, engine adapter, config schema, observation boundary | One reproducible complete hand and targeted betting tests                                                                                                          |
| P1        | Opponent factory and headless sessions                          | Every preset runs; measured behaviors differ in the intended directions                                                                                            |
| P2        | Arena UI, replay, and basic human practice                      | Human can play each preset, bookmark decisions, and review a completed session with future information hidden by default                                           |
| P3        | Evaluation harness, Leduc learning lab, and initial drills      | Frozen benchmark manifests, confidence intervals, a reproducible small-game learning result, and objective practice exercises with separate human progress metrics |
| P4        | Hold’em learning experiment                                     | Saved candidate plus honest held-out report, even if the baseline wins                                                                                             |
| P5        | Local autonomous bot and policy export                          | Unattended sessions use the same filtered interface and produce complete audit logs                                                                                |
| P6        | Advanced opponents and external adapter                         | Separate approval of venue, game compatibility, and operational limits before connection                                                                           |

## Autonomous bot end state

Package the policy behind a small adapter with decision deadlines, validated observations, a legal-action translator, deterministic logging, checkpoint selection, and an immediate stop control. A new environment requires compatibility tests for blinds, stack semantics, fees, betting rules, and action timing.

The first automated deployment is the local arena. Any external platform must explicitly allow bots. PokerStars, for example, prohibits automated play and real-time action advice. This project scope includes no poker-site scraping, client control, account connection, deposits, or wagering. [S4]

## First implementation task

Create a new Poker Arena repository and implement P0 only. Build a thin PokerKit adapter for two-player, fixed-stack no-limit Hold’em; define versioned public observations and exact legal actions; add the targeted betting and information-boundary tests; and provide a CLI demo that prints a seat-filtered hand. Document design choices and unresolved engine behavior. Stop with a runnable core and a clear P1 checklist. Do not start the web UI or neural training until this gate passes.

Record the decision events needed for later human review, but defer coaching scores and practice screens until P2. Keep the engine usable from both a human controller and an automated policy through the same observation/action boundary.

## Sources and design status

The architecture, opponent presets, budgets, and promotion rules above are proposed project decisions. Sources establish library capabilities and platform constraints, not expected agent performance. Checked October 2, 2026.

- [S1 PokerKit documentation](https://pokerkit.readthedocs.io/en/stable/)
- [S2 RLCard games](https://rlcard.org/games.html) and [learning algorithms](https://rlcard.org/algorithms.html)
- [S3 Gymnasium custom environments](https://gymnasium.farama.org/introduction/create_custom_env/) and [MaskablePPO documentation](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html)
- [S4 PokerStars prohibited tools policy](https://www.pokerstars.com/poker/room/prohibited/)
