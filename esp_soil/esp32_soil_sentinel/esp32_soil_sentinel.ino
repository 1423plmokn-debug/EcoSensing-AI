#include <Arduino.h>

const int SOIL_PIN = 32;
const int SAMPLE_COUNT = 32;
const int TRIM_COUNT = 4;

const float DRY_AIR_MV = 2750.0;
const float WET_WATER_MV = 1220.0;

float smoothed_vwc = -1.0;
const float EMA_ALPHA = 0.25;

void sortSamples(int *arr, int n) {
  for (int i = 0; i < n - 1; i++) {
    for (int j = 0; j < n - i - 1; j++) {
      if (arr[j] > arr[j + 1]) {
        int temp = arr[j];
        arr[j] = arr[j + 1];
        arr[j + 1] = temp;
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(SOIL_PIN, INPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);
}

void loop() {
  int raw_samples[SAMPLE_COUNT];
  int mv_samples[SAMPLE_COUNT];

  for (int i = 0; i < SAMPLE_COUNT; i++) {
    raw_samples[i] = analogRead(SOIL_PIN);
    mv_samples[i] = analogReadMilliVolts(SOIL_PIN);
    delay(8);
  }

  sortSamples(raw_samples, SAMPLE_COUNT);
  sortSamples(mv_samples, SAMPLE_COUNT);

  long raw_sum = 0;
  long mv_sum = 0;
  int valid_count = SAMPLE_COUNT - (2 * TRIM_COUNT);

  for (int i = TRIM_COUNT; i < SAMPLE_COUNT - TRIM_COUNT; i++) {
    raw_sum += raw_samples[i];
    mv_sum += mv_samples[i];
  }

  int filtered_adc = raw_sum / valid_count;
  float filtered_mv = (float)mv_sum / (float)valid_count;
  float voltage_v = filtered_mv / 1000.0;

  float normalized = (DRY_AIR_MV - filtered_mv) / (DRY_AIR_MV - WET_WATER_MV);
  if (normalized < 0.0) normalized = 0.0;
  if (normalized > 1.0) normalized = 1.0;

  float instant_vwc = normalized * 52.0;

  if (smoothed_vwc < 0.0) {
    smoothed_vwc = instant_vwc;
  } else {
    smoothed_vwc = (EMA_ALPHA * instant_vwc) + ((1.0 - EMA_ALPHA) * smoothed_vwc);
  }

  const char* hydro_regime = "SUB_OPTIMAL_DEPLETION";
  if (smoothed_vwc < 14.0) {
    hydro_regime = "PERMANENT_WILTING_POINT";
  } else if (smoothed_vwc >= 26.0 && smoothed_vwc <= 38.0) {
    hydro_regime = "OPTIMAL_FIELD_CAPACITY";
  } else if (smoothed_vwc > 38.0) {
    hydro_regime = "WATERLOGGING_HYPOXIA";
  }

  Serial.print("{\"device_id\":\"ESP32_SOIL_SENTINEL\",\"connected\":true,\"live_vwc_pct\":");
  Serial.print(smoothed_vwc, 1);
  Serial.print(",\"vwc_pct\":");
  Serial.print(smoothed_vwc, 1);
  Serial.print(",\"voltage_v\":");
  Serial.print(voltage_v, 3);
  Serial.print(",\"adc_raw\":");
  Serial.print(filtered_adc);
  Serial.print(",\"hydrological_regime\":\"");
  Serial.print(hydro_regime);
  Serial.println("\",\"status\":\"ONLINE\"}");

  delay(700);
}