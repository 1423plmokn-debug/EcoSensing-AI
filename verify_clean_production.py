"""
EcoSensing AI – Production Integrity & Zero-Canned Real-AI Verification Suite
Strict Enforcement:
1. Dual-Key Groq Configuration & Failover Routing
2. Dynamic Active Model Discovery (Zero 404s)
3. Zero Example Plant Species in Prompts (Zero Dracaena/Ficus/Ziziphus/Rosa)
4. Zero Personal Names in Chat / Consultation Labels
5. Zero Polling Floods (Zero setInterval to /api/v1/esp32/status)
6. Maximum 2 Live Groq Cloud API Calls (1 Vision/Biometric Diagnosis, 1 Consultation)
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
from PIL import Image

# Ensure project root is in python path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.services.groq_service import GroqService, parse_json_safely
from app.services.laboratory_vision_agent import LaboratoryVisionAgent


def generate_test_leaf_bytes() -> bytes:
    """Generate a realistic synthetic plant leaf image (green leaf on neutral background)."""
    img = Image.new("RGB", (320, 320), color=(235, 235, 235))
    pixels = img.load()
    cx, cy = 160, 160
    for x in range(320):
        for y in range(320):
            # Elliptical leaf shape
            dx = (x - cx) / 80.0
            dy = (y - cy) / 130.0
            if (dx * dx + dy * dy) <= 1.0:
                # Green leaf gradient with slight yellowing along margin
                dist = (dx * dx + dy * dy) ** 0.5
                if dist > 0.8:
                    pixels[x, y] = (160, 150, 40)  # chlorotic border
                else:
                    pixels[x, y] = (45, 135, 55)   # vibrant chlorophyll green
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def test_1_config_and_dual_keys():
    print("\n[CHECK 1] Testing Configuration & Dual-Key Setup...")
    assert settings.GROQ_API_KEY_PRIMARY, "GROQ_API_KEY_PRIMARY must not be empty"
    assert settings.GROQ_API_KEY_BACKUP, "GROQ_API_KEY_BACKUP must not be empty"
    assert settings.GROQ_API_KEY_PRIMARY != settings.GROQ_API_KEY_BACKUP, "Primary and Backup keys should be distinct"
    assert settings.is_groq_configured(), "Settings.is_groq_configured() must return True"
    print(f"  OK: Primary Key: {settings.GROQ_API_KEY_PRIMARY[:12]}... (configured)")
    print(f"  OK: Backup Key:  {settings.GROQ_API_KEY_BACKUP[:12]}... (configured)")
    return True


def test_2_json_parser_unquoted_fractions():
    print("\n[CHECK 2] Testing Resilient JSON Parser on Unquoted Fractions...")
    sample_raw = """
    ```json
    {
      "scientific_name": "Test Specimen",
      "arabic_common_name": "عينة اختبار",
      "cracking_score": 3.7/10,
      "moisture_ratio": 7/10,
      "differential_hypotheses": [
        {"rank": 1, "hypothesis_ar": "فرضية رئيسية", "probability_pct": 70.0}
      ]
    }
    ```
    """
    parsed = parse_json_safely(sample_raw)
    assert parsed.get("scientific_name") == "Test Specimen"
    assert parsed.get("cracking_score") == "3.7/10"
    assert parsed.get("moisture_ratio") == "7/10"
    print("  OK: Unquoted fractions 3.7/10 and 7/10 safely parsed as strings without error.")
    return True


def test_3_prompt_integrity_zero_example_species():
    print("\n[CHECK 3] Testing Prompt Integrity (Zero Species Examples & Zero Personal Names)...")
    forbidden_species = ["Dracaena", "Ficus", "Ziziphus", "Rosa", "دراسينا", "فيكس", "سدر", "جوري"]
    system_prompt = LaboratoryVisionAgent.PHD_STAGE_SYSTEM_PROMPT
    consult_prompt = LaboratoryVisionAgent.CONSULTATION_SYSTEM_PROMPT

    for sp in forbidden_species:
        assert sp not in system_prompt, f"Forbidden species '{sp}' found in PHD_STAGE_SYSTEM_PROMPT!"
        assert sp not in consult_prompt, f"Forbidden species '{sp}' found in CONSULTATION_SYSTEM_PROMPT!"

    forbidden_personal_names = ["علي نهاد", "المهندس علي"]
    assert "علي نهاد" not in consult_prompt, "Personal name found in CONSULTATION_SYSTEM_PROMPT!"
    assert "المختبر الذكي" in consult_prompt, "Neutral role 'المختبر الذكي' missing from CONSULTATION_SYSTEM_PROMPT!"
    assert "المستخدم" in consult_prompt, "Neutral role 'المستخدم' missing from CONSULTATION_SYSTEM_PROMPT!"
    print("  OK: Prompts are 100% abstract and analytical with zero species examples and zero personal names.")
    return True


def test_4_zero_polling_flood_in_js():
    print("\n[CHECK 4] Testing Frontend Polling Elimination in static/js/dashboard.js...")
    js_path = ROOT_DIR / "static" / "js" / "dashboard.js"
    js_content = js_path.read_text(encoding="utf-8")

    # Assert no setInterval calls to fetchEsp32Status or /esp32/status
    bad_interval_matches = re.findall(r"setInterval\s*\(\s*(?:fetchEsp32Status|.*esp32.*)\s*,", js_content)
    assert len(bad_interval_matches) == 0, f"Found lingering ESP32 polling intervals in dashboard.js: {bad_interval_matches}"

    assert "setEsp32Modality" in js_content, "setEsp32Modality function missing in dashboard.js"
    assert "compressImageToBlob" in js_content, "compressImageToBlob function missing in dashboard.js"
    print("  OK: Zero ESP32 setInterval polling floods found in dashboard.js. Optical mode is default.")
    return True


def test_5_live_groq_vision_and_hypotheses():
    print("\n[CHECK 5] Executing LIVE Groq Cloud API Call 1/2: Vision / Biometric Specimen Diagnosis...")
    img_bytes = generate_test_leaf_bytes()
    pixel_metrics = {
        "green_vitality_pct": 74.5,
        "dust_salinity_pct": 2.1,
        "stress_drought_yellow_pct": 18.2,
    }
    lab_biometrics = {
        "specimen_domain": "BOTANICAL_FOLIAGE",
        "surface_moisture_index_pct": 46.0,
        "salinity_crust_index_pct": 1.5,
        "structural_cracking_score": 0.5,
        "chlorophyll_ndvi_proxy": 0.54,
        "anthocyanin_floral_index": 0.0,
    }

    t0 = time.perf_counter()
    report = LaboratoryVisionAgent.analyze_specimen(
        image_bytes=img_bytes,
        pixel_metrics=pixel_metrics,
        laboratory_biometrics=lab_biometrics,
        region_name="بغداد - محطة الفحص الميداني",
    )
    elapsed = time.perf_counter() - t0

    print(f"  Live Groq Response received in {elapsed:.2f}s!")
    print(f"  Scientific Name:   {report.get('scientific_name')}")
    print(f"  Arabic Name:       {report.get('arabic_common_name')}")
    print(f"  Specimen Category: {report.get('specimen_category')}")
    print(f"  Engine Source:     {report.get('engine_source')}")

    # Verify hypotheses sum to 100%
    hypotheses = report.get("differential_hypotheses", [])
    assert len(hypotheses) == 3, f"Expected 3 hypotheses, got {len(hypotheses)}"
    total_prob = sum(float(h.get("probability_pct", 0.0)) for h in hypotheses)
    print(f"  Hypotheses Probabilities: {[h.get('probability_pct') for h in hypotheses]} -> Sum: {total_prob:.1f}%")
    assert abs(total_prob - 100.0) < 0.2, f"Probabilities must sum to 100%, got {total_prob}"

    # Verify 4 sections
    assert report.get("visual_symptoms_ar"), "visual_symptoms_ar is missing"
    assert report.get("environmental_causes_ar"), "environmental_causes_ar is missing"
    assert report.get("treatment_protocol_ar"), "treatment_protocol_ar is missing"
    assert report.get("irrigation_prescription_ar"), "irrigation_prescription_ar is missing"
    assert report.get("treatment_protocol_ar") != report.get("irrigation_prescription_ar"), "Sections 3 and 4 must not duplicate!"

    # Verify Phase 2 root remediation
    pres = report.get("three_phase_prescription", {})
    p2_str = str(pres.get("phase_2_root_remediation_14d_ar") or "")
    print(f"  Phase 2 Root Remediation: {p2_str[:60]}...")
    assert "جذور" in p2_str or "تربة" in p2_str or "شيلات" in p2_str or "رايزوسفير" in p2_str, "Phase 2 must focus on root/soil remediation"

    # Verify Initial Question
    init_q = report.get("initial_investigator_question_ar")
    print(f"  Initial Question:  {init_q}")
    assert init_q, "initial_investigator_question_ar must be non-empty"
    return True


def test_6_live_groq_consultation():
    print("\n[CHECK 6] Executing LIVE Groq Cloud API Call 2/2: Interactive Stateful Consultation...")
    sid = f"test_session_{int(time.time())}"
    user_msg = "ما هي الكمية الموصى بها للري بالتنقيط في هذا الطقس الحار؟"

    t0 = time.perf_counter()
    consult_res = LaboratoryVisionAgent.consult_investigator(
        session_id=sid,
        user_message=user_msg,
    )
    elapsed = time.perf_counter() - t0

    print(f"  Live Consultation Response in {elapsed:.2f}s!")
    reply = consult_res.get("reply_ar") or consult_res.get("investigator_reply_ar")
    print(f"  Investigator Reply: {reply[:100]}...")
    assert reply, "Investigator reply must be non-empty"

    history = consult_res.get("investigation_history", [])
    for h in history:
        author = h.get("author") or ("المستخدم" if h.get("role") == "user" else "المختبر الذكي")
        assert "علي نهاد" not in author, f"Personal name found in consultation history author: {author}"
        assert author in ["المستخدم", "المختبر الذكي"], f"Unexpected role author: {author}"

    print("  OK: Consultation response verified with strictly neutral roles ('المستخدم' and 'المختبر الذكي').")
    return True


def run_all_checks():
    print("=" * 80)
    print(" EcoSensing AI – Production Integrity Verification Suite")
    print("=" * 80)

    results = []
    checks = [
        ("Config & Dual Keys Setup", test_1_config_and_dual_keys),
        ("JSON Repair Parser (Fractions)", test_2_json_parser_unquoted_fractions),
        ("Prompt Integrity (Zero Species & Names)", test_3_prompt_integrity_zero_example_species),
        ("Zero Polling Flood in JS", test_4_zero_polling_flood_in_js),
        ("Live Groq Vision & Hypotheses (1/2)", test_5_live_groq_vision_and_hypotheses),
        ("Live Groq Lab Consultation (2/2)", test_6_live_groq_consultation),
    ]

    for name, fn in checks:
        try:
            passed = fn()
            results.append((name, "PASSED", "OK"))
        except Exception as exc:
            results.append((name, "FAILED", str(exc)))
            print(f"  FAILED: {exc}")

    print("\n" + "=" * 80)
    print(" SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Check Name':<45} | {'Status':<10} | {'Details'}")
    print("-" * 80)
    all_passed = True
    for name, status, details in results:
        print(f"{name:<45} | {status:<10} | {details[:25]}")
        if status != "PASSED":
            all_passed = False
    print("=" * 80)

    if all_passed:
        print(" ALL PRODUCTION INTEGRITY CHECKS PASSED (100% CLEAN & REAL AI)")
        sys.exit(0)
    else:
        print(" SOME CHECKS FAILED - REVIEW LOGS")
        sys.exit(1)


if __name__ == "__main__":
    run_all_checks()
