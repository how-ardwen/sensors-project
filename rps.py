"""
Rock-Paper-Scissors-Minus-One (RPS-1) — Optimal Strategy Implementation
MSE 3302B | Western University

Game Flow:
  1. Stage 1 hands are selected automatically using the optimal mixed
     strategy: play RP, RS, or PS each with probability 1/3. Any
     non-uniform distribution over these three pairs is exploitable by
     an adaptive opponent, so equal weighting is the Nash equilibrium.
  2. Opponent's hands are detected via CV (placeholder: random)
  3. Optimal strategy determines which hand to remove (Stage 2)
  4. Opponent removes one hand (placeholder: random)
  5. Winner is determined by standard RPS rules
  6. Scoreboard updated; player asked to play again
"""

import random

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHAPES = ["R", "P", "S"]
SHAPE_NAMES = {"R": "Rock", "P": "Paper", "S": "Scissors"}

# Payoff from Player 1's perspective: 1 = win, 0 = tie, -1 = loss
PAYOFF: dict[tuple[str, str], int] = {
    ("R", "R"):  0, ("R", "P"): -1, ("R", "S"):  1,
    ("P", "R"):  1, ("P", "P"):  0, ("P", "S"): -1,
    ("S", "R"): -1, ("S", "P"):  1, ("S", "S"):  0,
}

RESULT_LABEL = {1: "WIN 🎉", 0: "TIE 🤝", -1: "LOSS 😔"}

# The three non-dominated, non-symmetric Stage 1 strategies.
# Playing each with equal probability (1/3) is the Nash equilibrium:
# any bias toward one pair is exploitable by an adaptive opponent.
VALID_STAGE1_PLAYS: list[tuple[str, str]] = [("R", "P"), ("R", "S"), ("P", "S")]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def outcome(my_hand: str, opp_hand: str) -> int:
    """Return the payoff (1/0/-1) for my_hand vs opp_hand."""
    return PAYOFF[(my_hand, opp_hand)]


def hand_label(h: str) -> str:
    return f"{h} ({SHAPE_NAMES[h]})"


def fmt_hands(h1: str, h2: str) -> str:
    return f"{hand_label(h1)}  |  {hand_label(h2)}"


# ---------------------------------------------------------------------------
# CV Placeholders
# ---------------------------------------------------------------------------

def detect_opponent_stage1() -> tuple[str, str]:
    """
    [CV PLACEHOLDER — Stage 1]
    Detects the two hand gestures shown by the opponent.
    Replace this function with a real computer-vision call when available.

    Returns:
        (hand1, hand2): two shape strings from {'R', 'P', 'S'}
    """
    h1 = random.choice(SHAPES)
    h2 = random.choice(SHAPES)
    return h1, h2


def detect_opponent_stage2(opp_h1: str, opp_h2: str) -> tuple[str, str]:
    """
    [CV PLACEHOLDER — Stage 2]
    Detects which hand the opponent withdrew from the play area.
    Replace this function with a real computer-vision call when available.

    Args:
        opp_h1, opp_h2: the opponent's original two hands

    Returns:
        (kept, removed): the hand that stayed and the one that was withdrawn
    """
    idx_removed = random.randint(0, 1)
    hands = [opp_h1, opp_h2]
    removed = hands[idx_removed]
    kept = hands[1 - idx_removed]
    return kept, removed


# ---------------------------------------------------------------------------
# Core Strategy
# ---------------------------------------------------------------------------

def stronger_hand(h1: str, h2: str) -> str:
    """Return whichever of h1/h2 beats the other (or h1 on a tie)."""
    result = outcome(h1, h2)
    if result >= 0:
        return h1   # h1 wins or ties → keep h1
    return h2       # h1 loses → keep h2


def optimal_strategy(
    my_h1: str, my_h2: str,
    opp_h1: str, opp_h2: str,
) -> tuple[str, str, str]:
    """
    Determine which of our hands to keep using the Nash-equilibrium-derived
    RPS-1 optimal strategy.

    Strategy rules (in priority order):
      1. Opponent plays a dominated strategy (both hands identical)
         → Keep whichever of our hands doesn't lose to theirs.
      2. We play the same pair of shapes as the opponent
         → Keep the stronger hand (the one that beats the other).
      3. We play a different pair — one hand always overlaps
         → Keep the overlapping hand with p = 2/3 (Nash equilibrium).

    Args:
        my_h1, my_h2   : our two hands
        opp_h1, opp_h2 : opponent's two hands (from CV detection)

    Returns:
        (keep, remove, reasoning_string)
    """
    my_set  = {my_h1,  my_h2}
    opp_set = {opp_h1, opp_h2}

    # ------------------------------------------------------------------
    # Case 1: Opponent plays a dominated strategy (e.g. RR, PP, SS)
    # ------------------------------------------------------------------
    if opp_h1 == opp_h2:
        opp_shape = opp_h1
        # Prefer a hand that wins; settle for a tie; avoid loss
        best, best_score = my_h1, outcome(my_h1, opp_shape)
        if outcome(my_h2, opp_shape) > best_score:
            best = my_h2
        keep   = best
        remove = my_h2 if keep == my_h1 else my_h1
        reason = (
            f"Opponent plays dominated strategy "
            f"({opp_shape}{opp_shape}). {hand_label(keep)} "
            f"guarantees no loss (outcome: "
            f"{RESULT_LABEL.get(outcome(keep, opp_shape), '?')})."
        )
        return keep, remove, reason

    # ------------------------------------------------------------------
    # Case 2: Same strategy as the opponent
    # ------------------------------------------------------------------
    if my_set == opp_set:
        keep   = stronger_hand(my_h1, my_h2)
        remove = my_h2 if keep == my_h1 else my_h1
        reason = (
            f"Identical strategy ({my_h1}{my_h2}) — keep the "
            f"stronger hand: {hand_label(keep)}."
        )
        return keep, remove, reason

    # ------------------------------------------------------------------
    # Case 3: Different strategy — exactly one hand overlaps
    # (Always the case for any two distinct non-dominated strategies)
    # ------------------------------------------------------------------
    overlap = my_set & opp_set          # the shared shape
    if overlap:
        shared = next(iter(overlap))
        other  = my_h2 if my_h1 == shared else my_h1

        # Nash equilibrium: keep overlapping hand with p = 2/3
        if random.random() < 2 / 3:
            keep, remove = shared, other
            prob_label = "2/3"
        else:
            keep, remove = other, shared
            prob_label = "1/3"

        reason = (
            f"Different strategies — overlapping hand is {hand_label(shared)}. "
            f"Keeping {hand_label(keep)} (selected with p = {prob_label} "
            f"per Nash equilibrium)."
        )
        return keep, remove, reason

    # ------------------------------------------------------------------
    # Fallback (should not be reached with valid non-dominated strategies)
    # ------------------------------------------------------------------
    keep   = stronger_hand(my_h1, my_h2)
    remove = my_h2 if keep == my_h1 else my_h1
    return keep, remove, f"Fallback: keeping stronger hand {hand_label(keep)}."


