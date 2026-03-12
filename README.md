## Communication Protocol

Packets are sent from the laptop to the ESP32 as 4-byte ASCII strings over WiFi (UDP/WebSocket) or Bluetooth, terminated by a newline.

**Format:** `P[L][R]\n`

| Field | Description |
|-------|-------------|
| `P` | Header byte (hand position command) |
| `L` | Left hand gesture |
| `R` | Right hand gesture |
| `\n` | Newline terminator |

**Gesture Encoding:**

| Value | Gesture |
|-------|---------|
| `0` | Withdrawn (hand lifted out of play area) |
| `1` | Rock |
| `2` | Paper |
| `3` | Scissors |

**Example Game Flow:**

| Packet | Meaning |
|--------|---------|
| `P22\n` | Both hands neutral (paper) — start of game |
| `P13\n` | Left: Rock, Right: Scissors |
| `P03\n` | Left hand withdrawn, Right: Scissors remains |

Other header bytes are reserved for future message types (e.g., `S\n` for start, `R\n` for reset).