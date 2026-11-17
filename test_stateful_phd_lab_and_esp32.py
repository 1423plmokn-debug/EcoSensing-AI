# -*- coding: utf-8 -*-
"""
test_stateful_phd_lab_and_esp32.py
Automated Verification Suite for Module 2 Upgrade:
1. ESP32 Capacitive Soil Sentinel Gateway & Volumetric Water Content (VWC)
2. Stateful Multi-Sample Lab Session Manager (Foliage -> Soil Rhizosphere)
3. Evidence-Grounded Multi-Stage Differential Diagnosis (100% Attribution)
4. Rhizosphere Biogeochemistry & 3-Phase Clinical Prescription Protocol
5. Clinical Lab Investigator Consultation Console (Dossier Memory)
6. Zero Emojis and DOM ID Integrity
"""

import os
import sys
import re

# Force UTF-8 on Windows stdout
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app
from app.services.esp32_soil_bridge import ESP32SoilBridge

client = TestClient(app)

def test_dom_ids_and_zero_emojis():
    print("=== TEST 1: DOM IDs AND ZERO EMOJIS INTEGRITY ===")
    emoji_regex = re.compile(r'[\U00010000-\U0010ffff\u2600-\u27bf\U0001f1e6-\U0001f1ff\u2300-\u23ff\u2b50\u200d\ufe0f]')
    
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Verify zero emojis in index.html
    html_emojis = emoji_regex.findall(html)
    assert len(html_emojis) == 0, f"Emojis found in index.html: {html_emojis[:5]}"
    print("  [PASS] Zero emojis in static/index.html")

    required_ids = [
        "esp32SentinelCard", "esp32StatusBadge",
        "esp32Depth5Val", "esp32Depth15Val", "esp32Depth25Val",
        "btnLockDepth5", "btnLockDepth15", "btnLockDepth25",
        "esp32LiveVwcVal", "esp32HydrologicalStatus", "esp32GradientVal",
        "btnAnalyzeSample1", "btnAppendSample2", "btnResetLabSession",
        "btnCaptureAnalyze", "btnCaptureSample2",
        "labEvidenceTabs", "tabSample1Evidence", "tabSample2Evidence", "tabCombinedEvidence",
        "labHypothesesList", "labRhizosphereMechanism", "labPrescription3Phase", "labFieldDirective",
        "labCombinedReportCard", "labInvestigatorConsole", "labNextDirectiveBanner",
        "labConsultationLog", "labConsultInput", "btnSendLabConsult"
    ]

    for elem_id in required_ids:
        assert f'id="{elem_id}"' in html or f"id='{elem_id}'" in html, f"Missing required DOM ID: {elem_id}"
    print(f"  [PASS] All {len(required_ids)} required Module 2 DOM IDs verified in static/index.html")