# ---------------------------------------------------------------------------
# Stage 1 — Optimal hand selection
# ---------------------------------------------------------------------------

def select_stage1_hands() -> tuple[str, str]:
    """
    Automatically select our two Stage 1 hands using the optimal mixed
    strategy: choose uniformly at random from {RP, RS, PS}.

    Why these three and not others?
      - Dominated pairs (RR, PP, SS) are never optimal; the opponent's
        single shape beats or ties both our hands with certainty.
      - The three pairs {RP, RS, PS} are the only non-dominated options,
        and they are symmetric in strategic value.

    Why uniform (1/3 each)?
      - With no prior information about the opponent, any non-uniform
        distribution is exploitable. The Nash equilibrium for Stage 1
        is therefore the uniform mixture over these three pairs.

    Returns:
        (hand1, hand2) drawn uniformly from VALID_STAGE1_PLAYS
    """
    return random.choice(VALID_STAGE1_PLAYS)


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

def play_round() -> int:
    """
    Play one full round of RPS-1.
    Returns the round outcome: 1 (win), 0 (tie), -1 (loss).
    """
    separator = "─" * 52

    print(f"\n{separator}")

    # ── Stage 1 ──────────────────────────────────────────
    print("\n  ── Stage 1: Selecting hands (optimal mixed strategy) ──")
    my_h1, my_h2 = select_stage1_hands()
    print(f"\n  [YOU]      {fmt_hands(my_h1, my_h2)}"
          f"  ← drawn uniformly from {{RP, RS, PS}}")

    opp_h1, opp_h2 = detect_opponent_stage1()
    print(f"  [OPPONENT] {fmt_hands(opp_h1, opp_h2)}  ← detected by CV")

    # ── Strategy: decide which hand to remove ────────────
    print(f"\n{separator}")
    print("  ── Stage 2: Optimal strategy decision ──\n")

    keep, remove, reasoning = optimal_strategy(my_h1, my_h2, opp_h1, opp_h2)

    print(f"  Strategy : {reasoning}")
    print(f"  Removing : {hand_label(remove)}")
    print(f"  Keeping  : {hand_label(keep)}")

    # ── Opponent withdraws a hand ─────────────────────────
    opp_keep, opp_removed = detect_opponent_stage2(opp_h1, opp_h2)
    print(f"\n  [OPPONENT] Removes {hand_label(opp_removed)}, "
          f"keeps {hand_label(opp_keep)}  ← detected by CV")

    # ── Determine winner ──────────────────────────────────
    result = outcome(keep, opp_keep)

    print(f"\n{separator}")
    print(f"  FINAL:  You → {hand_label(keep)}  |  "
          f"Opponent → {hand_label(opp_keep)}")
    print(f"  RESULT: {RESULT_LABEL[result]}")
    print(f"{separator}")

    return result


def main() -> None:
    print("\n" + "=" * 52)
    print("   ROCK-PAPER-SCISSORS-MINUS-ONE  (RPS-1)")
    print("   Optimal Strategy Player — MSE 3302B")
    print("=" * 52)

    wins = losses = ties = total = win_rate = 0

    while True:
        result = play_round()

        if result == 1:
            wins += 1
        elif result == -1:
            losses += 1
        else:
            ties += 1

        total = wins + losses + ties
        win_rate = (wins / total * 100) if total else 0.0
        print(f"\n  SCOREBOARD  W {wins}  |  T {ties}  |  L {losses}"
              f"   ({win_rate:.0f}% win rate)")

        again = input("\n  Play again? [Y/N]: ").strip().upper()
        if again != "Y":
            print("\n  Thanks for playing! Final score: "
                  f"W {wins} | T {ties} | L {losses}\n")
            break


if __name__ == "__main__":
    main()