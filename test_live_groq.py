"""
EcoSensing AI – Live Groq Vision Verification Script
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

import sys
import time
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.ai_engine import EcoSensingAIEngine


def main():
    print("=" * 65)
    print("EcoSensing AI — Standalone Live Groq Vision Verification")
    print("=" * 65)

    sample_path = Path("static/samples/healthy_control_leaf.jpg")
    if not sample_path.exists():
        print(f"Error: Sample file not found at {sample_path}")
        sys.exit(1)

    image_bytes = sample_path.read_bytes()
    print(f"Loaded sample: {sample_path} ({len(image_bytes)} bytes)")

    t0 = time.perf_counter()
    result = EcoSensingAIEngine.analyze_field_sample(image_bytes, region_name="بغداد - محطة الفحص الميداني")
    latency = time.perf_counter() - t0

    print("-" * 65)
    print(f"Latency: {latency:.3f} seconds")
    print(f"Engine Source: {result.get('engine_source')}")
    print(f"Sample Category: {result.get('sample_category_ar')} ({result.get('sample_category')})")
    print(f"Primary Diagnosis: {result.get('primary_diagnosis_title_ar')}")
    print(f"Vitality: {result.get('vitality_pct')}%")
    print(f"Stress: {result.get('stress_pct')}%")
    print(f"Dust / Salinity: {result.get('dust_salinity_pct')}%")
    print(f"Visual Symptoms: {result.get('visual_symptoms_description_ar')}")
    print(f"Probable Causes: {result.get('probable_causes_ar')}")
    print(f"Treatment Protocol: {result.get('treatment_revival_protocol_ar')}")
    print(f"Irrigation Prescription: {result.get('irrigation_recommendation_ar')}")
    print("-" * 65)

    # Verification checks
    assert result.get("engine_source") == "GROQ_LLAMA_VISION_AI", (
        f"Expected engine_source == 'GROQ_LLAMA_VISION_AI', got '{result.get('engine_source')}'"
    )
    assert result.get("dust_salinity_pct") < 1.0, (
        f"Expected dust_salinity_pct < 1.0%, got {result.get('dust_salinity_pct')}%"
    )
    assert result.get("vitality_pct") > 80.0, (
        f"Expected vitality_pct > 80%, got {result.get('vitality_pct')}%"
    )
    assert result.get("primary_diagnosis_title_ar"), "Missing primary_diagnosis_title_ar"

    print("=" * 65)
    print("[SUCCESS] Live Groq Vision verified with 100% compliance!")
    print("=" * 65)


if __name__ == "__main__":
    main()

