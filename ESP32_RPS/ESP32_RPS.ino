/**
 * ESP32_RPS.ino
 * Rock-Paper-Scissors-Minus-One (RPS-1) — ESP32 Firmware
 * MSE 3302B | Western University
 *
 * Receives hand-position commands from the laptop over BLE (Nordic UART
 * Service) and drives a WS2812B smart LED on GPIO 21 as a placeholder until
 * the mechanical design is finalised.
 *
 * ── Communication Protocol (see README.md) ──────────────────────────────────
 *   Packet:  P[L][R]\n   (4 ASCII bytes + newline)
 *     L / R  = gesture code for left / right hand
 *       '0' → Withdrawn   '1' → Rock   '2' → Paper   '3' → Scissors
 *   Example: "P13\n" → Left: Rock, Right: Scissors
 *
 * ── LED Colour Scheme ────────────────────────────────────────────────────────
 *   Each hand contributes 125 to the channel that matches its sign:
 *     Rock      → Red   += 125
 *     Paper     → Green += 125
 *     Scissors  → Blue  += 125
 *     Withdrawn →  no contribution
 *
 *   Examples:
 *     P11\n  (Rock  | Rock)      → R=250, G=0,   B=0
 *     P22\n  (Paper | Paper)     → R=0,   G=250, B=0
 *     P23\n  (Paper | Scissors)  → R=0,   G=125, B=125
 *     P13\n  (Rock  | Scissors)  → R=125, G=0,   B=125
 *     P03\n  (Withdrawn|Scissors)→ R=0,   G=0,   B=125
 *
 * ── play() Placeholder ───────────────────────────────────────────────────────
 *   void play(int hand, char sign)
 *     hand : 0 = left, 1 = right
 *     sign : '1'=Rock  '2'=Paper  '3'=Scissors  '0'=Withdrawn
 *   Replace the LED logic inside this function with servo / motor calls once
 *   GPIOs are assigned in the mechanical design.
 *
 * ── Dependencies ─────────────────────────────────────────────────────────────
 *   Install via Arduino Library Manager:
 *     • "Adafruit NeoPixel"   by Adafruit
 *     • ESP32 Arduino core    (Board Manager → esp32 by Espressif)
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Adafruit_NeoPixel.h>
#include <ESP32Servo.h>

// ── Pin / LED configuration ──────────────────────────────────────────────────
#define LED_PIN        21    // Data pin for the WS2812B smart LED
#define LED_COUNT       1    // Number of LEDs in the strip / ring
#define LED_BRIGHTNESS 255   // Global brightness cap (0–255)

// RIGHT HAND
#define PIN_R_FINGER_A  26    // Index + Middle
#define PIN_R_FINGER_B  25    // Ring + Pinky
#define PIN_R_THUMB     33

// LEFT HAND (for later)
#define PIN_L_FINGER_A  14
#define PIN_L_FINGER_B  13
#define PIN_L_THUMB     27

// - Servo Angle Constants - 
#define WRIST_RETRACTED   0
#define WRIST_PLAYING    90

#define FINGER_OPEN       0
#define FINGER_SCISSORS  90
#define FINGER_CLOSED   180

#define THUMB_TUCKED      0
#define THUMB_EXTENDED   90

#define MOVE_DELAY_MS   400

// ── BLE UUIDs — Nordic UART Service (NUS) ────────────────────────────────────
// Must match the UUIDs used in rps.py on the laptop side.
#define NUS_SERVICE_UUID  "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define NUS_RX_CHAR_UUID  "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  // laptop → ESP32
#define NUS_TX_CHAR_UUID  "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  // ESP32 → laptop

// ── BLE device name (must match ESP32_BLE_NAME in rps.py) ────────────────────
#define DEVICE_NAME "RPS-ESP32"

// ── Gesture contribution to each RGB channel (per hand) ──────────────────────
#define HAND_VALUE 125   // Each hand contributes this much to its channel

// ── Global objects ────────────────────────────────────────────────────────────
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

BLEServer*          pServer    = nullptr;
BLECharacteristic*  pTxChar    = nullptr;
bool                deviceConnected = false;

//created servo objects
Servo rightFingerA, rightFingerB, rightThumb;
Servo leftFingerA,  leftFingerB,  leftThumb;

// Helper function
static const char* signName(char sign) {
  switch (sign) {
    case '0': return "Withdrawn";
    case '1': return "Rock";
    case '2': return "Paper";
    case '3': return "Scissors";
    default:  return "Unknown";
  }
}

//move hand function
static void moveHand(Servo& fingerA, Servo& fingerB, Servo& thumb, char sign) {
  int targetFinger, targetThumb;

  switch (sign) {
    case '0':  // Withdrawn
      targetFinger = FINGER_OPEN;
      targetThumb  = THUMB_TUCKED;
      break;
    case '1':  // Rock
      targetFinger = FINGER_CLOSED;
      targetThumb  = THUMB_TUCKED;
      break;
    case '2':  // Paper
      targetFinger = FINGER_OPEN;
      targetThumb  = THUMB_EXTENDED;
      break;
    case '3':  // Scissors
      targetFinger = FINGER_SCISSORS;
      targetThumb  = THUMB_TUCKED;
      break;
    default:
      Serial.printf("[SERVO] Unknown sign '%c' — no movement.\n", sign);
      return;
  }

  // Both finger servos move together (same angle), sequentially
  fingerA.write(targetFinger);
  delay(MOVE_DELAY_MS);

  fingerB.write(targetFinger);
  delay(MOVE_DELAY_MS);

  // Thumb last
  thumb.write(targetThumb);
  delay(MOVE_DELAY_MS);
}

// ── BLE Server Callbacks ──────────────────────────────────────────────────────
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    deviceConnected = true;
    Serial.println("[BLE] Client connected.");
  }
  void onDisconnect(BLEServer* pServer) override {
    deviceConnected = false;
    Serial.println("[BLE] Client disconnected — restarting advertising.");
    pServer->startAdvertising();
  }
};


// ── play() — Placeholder for mechanical actuation ────────────────────────────
/**
 * Called once per hand per packet. Drives the LED now; replace the body
 * with servo/motor calls when hardware GPIOs are assigned.
 *
 * @param hand  0 = left hand,  1 = right hand
 * @param sign  '0'=Withdrawn  '1'=Rock  '2'=Paper  '3'=Scissors
 */
