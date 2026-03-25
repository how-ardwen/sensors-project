## Communication Protocol

Three ESP32 microcontrollers each connect independently to the laptop over BLE.

---

### MCU 1 — Left Arm  (`RPS-MCU1`)
### MCU 2 — Right Arm  (`RPS-MCU2`)

Packet format: **`H[sign]\n`** (3-byte ASCII + newline)

| Field | Description |
|-------|-------------|
| `H` | Header byte (hand gesture command) |
| `sign` | Gesture code (see table below) |
| `\n` | Newline terminator |

**Gesture Encoding:**

| Value | Gesture | Pinky+Ring | Index+Middle | Thumb |
|-------|---------|------------|--------------|-------|
| `0` | Neutral (rest) | open | open | open |
| `1` | Rock | closed | closed | closed |
| `2` | Paper | open | open | open |
| `3` | Scissors | closed | open | open |

> Neutral (0) is mechanically identical to Paper — all fingers open.

---

### MCU 3 — Swivel Controller  (`RPS-MCU3`)

Packet format: **`S[arm]\n`** (3-byte ASCII + newline)

| Field | Description |
|-------|-------------|
| `S` | Header byte (swivel command) |
| `arm` | Which arm to swivel out of the game window |
| `\n` | Newline terminator |

**Arm Encoding:**

| Value | Action |
|-------|--------|
| `0` | Both arms in frame |
| `1` | Swivel **left** arm (MCU 1) out of frame |
| `2` | Swivel **right** arm (MCU 2) out of frame |

---

### BLE Service (all three MCUs — Nordic UART Service)

| UUID | Role |
|------|------|
| `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | NUS Service |
| `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | RX Characteristic — laptop writes here |
| `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | TX Characteristic — reserved for future use |

---

### Example Game Flow

| Step | Packet | Target | Meaning |
|------|--------|--------|---------|
| Stage 1 | `H1\n` | MCU 1 | Left arm shows Rock |
| Stage 1 | `H3\n` | MCU 2 | Right arm shows Scissors |
| Stage 2 | `S1\n` | MCU 3 | Swivel left arm out of frame |

Other header bytes are reserved for future message types (e.g., `R\n` for reset).