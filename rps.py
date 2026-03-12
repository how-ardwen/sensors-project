"""
Rock-Paper-Scissors-Minus-One (RPS-1) — Hardware-Integrated Implementation
MSE 3302B | Western University

Game Flow:
  1. Algorithm selects two Stage 1 hands (Nash equilibrium mixed strategy).
  2. Laptop sends hand positions to ESP32 via BLE  →  motors display signs.
  3. CV detects opponent's two hands  [PLACEHOLDER].
  4. Algorithm decides which hand to drop (optimal Stage 2 strategy).
  5. Laptop sends updated positions (one hand withdrawn) to ESP32 via BLE.
  6. CV detects opponent's remaining hand  [PLACEHOLDER].
  7. Winner is determined by standard RPS rules and scoreboard is updated.

Communication Protocol  (README.md):
  Packet format:  P[L][R]\\n   (4-byte ASCII + newline)
    L / R  =  left / right hand gesture code
      0 → Withdrawn   1 → Rock   2 → Paper   3 → Scissors
  Example:  b"P13\\n"  →  Left: Rock, Right: Scissors
"""

import asyncio
import random

from bleak import BleakClient, BleakScanner

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Name advertised by the ESP32 (change to match your firmware)
ESP32_BLE_NAME = "RPS-ESP32"

# UUID of the UART TX characteristic on the ESP32 (Nordic UART Service)
UART_TX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHAPES = ["R", "P", "S"]
SHAPE_NAMES = {"R": "Rock", "P": "Paper", "S": "Scissors"}

# Gesture codes used in the BLE protocol
GESTURE_CODE = {"W": "0", "R": "1", "P": "2", "S": "3"}  # W = Withdrawn

# Payoff from our perspective: 1 = win, 0 = tie, -1 = loss
PAYOFF: dict[tuple[str, str], int] = {
    ("R", "R"):  0, ("R", "P"): -1, ("R", "S"):  1,
    ("P", "R"):  1, ("P", "P"):  0, ("P", "S"): -1,
    ("S", "R"): -1, ("S", "P"):  1, ("S", "S"):  0,
}

RESULT_LABEL = {1: "WIN 🎉", 0: "TIE 🤝", -1: "LOSS 😔"}

# Nash-equilibrium Stage 1 options: uniform mix over {RP, RS, PS}
VALID_STAGE1_PLAYS: list[tuple[str, str]] = [("R", "P"), ("R", "S"), ("P", "S")]


# ---------------------------------------------------------------------------
# BLE Communication
# ---------------------------------------------------------------------------

def build_packet(left: str, right: str) -> bytes:
    """
    Encode a hand-position command into the 4-byte BLE packet.

    Args:
        left  : gesture for the left  hand — one of 'R', 'P', 'S', 'W'
        right : gesture for the right hand — one of 'R', 'P', 'S', 'W'

    Returns:
        bytes, e.g. b'P13\\n' for Left=Rock, Right=Scissors
    """
    l_code = GESTURE_CODE[left]
    r_code = GESTURE_CODE[right]
    return f"P{l_code}{r_code}\n".encode("ascii")


async def ble_send(client: BleakClient, packet: bytes) -> None:
    """Write a packet to the ESP32's UART TX characteristic."""
    await client.write_gatt_char(UART_TX_CHAR_UUID, packet, response=False)
    print(f"  [BLE →] {packet!r}")


async def ble_connect() -> BleakClient:
    """Scan for and connect to the ESP32 by its advertised name."""
    print(f"  Scanning for '{ESP32_BLE_NAME}'…")
    device = await BleakScanner.find_device_by_name(ESP32_BLE_NAME, timeout=10.0)
    if device is None:
        raise RuntimeError(
            f"ESP32 '{ESP32_BLE_NAME}' not found. "
            "Is it powered on and advertising?"
        )
    client = BleakClient(device)
    await client.connect()
    print(f"  Connected to {device.name} ({device.address})")
    return client


# ---------------------------------------------------------------------------
# CV Placeholders
# ---------------------------------------------------------------------------