void play(int hand, char sign) {
  Serial.printf("[SERVO] Hand=%s  Gesture=%s\n",
                hand == 0 ? "LEFT" : "RIGHT", signName(sign));

  if (hand == 0) {
    moveHand(leftFingerA,  leftFingerB,  leftThumb,  sign);
  } else {
    moveHand(rightFingerA, rightFingerB, rightThumb, sign);
  }
}

// ── applyLED() — Compute and display the blended LED colour ──────────────────
/**
 * Maps each sign to its RGB channel and sums contributions from both hands.
 *
 * @param leftSign   sign character for the left  hand ('0'–'3')
 * @param rightSign  sign character for the right hand ('0'–'3')
 */
void applyLED(char leftSign, char rightSign) {
  int r = 0, g = 0, b = 0;

  // Helper lambda: add one hand's contribution
  auto addHand = [&](char sign) {
    switch (sign) {
      case '1': r += HAND_VALUE; break;   // Rock     → Red
      case '2': g += HAND_VALUE; break;   // Paper    → Green
      case '3': b += HAND_VALUE; break;   // Scissors → Blue
      case '0': /* Withdrawn — no contribution */ break;
      default:  Serial.printf("[LED] Unknown sign '%c'\n", sign); break;
    }
  };

  addHand(leftSign);
  addHand(rightSign);

  // Clamp to 0–255
  r = constrain(r, 0, 255);
  g = constrain(g, 0, 255);
  b = constrain(b, 0, 255);

  strip.setPixelColor(0, strip.Color(r, g, b));
  strip.show();

  Serial.printf("[LED] L='%c' R='%c'  →  RGB(%d, %d, %d)\n",
                leftSign, rightSign, r, g, b);
}