def test_esp32_soil_bridge():
    print("\n=== TEST 2: ESP32 CAPACITIVE SOIL BRIDGE & HYDROLOGICAL PHYSICS ===")
    
    # 1. Initial Status
    resp = client.get("/api/v1/esp32/status")
    assert resp.status_code == 200, f"Status failed: {resp.text}"
    status_data = resp.json()
    assert "is_connected" in status_data
    assert "depth_profiles" in status_data
    print("  [PASS] GET /api/v1/esp32/status returned 200 OK")

    # 2. Ingest Simulated Telemetry (Voltage 1.6V -> Optimal Range in Mesopotamian Clay-Loam)
    ingest_payload = {
        "voltage_v": 1.60,
        "temperature_c": 26.5
    }
    resp = client.post("/api/v1/esp32/ingest", json=ingest_payload)
    assert resp.status_code == 200, f"Ingest failed: {resp.text}"
    reading = resp.json()
    vwc = reading.get("vwc_pct") or reading.get("live_vwc_pct")
    assert vwc is not None and 25.0 <= vwc <= 40.0, f"Unexpected VWC: {vwc}"
    assert "السعة الحقلية" in reading.get("hydrological_status_ar", "") or reading.get("hydrological_regime") == "FIELD_CAPACITY", f"Unexpected status: {reading}"
    print(f"  [PASS] POST /api/v1/esp32/ingest: 1.60V -> VWC {vwc}% ({reading['hydrological_status_ar']})")

    # 3. Lock Multi-Depth Profiles & Gradient Calculation
    # Surface 5cm (dryer, 18% VWC) -> 2.05V
    client.post("/api/v1/esp32/ingest", json={"voltage_v": 2.05, "temperature_c": 28.0})
    resp = client.post("/api/v1/esp32/lock-depth", json={"depth": "surface_5cm"})
    assert resp.status_code == 200

    # Mid 15cm (moderate, 27.7% VWC) -> 1.60V
    client.post("/api/v1/esp32/ingest", json={"voltage_v": 1.60, "temperature_c": 25.0})
    resp = client.post("/api/v1/esp32/lock-depth", json={"depth": "mid_15cm"})
    assert resp.status_code == 200

    # Root 25cm (moist, 35% VWC) -> 1.30V
    client.post("/api/v1/esp32/ingest", json={"voltage_v": 1.30, "temperature_c": 23.0})
    resp = client.post("/api/v1/esp32/lock-depth", json={"depth": "root_25cm"})
    assert resp.status_code == 200

    # Check status for locked depths & gradient
    resp = client.get("/api/v1/esp32/status")
    final_status = resp.json()
    assert final_status["depth_profiles"]["surface_5cm"] is not None
    assert final_status["depth_profiles"]["root_25cm"] is not None
    grad = final_status.get("vertical_gradient_pct_per_cm")
    assert grad is not None and grad > 0, f"Gradient should be positive from surface to root: {grad}"
    print(f"  [PASS] Vertical Moisture Gradient successfully calculated: {grad:.3f} %/cm")


