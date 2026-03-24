/**
 * ESP32_RPS.ino
 * Rock-Paper-Scissors-Minus-One (RPS-1) — ESP32 Firmware
 * MSE 3302B | Western University
 *
 * Receives hand-position commands from the laptop over BLE (Nordic UART
 * Service) and drives servos for finger/thumb gestures and a stepper motor
 * for arm withdrawal.
 *
 * ── Communication Protocol ───────────────────────────────────────────────────
 *   Gesture packet:   P[L][R]
 *     '0' → Withdrawn   '1' → Rock   '2' → Paper   '3' → Scissors
 *     Example: "P13" → Left: Rock, Right: Scissors
 *
 *   Withdraw packet:  W[D]
 *     '1' → Withdraw arm (rotate stepper to out-of-play position)
 *     '0' → Return arm   (rotate stepper back to playing position)
 *     Example: "W1" → Withdraw this arm
 *              "W0" → Return this arm to playing position
 *
 * ── Servo Architecture ───────────────────────────────────────────────────────
 *     FINGER A servo — Index + Middle fingers
 *     FINGER B servo — Ring  + Pinky  fingers
 *     THUMB servo    — Thumb
 *
 *   Gesture mapping:
 *     '0' Withdrawn → fingers open  (180°), thumb tucked   (180°)
 *     '1' Rock      → fingers closed  (0°), thumb tucked   (180°)
 *     '2' Paper     → fingers open  (180°), thumb extended   (0°)
 *     '3' Scissors  → index+middle open (180°), ring+pinky closed (0°), thumb tucked (180°)
 *
 * ── Stepper Architecture ─────────────────────────────────────────────────────
 *   28BYJ-48 stepper via ULN2003 driver board.
 *   Sits completely idle until a W1 or W0 command is received.
 *   ULN2003 IN1 → GPIO 19
 *   ULN2003 IN2 → GPIO 18
 *   ULN2003 IN3 → GPIO  5
 *   ULN2003 IN4 → GPIO  4
 *
 *   WITHDRAW_STEPS controls how far the arm rotates:
 *     512  steps = quarter turn  (90°)
 *     1024 steps = half turn    (180°)
 *     2048 steps = full turn    (360°)
 *
 * ── GPIO Mapping ─────────────────────────────────────────────────────────────
 *               LEFT HAND      RIGHT HAND
 *   Finger A     GPIO 14        GPIO 26
 *   Finger B     GPIO 13        GPIO 25
 *   Thumb        GPIO 27        GPIO 33
 *   Stepper      IN1=19, IN2=18, IN3=5, IN4=4
 *
 * ── BLE Device Names ─────────────────────────────────────────────────────────
 *   Right arm board: #define DEVICE_NAME "RPS-ESP32-R"
 *   Left  arm board: #define DEVICE_NAME "RPS-ESP32-L"
 *   Change this before uploading to each board.
 *
 * ── Dependencies ─────────────────────────────────────────────────────────────
 *   Install via Arduino Library Manager:
 *     • "Adafruit NeoPixel"   by Adafruit
 *     • "ESP32Servo"          by Kevin Harrington
 *     • ESP32 Arduino core    (Board Manager → esp32 by Espressif)
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Adafruit_NeoPixel.h>
#include <ESP32Servo.h>


// ── Pin / LED configuration ──────────────────────────────────────────────────
#define LED_PIN        21
#define LED_COUNT       1
#define LED_BRIGHTNESS 255


// ── Servo GPIO assignments ────────────────────────────────────────────────────
#define PIN_R_FINGER_A  26    // Right: Index + Middle
#define PIN_R_FINGER_B  25    // Right: Ring  + Pinky
#define PIN_R_THUMB     33    // Right: Thumb

#define PIN_L_FINGER_A  14    // Left: Index + Middle  (not connected yet)
#define PIN_L_FINGER_B  13    // Left: Ring  + Pinky   (not connected yet)
#define PIN_L_THUMB     27    // Left: Thumb            (not connected yet)


// ── Stepper GPIO assignments ──────────────────────────────────────────────────
#define STEPPER_IN1     19
#define STEPPER_IN2     18
#define STEPPER_IN3      5
#define STEPPER_IN4      4


// ── Servo angle constants ─────────────────────────────────────────────────────
#define FINGER_OPEN    180    // String pulled — fingers extended
#define FINGER_CLOSED    0    // String slack  — fingers curl

#define THUMB_TUCKED   180    // Thumb closed
#define THUMB_EXTENDED   0    // Thumb open

#define MOVE_DELAY_MS  500    // ms to wait between each servo movement


// ── Stepper constants ─────────────────────────────────────────────────────────
// Start with 512 (quarter turn) and increase until arm clears play area
#define WITHDRAW_STEPS  1500   // !! tune this value to your mechanism !!
#define STEP_DELAY_US  1200   // microseconds between steps (min ~900)


// ── BLE UUIDs — Nordic UART Service ──────────────────────────────────────────
#define NUS_SERVICE_UUID  "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define NUS_RX_CHAR_UUID  "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
#define NUS_TX_CHAR_UUID  "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

// !! CHANGE THIS before uploading to each board !!
// Right arm: "RPS-ESP32-R"
// Left  arm: "RPS-ESP32-L"
#define DEVICE_NAME "RPS-ESP32-R"

#define HAND_VALUE 125


// ── Global objects ────────────────────────────────────────────────────────────
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

Servo rightFingerA, rightFingerB, rightThumb;
Servo leftFingerA,  leftFingerB,  leftThumb;

BLEServer*          pServer         = nullptr;
BLECharacteristic*  pTxChar         = nullptr;
bool                deviceConnected = false;


// ── Stepper half-step sequence ────────────────────────────────────────────────
const int stepSequence[8][4] = {
  {1, 0, 0, 0},
  {1, 1, 0, 0},
  {0, 1, 0, 0},
  {0, 1, 1, 0},
  {0, 0, 1, 0},
  {0, 0, 1, 1},
  {0, 0, 0, 1},
  {1, 0, 0, 1}
};

int stepIndex = 0;


// ── stepMotor() — advance stepper one step in given direction ─────────────────
void stepMotor(int direction) {
  stepIndex = (stepIndex + direction + 8) % 8;
  digitalWrite(STEPPER_IN1, stepSequence[stepIndex][0]);
  digitalWrite(STEPPER_IN2, stepSequence[stepIndex][1]);
  digitalWrite(STEPPER_IN3, stepSequence[stepIndex][2]);
  digitalWrite(STEPPER_IN4, stepSequence[stepIndex][3]);
  delayMicroseconds(STEP_DELAY_US);
}


// ── stepperOff() — cut power to all stepper coils ────────────────────────────
void stepperOff() {
  digitalWrite(STEPPER_IN1, LOW);
  digitalWrite(STEPPER_IN2, LOW);
  digitalWrite(STEPPER_IN3, LOW);
  digitalWrite(STEPPER_IN4, LOW);
}


// ── withdraw() — rotate stepper to withdraw or return the arm ─────────────────
void withdraw(bool out) {
  int direction = out ? 1 : -1;
  Serial.printf("[STEPPER] %s arm — %d steps\n",
                out ? "Withdrawing" : "Returning", WITHDRAW_STEPS);
  for (int i = 0; i < WITHDRAW_STEPS; i++) {
    stepMotor(direction);
  }
  stepperOff();
  Serial.println("[STEPPER] Done.");
}


// ── signName() ────────────────────────────────────────────────────────────────
static const char* signName(char sign) {
  switch (sign) {
    case '0': return "Withdrawn";
    case '1': return "Rock";
    case '2': return "Paper";
    case '3': return "Scissors";
    default:  return "Unknown";
  }
}


// ── moveHand() ────────────────────────────────────────────────────────────────
static void moveHand(Servo& fingerA, Servo& fingerB, Servo& thumb, char sign) {
  int targetFingerA, targetFingerB, targetThumb;

  switch (sign) {
    case '0':
      targetFingerA = FINGER_OPEN;
      targetFingerB = FINGER_OPEN;
      targetThumb   = THUMB_TUCKED;
      break;
    case '1':
      targetFingerA = FINGER_CLOSED;
      targetFingerB = FINGER_CLOSED;
      targetThumb   = THUMB_TUCKED;
      break;
    case '2':
      targetFingerA = FINGER_OPEN;
      targetFingerB = FINGER_OPEN;
      targetThumb   = THUMB_EXTENDED;
      break;
    case '3':
      targetFingerA = FINGER_OPEN;
      targetFingerB = FINGER_CLOSED;
      targetThumb   = THUMB_TUCKED;
      break;
    default:
      Serial.printf("[SERVO] Unknown sign '%c' — no movement.\n", sign);
      return;
  }

  fingerA.write(targetFingerA);
  delay(MOVE_DELAY_MS);
  fingerB.write(targetFingerB);
  delay(MOVE_DELAY_MS);
  thumb.write(targetThumb);
  delay(MOVE_DELAY_MS);
}


// ── play() ───────────────────────────────────────────────────────────────────
void play(int hand, char sign) {
  Serial.printf("[SERVO] Hand=%s  Gesture=%s\n",
                hand == 0 ? "LEFT" : "RIGHT", signName(sign));
  if (hand == 0) {
    moveHand(leftFingerA,  leftFingerB,  leftThumb,  sign);
  } else {
    moveHand(rightFingerA, rightFingerB, rightThumb, sign);
  }
}


// ── applyLED() ───────────────────────────────────────────────────────────────
void applyLED(char leftSign, char rightSign) {
  int r = 0, g = 0, b = 0;
  auto addHand = [&](char sign) {
    switch (sign) {
      case '1': r += HAND_VALUE; break;
      case '2': g += HAND_VALUE; break;
      case '3': b += HAND_VALUE; break;
      case '0': break;
      default:  Serial.printf("[LED] Unknown sign '%c'\n", sign); break;
    }
  };
  addHand(leftSign);
  addHand(rightSign);
  r = constrain(r, 0, 255);
  g = constrain(g, 0, 255);
  b = constrain(b, 0, 255);
  strip.setPixelColor(0, strip.Color(r, g, b));
  strip.show();
  Serial.printf("[LED] L='%c' R='%c'  →  RGB(%d, %d, %d)\n",
                leftSign, rightSign, r, g, b);
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


// ── BLE RX Characteristic Callbacks ──────────────────────────────────────────
class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pChar) override {
    String raw = pChar->getValue();
    Serial.printf("[BLE ←] raw: \"%s\" (%d bytes)\n",
                  raw.c_str(), (int)raw.length());

    // ── Withdraw packet: W[D] ─────────────────────────────────────────────
    if (raw.length() >= 2 && raw[0] == 'W') {
      if (raw[1] == '1') {
        withdraw(true);
      } else if (raw[1] == '0') {
        withdraw(false);
      } else {
        Serial.println("[BLE] Invalid withdraw command. Expected W1 or W0.");
      }
      return;
    }

    // ── Gesture packet: P[L][R] ───────────────────────────────────────────
    if (raw.length() < 3 || raw[0] != 'P') {
      Serial.println("[BLE] Invalid packet — expected P[L][R] or W[D]. Ignoring.");
      return;
    }

    char leftSign  = raw[1];
    char rightSign = raw[2];

    if (leftSign  < '0' || leftSign  > '3' ||
        rightSign < '0' || rightSign > '3') {
      Serial.println("[BLE] Invalid gesture codes. Expected '0'-'3'. Ignoring.");
      return;
    }

    play(0, leftSign);
    play(1, rightSign);
    applyLED(leftSign, rightSign);
  }
};


// ── setup() ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n[RPS-1] ESP32 firmware starting...");

  // ── Stepper pin init ──────────────────────────────────────────────────────
  pinMode(STEPPER_IN1, OUTPUT);
  pinMode(STEPPER_IN2, OUTPUT);
  pinMode(STEPPER_IN3, OUTPUT);
  pinMode(STEPPER_IN4, OUTPUT);
  stepperOff();
  Serial.println("[STEPPER] Pins initialised — motor idle.");

  // ── Servo init ────────────────────────────────────────────────────────────
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  rightFingerA.setPeriodHertz(50); rightFingerA.attach(PIN_R_FINGER_A, 500, 2400);
  rightFingerB.setPeriodHertz(50); rightFingerB.attach(PIN_R_FINGER_B, 500, 2400);
  rightThumb  .setPeriodHertz(50); rightThumb  .attach(PIN_R_THUMB,    500, 2400);

  play(1, '0');
  Serial.println("[SERVO] Right hand homed to Withdrawn.");

  // ── Boot test sequence ────────────────────────────────────────────────────
  delay(1000);
  Serial.println("[TEST] Starting boot gesture sequence...");
  play(1, '1'); delay(1500);
  play(1, '2'); delay(1500);
  play(1, '3'); delay(1500);
  play(1, '0'); delay(1500);
  Serial.println("[TEST] Boot sequence complete.");

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

  BLECharacteristic* pRxChar = pService->createCharacteristic(
    NUS_RX_CHAR_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR
  );
  pRxChar->setCallbacks(new RxCallbacks());

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
  Serial.println("[RPS-1] Ready — waiting for BLE connection.");
}


// ── loop() ───────────────────────────────────────────────────────────────────
void loop() {
  delay(10);
}
