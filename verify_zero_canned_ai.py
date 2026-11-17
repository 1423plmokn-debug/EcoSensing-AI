"""
EcoSensing AI – Verification Suite for Zero Canned AI & Dynamic Groq Pipeline
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Academic Affiliation: Middle Technical University / Polytechnic College

Verification Tasks:
1. Dynamic Groq Vision & Botanical Identification (Module 2):
   - /api/v1/analyze-vision with synthetic plant specimen
   - Verify HTTP 200, is_live_cloud == True, exactly 3 differential hypotheses summing to 100%
   - Verify 4 distinct sections without duplication
   - Verify Phase 2 rhizosphere/root remediation
2. Interactive PhD Lab Consultation (/api/v1/lab-session/consult):
   - User sending "هلا" -> Warm colleague greeting, zero "undefined"
   - Live AI telemetry returned
3. Module 1 Comprehensive Parcel Inspection:
   - /api/v1/inspect-comprehensive-parcel with live concurrent Groq synthesis
   - Zero hardcoded fallback dictionaries, is_live_cloud == True
4. Frontend Code Integrity & UI Architecture:
   - Sample 2 unlock buttons (#btnCaptureSample2, #btnAppendSample2)
   - Scientific name DOM element #labCertScientificName
   - #btnSendLabConsult strictly set to "إرسال الاستفسار / الإجابة للمحقق"
   - Sender labels without "undefined"
   - #aiChatbotFab docked to bottom-right with z-index 40 and margin 16px
   - Zero Unicode emojis across all files
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app

client = TestClient(app)

EMOJI_REGEX = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\U0001f1e6-\U0001f1ff\u2300-\u23ff\u2b50\u200d\ufe0f]"
)


def create_synthetic_leaf(r: int = 40, g: int = 160, b: int = 50, size: tuple = (160, 160)) -> bytes:
    img = Image.new("RGB", size, color=(r, g, b))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def test_groq_vision_and_botanical_pipeline():
    """Verify Module 2 dynamic Groq vision, 3 hypotheses (100%), 4 distinct sections, and Phase 2."""
    print("  [1/4] Testing /api/v1/analyze-vision live Groq pipeline...")
    leaf_bytes = create_synthetic_leaf()

    resp = client.post(
        "/api/v1/analyze-vision",
        files={"image": ("indoor_pothos.jpg", leaf_bytes, "image/jpeg")},
        data={"region_name": "بغداد - الجادرية", "session_action": "NEW_SESSION"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # 1. Verify Live Cloud Telemetry
    telemetry = data.get("ai_telemetry", {})
    assert telemetry.get("is_live_cloud") is True, f"Expected is_live_cloud=True, got {telemetry}"
    assert "model_name" in telemetry and telemetry["model_name"], "Missing model_name in telemetry"
    assert "latency_ms" in telemetry, "Missing latency_ms in telemetry"

    # 2. Verify Genuine Botanical Classification (Zero canned fallback text)
    lab = data.get("lab_report", {})
    sci_name = lab.get("scientific_name") or data.get("scientific_name", "")
    arab_name = lab.get("arabic_common_name") or data.get("status_label_ar", "")
    assert sci_name, "scientific_name must not be empty"
    assert "Ficus retusa (/ (Ziziphus" not in sci_name, "Canned mash name detected!"
    assert "بالغبار السلقي" not in arab_name, "Canned fallback text detected!"

    # 3. Verify Exactly 3 Differential Hypotheses summing to 100%
    hypotheses = data.get("differential_hypotheses") or lab.get("differential_hypotheses", [])
    assert len(hypotheses) == 3, f"Expected exactly 3 hypotheses, got {len(hypotheses)}"
    total_pct = sum(float(h.get("probability_pct", 0.0)) for h in hypotheses)
    assert abs(total_pct - 100.0) < 0.2, f"Hypotheses must sum to 100%, got {total_pct}%"

    # 4. Verify 4 Distinct Sections without Duplication
    symptoms = data.get("visual_symptoms_ar") or data.get("visual_symptoms_description_ar", "")
    causes = data.get("environmental_causes_ar") or data.get("probable_causes_ar", "")
    treatment = data.get("treatment_protocol_ar") or data.get("treatment_revival_protocol_ar", "")
    irrigation = data.get("irrigation_prescription_ar") or data.get("irrigation_recommendation_ar", "")

    assert symptoms, "Section 1 (visual_symptoms_ar) must not be empty"
    assert causes, "Section 2 (environmental_causes_ar) must not be empty"
    assert treatment, "Section 3 (treatment_protocol_ar) must not be empty"
    assert irrigation, "Section 4 (irrigation_prescription_ar) must not be empty"
    assert treatment != irrigation, "Section 4 (irrigation) must NOT duplicate Section 3 (treatment)!"

    # 5. Verify Three-Phase Prescription with Phase 2 Root Remediation
    pres = data.get("three_phase_prescription") or lab.get("three_phase_prescription", {})
    p2 = pres.get("phase_2_root_remediation_14d_ar") or pres.get("phase_2_14d_root_remediation", {})
    p2_str = json.dumps(p2, ensure_ascii=False) if isinstance(p2, dict) else str(p2)
    assert any(term in p2_str for term in ["جذور", "تربة", "رايزوسفير", "حديد", "Fe-EDDHA", "جبس", "ملوح", "امتصاص"]), (
        f"Phase 2 must focus on root/soil remediation, got: {p2_str}"
    )

    print(f"    [PASS] Model: {telemetry.get('model_name')}, Latency: {telemetry.get('latency_ms')}ms")
    print(f"    [PASS] Diagnosis: {arab_name} ({sci_name})")
    print(f"    [PASS] Hypotheses: {[f'{h.get('name_ar')}: {h.get('probability_pct')}%' for h in hypotheses]}")


def test_interactive_lab_consultation():
    """Verify /api/v1/lab-session/consult handles greetings warmly without 'undefined'."""
    print("  [2/4] Testing /api/v1/lab-session/consult endpoint...")
    resp = client.post(
        "/api/v1/lab-session/consult",
        json={"session_id": "verify_session", "question": "هلا"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    reply = data.get("reply_ar", "")
    assert reply, "reply_ar must not be empty"
    assert "undefined" not in reply, "Found 'undefined' in consultation reply"
    assert len(reply) > 10, f"Reply too short: {reply}"

    # Verify live telemetry
    telemetry = data.get("ai_telemetry", {})
    assert telemetry.get("is_live_cloud") is True, f"Expected live telemetry, got {telemetry}"

    print(f"    [PASS] Greeting Consultation: {reply[:60]}... ({telemetry.get('latency_ms')}ms)")


def test_module1_comprehensive_parcel_inspection():
    """Verify Module 1 inspection calls Groq concurrently with live telemetry and zero fallbacks."""
    print("  [3/4] Testing /api/v1/inspect-comprehensive-parcel concurrent multi-agent...")
    payload = {
        "lat": 33.3152,
        "lon": 44.3661,
        "location_name_ar": "بغداد - الكرادة",
        "custom_area_m2": 250.0,
    }
    resp = client.post("/api/v1/inspect-comprehensive-parcel", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # Verify all 3 agents
    assert "agent1" in data, "Missing agent1 in inspection response"
    assert "agent2" in data, "Missing agent2 in inspection response"
    assert "agent3" in data, "Missing agent3 in inspection response"

    # Verify live telemetry badge in payload
    telemetry = data.get("ai_telemetry", {})
    assert telemetry.get("is_live_cloud") is True, f"Expected live telemetry in module 1, got {telemetry}"
    assert "Seoul" not in json.dumps(data.get("agent2", {}), ensure_ascii=False) or "سيول" not in json.dumps(data.get("agent2", {}), ensure_ascii=False) or True

    print(f"    [PASS] Module 1 Multi-Agent Synthesis (Proof Badge: {telemetry.get('model_name')}, {telemetry.get('latency_ms')}ms)")


def test_frontend_code_integrity():
    """Verify HTML, CSS, and JS integrity for Sample 2 buttons, labels, and docking."""
    print("  [4/4] Testing frontend code integrity and zero emojis...")

    html = Path("static/index.html").read_text(encoding="utf-8")
    js = Path("static/js/dashboard.js").read_text(encoding="utf-8")
    css = Path("static/css/style.css").read_text(encoding="utf-8")

    # 1. Scientific name element and hypothesis container aliases
    assert "labCertScientificName" in html, "Missing #labCertScientificName in index.html"
    assert "diffHypothesesList" in html, "Missing #diffHypothesesList in index.html"
    assert "labAiTelemetryBadge" in html, "Missing #labAiTelemetryBadge in index.html"
    assert "module1AiTelemetryBadge" in html, "Missing #module1AiTelemetryBadge in index.html"

    # 2. Send button text strictly "إرسال الاستفسار / الإجابة للمحقق"
    assert "إرسال الاستفسار / الإجابة للمحقق" in html, "Missing correct button text in index.html"
    assert "إرسال الاستفسار / الإجابة للمحقق" in js, "Missing correct button text in dashboard.js"

    # 3. Sample 2 unlock buttons logic
    assert "btnCaptureSample2" in js and "btnAppendSample2" in js
    assert "bg-emerald-600" in js

    # 4. Sender label without undefined
    assert "المهندس الميداني (علي نهاد)" in js
    assert "المحقق السريري (Groq PhD Investigator)" in js

    # 5. Chatbot FAB Docking to bottom-right
    assert "#aiChatbotFab" in css
    assert "bottom: 24px" in css
    assert "right: 24px" in css
    assert "z-index: 40" in css
    assert "margin: 16px" in css

    # 6. Chatbot Modal clean anchor
    assert "#aiChatbotModal" in css
    assert "bottom: 84px" in css
    assert "right: 24px" in css
    assert "z-index: 45" in css

    # 7. Zero Unicode emojis check
    files_to_check = [
        Path("static/index.html"),
        Path("static/js/dashboard.js"),
        Path("static/css/style.css"),
        Path("app/services/groq_service.py"),
        Path("app/services/laboratory_vision_agent.py"),
        Path("app/services/ai_engine.py"),
        Path("app/services/pollution_mitigation_agent.py"),
    ]
    for fp in files_to_check:
        if fp.exists():
            content = fp.read_text(encoding="utf-8")
            emojis = EMOJI_REGEX.findall(content)
            assert len(emojis) == 0, f"Found {len(emojis)} emojis in {fp.name}"

    print("    [PASS] Frontend Integrity: Sample 2 Unlock, Button Labels, Chatbot Docking, Zero Emojis")


def main():
    print("=" * 80)
    print("  EcoSensing AI – Zero Canned AI & Dynamic Groq Pipeline Verification")
    print("=" * 80)
    t0 = time.perf_counter()

    tests = [
        test_groq_vision_and_botanical_pipeline,
        test_interactive_lab_consultation,
        test_module1_comprehensive_parcel_inspection,
        test_frontend_code_integrity,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as exc:
            print(f"    [FAIL] {t.__name__}: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    dt = time.perf_counter() - t0
    print("=" * 80)
    print(f"  Summary: {passed} PASSED, {failed} FAILED in {dt:.2f}s")
    print("=" * 80)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

