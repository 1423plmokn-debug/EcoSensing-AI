"""
EcoSensing AI - Full Endpoint & AI Diagnostics Audit Script
Verifies all FastAPI routes, ESP32 telemetry, ExperimentLogger, ModelEvaluator,
Diurnal Plume Physics, and Live Groq AI Agents (Vision, Consultation, Mitigation, Parcel).
"""

import base64
import io
import json
import sys
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from PIL import Image
from starlette.testclient import TestClient
from main import app

def run_audit():
    client = TestClient(app)
    results = {}

    print("=================================================================")
    print("      ECOSENSING AI FULL SYSTEM & DIAGNOSTICS AUDIT")
    print("=================================================================")

    # 1. Dashboard Root
    t0 = time.perf_counter()
    r = client.get("/")
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"GET / failed: {r.status_code}"
    results["GET /"] = f"OK (200, {elapsed}ms)"
    print(f"[+] GET / -> {results['GET /']}")

    # 2. ESP32 Unified Status
    t0 = time.perf_counter()
    r = client.get("/api/v1/esp32/status")
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"GET /api/v1/esp32/status failed: {r.status_code}"
    results["GET /api/v1/esp32/status"] = f"OK (200, {elapsed}ms, connected={r.json().get('connected')})"
    print(f"[+] GET /api/v1/esp32/status -> {results['GET /api/v1/esp32/status']}")

    # 3. ESP32 Wi-Fi Push
    t0 = time.perf_counter()
    push_payload = {
        "device_id": "ESP32_SOIL_NODE_01",
        "gpio_pin": 32,
        "sample_count": 32,
        "raw_adc": 2420.0,
        "filtered_adc": 2418.5,
        "voltage_mv": 1950.0,
        "moisture_pct": 44.2,
        "soil_status": "OPTIMAL_FIELD_CAPACITY",
        "calibration_status": "FIELD_CALIBRATED",
        "wifi_rssi": -55,
        "telemetry_source": "WIFI_WIRELESS",
        "timestamp_iso": "2026-11-15T20:00:00Z"
    }
    r = client.post("/api/v1/esp32/push", json=push_payload)
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"POST /api/v1/esp32/push failed: {r.status_code}"
    results["POST /api/v1/esp32/push"] = f"OK (200, {elapsed}ms)"
    print(f"[+] POST /api/v1/esp32/push -> {results['POST /api/v1/esp32/push']}")

    # 4. ESP32 Latest Wi-Fi Reading
    t0 = time.perf_counter()
    r = client.get("/api/v1/esp32/latest-wifi")
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"GET /api/v1/esp32/latest-wifi failed: {r.status_code}"
    results["GET /api/v1/esp32/latest-wifi"] = f"OK (200, {elapsed}ms, vwc={r.json().get('moisture_pct')}%)"
    print(f"[+] GET /api/v1/esp32/latest-wifi -> {results['GET /api/v1/esp32/latest-wifi']}")

    # 5. Lock Depths (5cm, 15cm, 25cm)
    for d_name in ["5cm", "15cm", "25cm"]:
        r = client.post("/api/v1/esp32/lock-depth", json={"depth": d_name, "vwc_pct": 40.0})
        assert r.status_code == 200, f"POST /api/v1/esp32/lock-depth ({d_name}) failed"
    results["POST /api/v1/esp32/lock-depth"] = "OK (All 3 depths locked successfully)"
    print(f"[+] POST /api/v1/esp32/lock-depth -> {results['POST /api/v1/esp32/lock-depth']}")

    # 6. Experiments Status
    t0 = time.perf_counter()
    r = client.get("/api/v1/experiments/status")
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"GET /api/v1/experiments/status failed: {r.status_code}"
    results["GET /api/v1/experiments/status"] = f"OK (200, {elapsed}ms, active={r.json().get('is_logging')})"
    print(f"[+] GET /api/v1/experiments/status -> {results['GET /api/v1/experiments/status']}")

    # 7. Model Evaluation Summary
    t0 = time.perf_counter()
    r = client.get("/api/v1/evaluation/summary")
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"GET /api/v1/evaluation/summary failed: {r.status_code}"
    status_label = r.json().get("evaluation_status")
    results["GET /api/v1/evaluation/summary"] = f"OK (200, {elapsed}ms, status={status_label})"
    print(f"[+] GET /api/v1/evaluation/summary -> {results['GET /api/v1/evaluation/summary']}")

    # 8. Diurnal Plume Physics
    t0 = time.perf_counter()
    r = client.post("/api/v1/physics/diurnal-plume", json={"hour_of_day": 14.0, "base_pm25": 35.0, "wind_speed_ms": 3.5})
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"POST /api/v1/physics/diurnal-plume failed: {r.status_code}"
    results["POST /api/v1/physics/diurnal-plume"] = f"OK (200, {elapsed}ms)"
    print(f"[+] POST /api/v1/physics/diurnal-plume -> {results['POST /api/v1/physics/diurnal-plume']}")

    # 9. Live Weather & Pollution Sentinel
    t0 = time.perf_counter()
    r = client.get("/api/weather?lat=33.3152&lon=44.3661&location_name_ar=بغداد")
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"GET /api/weather failed: {r.status_code}"
    results["GET /api/weather"] = f"OK (200, {elapsed}ms, temp={r.json().get('air_temp_c')}C)"
    print(f"[+] GET /api/weather -> {results['GET /api/weather']}")

    t0 = time.perf_counter()
    r = client.get("/api/pollution-sentinel?lat=33.3152&lon=44.3661")
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"GET /api/pollution-sentinel failed: {r.status_code}"
    results["GET /api/pollution-sentinel"] = f"OK (200, {elapsed}ms, aqi={r.json().get('aqi')})"
    print(f"[+] GET /api/pollution-sentinel -> {results['GET /api/pollution-sentinel']}")

    # 10. Agent 3: Live Groq Vision Analysis (/api/v1/analyze-vision)
    print("\n--- Testing Agent 3: Live Groq Vision Analysis ---")
    img = Image.new("RGB", (128, 128), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    t0 = time.perf_counter()
    r = client.post(
        "/api/v1/analyze-vision",
        files={"image": ("test_leaf.jpg", img_bytes, "image/jpeg")},
        data={"region_name": "بغداد - الكرادة", "session_id": "audit_session", "session_action": "NEW_SESSION"}
    )
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"POST /api/v1/analyze-vision failed: {r.status_code}, {r.text}"
    v_data = r.json()
    model_used = v_data.get("ai_telemetry", {}).get("model_name")
    is_live = v_data.get("ai_telemetry", {}).get("is_live_cloud")
    sci_name = v_data.get("scientific_name") or v_data.get("lab_report", {}).get("scientific_name")
    ar_name = v_data.get("arabic_common_name") or v_data.get("lab_report", {}).get("arabic_common_name")
    results["POST /api/v1/analyze-vision"] = f"OK (200, {elapsed}ms, model={model_used}, live={is_live}, sci={sci_name}, ar={ar_name})"
    print(f"[+] POST /api/v1/analyze-vision -> {results['POST /api/v1/analyze-vision']}")
    assert is_live is True, "Expected is_live_cloud to be True"
    assert sci_name != "Groq LPU Diagnostic Exception", f"Unexpected diagnostic exception: {v_data}"

    # 11. Interactive Clinical Consultation (/api/v1/lab-session/consult)
    print("\n--- Testing Interactive Clinical Consultation ---")
    t0 = time.perf_counter()
    consult_payload = {
        "session_id": "audit_session",
        "user_message": "ما هو تشخيص العينة بناء على الرطوبة المقاسة؟",
        "sender": "المستخدم"
    }
    r = client.post("/api/v1/lab-session/consult", json=consult_payload)
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"POST /api/v1/lab-session/consult failed: {r.status_code}, {r.text}"
    c_data = r.json()
    c_reply = c_data.get("investigator_reply_ar") or c_data.get("reply_ar") or ""
    results["POST /api/v1/lab-session/consult"] = f"OK (200, {elapsed}ms, reply_len={len(c_reply)})"
    print(f"[+] POST /api/v1/lab-session/consult -> {results['POST /api/v1/lab-session/consult']}")

    # 12. Pollution Mitigation Diagnosis (/api/v1/diagnose-pollution-mitigation)
    print("\n--- Testing Pollution Mitigation Diagnosis ---")
    t0 = time.perf_counter()
    mitigation_payload = {
        "lat": 33.3152,
        "lon": 44.3661,
        "district_name_ar": "الكرادة",
        "land_use_tag": "COMMERCIAL",
        "impervious_pct": 75.0,
        "bare_soil_pct": 10.0,
        "is_built_up": True,
        "is_airport": False
    }
    r = client.post("/api/v1/diagnose-pollution-mitigation", json=mitigation_payload)
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"POST /api/v1/diagnose-pollution-mitigation failed: {r.status_code}, {r.text}"
    m_data = r.json()
    results["POST /api/v1/diagnose-pollution-mitigation"] = f"OK (200, {elapsed}ms)"
    print(f"[+] POST /api/v1/diagnose-pollution-mitigation -> {results['POST /api/v1/diagnose-pollution-mitigation']}")

    # 13. Comprehensive Parcel Inspection (/api/v1/inspect-comprehensive-parcel)
    print("\n--- Testing Comprehensive Parcel Inspection ---")
    t0 = time.perf_counter()
    parcel_payload = {
        "lat": 33.3152,
        "lon": 44.3661,
        "location_name_ar": "بغداد - الكرادة",
        "polygon_coords": [[33.3152, 44.3661], [33.3160, 44.3661], [33.3160, 44.3670], [33.3152, 44.3670]],
        "custom_area_m2": 500.0
    }
    r = client.post("/api/v1/inspect-comprehensive-parcel", json=parcel_payload)
    elapsed = int((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200, f"POST /api/v1/inspect-comprehensive-parcel failed: {r.status_code}, {r.text}"
    p_data = r.json()
    results["POST /api/v1/inspect-comprehensive-parcel"] = f"OK (200, {elapsed}ms)"
    print(f"[+] POST /api/v1/inspect-comprehensive-parcel -> {results['POST /api/v1/inspect-comprehensive-parcel']}")

    print("\n=================================================================")
    print("      ALL ENDPOINTS AUDITED SUCCESSFULLY WITH ZERO ERRORS!")
    print("=================================================================")
    return results

if __name__ == "__main__":
    run_audit()
