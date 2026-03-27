"""
Rock-Paper-Scissors-Minus-One (RPS-1) — Hardware-Integrated Implementation
MSE 3302B | Western University

System Architecture:
  MCU 1 (RPS-ESP32-L) — Left arm:    3 finger servos + stepper for withdrawal
  MCU 2 (RPS-ESP32-R) — Right arm:   3 finger servos + stepper for withdrawal

  Each arm MCU handles its own withdrawal via stepper motor.
  The laptop sends W1 to withdraw an arm and W0 to return it.

Game Flow:
  1. Algorithm selects two Stage 1 hands (Nash equilibrium mixed strategy).
  2. Commands sent to MCU 1 and MCU 2 simultaneously via BLE → motors display signs.
  3. CV detects opponent's two hands  [PLACEHOLDER].
  4. Algorithm decides which hand to withdraw (optimal Stage 2 strategy).
  5. CV detects opponent's remaining hand  [PLACEHOLDER].
  6. Winner is determined and scoreboard updated.

Communication Protocol  (see README.md):
  Gesture:   P[L][R]   L/R: 0=Withdrawn  1=Rock  2=Paper  3=Scissors
  Withdraw:  W[D]       D:   1=withdraw this arm    0=return this arm
"""

import asyncio
import random

from bleak import BleakClient, BleakScanner

# ---------------------------------------------------------------------------
# BLE Device Configuration
# ---------------------------------------------------------------------------

# Device names must match DEVICE_NAME in each .ino file
BLE_DEVICES = {
    "arm_left":  "RPS-ESP32-L",   # Left arm  — ESP32_RPS_L/ESP32_RPS_L.ino
    "arm_right": "RPS-ESP32-R",   # Right arm — ESP32_RPS_R/ESP32_RPS_R.ino
}

# Both MCUs share the same Nordic UART Service characteristic UUID
NUS_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"   # Laptop → ESP32

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHAPES = ["R", "P", "S"]
SHAPE_NAMES = {"R": "Rock", "P": "Paper", "S": "Scissors"}

# BLE gesture codes used in P[L][R] packets
GESTURE_CODE = {"R": "1", "P": "2", "S": "3", "N": "0"}   # N = Withdrawn

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
# BLE Packet Builders
# ---------------------------------------------------------------------------

def build_gesture_packet(left: str, right: str) -> bytes:
    """
    Build a P[L][R] gesture packet for an arm MCU.

    Args:
        left  : shape string for left  hand — 'R', 'P', 'S', or 'N' (withdrawn)
        right : shape string for right hand — 'R', 'P', 'S', or 'N' (withdrawn)

    Returns:
        bytes, e.g. b'P13' for Left=Rock, Right=Scissors
    """
    return f"P{GESTURE_CODE[left]}{GESTURE_CODE[right]}".encode("ascii")


def build_withdraw_packet(withdraw: bool) -> bytes:
    """
    Build a W[D] withdraw packet for an arm MCU.

    Args:
        withdraw : True  → W1 (withdraw arm from play area)
                   False → W0 (return arm to play area)

    Returns:
        bytes, e.g. b'W1'
    """
    return b"W1" if withdraw else b"W0"


# ---------------------------------------------------------------------------
# BLE Communication
# ---------------------------------------------------------------------------

async def ble_send(client: BleakClient, packet: bytes, label: str = "") -> None:
    """Write a packet to an MCU's UART RX characteristic."""
    await client.write_gatt_char(NUS_RX_CHAR_UUID, packet, response=False)
    tag = f" [{label}]" if label else ""
    print(f"  [BLE{tag} →] {packet!r}")


async def ble_connect_one(name: str) -> BleakClient:
    """Scan for and connect to a single ESP32 by its advertised name."""
    print(f"  Scanning for '{name}'…")
    device = await BleakScanner.find_device_by_name(name, timeout=10.0)
    if device is None:
        raise RuntimeError(
            f"Device '{name}' not found. Is it powered on and advertising?"
        )
    client = BleakClient(device)
    await client.connect()
    print(f"  Connected → {device.name} ({device.address})")
    return client


async def ble_connect_all() -> dict[str, BleakClient]:
    """Connect to both arm MCUs concurrently. Returns {role: client}."""
    print("\n  Connecting to arm MCUs…")
    clients_list = await asyncio.gather(
        *(ble_connect_one(name) for name in BLE_DEVICES.values())
    )
    return dict(zip(BLE_DEVICES.keys(), clients_list))


async def ble_disconnect_all(clients: dict[str, BleakClient]) -> None:
    """Disconnect from all MCUs."""
    await asyncio.gather(*(c.disconnect() for c in clients.values()))
    print("  All BLE connections closed.")


# ---------------------------------------------------------------------------
# CV Placeholders
# ---------------------------------------------------------------------------

def cv_detect_stage1() -> tuple[str, str]:
    input("Press Enter when ready to show Stage 1 hands")
    h1 = input("Enter your left hand: ")
    h2 = input("Enter your right hand: ")
    return h1, h2


