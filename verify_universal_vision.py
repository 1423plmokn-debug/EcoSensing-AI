"""
EcoSensing AI – Universal 4-Scene Agro-Ecological Vision & Diagnostic Test Suite
Verification of 100% Groq Vision Architecture, Foreground Isolation, & REST Endpoints.

Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Academic Affiliation: Middle Technical University / Polytechnic College
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app
from app.services.ai_engine import EcoSensingAIEngine
from app.services.chatbot_engine import IraqiContextChatbotEngine
from app.models.schemas import ChatbotRequest
from app.services.vision_filter import VisionFilterEngine


def print_header(title: str):
    sep = "=" * 70
    print(sep)
    print(f"  {title}")
    print(sep)


def test_groq_vision_multimodal():
    """Test Groq Vision multimodal API call using an in-memory synthetic sample."""
    t0 = time.perf_counter()
    assert settings.is_groq_configured(), "GROQ_API_KEY must be configured."

    # Create synthetic test plant image (> 32x32 pixels)
    img = Image.new("RGB", (128, 128), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()

    result = EcoSensingAIEngine.analyze_field_sample(image_bytes, region_name="بغداد - اختبار الحقل")
    dt = time.perf_counter() - t0

    assert "sample_category" in result, "Missing sample_category in result"
    assert "primary_diagnosis_title_ar" in result, "Missing primary_diagnosis_title_ar"
    assert "treatment_revival_protocol_ar" in result, "Missing treatment_revival_protocol_ar"
    assert "irrigation_recommendation_ar" in result, "Missing irrigation_recommendation_ar"
    assert result["sample_category"] in ["LEAF", "TREE", "TURFGRASS", "SOIL"], f"Invalid category: {result['sample_category']}"
    assert "thermal_image_b64" in result and result["thermal_image_b64"].startswith("data:image/jpeg;base64,"), "Invalid thermal_image_b64"
    assert "spectral_image_b64" in result and result["spectral_image_b64"].startswith("data:image/jpeg;base64,"), "Invalid spectral_image_b64"

    print(f"  [PASS] Groq Vision Multimodal Inference ({result['engine_source']}) [{dt:.3f}s]")


def test_foreground_isolation_and_opencv_filters():
    """Test leaf foreground isolation, skin exclusion, and OpenCV thermal/spectral generation."""
    t0 = time.perf_counter()

    # Load authentic healthy leaf
    sample_path = Path("static/samples/healthy_control_leaf.jpg")
    assert sample_path.exists(), f"Sample {sample_path} not found."
    image_bytes = sample_path.read_bytes()

    res = VisionFilterEngine.process_image(image_bytes)
    metrics = res["pixel_metrics"]

    assert "green_vitality_pct" in metrics, "Missing green_vitality_pct"
    assert "stress_drought_yellow_pct" in metrics, "Missing stress_drought_yellow_pct"
    assert "dust_salinity_pct" in metrics, "Missing dust_salinity_pct"
    assert "calibrated_surface_temp_c" in metrics, "Missing calibrated_surface_temp_c"

    # Healthy leaf should have high green vitality and low dust/stress
    assert metrics["green_vitality_pct"] > 60.0, f"Expected green_vitality_pct > 60, got {metrics['green_vitality_pct']}"
    assert metrics["dust_salinity_pct"] < 5.0, f"Expected dust_salinity_pct < 5, got {metrics['dust_salinity_pct']}"
    assert metrics["stress_drought_yellow_pct"] < 5.0, f"Expected stress_drought_yellow_pct < 5, got {metrics['stress_drought_yellow_pct']}"

    # Verify thermal and spectral data URIs
    assert res["thermal_image_b64"].startswith("data:image/jpeg;base64,"), "thermal_image_b64 malformed"
    assert res["spectral_image_b64"].startswith("data:image/jpeg;base64,"), "spectral_image_b64 malformed"

    dt = time.perf_counter() - t0
    print(f"  [PASS] OpenCV Foreground Isolation & True Metrics (Green: {metrics['green_vitality_pct']}%) [{dt:.3f}s]")


def test_api_analyze_endpoints():
    """Test both POST /api/analyze-image and POST /api/analyze endpoints with file uploads & sample_type."""
    t0 = time.perf_counter()
    client = TestClient(app)

    # 1. Test POST /api/analyze-image with multipart file upload
    sample_path = Path("static/samples/healthy_control_leaf.jpg")
    with open(sample_path, "rb") as f:
        resp = client.post(
            "/api/analyze-image",
            files={"image": ("test_leaf.jpg", f, "image/jpeg")},
            data={"region_name": "بغداد — محطة الزعفرانية"},
        )
    assert resp.status_code == 200, f"POST /api/analyze-image failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "sample_category" in data, "Missing sample_category in API response"
    assert "primary_diagnosis_title_ar" in data, "Missing primary_diagnosis_title_ar"
    assert "thermal_image_b64" in data, "Missing thermal_image_b64"

    # 2. Test POST /api/analyze with sample_type query param
    for s_type in ["dust", "water_stress", "turfgrass", "soil"]:
        resp2 = client.post(f"/api/analyze?sample_type={s_type}")
        assert resp2.status_code == 200, f"POST /api/analyze?sample_type={s_type} failed: {resp2.status_code} {resp2.text}"
        data2 = resp2.json()
        assert "sample_category" in data2, f"Missing sample_category for {s_type}"
        assert "treatment_revival_protocol_ar" in data2, f"Missing treatment for {s_type}"

    dt = time.perf_counter() - t0
    print(f"  [PASS] REST Endpoints POST /api/analyze-image & POST /api/analyze (5 Scenes Verified) [{dt:.3f}s]")


def test_zero_gemini_architecture_compliance():
    """Verify 0% Gemini dependencies across active config, routes, and health check."""
    t0 = time.perf_counter()
    client = TestClient(app)

    # Verify /api/health
    resp = client.get("/api/health")
    assert resp.status_code == 200, "Health check failed"
    data = resp.json()
    assert data["is_groq_configured"] is True, "Groq must be configured in health check"
    assert "active_groq_vision_model" in data, "active_groq_vision_model must be in health check"
    assert "active_gemini_model" not in data, "active_gemini_model must be purged from health check"
    assert "is_cloud_gemini_configured" not in data, "is_cloud_gemini_configured must be purged"

    # Verify .env has no active GEMINI_API_KEY
    env_content = Path(".env").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" not in env_content, "GEMINI_API_KEY must not exist in .env"

    dt = time.perf_counter() - t0
    print(f"  [PASS] Zero-Gemini Architecture Compliance (100% Groq, 0% Gemini) [{dt:.3f}s]")


def test_floating_chatbot_vision_telemetry():
    """Verify chatbot answers questions about diagnosed vision samples using injected telemetry."""
    t0 = time.perf_counter()

    req = ChatbotRequest(
        message="شنو علاج هاي الشجرة أو الثيل اللي فحصته؟",
        active_section="vision",
        live_telemetry={
            "vision_diagnosis": {
                "sample_category_ar": "مسطح ثيل حدائق",
                "primary_diagnosis_title_ar": "احتراق حراري وتملح بقعي للثيل",
                "treatment_revival_protocol_ar": "1. تهوية الجذور (Aeration).\n2. تسميد بسماد بوتاسي عالي.",
                "irrigation_recommendation_ar": "ري في الساعة 5 فجراً لتوفير 37% مياه.",
            }
        },
    )

    resp = IraqiContextChatbotEngine.chat(req)
    assert resp.reply_ar and len(resp.reply_ar) > 30, "Chatbot reply too short"
    assert resp.engine_source and ("GROQ" in resp.engine_source or "DETERMINISTIC" in resp.engine_source), f"Unexpected source: {resp.engine_source}"

    # Check that it referenced the turfgrass / treatment context
    assert any(w in resp.reply_ar for w in ["ثيل", "العينة", "علاج", "الري", "بوتاسي", "فحص"]), "Chatbot failed to reference vision diagnosis"

    dt = time.perf_counter() - t0
    print(f"  [PASS] Floating Chatbot Grounded Agronomic Advice ({resp.engine_source}) [{dt:.3f}s]")


def main():
    print_header("EcoSensing AI — Universal 4-Scene Vision Verification Suite")
    tests = [
        ("Groq Vision Multimodal", test_groq_vision_multimodal),
        ("Foreground Isolation & OpenCV", test_foreground_isolation_and_opencv_filters),
        ("API REST Endpoints", test_api_analyze_endpoints),
        ("Zero-Gemini Architecture", test_zero_gemini_architecture_compliance),
        ("Chatbot Telemetry Grounding", test_floating_chatbot_vision_telemetry),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {name}: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 70)
    print(f"Universal Vision Verification Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