def cv_detect_stage1() -> tuple[str, str]:
    """
    [CV PLACEHOLDER — Stage 1]
    Capture a frame and return the two gestures the opponent is showing.
    Replace with a real computer-vision call when available.

    Returns:
        (left_hand, right_hand): shape strings from {'R', 'P', 'S'}
    """
    h1 = random.choice(SHAPES)
    h2 = random.choice(SHAPES)
    print(f"  [CV]  Opponent Stage 1 detected: {SHAPE_NAMES[h1]} | {SHAPE_NAMES[h2]}")
    return h1, h2


def cv_detect_stage2(opp_h1: str, opp_h2: str) -> str:
    """
    [CV PLACEHOLDER — Stage 2]
    Detect which single hand the opponent kept after withdrawing one.
    Replace with a real computer-vision call when available.

    Args:
        opp_h1, opp_h2: the opponent's original two hands

    Returns:
        kept_hand: the shape string the opponent kept
    """
    kept = random.choice([opp_h1, opp_h2])
    print(f"  [CV]  Opponent Stage 2 detected: kept {SHAPE_NAMES[kept]}")
    return kept


# ---------------------------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------------------------

def outcome(my_hand: str, opp_hand: str) -> int:
    """Return the payoff (1/0/-1) for my_hand vs opp_hand."""
    return PAYOFF[(my_hand, opp_hand)]


def hand_label(h: str) -> str:
    return f"{h} ({SHAPE_NAMES[h]})"


def fmt_hands(h1: str, h2: str) -> str:
    return f"{hand_label(h1)}  |  {hand_label(h2)}"


# ---------------------------------------------------------------------------
# Core Strategy
# ---------------------------------------------------------------------------

def select_stage1_hands() -> tuple[str, str]:
    """
    Select two Stage 1 hands using the Nash-equilibrium mixed strategy:
    choose uniformly at random from {RP, RS, PS}.

    - Dominated pairs (RR, PP, SS) are never optimal.
    - Any non-uniform bias over the three valid pairs is exploitable.
    Returns (left_hand, right_hand).
    """
    return random.choice(VALID_STAGE1_PLAYS)


def stronger_hand(h1: str, h2: str) -> str:
    """Return whichever of h1/h2 beats the other (h1 on a tie)."""
    return h1 if outcome(h1, h2) >= 0 else h2


def optimal_stage2(
    my_h1: str, my_h2: str,
    opp_h1: str, opp_h2: str,
) -> tuple[str, str, str]:
    """
    Decide which of our hands to keep (Stage 2) using Nash-equilibrium rules.

    Priority:
      1. Opponent shows a dominated pair (e.g. RR) → keep the hand that
         doesn't lose to their forced shape.
      2. Both players show the same pair → keep the stronger hand.
      3. One hand overlaps → keep the overlapping hand with p = 2/3
         (Nash equilibrium for this sub-game).

    Returns:
        (keep, withdraw, reasoning_string)
    """
    my_set  = {my_h1,  my_h2}
    opp_set = {opp_h1, opp_h2}

    # Case 1: Opponent dominated (RR / PP / SS)
    if opp_h1 == opp_h2:
        opp_shape  = opp_h1
        best       = my_h1 if outcome(my_h1, opp_shape) >= outcome(my_h2, opp_shape) else my_h2
        withdraw   = my_h2 if best == my_h1 else my_h1
        reason     = (
            f"Opponent dominated ({opp_shape}{opp_shape}) → "
            f"keep {hand_label(best)} "
            f"[{RESULT_LABEL.get(outcome(best, opp_shape), '?')}]."
        )
        return best, withdraw, reason

    # Case 2: Identical strategies
    if my_set == opp_set:
        keep     = stronger_hand(my_h1, my_h2)
        withdraw = my_h2 if keep == my_h1 else my_h1
        reason   = (
            f"Identical strategies ({my_h1}{my_h2}) → "
            f"keep stronger hand {hand_label(keep)}."
        )
        return keep, withdraw, reason

    # Case 3: One overlapping hand
    overlap = my_set & opp_set
    if overlap:
        shared   = next(iter(overlap))
        other    = my_h2 if my_h1 == shared else my_h1
        if random.random() < 2 / 3:
            keep, withdraw, prob = shared, other, "2/3"
        else:
            keep, withdraw, prob = other, shared, "1/3"
        reason = (
            f"One overlap ({hand_label(shared)}) → "
            f"keeping {hand_label(keep)} (p = {prob}, Nash equilibrium)."
        )
        return keep, withdraw, reason

    # Fallback
    keep     = stronger_hand(my_h1, my_h2)
    withdraw = my_h2 if keep == my_h1 else my_h1
    return keep, withdraw, f"Fallback: keeping stronger hand {hand_label(keep)}."