def test_stateful_phd_session_workflow():
    print("\n=== TEST 3: STATEFUL MULTI-SAMPLE LAB SESSION WORKFLOW ===")
    session_id = "test_phd_session_baghdad_99"

    # Step 0: Reset Session
    resp = client.post("/api/v1/lab-session/reset", json={"session_id": session_id})
    assert resp.status_code == 200
    print("  [PASS] POST /api/v1/lab-session/reset: Session initialized")

    # Step 1: Sample 1 - Foliage / Water Stress Sample (NEW_SESSION)
    resp = client.post(
        f"/api/v1/analyze-vision?sample_type=water_stress&region_name=بغداد - الدورة&session_id={session_id}&session_action=NEW_SESSION"
    )
    assert resp.status_code == 200, f"Sample 1 failed: {resp.text}"
    s1_data = resp.json()

    # Verify Backward Compatibility
    assert "primary_diagnosis_title_ar" in s1_data
    assert "vitality_pct" in s1_data
    assert "stress_pct" in s1_data

    # Verify Engine 1: Differential Hypotheses
    hypotheses = s1_data.get("differential_hypotheses", [])
    assert len(hypotheses) == 3, f"Expected 3 differential hypotheses, got {len(hypotheses)}"
    total_prob = sum(h["probability_pct"] for h in hypotheses)
    assert 99.0 <= total_prob <= 101.0, f"Hypotheses sum must be 100%, got {total_prob}"
    print(f"  [PASS] Engine 1 Differential Hypotheses sum to {total_prob:.1f}%: {[h.get('hypothesis_ar') or h.get('name_ar') for h in hypotheses]}")

    # Verify Engine 2: Confirmatory Field Directive & Rhizosphere Biogeochemistry
    assert s1_data.get("confirmatory_field_directive_ar"), "Missing confirmatory field directive"
    assert s1_data.get("rhizosphere_mechanism_ar"), "Missing rhizosphere mechanism"
    print(f"  [PASS] Engine 2 Confirmatory Field Directive: {s1_data['confirmatory_field_directive_ar'][:60]}...")

    # Verify Engine 3: 3-Phase Clinical Prescription Protocol
    pres = s1_data.get("three_phase_prescription")
    assert pres is not None, "Missing three_phase_prescription"
    assert "phase_1_48h_emergency" in pres
    assert "phase_2_14d_root_remediation" in pres
    assert "phase_3_sustainable_prevention" in pres
    print(f"  [PASS] Engine 3 Three-Phase Clinical Protocol present with all 3 phases")

    # Verify Session State after Sample 1
    session_state = s1_data.get("session_state")
    assert session_state is not None, "Missing session_state in response"
    assert len(session_state.get("samples", [])) == 1
    assert session_state.get("combined_synthesis_report") is None
    print("  [PASS] Session correctly holds Sample 1 awaiting Sample 2")

    # Step 2: Sample 2 - Rhizosphere Soil Sample (APPEND_SAMPLE)
    resp = client.post(
        f"/api/v1/analyze-vision?sample_type=soil&region_name=بغداد - الدورة&session_id={session_id}&session_action=APPEND_SAMPLE"
    )
    assert resp.status_code == 200, f"Sample 2 failed: {resp.text}"
    s2_data = resp.json()

    session_state_2 = s2_data.get("session_state")
    assert session_state_2 is not None
    assert len(session_state_2.get("samples", [])) == 2, f"Expected 2 samples, got {len(session_state_2.get('samples', []))}"

    # Verify Engine 4: Multi-Sample Cumulative Synthesis Report Generated!
    comb = session_state_2.get("combined_synthesis_report")
    assert comb is not None, "Combined synthesis report was NOT generated after 2 samples!"
    assert comb.get("confirmed_differential_hypothesis_ar"), "Missing confirmed differential hypothesis"
    assert comb.get("causal_correlation_foliage_to_soil_ar"), "Missing foliage-to-soil causal link"
    assert comb.get("plant_health_prognosis_score") is not None
    assert comb.get("unified_three_phase_prescription"), "Missing unified three phase prescription"
    print(f"  [PASS] Engine 4 Cumulative Multi-Sample Synthesis Report verified:")
    print(f"         Confirmed Hypothesis: {comb['confirmed_differential_hypothesis_ar']}")
    print(f"         Prognosis Score: {comb['plant_health_prognosis_score']}/100")
    print(f"         Causal Correlation: {comb['causal_correlation_foliage_to_soil_ar'][:70]}...")

    # Step 3: Interactive Clinical Consultation (Investigator Console)
    consult_req = {
        "session_id": session_id,
        "question": "هل يفسر تملح التربة وقشور الصوديوم احتراق حواف الأوراق المفحوصة في العينة 1؟"
    }
    resp = client.post("/api/v1/lab-session/consult", json=consult_req)
    assert resp.status_code == 200, f"Consult failed: {resp.text}"
    consult_res = resp.json()
    reply = consult_res.get("reply_ar")
    assert reply and len(reply) > 20, f"Short or missing reply: {reply}"
    history = consult_res.get("investigation_history", [])
    assert len(history) >= 1, f"History should contain consult question: {history}"
    print(f"  [PASS] Clinical Lab Investigator Reply: {reply[:80]}...")

    # Step 4: GET Session State Readout
    resp = client.get(f"/api/v1/lab-session/state?session_id={session_id}")
    assert resp.status_code == 200
    state_res = resp.json()
    assert state_res.get("session_id") == session_id
    assert len(state_res.get("samples", [])) == 2
    assert len(state_res.get("investigation_history", [])) >= 1
    print("  [PASS] GET /api/v1/lab-session/state verified complete dossier state")


if __name__ == "__main__":
    print("STARTING TEST SUITE: test_stateful_phd_lab_and_esp32.py\n")
    try:
        test_dom_ids_and_zero_emojis()
        test_esp32_soil_bridge()
        test_stateful_phd_session_workflow()
        print("\n>>> ALL TESTS IN test_stateful_phd_lab_and_esp32.py PASSED PERFECTLY! <<<")
    except AssertionError as e:
        import traceback
        traceback.print_exc()
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
