"""
verify_architectural_repairs.py
===============================
Verification test suite for EcoSensing AI Architectural Repairs & Upgrades:
1. Top Header Cleanup (No university banner, executive minimalist navbar).
2. Genuine AI & CV Rooftop vs Barren Soil Classification (Zero trees for roof, REJECTED_BUILDING_OR_ROAD).
3. Direct GPS Coordinates Search & Baghdad Landmark Gazetteer Verification.
4. Solar Rooftop Cleanup (Zero cooling bonus, Zero emojis, Verified financial metrics).
5. Iraqi Context Chatbot Conversational Response for Site Planting.

Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

import sys
import io
import time
import re

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import LandInspectionRequest, SolarCalculationRequest, ChatbotRequest
from app.services.land_suitability import LandSuitabilityClassifier
from app.services.weather_geo_service import WeatherAndGeoIntelligenceService, _BAGHDAD_GAZETTEER
from app.services.solar_engine import SolarRooftopAndGeneratorEngine
from app.services.chatbot_engine import IraqiContextChatbotEngine

client = TestClient(app)

PASS = 0
FAIL = 0
results: list[tuple[str, bool, str, float]] = []

def register(name):
    def decorator(fn):
        def wrapper():
            global PASS, FAIL
            t0 = time.perf_counter()
            try:
                fn()
                elapsed = time.perf_counter() - t0
                results.append((name, True, '', elapsed))
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
# 1. HEADER CLEANUP TESTS
# ═════════════════════════════════════════════════════════════════════════════

@register("Header: Top navbar contains ONLY workspace selector, status pill, and clock")
def test_header_minimalist():
    r = client.get('/')
    assert r.status_code == 200
    html = r.text
    # Extract execHeader content
    m = re.search(r'<header id="execHeader">([\s\S]*?)</header>', html)
    assert m is not None, "execHeader not found"
    header_content = m.group(1)

    # University name and large project title MUST be completely removed from header
    assert "الجامعة التقنية الوسطى" not in header_content, "University banner still in top header!"
    assert "كلية البوليتكنك" not in header_content, "Polytechnic banner still in top header!"
    assert "<h1>" not in header_content, "Large project title h1 still in top header!"

    # Must contain dropdown selector
    assert 'id="workspaceDropdown"' in header_content, "workspaceDropdown missing from header"
    assert "اختر المنظومة الفعالة ▾" in header_content, "Dropdown selector prompt missing"

    # Must contain live status pill
    assert 'id="liveStatusPill"' in header_content or "live-status-pill" in header_content, "Status pill missing"
    assert "السيرفر: متصل" in header_content, "Server connected text missing from status pill"
    assert "سحابة الذكاء الاصطناعي: نشطة" in header_content, "AI cloud active text missing"

    # Must contain clock
    assert 'id="headerClock"' in header_content, "Clock missing from header"


# ═════════════════════════════════════════════════════════════════════════════
# 2. GENUINE AI & CV ROOFTOP VS BARREN SOIL CLASSIFICATION
# ═════════════════════════════════════════════════════════════════════════════

@register("CV/AI: Residential house (180 m² in Baghdad) rejected as building roof")
def test_residential_house_rejected():
    req = LandInspectionRequest(
        lat=33.3152,
        lon=44.3661,
        location_name_ar="حي سكني في بغداد",
        custom_area_m2=180.0,  # Standard Baghdad residential parcel
    )
    result = LandSuitabilityClassifier.inspect_land(req)

    assert result.suitability_code == "REJECTED_BUILDING_OR_ROAD", \
        f"Expected REJECTED_BUILDING_OR_ROAD, got {result.suitability_code}"
    assert result.can_plant_trees is False, "can_plant_trees must be False for residential roof"
    assert result.suggest_solar_rooftop_mode is True, "suggest_solar_rooftop_mode must be True for roof"
    assert len(result.valid_tree_nodes) == 0, \
        f"ZERO tree nodes must be plotted over building roofs, got {len(result.valid_tree_nodes)}"

    # Check exact Arabic verdict text
    expected_explanation_part = "الموقع المحدد هو سطح مبنى سكني/خرساني غير صالح للزراعة المباشرة فوق الصبة"
    assert expected_explanation_part in result.suitability_explanation_ar, \
        f"Verdict explanation mismatch: {result.suitability_explanation_ar}"


@register("CV/AI: Open agricultural plot (10,000 m²) accepted as barren plantable land")
def test_barren_land_accepted():
    req = LandInspectionRequest(
        lat=33.2200,
        lon=44.2500,
        location_name_ar="أطراف بغداد الزراعية",
        custom_area_m2=10000.0,
    )
    result = LandSuitabilityClassifier.inspect_land(req)

    assert result.suitability_code == "SUITABLE_BARREN_LAND", \
        f"Expected SUITABLE_BARREN_LAND, got {result.suitability_code}"
    assert result.can_plant_trees is True, "can_plant_trees must be True for barren soil"
    assert result.suggest_solar_rooftop_mode is False, "suggest_solar_rooftop_mode must be False"
    assert len(result.valid_tree_nodes) > 0, "Must generate tree nodes for plantable barren land"


# ═════════════════════════════════════════════════════════════════════════════
# 3. DIRECT GPS COORDINATES & GAZETTEER VERIFICATION
# ═════════════════════════════════════════════════════════════════════════════

@register("Search: Direct GPS coordinates parsing ('33.2410, 44.4760')")
def test_search_direct_coordinates():
    results = WeatherAndGeoIntelligenceService.search_places("33.2410, 44.4760")
    assert len(results) >= 1, "Must return coordinate result"
    top = results[0]
    assert top["source"] == "DIRECT_COORDINATES", f"Expected DIRECT_COORDINATES, got {top.get('source')}"
    assert top["score"] >= 2.0, "Coordinate result must have top priority score"
    assert abs(top["lat"] - 33.2410) < 0.0001
    assert abs(top["lon"] - 44.4760) < 0.0001


@register("Search: Space-separated coordinates ('33.3622 44.4055')")
def test_search_space_separated_coordinates():
    results = WeatherAndGeoIntelligenceService.search_places("33.3622 44.4055")
    assert len(results) >= 1
    top = results[0]
    assert top["source"] == "DIRECT_COORDINATES"
    assert abs(top["lat"] - 33.3622) < 0.0001
    assert abs(top["lon"] - 44.4055) < 0.0001


@register("Gazetteer: MTU / Polytechnic verified at exact [33.2410, 44.4760] in Al-Za'franiyah")
def test_gazetteer_mtu_zafraniyah():
    mtu = [p for p in _BAGHDAD_GAZETTEER if "التقنية الوسطى" in p["name_ar"]]
    assert len(mtu) >= 1, "MTU not found in gazetteer"
    assert abs(mtu[0]["lat"] - 33.2410) < 0.0001, f"MTU lat incorrect: {mtu[0]['lat']}"
    assert abs(mtu[0]["lon"] - 44.4760) < 0.0001, f"MTU lon incorrect: {mtu[0]['lon']}"


@register("Gazetteer: Palestine St, Mustansiriyah, Karrada, Mansour, Jadriya coordinates")
def test_gazetteer_landmarks():
    places = {p["name_ar"]: (p["lat"], p["lon"]) for p in _BAGHDAD_GAZETTEER}

    # Palestine Street [33.3622, 44.4055]
    pal = [v for k, v in places.items() if "فلسطين" in k]
    assert pal and abs(pal[0][0] - 33.3622) < 0.001 and abs(pal[0][1] - 44.4055) < 0.001

    # Mustansiriyah [33.3645, 44.4080]
    mus = [v for k, v in places.items() if "المستنصرية" in k]
    assert mus and abs(mus[0][0] - 33.3645) < 0.001 and abs(mus[0][1] - 44.4080) < 0.001

    # Karrada [33.3050, 44.4250]
    kar = [v for k, v in places.items() if "الكرادة داخل / خارج" in k]
    assert kar and abs(kar[0][0] - 33.3050) < 0.001 and abs(kar[0][1] - 44.4250) < 0.001

    # Mansour 14 Ramadan [33.3160, 44.3415]
    man = [v for k, v in places.items() if "14 رمضان" in k or "المنصور /" in k]
    assert man and abs(man[0][0] - 33.3160) < 0.001 and abs(man[0][1] - 44.3415) < 0.001

    # Jadriya / University of Baghdad [33.2745, 44.3802]
    jad = [v for k, v in places.items() if "الجادرية / جامعة بغداد" in k]
    assert jad and abs(jad[0][0] - 33.2745) < 0.001 and abs(jad[0][1] - 44.3802) < 0.001


# ═════════════════════════════════════════════════════════════════════════════
# 4. SOLAR ROOFTOP CLEANUP & ZERO EMOJIS
# ═════════════════════════════════════════════════════════════════════════════

@register("Solar: Roof cooling bonus completely removed (0.0)")
def test_solar_no_cooling_bonus():
    req = SolarCalculationRequest(
        roof_area_m2=180.0,
        required_amperes=12.0,
        ampere_price_iqd=15000.0,
        months_count=12,
    )
    result = SolarRooftopAndGeneratorEngine.calculate_solar_roi(req)

    # Cooling bonus MUST be 0.0
    assert result.ac_cooling_bonus_saved_iqd == 0.0, \
        f"ac_cooling_bonus_saved_iqd must be 0.0, got {result.ac_cooling_bonus_saved_iqd}"

    # Total savings must equal pure generator subscription savings
    expected_gen_savings = 12.0 * 15000.0 * 12
    assert result.total_financial_savings_period_iqd == expected_gen_savings, \
        f"Total savings {result.total_financial_savings_period_iqd} != generator savings {expected_gen_savings}"

    # Cooling text not in report
    assert "تبريد السقف" not in result.executive_solar_report_ar, "Roof cooling bonus text found in solar report!"
    assert "مكافأة تبريد" not in result.executive_solar_report_ar, "Cooling bonus text found in solar report!"


@register("Solar: ZERO emojis in engineering report")
def test_solar_zero_emojis_in_report():
    req = SolarCalculationRequest(roof_area_m2=200.0, required_amperes=15.0)
    result = SolarRooftopAndGeneratorEngine.calculate_solar_roi(req)
    rep = result.executive_solar_report_ar

    # Test for common emojis that were previously present
    forbidden_emojis = ["🔆", "📐", "⚡", "☀️", "💰", "🌍", "✅", "⚠️", "🔥", "🌱", "💧"]
    found = [e for e in forbidden_emojis if e in rep]
    assert len(found) == 0, f"Emojis found in solar report: {found}"


@register("Solar: Verified financial metrics present")
def test_solar_metrics_present():
    req = SolarCalculationRequest(roof_area_m2=150.0, required_amperes=10.0)
    result = SolarRooftopAndGeneratorEngine.calculate_solar_roi(req)

    assert result.roof_area_m2 == 150.0
    assert result.usable_roof_area_m2 > 0
    assert result.recommended_panels_count >= 1
    assert result.generated_amperes_iraqi_220v > 0
    assert result.generator_subscription_saved_iqd > 0
    assert result.total_panels_cost_iqd > 0
    assert result.total_system_estimated_cost_iqd > result.total_panels_cost_iqd
    assert result.payback_period_months > 0


# ═════════════════════════════════════════════════════════════════════════════
# 5. CHATBOT CONVERSATIONAL SITE PLANTING QUERY
# ═════════════════════════════════════════════════════════════════════════════

@register("Chatbot: 'شنو رايك بل موقع محدد هل ازرع بيها؟' with rooftop selected")
def test_chatbot_roof_planting_verdict():
    req = ChatbotRequest(
        message="شنو رايك بل موقع محدد هل ازرع بيها؟",
        active_section="afforestation",
        live_telemetry={
            "total_selected_area_m2": 200,
            "suitability_code": "REJECTED_BUILDING_OR_ROAD",
            "solar_amps": 12,
            "generated_amperes_iraqi_220v": 12,
        },
        history=[],
    )
    res = IraqiContextChatbotEngine.chat(req)
    reply = res.reply_ar
    print(f"\n    [INFO] Chatbot reply for roof: {reply}")

    # Must state that this is a concrete building roof that cannot be planted with trees, but suitable for solar
    assert "سطح مبنى" in reply or "صبة كونكريتية" in reply or "صبة" in reply, "Chatbot failed to recognize concrete roof"
    assert "طاقة شمسية" in reply or "أمبير" in reply or "المولدة" in reply, "Chatbot failed to suggest solar generator replacement"


@register("Chatbot: 'شنو رايك بل موقع محدد هل ازرع بيها؟' with barren soil selected")
def test_chatbot_barren_planting_verdict():
    req = ChatbotRequest(
        message="شنو رايك بل موقع محدد هل ازرع بيها؟",
        active_section="afforestation",
        live_telemetry={
            "total_selected_area_m2": 5000,
            "total_selected_area_dunums": 2.0,
            "suitability_code": "SUITABLE_BARREN_LAND",
        },
        history=[],
    )
    res = IraqiContextChatbotEngine.chat(req)
    reply = res.reply_ar
    print(f"\n    [INFO] Chatbot reply for barren soil: {reply}")

    # Must encourage planting trees like Sidr/Neem
    assert "أرض جرداء" in reply or "السدر" in reply or "النبق" in reply or "صالح" in reply or "زراعة" in reply, \
        "Chatbot failed to recommend planting on barren land"


# ═════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═════════════════════════════════════════════════════════════════════════════

def run_all():
    print("=" * 70)
    print("EcoSensing AI — Architectural Repairs Verification Suite")
    print("=" * 70)

    test_header_minimalist()
    test_residential_house_rejected()
    test_barren_land_accepted()
    test_search_direct_coordinates()
    test_search_space_separated_coordinates()
    test_gazetteer_mtu_zafraniyah()
    test_gazetteer_landmarks()
    test_solar_no_cooling_bonus()
    test_solar_zero_emojis_in_report()
    test_solar_metrics_present()
    test_chatbot_roof_planting_verdict()
    test_chatbot_barren_planting_verdict()

    print("=" * 70)
    print(f"Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
    print("=" * 70)

    if FAIL > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_all()
