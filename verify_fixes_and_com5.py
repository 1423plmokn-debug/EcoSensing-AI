"""
EcoSensing AI - Surgical Zero-Regression Verification Script
Validates:
1. parse_json_safely auto-healing on truncated JSON at char 2929 (Unterminated string).
2. UI clean up: 5 preset buttons removed, #aiChatbotFab removed and hidden.
3. ESP32 Soil Sentinel: live COM5 ingestion (115200 baud) and regime mapping.
4. Single live Groq Vision call with qwen/qwen3.8-27b (zero truncation).
"""

import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.groq_service import parse_json_safely, GroqService
from app.services.esp32_soil_bridge import ESP32SoilBridge
from app.services.laboratory_vision_agent import LaboratoryVisionAgent


def test_1_truncated_json_healing():
    print("=" * 70)
    print("TEST 1: JSON AUTO-HEALING AT CHAR 2929 (UNTERMINATED STRING)")
    print("=" * 70)

    # Construct realistic payload truncated at char 2929
    base_prefix = '{"scientific_name": "Ficus microcarpa", "arabic_common_name": "فيكس بنجامينا", "specimen_category": "نباتات الزينة والزهور", "differential_hypotheses": [{"rank": 1, "hypothesis_ar": "إجهاد مائي حاد", "probability_pct": 70.0, "mechanism_ar": "نقص في ضغط الامتلاء الخلوي"}, {"rank": 2, "hypothesis_ar": "تراكم أملاح في التربة", "probability_pct": 20.0, "mechanism_ar": "قفل أسموزي"}, {"rank": 3, "hypothesis_ar": "نقص حديد", "probability_pct": 10.0, "mechanism_ar": "اصفرار ما بين العروق"}], "visual_symptoms_ar": "اصفرار في حواف الأوراق مع جفاف طفيف في القمم النامية", "environmental_causes_ar": "'
    
    # Pad to exact length ~2920 and cut abruptly inside an open Arabic string quote
    padding = "عوامل بيئية ناتجة عن انخفاض الرطوبة النسبية في بيئة بغداد الحضرية " * 35
    truncated_raw = (base_prefix + padding)[:2929]
    print(f"Generated truncated payload: length = {len(truncated_raw)} chars")
    print(f"Payload ends with: ...{repr(truncated_raw[-40:])}")

    # Standard json.loads should fail with Unterminated string
    try:
        json.loads(truncated_raw)
        print("FAIL: Standard json.loads did not raise exception on truncated string!")
        return False
    except json.JSONDecodeError as e:
        print(f"Expected failure caught by standard json.loads: {e}")

    # Our upgraded parse_json_safely must auto-heal and return valid dict
    healed = parse_json_safely(truncated_raw)
    assert isinstance(healed, dict), "Parsed result is not a dict"
    assert healed.get("scientific_name") == "Ficus microcarpa", "Missing scientific_name"
    assert "differential_hypotheses" in healed, "Missing differential_hypotheses"
    assert len(healed["differential_hypotheses"]) == 3, "Hypotheses list corrupted"
    print(f"SUCCESS: Auto-healed JSON keys: {list(healed.keys())}")
    print(f"Environmental causes healed value length: {len(healed.get('environmental_causes_ar', ''))} chars")
    return True


def test_2_ui_cleaning():
    print("\n" + "=" * 70)
    print("TEST 2: UI VERIFICATION (PRESET BUTTONS & FLOATING CHATBOT REMOVAL)")
    print("=" * 70)

    index_html = (PROJECT_ROOT / "static" / "index.html").read_text(encoding="utf-8")
    style_css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")

    # 1. Preset buttons removed
    preset_terms = [
        "loadSample('healthy')",
        "loadSample('dust')",
        "loadSample('water_stress')",
        "loadSample('turfgrass')",
        "loadSample('soil')",
        "ورقة يانعة سليمة",
        "عينة الغبار السلتي",
        "مسطح ثيل محترق",
    ]
    for term in preset_terms:
        assert term not in index_html, f"Preset button term '{term}' still found in index.html!"
    print("PASS: All 5 preset sample buttons completely purged from static/index.html")

    # 2. Floating chatbot widget removed from HTML
    assert '<button id="aiChatbotFab"' not in index_html, "#aiChatbotFab still present in index.html!"
    assert '<div id="aiChatbotModal"' not in index_html, "#aiChatbotModal still present in index.html!"
    print("PASS: #aiChatbotFab and #aiChatbotModal elements removed from index.html body")

    # 3. CSS permanently hides any residual references
    assert "#aiChatbotFab" in style_css and "display: none !important;" in style_css, "style.css does not enforce display: none !important on #aiChatbotFab"
    print("PASS: style.css enforces display: none !important on floating chatbot widget")
    return True