# ---------------------------------------------------------------------------
# Game Round  (async — drives the full hardware pipeline)
# ---------------------------------------------------------------------------

async def play_round(client: BleakClient) -> int:
    """
    Execute one complete round of RPS-1 over the hardware pipeline.

    Steps:
      1. Select Stage 1 hands  →  send to ESP32 via BLE
      2. CV detects opponent Stage 1 hands  [PLACEHOLDER]
      3. Decide which hand to withdraw  →  send updated positions to ESP32
      4. CV detects opponent's kept hand  [PLACEHOLDER]
      5. Determine and return outcome (1=win, 0=tie, -1=loss)
    """
    sep = "─" * 52
    print(f"\n{sep}")

    # ── Step 1: Stage 1 hand selection & BLE command ──────────────────────
    print("\n  ── Stage 1: Hand Selection ──")
    my_h1, my_h2 = select_stage1_hands()
    print(f"  [US]   {fmt_hands(my_h1, my_h2)}  ← Nash equilibrium draw")

    packet_s1 = build_packet(my_h1, my_h2)
    await ble_send(client, packet_s1)
    print("  Motors displaying Stage 1 hands…")

    # Brief pause — allow motors to move before CV fires
    await asyncio.sleep(1.5)

    # ── Step 2: CV — detect opponent's Stage 1 hands ──────────────────────
    opp_h1, opp_h2 = cv_detect_stage1()
    print(f"  [OPP]  {fmt_hands(opp_h1, opp_h2)}  ← detected by CV")

    # ── Step 3: Stage 2 strategy decision & BLE command ───────────────────
    print(f"\n{sep}")
    print("  ── Stage 2: Optimal Drop Decision ──\n")

    keep, withdraw, reasoning = optimal_stage2(my_h1, my_h2, opp_h1, opp_h2)
    print(f"  Strategy : {reasoning}")
    print(f"  Withdraw : {hand_label(withdraw)}")
    print(f"  Keep     : {hand_label(keep)}")

    # Build Stage 2 packet: withdrawn hand becomes '0'
    # Determine which physical hand (left/right) is being withdrawn
    if withdraw == my_h1:
        # my_h1 was the left hand
        packet_s2 = build_packet("W", my_h2)
    else:
        # my_h2 was the right hand
        packet_s2 = build_packet(my_h1, "W")

    await ble_send(client, packet_s2)
    print("  Motor lifting withdrawn hand…")

    await asyncio.sleep(1.5)

    # ── Step 4: CV — detect opponent's remaining hand ──────────────────────
    opp_keep = cv_detect_stage2(opp_h1, opp_h2)

    # ── Step 5: Determine winner ───────────────────────────────────────────
    result = outcome(keep, opp_keep)

    print(f"\n{sep}")
    print(f"  FINAL:  Us → {hand_label(keep)}  |  Opponent → {hand_label(opp_keep)}")
    print(f"  RESULT: {RESULT_LABEL[result]}")
    print(f"{sep}")

    return result


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

async def main() -> None:
    print("\n" + "=" * 52)
    print("   ROCK-PAPER-SCISSORS-MINUS-ONE  (RPS-1)")
    print("   Optimal Strategy Player — MSE 3302B")
    print("=" * 52)

    # Connect to ESP32 over BLE
    client = await ble_connect()

    wins = losses = ties = 0

    try:
        while True:
            result = await play_round(client)

            if result == 1:
                wins += 1
            elif result == -1:
                losses += 1
            else:
                ties += 1

            total    = wins + losses + ties
            win_rate = (wins / total * 100) if total else 0.0
            print(f"\n  SCOREBOARD  W {wins}  |  T {ties}  |  L {losses}"
                  f"   ({win_rate:.0f}% win rate)")

            again = input("\n  Play again? [Y/N]: ").strip().upper()
            if again != "Y":
                print(f"\n  Thanks for playing! Final: W {wins} | T {ties} | L {losses}\n")
                break
    finally:
        await client.disconnect()
        print("  BLE disconnected.")


if __name__ == "__main__":
    asyncio.run(main())