def cv_detect_stage2(opp_h1: str, opp_h2: str) -> str:
    return input("Enter the hand opponent kept: ")


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
    uniform random choice from {RP, RS, PS}.
    Returns (left_hand, right_hand).
    """
    return random.choice(VALID_STAGE1_PLAYS)


def stronger_hand(h1: str, h2: str) -> str:
    """Return whichever of h1/h2 beats the other (h1 on a tie)."""
    return h1 if outcome(h1, h2) >= 0 else h2


def optimal_stage2(
    my_left: str, my_right: str,
    opp_h1: str,  opp_h2: str,
) -> tuple[str, str, str]:
    """
    Decide which hand to keep (Stage 2) using Nash-equilibrium rules.

    Returns:
        (keep, withdraw, reasoning_string)
        keep/withdraw are shape strings; caller uses position (left/right)
        to determine swivel direction.
    """
    my_set  = {my_left,  my_right}
    opp_set = {opp_h1, opp_h2}

    # Case 1: Opponent dominated (RR / PP / SS)
    if opp_h1 == opp_h2:
        opp_shape = opp_h1
        best = my_left if outcome(my_left, opp_shape) >= outcome(my_right, opp_shape) else my_right
        withdraw = my_right if best == my_left else my_left
        reason = (
            f"Opponent dominated ({opp_shape}{opp_shape}) → "
            f"keep {hand_label(best)} "
            f"[{RESULT_LABEL.get(outcome(best, opp_shape), '?')}]."
        )
        return best, withdraw, reason

    # Case 2: Identical strategies
    if my_set == opp_set:
        keep     = stronger_hand(my_left, my_right)
        withdraw = my_right if keep == my_left else my_left
        reason   = (
            f"Identical strategies ({my_left}{my_right}) → "
            f"keep stronger hand {hand_label(keep)}."
        )
        return keep, withdraw, reason

    # Case 3: One overlapping hand (Nash equilibrium: keep overlap with p=2/3)
    overlap = my_set & opp_set
    if overlap:
        shared = next(iter(overlap))
        other  = my_right if my_left == shared else my_left
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
    keep     = stronger_hand(my_left, my_right)
    withdraw = my_right if keep == my_left else my_left
    return keep, withdraw, f"Fallback: keeping stronger hand {hand_label(keep)}."


# ---------------------------------------------------------------------------
# Game Round  (async — drives the full hardware pipeline)
# ---------------------------------------------------------------------------

async def play_round(clients: dict[str, BleakClient]) -> int:
    """
    Execute one complete round of RPS-1 over the 3-MCU hardware pipeline.

    Steps:
      1. Select Stage 1 hands  →  send H[sign]\\n to MCU 1 and MCU 2
      2. CV detects opponent's Stage 1 hands  [PLACEHOLDER]
      3. Decide which hand to withdraw  →  send S[arm]\\n to MCU 3
      4. CV detects opponent's kept hand  [PLACEHOLDER]
      5. Determine and return outcome (1=win, 0=tie, -1=loss)
    """
    sep = "─" * 52
    print(f"\n{sep}")

    # ── Step 1: Stage 1 — command both arm MCUs simultaneously ───────────────
    print("\n  ── Stage 1: Hand Selection ──")
    my_left, my_right = select_stage1_hands()
    print(f"  [US]  Left: {hand_label(my_left)}   Right: {hand_label(my_right)}"
          f"  ← Nash equilibrium draw")

    # P[L][R] packet is the same for both MCUs since each MCU knows its role
    gesture_pkt = build_gesture_packet(my_left, my_right)
    await asyncio.gather(
        ble_send(clients["arm_left"],  gesture_pkt, "MCU1-Left"),
        ble_send(clients["arm_right"], gesture_pkt, "MCU2-Right"),
    )
    print("  Arms displaying Stage 1 signs…")

    # Allow motors to reach position before CV fires
    await asyncio.sleep(1.5)

    # ── Step 2: CV — detect opponent's Stage 1 hands ──────────────────────────
    opp_h1, opp_h2 = cv_detect_stage1()
    print(f"  [OPP] {fmt_hands(opp_h1, opp_h2)}  ← detected by CV")

    # ── Step 3: Stage 2 — decide which arm to withdraw ────────────────────────
    print(f"\n{sep}")
    print("  ── Stage 2: Drop Decision ──\n")

    keep, withdraw, reasoning = optimal_stage2(my_left, my_right, opp_h1, opp_h2)
    print(f"  Strategy : {reasoning}")
    print(f"  Withdraw : {hand_label(withdraw)}")
    print(f"  Keep     : {hand_label(keep)}")

    # Send W1 to whichever MCU owns the withdrawing arm
    withdrawing_role = "arm_left" if withdraw == my_left else "arm_right"
    keeping_role     = "arm_right" if withdrawing_role == "arm_left" else "arm_left"
    label = "MCU1-Left" if withdrawing_role == "arm_left" else "MCU2-Right"

    await ble_send(clients[withdrawing_role], build_withdraw_packet(True), label)
    print(f"  Stepper withdrawing {'left' if withdrawing_role == 'arm_left' else 'right'} arm…")

    await asyncio.sleep(1.5)

    # ── Step 4: CV — detect opponent's remaining hand ──────────────────────────
    opp_keep = cv_detect_stage2(opp_h1, opp_h2)

    # ── Step 5: Determine winner ───────────────────────────────────────────────
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

    clients = await ble_connect_all()

    wins = losses = ties = 0

    try:
        while True:
            result = await play_round(clients)

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
        await ble_disconnect_all(clients)


if __name__ == "__main__":
    asyncio.run(main())