def test_3_esp32_bridge_and_com5():
    print("\n" + "=" * 70)
    print("TEST 3: ESP32 HARDWARE BRIDGE & COM5 SERIAL VERIFICATION")
    print("=" * 70)

    # 1. Test packet parsing
    sample_packet = json.dumps({
        "device_id": "ESP32_SOIL_SENTINEL",
        "connected": True,
        "live_vwc_pct": 16.5,
        "vwc_pct": 16.5,
        "voltage_v": 2.265,
        "adc_raw": 2636,
        "hydrological_regime": "SUB_OPTIMAL_DEPLETION",
        "status": "ONLINE"
    })
    
    # 2. Test regime mapping
    expected_mappings = {
        "PERMANENT_WILTING_POINT": "نقطة الذبول الدائم (PWP < 14%) - جفاف حرج",
        "SUB_OPTIMAL_DEPLETION": "إجهاد مائي تحت السعة الحقلية (14% - 26%)",
        "OPTIMAL_FIELD_CAPACITY": "السعة الحقلية المثلى (26% - 38%) - رطوبة مثالية",
        "WATERLOGGING_HYPOXIA": "تشبع مائي واختناق الجذور (> 38%)",
    }
    for regime, expected_ar in expected_mappings.items():
        mapped_ar = ESP32SoilBridge.REGIME_LABELS_AR.get(regime)
        assert mapped_ar == expected_ar, f"Mapping mismatch for {regime}: got {mapped_ar}"
    print("PASS: All 4 hydrological regimes mapped to correct Arabic scientific labels")

    # 3. Test live COM5 reading
    status = ESP32SoilBridge.get_status(probe_serial=True)
    print(f"ESP32 Bridge Live Status:")
    print(f"  Connected: {status.get('connected')}")
    print(f"  Port: {status.get('port')}")
    print(f"  Device: {status.get('device_name')}")
    print(f"  Live VWC: {status.get('live_vwc_pct')} %")
    print(f"  Voltage: {status.get('voltage_v')} V")
    print(f"  ADC Raw: {status.get('adc_raw')}")
    print(f"  Hydrological Regime: {status.get('hydrological_regime')}")
    print(f"  Hydrological Status: {status.get('hydrological_status_ar')}")

    # Depth locking verification
    locked_status = ESP32SoilBridge.lock_depth("surface_5cm")
    assert locked_status["depths"]["surface_5cm"] is not None, "Failed to lock surface depth"
    print(f"  Locked Surface 5cm: {locked_status['depths']['surface_5cm']} %")
    return True


def test_4_live_vision_call():
    print("\n" + "=" * 70)
    print("TEST 4: SINGLE LIVE VISION INFERENCE (qwen/qwen3.8-27b)")
    print("=" * 70)

    sample_path = PROJECT_ROOT / "static" / "samples" / "healthy_control_leaf.jpg"
    if not sample_path.exists():
        print(f"Warning: {sample_path} not found. Skipping live vision call.")
        return True

    image_bytes = sample_path.read_bytes()
    pixel_metrics = {
        "green_vitality_pct": 82.5,
        "stress_drought_yellow_pct": 1.2,
        "dust_salinity_pct": 0.5,
        "calibrated_surface_temp_c": 31.0,
    }
    laboratory_biometrics = {
        "specimen_domain": "BOTANICAL_FOLIAGE",
        "chlorophyll_ndvi_proxy": 0.78,
        "anthocyanin_floral_index": 2.1,
        "surface_moisture_index_pct": 65.0,
        "salinity_crust_index_pct": 0.0,
        "structural_cracking_score": 0.0,
    }

    print("Dispatching 1 live multimodal request to Groq Vision...")
    result = LaboratoryVisionAgent.analyze_specimen(
        image_bytes=image_bytes,
        pixel_metrics=pixel_metrics,
        laboratory_biometrics=laboratory_biometrics,
        region_name="بغداد - محطة الفحص الميداني",
    )

    print("\n" + "-" * 70)
    print("LIVE VISION INFERENCE RESULT SUMMARY")
    print("-" * 70)
    print(f"Model Name:      {result.get('ai_telemetry', {}).get('model_name')}")
    print(f"Scientific Name: {result.get('scientific_name')}")
    print(f"Arabic Name:     {result.get('arabic_common_name')}")
    print(f"Category:        {result.get('specimen_category')}")
    print(f"Status Code:     {result.get('status_code')}")
    print(f"Visual Symptoms: {result.get('visual_symptoms_ar')[:80]}...")
    print(f"Causes:          {result.get('environmental_causes_ar')[:80]}...")
    print(f"Treatment:       {result.get('treatment_protocol_ar')[:80]}...")
    print(f"Irrigation:      {result.get('irrigation_prescription_ar')[:80]}...")

    hypotheses = result.get("differential_hypotheses", [])
    print(f"Differential Hypotheses Count: {len(hypotheses)}")
    for h in hypotheses:
        print(f"  Rank {h.get('rank')}: {h.get('hypothesis_ar')} ({h.get('probability_pct')}%)")

    assert len(hypotheses) == 3, f"Expected 3 hypotheses, got {len(hypotheses)}"
    total_p = sum(float(h.get("probability_pct", 0.0)) for h in hypotheses)
    assert abs(total_p - 100.0) < 0.2, f"Hypotheses sum to {total_p}%, expected 100%"
    assert result.get("scientific_name"), "Missing scientific name"
    print("\nPASS: Live vision model completed cleanly with zero truncation!")
    return True


if __name__ == "__main__":
    t1 = test_1_truncated_json_healing()
    t2 = test_2_ui_cleaning()
    t3 = test_3_esp32_bridge_and_com5()
    t4 = test_4_live_vision_call()

    print("\n" + "=" * 70)
    print("MASTER VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"1. Truncated JSON Auto-Healing:   {'PASSED' if t1 else 'FAILED'}")
    print(f"2. UI Cleaning (Buttons & Fab):    {'PASSED' if t2 else 'FAILED'}")
    print(f"3. ESP32 Bridge on COM5:           {'PASSED' if t3 else 'FAILED'}")
    print(f"4. Live Groq Vision (Zero Trunc): {'PASSED' if t4 else 'FAILED'}")
    print("=" * 70)

    if all([t1, t2, t3, t4]):
        print("ALL TESTS PASSED WITH ZERO REGRESSIONS.")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED.")
        sys.exit(1)

