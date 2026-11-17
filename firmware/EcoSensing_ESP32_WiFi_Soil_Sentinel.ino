/**
 * EcoSensing AI — ESP32 Capacitive Soil Moisture Sentinel
 * =========================================================
 * Platform  : ESP32 DevKit V1 on Expansion Shield V3
 * Sensor    : Capacitive Soil Moisture Sensor V1.2 (Analog)
 * Power     : 18650 Lithium Battery Shield V3
 *
 * Features:
 *  - 32-sample Trimmed Mean (removes 4 outliers each end) + EMA smoothing
 *  - 3-depth Virtual Moisture Gradient simulation (surface / mid / root)
 *  - Hydrological Regime Classification (4 levels)
 *  - Wi-Fi push to EcoSensing AI FastAPI backend (/api/v1/esp32/push)
 *  - Serial JSON telemetry @ 115200 baud for USB debug / calibration
 *
 * Wiring (see static/images/esp32_wiring_diagram.jpg):
 *  Battery Shield 5V  → ESP32 5V  (Red wire)
 *  Battery Shield GND → ESP32 GND (Black wire)
 *  ESP32 3.3V         → Sensor VCC (Orange wire)
 *  ESP32 GND          → Sensor GND (Gray wire)
 *  ESP32 GPIO 32      → Sensor AOUT (Purple wire)
 *
 * Calibration Commands (send via Serial Monitor @ 115200 baud):
 *  CAL_DRY   — record dry-air ADC baseline (hold sensor in open air)
 *  CAL_WET   — record water-saturation ADC baseline (submerge sensor tip)
 *
 * Author : Ali Nihad Qadir (علي نهاد قادر)
 * Project: EcoSensing AI — Urban Microclimate Observatory & Field Sentinel
 * Context: EcoTech AI Green Innovation Hackathon (16-11-2026)
 *          Middle Technical University — Polytechnic College
 *          Dept. of Electronic & AI Engineering Technologies
 *
 * IMPORTANT: Replace the three placeholders below before flashing:
 *   YOUR_WIFI_SSID      → your Wi-Fi network name
 *   YOUR_WIFI_PASSWORD  → your Wi-Fi password
 *   YOUR_SERVER_IP      → IP address of the machine running EcoSensing AI
 * =========================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ── Wi-Fi Credentials (replace before flashing) ──────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ── EcoSensing AI Backend Endpoint ───────────────────────────
// Replace YOUR_SERVER_IP with the LAN IP of the machine running uvicorn.
// Example: "http://192.168.1.100:8000/api/v1/esp32/push"
const char* PUSH_ENDPOINT = "http://YOUR_SERVER_IP:8000/api/v1/esp32/push";

// ── Hardware Configuration ────────────────────────────────────
const int SOIL_PIN    = 32;      // GPIO 32 → Sensor AOUT (Purple wire)
const int SAMPLE_COUNT = 32;
const int TRIM_COUNT   = 4;      // Trim 4 from each end → 24 valid samples

// ── Calibration Baselines (mV) ────────────────────────────────
// Override with CAL_DRY / CAL_WET serial commands during first run.
float DRY_AIR_MV  = 2750.0f;   // Sensor in open air
float WET_WATER_MV = 1220.0f;  // Sensor fully submerged (tip only)

// ── EMA State ─────────────────────────────────────────────────
float smoothed_vwc   = -1.0f;
const float EMA_ALPHA = 0.25f;

// ── Virtual Depth Gradient Offsets (simulated) ───────────────
const float DEPTH_SURFACE_OFFSET = +3.0f;   //  0–10 cm: slightly drier
const float DEPTH_MID_OFFSET     =  0.0f;   // 10–20 cm: reference
const float DEPTH_ROOT_OFFSET    = -2.5f;   // 20–30 cm: slightly wetter

// ── Forward Declarations ──────────────────────────────────────
void sortSamples(int* arr, int n);
void handleSerialCalibration();
const char* classifyHydroRegime(float vwc);
void pushToServer(float vwc, float voltage_v, int adc_raw, const char* regime);

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(600);
  Serial.println(F("[EcoSensing] ESP32 Soil Sentinel booting..."));

  pinMode(SOIL_PIN, INPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);

  // Connect to Wi-Fi
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Connected. IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println(F("\n[WiFi] Connection failed — running in USB-only mode."));
  }
}

// ─────────────────────────────────────────────────────────────
void loop() {
  handleSerialCalibration();

  // ── Collect 32 samples ──────────────────────────────────────
  int raw_samples[SAMPLE_COUNT];
  int mv_samples[SAMPLE_COUNT];
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    raw_samples[i] = analogRead(SOIL_PIN);
    mv_samples[i]  = analogReadMilliVolts(SOIL_PIN);
    delay(8);
  }

  // ── Trimmed Mean ────────────────────────────────────────────
  sortSamples(raw_samples, SAMPLE_COUNT);
  sortSamples(mv_samples, SAMPLE_COUNT);

  long raw_sum = 0, mv_sum = 0;
  int valid_count = SAMPLE_COUNT - (2 * TRIM_COUNT);
  for (int i = TRIM_COUNT; i < SAMPLE_COUNT - TRIM_COUNT; i++) {
    raw_sum += raw_samples[i];
    mv_sum  += mv_samples[i];
  }
  int   filtered_adc = raw_sum / valid_count;
  float filtered_mv  = (float)mv_sum / (float)valid_count;
  float voltage_v    = filtered_mv / 1000.0f;

  // ── Normalize → VWC % ───────────────────────────────────────
  float normalized   = (DRY_AIR_MV - filtered_mv) / (DRY_AIR_MV - WET_WATER_MV);
  normalized = constrain(normalized, 0.0f, 1.0f);
  float instant_vwc  = normalized * 52.0f;   // Max clay VWC ≈ 52%

  // ── EMA Smoothing ────────────────────────────────────────────
  smoothed_vwc = (smoothed_vwc < 0.0f)
    ? instant_vwc
    : (EMA_ALPHA * instant_vwc) + ((1.0f - EMA_ALPHA) * smoothed_vwc);

  // ── Classify Hydrological Regime ────────────────────────────
  const char* regime = classifyHydroRegime(smoothed_vwc);

  // ── Virtual Depth Gradient ───────────────────────────────────
  float vwc_surface = constrain(smoothed_vwc + DEPTH_SURFACE_OFFSET, 0.0f, 55.0f);
  float vwc_mid     = constrain(smoothed_vwc + DEPTH_MID_OFFSET,     0.0f, 55.0f);
  float vwc_root    = constrain(smoothed_vwc + DEPTH_ROOT_OFFSET,    0.0f, 55.0f);

  // ── Serial JSON Telemetry ────────────────────────────────────
  Serial.printf(
    "{\"device_id\":\"ESP32_SOIL_SENTINEL\","
    "\"connected\":true,"
    "\"live_vwc_pct\":%.1f,"
    "\"vwc_pct\":%.1f,"
    "\"voltage_v\":%.3f,"
    "\"adc_raw\":%d,"
    "\"surface_5cm\":%.1f,"
    "\"mid_15cm\":%.1f,"
    "\"root_25cm\":%.1f,"
    "\"hydrological_regime\":\"%s\","
    "\"status\":\"ONLINE\"}\n",
    smoothed_vwc, smoothed_vwc, voltage_v, filtered_adc,
    vwc_surface, vwc_mid, vwc_root, regime
  );

  // ── Wi-Fi Push to EcoSensing AI Backend ─────────────────────
  if (WiFi.status() == WL_CONNECTED) {
    pushToServer(smoothed_vwc, voltage_v, filtered_adc, regime);
  }

  delay(700);
}

// ─────────────────────────────────────────────────────────────
void sortSamples(int* arr, int n) {
  for (int i = 0; i < n - 1; i++)
    for (int j = 0; j < n - i - 1; j++)
      if (arr[j] > arr[j + 1]) {
        int t = arr[j]; arr[j] = arr[j + 1]; arr[j + 1] = t;
      }
}

// ─────────────────────────────────────────────────────────────
const char* classifyHydroRegime(float vwc) {
  if      (vwc < 14.0f)                      return "PERMANENT_WILTING_POINT";
  else if (vwc >= 26.0f && vwc <= 38.0f)     return "OPTIMAL_FIELD_CAPACITY";
  else if (vwc > 38.0f)                      return "WATERLOGGING_HYPOXIA";
  else                                        return "SUB_OPTIMAL_DEPLETION";
}

// ─────────────────────────────────────────────────────────────
void pushToServer(float vwc, float voltage_v, int adc_raw, const char* regime) {
  HTTPClient http;
  http.begin(PUSH_ENDPOINT);
  http.addHeader("Content-Type", "application/json");

  String payload = String("{\"device_id\":\"ESP32_SOIL_SENTINEL\","
    "\"connected\":true,"
    "\"live_vwc_pct\":") + String(vwc, 1) +
    ",\"vwc_pct\":"    + String(vwc, 1) +
    ",\"voltage_v\":"  + String(voltage_v, 3) +
    ",\"adc_raw\":"    + String(adc_raw) +
    ",\"hydrological_regime\":\"" + String(regime) + "\""
    ",\"status\":\"ONLINE\"}";

  int code = http.POST(payload);
  if (code > 0) {
    Serial.printf("[HTTP] Push OK → %s  code=%d\n", PUSH_ENDPOINT, code);
  } else {
    Serial.printf("[HTTP] Push failed: %s\n", http.errorToString(code).c_str());
  }
  http.end();
}

// ─────────────────────────────────────────────────────────────
void handleSerialCalibration() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd == "CAL_DRY") {
    int mv = analogReadMilliVolts(SOIL_PIN);
    DRY_AIR_MV = (float)mv;
    Serial.printf("[CAL] DRY baseline updated → %.0f mV\n", DRY_AIR_MV);
  } else if (cmd == "CAL_WET") {
    int mv = analogReadMilliVolts(SOIL_PIN);
    WET_WATER_MV = (float)mv;
    Serial.printf("[CAL] WET baseline updated → %.0f mV\n", WET_WATER_MV);
  }
}
