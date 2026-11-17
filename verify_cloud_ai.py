"""
Live Cloud Gemini 2.5 Flash API Verification Script
EcoSensing AI - Urban Microclimate & Field Sentinel
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Middle Technical University / Polytechnic College
"""

import sys
import os
import time
import cv2
import numpy as np
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from app.services.ai_engine import EcoSensingAIEngine


def generate_heat_and_dust_leaf_sample() -> bytes:
    """
    Synthesize an in-memory test image of a vegetation sample suffering from
    both high thermal stress and mineral Iraqi dust accumulation.
    """
    img = np.zeros((480, 480, 3), dtype=np.uint8)
    img[:] = (35, 30, 25)

    center = (240, 240)
    axes = (140, 210)

    # Base green leaf with chlorotic warm patches
    cv2.ellipse(img, center, axes, -20, 0, 360, (35, 140, 50), -1)
    cv2.ellipse(img, (270, 200), (50, 80), -20, 0, 360, (25, 175, 210), -1)

    # Mineral dust storm deposition (pale silt-ochre film: BGR ~ 120, 155, 180)
    dust_overlay = img.copy()
    cv2.ellipse(dust_overlay, center, (135, 205), -20, 0, 360, (120, 155, 180), -1)

    # Silt particle noise
    noise = np.random.normal(0, 10, (480, 480, 3)).astype(np.int16)
    dusty_composite = np.clip(dust_overlay.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Apply 70% dust film coverage
    mask = np.zeros((480, 480), dtype=np.uint8)
    cv2.ellipse(mask, center, (135, 205), -20, 0, 360, 255, -1)
    cv2.ellipse(mask, (210, 270), (45, 75), -20, 0, 360, 0, -1)

    result = img.copy()
    result[mask > 0] = cv2.addWeighted(img[mask > 0], 0.25, dusty_composite[mask > 0], 0.75, 0)

    # Leaf vein structure
    cv2.line(result, (150, 370), (320, 120), (18, 90, 30), 3)

    _, encoded = cv2.imencode(".jpg", result, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return encoded.tobytes()


def run_cloud_verification():
    print("=" * 80)
    print("🛰️  EcoSensing AI - Live Cloud Gemini 2.5 Flash Verification")
    print(f"🏛️  Institution: {settings.INSTITUTION}")
    print(f"👤 Project Manager: {settings.AUTHOR}")
    print(f"🔑 API Key Configured: {'YES' if settings.is_gemini_configured() else 'NO'}")
    print(f"🤖 Target Cloud Model: {settings.GEMINI_MODEL}")
    print("=" * 80)

    if not settings.is_gemini_configured():
        print("❌ Error: GEMINI_API_KEY is not configured or is a placeholder in .env!")
        sys.exit(1)

    print("\n[1/3] Generating in-memory test sample (simulated heat & Iraqi dust storm deposition)...")
    sample_bytes = generate_heat_and_dust_leaf_sample()
    print(f"  ✓ Sample generated ({len(sample_bytes)} bytes)")

    print("\n[2/3] Calling EcoSensingAIEngine.analyze_field_sample (Live Cloud Roundtrip)...")
    t0 = time.perf_counter()
    result = EcoSensingAIEngine.analyze_field_sample(
        sample_bytes,
        region_name="بغداد - حقول جامعة التقنية الوسطى / الزعفرانية",
    )
    roundtrip_sec = time.perf_counter() - t0

    ai = result["ai_analysis"]
    metrics = result["pixel_metrics"]
    engine_source = result["engine_source"]

    print("\n[3/3] Live Verification Report:")
    print("-" * 80)
    print(f"  📡 Connection Status: {'LIVE_CLOUD_GEMINI_ONLINE' if 'LIVE_CLOUD' in engine_source or 'GEMINI' in engine_source else 'FALLBACK_OFFLINE'}")
    print(f"  🧠 Model Used: {settings.GEMINI_MODEL}")
    print(f"  🏷️  Engine Source: {engine_source}")
    print(f"  ⏱️  Total Roundtrip Latency: {roundtrip_sec:.3f}s (Engine Internal: {result['inference_time_seconds']:.3f}s)")
    print("-" * 80)
    print(f"  📊 Ground-Truth OpenCV Metrics:")
    print(f"     - Healthy Green Canopy: {metrics['green_canopy_pct']}%")
    print(f"     - Iraqi Dust Index: {metrics['iraqi_dust_index_pct']}%")
    print(f"     - Water Stress Yellow: {metrics['water_stress_yellow_pct']}%")
    print(f"     - Calibrated Surface Temp: {metrics['estimated_surface_temp_c']} °C")
    print("-" * 80)
    print(f"  🩺 Cloud Gemini 2.5 Flash Diagnosis:")
    print(f"     - Diagnosis Code: {ai.get('diagnosis_code')}")
    print(f"     - Diagnosis Title (AR): {ai.get('diagnosis_title_ar')}")
    print(f"     - Dust Accumulation: {ai.get('dust_accumulation_pct')}%")
    print(f"     - Water Stress Index: {ai.get('water_stress_index_pct')}%")
    print(f"     - Surface Temp Before / After: {ai.get('estimated_lst_before_c')} °C -> {ai.get('estimated_lst_after_c')} °C")
    
    cooling_potential = round(float(ai.get('estimated_lst_before_c', 0.0)) - float(ai.get('estimated_lst_after_c', 0.0)), 2)
    print(f"     - LST Cooling Potential: {cooling_potential} °C drop")
    print(f"     - Expected Water Saving: {ai.get('expected_water_saving_pct')}%")
    print(f"     - Early Damage Risk: {ai.get('early_damage_risk_before_pct')}% -> {ai.get('early_damage_risk_after_pct')}%")
    print(f"\n  🌱 Arabic Agronomic Recommendation:\n     \"{ai.get('recommended_irrigation_action_ar')}\"")
    print("-" * 80)

    # Verification assertions
    is_live = "LIVE_CLOUD" in engine_source or "GEMINI" in engine_source
    if is_live:
        print("\n✅ SUCCESS: Live Cloud Gemini API is ONLINE and fully operational!")
        
        # Warm Production Roundtrip Benchmark
        print("\n[WARM CACHE PRODUCTION BENCHMARK]")
        t_warm0 = time.perf_counter()
        warm_res = EcoSensingAIEngine.analyze_field_sample(sample_bytes, region_name="بغداد - محطة الفحص 2")
        warm_roundtrip = time.perf_counter() - t_warm0
        print(f"  ⚡ Warm Engine Roundtrip: {warm_roundtrip:.3f}s (Guaranteed < 3.0s: {warm_roundtrip < 3.0})")
        print(f"  🏷️  Engine Source: {warm_res['engine_source']}")
    else:
        print("\n⚠️ WARNING: Fallback was triggered. Inspect connection/credentials.")

    print("=" * 80)


if __name__ == "__main__":
    run_cloud_verification()
