"""
verify_master_upgrade.py
========================
Master Architectural Rebuild Verification Suite for EcoSensing AI:
1. Groq API Connectivity (Llama 3.3 70B & Active Groq Engine).
2. Genuine Leaf Vision Inference & Authentic Base64 Heatmaps.
3. Multi-Feature Land Suitability & Rooftop Rejection (0 Trees).
4. Pure Solar Calculations (0 Cooling Bonus, 0 Emojis, Strict Dual Input).
5. Dynamic Place Search & Direct Coordinates Parser.
6. Minimalist 2.5D Top Header Purge.
7. Iraqi Context-Aware Telemetry Grounded Chatbot.

Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

import io
import re
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.models.schemas import (
    ChatbotRequest,
    LandInspectionRequest,
    SolarCalculationRequest,
)
from app.services.ai_engine import EcoSensingAIEngine
from app.services.chatbot_engine import IraqiContextChatbotEngine
from app.services.land_suitability import LandSuitabilityClassifier
from app.services.solar_engine import SolarRooftopAndGeneratorEngine
from app.services.weather_geo_service import WeatherAndGeoIntelligenceService

client = TestClient(app)

PASS = 0
FAIL = 0
results: list[tuple[str, bool, str, float]] = []


def register(name: str):
    def decorator(fn):
        def wrapper():
            global PASS, FAIL
            t0 = time.perf_counter()
            try:
                fn()
                elapsed = time.perf_counter() - t0
                results.append((name, True, "", elapsed))
                PASS += 1
                print(f"  [PASS] {name} [{elapsed:.3f}s]")
            except Exception as e:
                elapsed = time.perf_counter() - t0
                msg = str(e)
                results.append((name, False, msg, elapsed))
                FAIL += 1
                print(f"  [FAIL] {name} [{elapsed:.3f}s]")
                print(f"         Error: {msg}")
        return wrapper
    return decorator


# ═════════════════════════════════════════════════════════════════════════════
# 1. GROQ API CONNECTIVITY
# ═════════════════════════════════════════════════════════════════════════════

@register("Groq API: Official Key Connectivity & Fast Inference")
def test_groq_connectivity():
    from groq import Groq
    assert settings.is_groq_configured(), "GROQ_API_KEY is missing or placeholder!"
    groq_client = Groq(api_key=settings.GROQ_API_KEY)

    models_to_try = [
        settings.GROQ_MODEL,
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "allam-2-7b",
    ]
    response_text = None
    used_model = None

    for m in models_to_try:
        try:
            res = groq_client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "Hello! Confirm EcoSensing AI operational."}],
                max_tokens=50,
            )
            if res and res.choices and res.choices[0].message.content:
                response_text = res.choices[0].message.content
                used_model = m
                break
        except Exception:
            continue

    assert response_text is not None, "Failed to get response from Groq API!"
    assert len(response_text) > 0, "Empty response from Groq!"
    print(f"\n    [Groq Active Model: {used_model}]")


# ═════════════════════════════════════════════════════════════════════════════
# 2. COMPUTER VISION LEAF LAB & BASE64 HEATMAPS
# ═════════════════════════════════════════════════════════════════════════════

@register("Leaf Vision: Authentic Base64 Heatmaps & Pixel Metrics")
def test_leaf_vision_inference():
    # Test healthy leaf
    r_healthy = client.post("/api/analyze-image?sample_type=healthy")
    assert r_healthy.status_code == 200, f"Status: {r_healthy.status_code}"
    data_h = r_healthy.json()
    assert data_h["diagnosis_code"] == "OPTIMAL_HEALTH"
    assert data_h["thermal_image_b64"].startswith("data:image/jpeg;base64,")
    assert data_h["spectral_image_b64"].startswith("data:image/jpeg;base64,")
    metrics_h = data_h["pixel_metrics"]
    assert metrics_h["green_canopy_pct"] > 0.0
    assert metrics_h["calibrated_surface_temp_c"] >= 30.0

    # Test dusty leaf
    r_dust = client.post("/api/analyze-image?sample_type=dust")
    assert r_dust.status_code == 200
    data_d = r_dust.json()
    assert data_d["diagnosis_code"] == "DUST_THERMAL_SUFFOCATION"
    assert "رش ضبابي" in data_d["irrigation_prescription_ar"]
    assert data_d["pixel_metrics"]["iraqi_dust_index_pct"] > 0.5

    # Test water stressed leaf
    r_water = client.post("/api/analyze-image?sample_type=water_stress")
    assert r_water.status_code == 200
    data_w = r_water.json()
    assert data_w["diagnosis_code"] == "ROOT_WATER_STRESS"
    assert "ري جذوري دقيق" in data_w["irrigation_prescription_ar"]
    assert data_w["pixel_metrics"]["water_stress_yellow_pct"] > 2.0


# ═════════════════════════════════════════════════════════════════════════════
# 3. LAND SUITABILITY & ROOFTOP REJECTION
# ═════════════════════════════════════════════════════════════════════════════

@register("Land Suitability: Building Rooftop Rejected with 0 Trees")
def test_land_suitability_rejection():
    req = LandInspectionRequest(
        lat=33.3152,
        lon=44.3661,
        location_name_ar="سقف مبنى في بغداد",
        custom_area_m2=180.0,
    )
    res = LandSuitabilityClassifier.inspect_land(req)

    assert res.suitability_code == "REJECTED_BUILDING_OR_ROAD"
    assert res.can_plant_trees is False
    assert res.suggest_solar_rooftop_mode is True
    assert len(res.valid_tree_nodes) == 0, f"Expected 0 trees on roof, got {len(res.valid_tree_nodes)}"
    assert res.net_plantable_area_m2 == 0.0
    assert "سقف مبنى" in res.suitability_explanation_ar or "صبة" in res.suitability_explanation_ar

    # Test open barren land
    req_barren = LandInspectionRequest(
        lat=33.2200,
        lon=44.2500,
        location_name_ar="أرض جرداء في أطراف بغداد",
        custom_area_m2=5000.0,
    )
    res_barren = LandSuitabilityClassifier.inspect_land(req_barren)
    assert res_barren.suitability_code == "SUITABLE_BARREN_LAND"
    assert res_barren.can_plant_trees is True
    assert len(res_barren.valid_tree_nodes) > 0


# ═════════════════════════════════════════════════════════════════════════════
# 4. SOLAR ROOFTOP ENGINE
# ═════════════════════════════════════════════════════════════════════════════

@register("Solar Engine: 0 Cooling Bonus, 0 Emojis, Exact Payback")
def test_solar_calculations():
    req = SolarCalculationRequest(
        roof_area_m2=180.0,
        required_amperes=12.0,
        ampere_price_iqd=15000.0,
        months_count=12,
        panel_unit_price_iqd=165000.0,
    )
    res = SolarRooftopAndGeneratorEngine.calculate_solar_roi(req)

    # 1. Zero cooling bonus
    assert res.ac_cooling_bonus_saved_iqd == 0.0
    assert res.roof_shading_temp_drop_c == 0.0

    # 2. Generator savings = amps * price * months
    expected_savings = 12.0 * 15000.0 * 12
    assert res.total_financial_savings_period_iqd == expected_savings

    # 3. Payback period = total_system_cost / monthly_savings
    monthly_sav = 12.0 * 15000.0
    expected_payback = round(res.total_system_estimated_cost_iqd / monthly_sav, 1)
    assert res.payback_period_months == expected_payback

    # 4. Zero emojis in report
    forbidden_emojis = ["🔆", "📐", "⚡", "☀️", "💰", "🌍", "✅", "⚠️", "🔥", "🌱", "💧"]
    found = [e for e in forbidden_emojis if e in res.executive_solar_report_ar]
    assert len(found) == 0, f"Found emojis: {found}"


# ═════════════════════════════════════════════════════════════════════════════
# 5. DYNAMIC SEARCH & DIRECT GPS COORDINATES
# ═════════════════════════════════════════════════════════════════════════════

@register("Search: Direct GPS Coordinates & Live Search Engine")
def test_search_and_geocoding():
    # Direct coordinates
    res_coords = WeatherAndGeoIntelligenceService.search_places("33.2410, 44.4760")
    assert len(res_coords) >= 1
    assert res_coords[0]["source"] == "DIRECT_COORDINATES"
    assert abs(res_coords[0]["lat"] - 33.2410) < 0.001
    assert abs(res_coords[0]["lon"] - 44.4760) < 0.001

    # Live place search (Middle Technical University in Baghdad)
    res_places = WeatherAndGeoIntelligenceService.search_places("الجامعة التقنية الوسطى")
    assert len(res_places) >= 1
    assert "التقنية" in res_places[0]["name_ar"] or "الوسطى" in res_places[0]["name_ar"]


# ═════════════════════════════════════════════════════════════════════════════
# 6. HEADER PURGE & MINIMALIST 2.5D NAVBAR
# ═════════════════════════════════════════════════════════════════════════════

@register("Header: Minimalist Top Strip without University Banner")
def test_header_purge():
    r = client.get("/")
    assert r.status_code == 200
    html = r.text

    m = re.search(r'<header id="execHeader">([\s\S]*?)</header>', html)
    assert m is not None, "execHeader not found"
    header_content = m.group(1)

    assert "الجامعة التقنية الوسطى" not in header_content
    assert "كلية البوليتكنك" not in header_content
    assert "<h1>" not in header_content

    assert 'id="workspaceDropdown"' in header_content
    assert "اختر المنظومة الفعالة ▾" in header_content
    assert 'id="liveStatusPill"' in header_content
    assert "Llama-3.3-70B" in header_content or "نشط" in header_content
    assert 'id="headerClock"' in header_content


# ═════════════════════════════════════════════════════════════════════════════
# 7. IRAQI CONTEXT-AWARE CHATBOT
# ═════════════════════════════════════════════════════════════════════════════

@register("Chatbot: Grounded Iraqi Advice for Rooftop vs Barren Soil")
def test_iraqi_chatbot():
    # Rooftop inquiry
    r_roof = IraqiContextChatbotEngine.chat(ChatbotRequest(
        message="شنو رايك بل موقع محدد هل ازرع بيها؟",
        active_section="afforestation",
        live_telemetry={
            "total_selected_area_m2": 250,
            "suitability_code": "REJECTED_BUILDING_OR_ROAD",
            "solar_amps": 15,
        },
    ))
    reply_r = r_roof.reply_ar
    assert ("سطح مبنى" in reply_r or "صبة" in reply_r), "Chatbot should state this is a roof"
    assert ("شمسية" in reply_r or "أمبير" in reply_r or "مولدة" in reply_r), "Chatbot should recommend solar"

    # Barren land inquiry
    r_barren = IraqiContextChatbotEngine.chat(ChatbotRequest(
        message="شنو رايك بل موقع محدد هل ازرع بيها؟",
        active_section="afforestation",
        live_telemetry={
            "total_selected_area_m2": 5000,
            "total_selected_area_dunums": 2.0,
            "suitability_code": "SUITABLE_BARREN_LAND",
        },
    ))
    reply_b = r_barren.reply_ar
    assert ("أرض جرداء" in reply_b or "صالح" in reply_b or "السدر" in reply_b or "زراعة" in reply_b)


# ═════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═════════════════════════════════════════════════════════════════════════════

def run_all():
    print("=" * 70)
    print("EcoSensing AI — Master Architectural Upgrade Verification Suite")
    print("=" * 70)

    test_groq_connectivity()
    test_leaf_vision_inference()
    test_land_suitability_rejection()
    test_solar_calculations()
    test_search_and_geocoding()
    test_header_purge()
    test_iraqi_chatbot()

    print("=" * 70)
    print(f"Master Verification Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
    print("=" * 70)

    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()

