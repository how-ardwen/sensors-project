"""
Rock-Paper-Scissors-Minus-One (RPS-1) — Monte Carlo Simulation
MSE 3302B | Western University

Simulates 10 000 rounds of our Nash-equilibrium strategy against several
opponent models:

  1. Nash            — identical strategy (baseline, should be ≈ 0 EV)
  2. Fixed Stage 1   — opponent always plays the same Stage 1 pair
  3. Biased Stage 2  — opponent never mixes at Stage 2; always keeps their
                       "stronger" hand deterministically
  4. Biased pair     — opponent overweights one Stage 1 pair (e.g. always RP)

Key result:
  - Nash vs Nash    → EV ≈ 0  (fundamental game-theory guarantee)
  - Nash vs Non-Nash → EV > 0  (Nash exploits any deviation)

Run:
    python simulate.py
"""

import random
from collections import Counter

# ---------------------------------------------------------------------------
# Constants (mirrors rps.py)
# ---------------------------------------------------------------------------

SHAPES = ["R", "P", "S"]
SHAPE_NAMES = {"R": "Rock", "P": "Paper", "S": "Scissors"}

PAYOFF: dict[tuple[str, str], int] = {
    ("R", "R"):  0, ("R", "P"): -1, ("R", "S"):  1,
    ("P", "R"):  1, ("P", "P"):  0, ("P", "S"): -1,
    ("S", "R"): -1, ("S", "P"):  1, ("S", "S"):  0,
}

VALID_STAGE1_PLAYS: list[tuple[str, str]] = [("R", "P"), ("R", "S"), ("P", "S")]

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def outcome(my_hand: str, opp_hand: str) -> int:
    return PAYOFF[(my_hand, opp_hand)]


def stronger_hand(h1: str, h2: str) -> str:
    """Return whichever of h1/h2 beats the other (h1 on a tie)."""
    return h1 if outcome(h1, h2) >= 0 else h2


# ---------------------------------------------------------------------------
# Stage 1 strategies
# ---------------------------------------------------------------------------

def stage1_nash() -> tuple[str, str]:
    """Uniform mix over {RP, RS, PS} — Nash equilibrium."""
    return random.choice(VALID_STAGE1_PLAYS)


def stage1_fixed(pair: tuple[str, str]) -> tuple[str, str]:
    """Always play the same pair (maximally exploitable)."""
    return pair


def stage1_biased(favoured: tuple[str, str], weight: float = 0.6) -> tuple[str, str]:
    """Play favoured pair with probability `weight`, others with equal share."""
    if random.random() < weight:
        return favoured
    others = [p for p in VALID_STAGE1_PLAYS if p != favoured]
    return random.choice(others)


def stage1_fully_random() -> tuple[str, str]:
    """Pick two hands independently and uniformly from {R, P, S} — repeats allowed (e.g. RR)."""
    return random.choice(SHAPES), random.choice(SHAPES)


def stage1_random_different() -> tuple[str, str]:
    """Pick two *distinct* hands uniformly at random (no repeats)."""
    h1 = random.choice(SHAPES)
    h2 = random.choice([s for s in SHAPES if s != h1])
    return h1, h2


# ---------------------------------------------------------------------------
# Stage 2 strategies
# ---------------------------------------------------------------------------

def stage2_nash(my_left: str, my_right: str,
                opp_h1:  str, opp_h2:  str) -> str:
    """
    Nash-equilibrium Stage 2 decision (mirrors rps.py optimal_stage2).
    Returns the kept hand string.
    """
    my_set  = {my_left,  my_right}
    opp_set = {opp_h1, opp_h2}

    # Case 1: Opponent dominated (e.g. RR)
    if opp_h1 == opp_h2:
        opp_shape = opp_h1
        return my_left if outcome(my_left, opp_shape) >= outcome(my_right, opp_shape) else my_right

    # Case 2: Identical strategy sets
    if my_set == opp_set:
        return stronger_hand(my_left, my_right)

    # Case 3: One overlapping hand — keep overlap with p = 2/3 (Nash)
    overlap = my_set & opp_set
    if overlap:
        shared = next(iter(overlap))
        other  = my_right if my_left == shared else my_left
        return shared if random.random() < 2 / 3 else other

    # Fallback
    return stronger_hand(my_left, my_right)


def stage2_always_stronger(my_left: str, my_right: str,
                            _opp_h1: str, _opp_h2: str) -> str:
    """
    Biased Stage 2: always keep the hand that beats the other, ignoring
    the opponent entirely.  Deviates from Nash in Case 3.
    """
    return stronger_hand(my_left, my_right)


def stage2_always_overlap(my_left: str, my_right: str,
                           opp_h1: str, opp_h2: str) -> str:
    """
    Biased Stage 2: always keep the overlapping hand (p=1 instead of 2/3).
    Deviates from Nash — opponent can exploit by always keeping non-overlap.
    """
    my_set  = {my_left, my_right}
    opp_set = {opp_h1, opp_h2}
    overlap = my_set & opp_set
    if overlap:
        return next(iter(overlap))
    return stronger_hand(my_left, my_right)


def stage2_random(my_left: str, my_right: str,
                  _opp_h1: str, _opp_h2: str) -> str:
    """Withdraw randomly — keep either hand with equal probability."""
    return random.choice([my_left, my_right])


# ---------------------------------------------------------------------------
# Single round simulation
# ---------------------------------------------------------------------------