// ── BLE RX Characteristic Callbacks ──────────────────────────────────────────
class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pChar) override {
    String raw = pChar->getValue();
    Serial.printf("[BLE ←] raw: \"%s\" (%d bytes)\n",
                  raw.c_str(), (int)raw.length());

    // ── Validate packet format: P[L][R]\n ─────────────────────────────────
    // Accept with or without trailing newline to be robust.
    if (raw.length() < 3 || raw[0] != 'P') {
      Serial.println("[BLE] Invalid packet — expected P[L][R]\\n. Ignoring.");
      return;
    }

    char leftSign  = raw[1];
    char rightSign = raw[2];

    if (leftSign  < '0' || leftSign  > '3' ||
        rightSign < '0' || rightSign > '3') {
      Serial.println("[BLE] Invalid gesture codes. Expected '0'–'3'. Ignoring.");
      return;
    }

    // ── Dispatch to play() for each hand ──────────────────────────────────
    play(0, leftSign);    // left  hand
    play(1, rightSign);   // right hand
    
    // ── Update LED ────────────────────────────────────────────────────────
    applyLED(leftSign, rightSign);
  }
};


// ── setup() ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n[RPS-1] ESP32 firmware starting…");

  // Servo init
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  rightFingerA.setPeriodHertz(50); rightFingerA.attach(PIN_R_FINGER_A, 500, 2400);
  rightFingerB.setPeriodHertz(50); rightFingerB.attach(PIN_R_FINGER_B, 500, 2400);
  rightThumb  .setPeriodHertz(50); rightThumb  .attach(PIN_R_THUMB,    500, 2400);


  play(0, '0');   // home both hands on boot
  play(1, '0');
  delay(MOVE_DELAY_MS);
  Serial.println("[SERVO] All servos initialised and homed.");

  // ── LED init ──────────────────────────────────────────────────────────────
  strip.begin();
  strip.setBrightness(LED_BRIGHTNESS);
  strip.clear();
  strip.show();
  Serial.printf("[LED] NeoPixel initialised on GPIO %d\n", LED_PIN);

  // ── BLE init ──────────────────────────────────────────────────────────────
  BLEDevice::init(DEVICE_NAME);
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  BLEService* pService = pServer->createService(NUS_SERVICE_UUID);

  // RX characteristic — laptop writes here
  BLECharacteristic* pRxChar = pService->createCharacteristic(
    NUS_RX_CHAR_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR
  );
  pRxChar->setCallbacks(new RxCallbacks());

  // TX characteristic — ESP32 notifies laptop (reserved for future use)
  pTxChar = pService->createCharacteristic(
    NUS_TX_CHAR_UUID,
    BLECharacteristic::PROPERTY_NOTIFY
  );
  pTxChar->addDescriptor(new BLE2902());

  pService->start();

  BLEAdvertising* pAdv = BLEDevice::getAdvertising();
  pAdv->addServiceUUID(NUS_SERVICE_UUID);
  pAdv->setScanResponse(true);
  BLEDevice::startAdvertising();

  Serial.printf("[BLE] Advertising as \"%s\"\n", DEVICE_NAME);
  Serial.println("[RPS-1] Ready — waiting for connection.");

  delay(1000);

  play(1, '0'); delay(1500);  // Withdrawn
  play(1, '1'); delay(1500);  // Rock
  play(1, '2'); delay(1500);  // Paper
  play(1, '3'); delay(1500);  // Scissors
  play(1, '0'); delay(1500);  // Back to Withdrawn
}


// ── loop() ───────────────────────────────────────────────────────────────────
void loop() {
  // All work is done in BLE callbacks — nothing to do here.
  delay(10);
}