def play_round(
    us_stage1_fn,
    us_stage2_fn,
    opp_stage1_fn,
    opp_stage2_fn,
) -> int:
    """
    Simulate one RPS-1 round given stage-1 and stage-2 strategy callables
    for each player.

    Returns 1 (win), 0 (tie), or -1 (loss) from our perspective.
    """
    us_left,  us_right  = us_stage1_fn()
    opp_left, opp_right = opp_stage1_fn()

    us_keep  = us_stage2_fn(us_left,   us_right,  opp_left, opp_right)
    opp_keep = opp_stage2_fn(opp_left, opp_right, us_left,  us_right)

    return outcome(us_keep, opp_keep)


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def run_simulation(
    label: str,
    us_stage1_fn,
    us_stage2_fn,
    opp_stage1_fn,
    opp_stage2_fn,
    n_trials: int = 10_000,
) -> None:
    counts: Counter[int] = Counter()
    for _ in range(n_trials):
        counts[play_round(us_stage1_fn, us_stage2_fn,
                          opp_stage1_fn, opp_stage2_fn)] += 1

    wins   = counts[ 1]
    ties   = counts[ 0]
    losses = counts[-1]
    total  = wins + ties + losses

    win_rate  = wins   / total * 100
    tie_rate  = ties   / total * 100
    loss_rate = losses / total * 100
    ev        = (wins - losses) / total

    print(f"  {label}")
    print(f"    W {wins:>5,} ({win_rate:5.1f}%)  "
          f"T {ties:>5,} ({tie_rate:5.1f}%)  "
          f"L {losses:>5,} ({loss_rate:5.1f}%)  "
          f"EV = {ev:+.4f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(n_trials: int = 10_000, seed: int | None = 42) -> None:
    if seed is not None:
        random.seed(seed)

    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  RPS-1 Monte Carlo Simulation  ({n_trials:,} trials each)")
    print(f"  US: Nash strategy vs various opponent models")
    print(sep)
    print(f"  {'Scenario':<48}  {'Result'}")
    print(f"  {'-'*48}  {'-'*22}")

    # ── 1. Baseline: Nash vs Nash ──────────────────────────────────────────
    run_simulation(
        "Nash Stage 1+2  vs  Nash Stage 1+2  [baseline, EV must ≈ 0]",
        stage1_nash, stage2_nash,
        stage1_nash, stage2_nash,
        n_trials=n_trials,
    )

    print()

    # ── 2. Nash vs fixed Stage 1 pairs ────────────────────────────────────
    for pair in VALID_STAGE1_PLAYS:
        run_simulation(
            f"Nash Stage 1+2  vs  Fixed Stage 1 = {pair[0]}{pair[1]}  (Nash Stage 2)",
            stage1_nash, stage2_nash,
            lambda p=pair: stage1_fixed(p), stage2_nash,
            n_trials=n_trials,
        )

    print()

    # ── 3. Nash vs biased Stage 1 (60% RP) ────────────────────────────────
    run_simulation(
        "Nash Stage 1+2  vs  Biased Stage 1 (60% RP) + Nash Stage 2",
        stage1_nash, stage2_nash,
        lambda: stage1_biased(("R", "P"), 0.60), stage2_nash,
        n_trials=n_trials,
    )

    print()

    # ── 4. Nash vs deterministic Stage 2 (always keep stronger) ──────────
    run_simulation(
        "Nash Stage 1+2  vs  Nash Stage 1  + Deterministic Stage 2",
        stage1_nash, stage2_nash,
        stage1_nash, stage2_always_stronger,
        n_trials=n_trials,
    )

    # ── 5. Nash vs always-overlap Stage 2 bias ────────────────────────────
    run_simulation(
        "Nash Stage 1+2  vs  Nash Stage 1  + Always-overlap Stage 2",
        stage1_nash, stage2_nash,
        stage1_nash, stage2_always_overlap,
        n_trials=n_trials,
    )

    print()

    # ── 6. Nash vs fully random (repeats allowed) + random withdraw ────────
    run_simulation(
        "Nash Stage 1+2  vs  Fully random Stage 1 (RR allowed) + Random Stage 2",
        stage1_nash, stage2_nash,
        stage1_fully_random, stage2_random,
        n_trials=n_trials,
    )

    # ── 7. Nash vs random distinct hands + random withdraw ─────────────────
    run_simulation(
        "Nash Stage 1+2  vs  Random distinct Stage 1          + Random Stage 2",
        stage1_nash, stage2_nash,
        stage1_random_different, stage2_random,
        n_trials=n_trials,
    )

    print()

    # ── 6. What happens if WE deviate from Nash Stage 2? ──────────────────
    print("  -- Effect of OUR deviations (opponent plays full Nash) --")
    run_simulation(
        "Deterministic Stage 2 (us)  vs  Nash Stage 1+2  (opp)",
        stage1_nash, stage2_always_stronger,
        stage1_nash, stage2_nash,
        n_trials=n_trials,
    )
    run_simulation(
        "Always-overlap Stage 2 (us) vs  Nash Stage 1+2  (opp)",
        stage1_nash, stage2_always_overlap,
        stage1_nash, stage2_nash,
        n_trials=n_trials,
    )

    print(sep)
    print()
    print("  KEY TAKEAWAY")
    print("  ─────────────────────────────────────────────────────────────")
    print("  ✓ Nash vs Nash  →  EV ≈ 0  (minimax theorem, unfalsifiable)")
    print("  ✓ Nash vs fixed/biased Stage 1  →  EV > 0  (Nash exploits)")
    print("  ✓ Nash vs deterministic Stage 2  →  small EV gain")
    print("  ✗ Deviating FROM Nash ourselves  →  EV ≈ 0 (opponent can exploit)")
    print("  ─────────────────────────────────────────────────────────────")
    print("  Against a computer playing true Nash, there is no exploiting")
    print("  strategy — any gain comes from opponent deviations, not ours.")
    print(f"{sep}\n")


if __name__ == "__main__":
    main(n_trials=10_000)
