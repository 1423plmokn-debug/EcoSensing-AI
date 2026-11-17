"""
EcoSensing AI – Verification Suite
LocationIQ 2.5D Engine & Specialized AI Agents Verification
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

import os
import re
import sys
from pathlib import Path

# Ensure UTF-8 output encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import EMOJI_REGEX, settings, strip_all_emojis
from app.models.schemas import LandInspectionRequest
from app.services.pedological_agent import PedologicalBotanicalAgent
from app.services.pollution_agent import GlobalPollutionResearchAgent
from app.services.weather_geo_service import WeatherAndGeoIntelligenceService


def test_zero_leaflet_solar_emoji():
    print("[TEST 1] Verifying Zero Leaflet / Zero Solar / Zero Emoji in static files...")

    index_html = Path("static/index.html").read_text(encoding="utf-8")
    dashboard_js = Path("static/js/dashboard.js").read_text(encoding="utf-8")

    # 1. No Leaflet
    assert "leaflet.js" not in index_html, "Found leaflet.js in static/index.html"
    assert "leaflet.css" not in index_html, "Found leaflet.css in static/index.html"
    assert not re.search(r"\bL\.", dashboard_js), "Found L. (Leaflet) in static/js/dashboard.js"
    print("  -> Passed: Zero Leaflet in index.html and dashboard.js")

    # 2. No Solar Module Workspace
    assert "workspace-solar" not in index_html, "Found workspace-solar in static/index.html"
    assert "solar-calculate" not in dashboard_js, "Found solar-calculate in static/js/dashboard.js"
    assert "calculateSolar" not in dashboard_js, "Found calculateSolar in static/js/dashboard.js"
    assert "option value=\"solar\"" not in index_html, "Found solar option in workspace dropdown"
    print("  -> Passed: Zero Solar Module in index.html and dashboard.js")

    # 3. No Hotspot Buttons
    assert "pollutionHotspotsBar" not in index_html, "Found pollutionHotspotsBar in static/index.html"
    assert "loadPollutionHotspot" not in dashboard_js, "Found loadPollutionHotspot in dashboard.js"
    print("  -> Passed: Zero Canned Hotspot Buttons")

    # 4. Zero Emojis in files
    emoji_html = EMOJI_REGEX.findall(index_html)
    assert len(emoji_html) == 0, f"Found emojis in static/index.html: {emoji_html[:5]}"
    emoji_js = EMOJI_REGEX.findall(dashboard_js)
    assert len(emoji_js) == 0, f"Found emojis in static/js/dashboard.js: {emoji_js[:5]}"
    print("  -> Passed: Zero Emojis in frontend files")


def test_locationiq_forward_and_reverse():
    print("\n[TEST 2] Verifying LocationIQ Forward Search & Reverse Geocoding in Baghdad...")

    import time
    test_queries = ["الجامعة التقنية الوسطى", "الكرادة", "المنصور"]
    for q in test_queries:
        time.sleep(0.7)
        results = WeatherAndGeoIntelligenceService.search_places(q)
        assert len(results) > 0, f"LocationIQ search returned no results for '{q}'"
        first = results[0]
        assert "lat" in first and "lon" in first, f"Missing lat/lon in result for '{q}'"
        assert 33.05 <= first["lat"] <= 33.55, f"Latitude {first['lat']} outside Baghdad for '{q}'"
        assert 44.05 <= first["lon"] <= 44.70, f"Longitude {first['lon']} outside Baghdad for '{q}'"
        # Verify zero emojis
        assert not EMOJI_REGEX.search(first["name_ar"]), f"Emoji found in result name_ar for '{q}'"
        print(f"  -> Forward Search '{q}': Found '{first['name_ar']}' at ({first['lat']}, {first['lon']})")

    # Test Reverse Geocoding
    rev_district = GlobalPollutionResearchAgent.reverse_geocode_locationiq(33.3152, 44.3661)
    assert rev_district and len(rev_district) > 1, "LocationIQ Reverse geocoding returned empty"
    assert not EMOJI_REGEX.search(rev_district), "Emoji found in reverse geocode district"
    print(f"  -> Reverse Geocoding (33.3152, 44.3661): '{rev_district}'")


def test_pedological_botanical_agent():
    print("\n[TEST 3] Verifying PedologicalBotanicalAgent (Building Rejection vs Barren Ground)...")

    # 1. Building / Compact Rooftop Rejection (< 850 m2 with orthogonal edges)
    rooftop_req = LandInspectionRequest(
        lat=33.3152,
        lon=44.3661,
        polygon_coords=[
            [33.3150, 44.3660],
            [33.3150, 44.3662],
            [33.3152, 44.3662],
            [33.3152, 44.3660],
        ],
        location_name_ar="الكرادة",
        custom_area_m2=200.0,
    )
    rooftop_res = PedologicalBotanicalAgent.inspect_land(rooftop_req)
    assert rooftop_res["suitability_code"] == "REJECTED_BUILDING_OR_ROAD", (
        f"Expected REJECTED_BUILDING_OR_ROAD, got {rooftop_res['suitability_code']}"
    )
    assert rooftop_res["can_plant_trees"] is False, "Expected can_plant_trees == False for rooftop"
    assert len(rooftop_res["valid_tree_nodes"]) == 0, "Tree nodes must be empty for building roof"
    assert "لا يمكن غرس الأشجار فوق الصبات الخرسانية" in rooftop_res["suitability_explanation_ar"]
    assert not EMOJI_REGEX.search(rooftop_res["suitability_explanation_ar"]), "Emoji in refusal explanation"
    print("  -> Passed: Building Rooftop correctly rejected with Arabic refusal message.")

    # 2. Barren Ground Inspection (Large open parcel, e.g. 5,000 m2)
    barren_req = LandInspectionRequest(
        lat=33.2850,
        lon=44.4250,
        polygon_coords=[
            [33.2840, 44.4230],
            [33.2845, 44.4270],
            [33.2865, 44.4265],
            [33.2860, 44.4225],
        ],
        location_name_ar="حي الزعفرانية",
        custom_area_m2=5000.0,
    )
    barren_res = PedologicalBotanicalAgent.inspect_land(barren_req)
    assert barren_res["suitability_code"] == "SUITABLE_BARREN_LAND", (
        f"Expected SUITABLE_BARREN_LAND, got {barren_res['suitability_code']}"
    )
    assert barren_res["can_plant_trees"] is True, "Expected can_plant_trees == True for barren land"
    assert len(barren_res["selected_species"]) == 4, (
        f"Expected exactly 4 species, got {len(barren_res['selected_species'])}"
    )

    total_alloc = sum(sp["allocation_pct"] for sp in barren_res["selected_species"])
    assert 99.0 <= total_alloc <= 101.0, f"Expected allocation_pct sum ~ 100%, got {total_alloc}"

    for sp in barren_res["selected_species"]:
        assert "soil_climate_match_reason_ar" in sp, f"Missing soil_climate_match_reason_ar in {sp}"
        assert len(sp["soil_climate_match_reason_ar"]) > 10, "Empty soil_climate_match_reason_ar"
        assert not EMOJI_REGEX.search(sp["soil_climate_match_reason_ar"]), "Emoji in match reason"

    assert len(barren_res["valid_tree_nodes"]) > 0, "No tree nodes generated"
    assert barren_res["soil_type_title_ar"], "Missing soil_type_title_ar"
    assert barren_res["soil_salinity_ece_dsm"] > 0, "Missing soil_salinity_ece_dsm"
    assert barren_res["soil_ph"] > 0, "Missing soil_ph"

    print(f"  -> Passed: Barren ground matched soil: '{barren_res['soil_type_title_ar']}'")
    print(f"     Salinity: {barren_res['soil_salinity_ece_dsm']} dS/m | pH: {barren_res['soil_ph']}")
    print(f"     4 Species: {[s['name_ar'] for s in barren_res['selected_species']]}")


def test_global_pollution_research_agent():
    print("\n[TEST 4] Verifying GlobalPollutionResearchAgent (Live Groq CAMS synthesis)...")

    pol_res = GlobalPollutionResearchAgent.get_pollution_sentinel(33.2750, 44.4050, "الدورة")

    assert pol_res["uhi_anomaly_c"] < 5.0, f"uhi_anomaly_c must be < 5.0, got {pol_res['uhi_anomaly_c']}"
    assert pol_res["uhi_anomaly_c"] >= 1.6, f"uhi_anomaly_c must be >= 1.6, got {pol_res['uhi_anomaly_c']}"
    assert pol_res["dominant_hazard_title_ar"], "Missing dominant_hazard_title_ar"
    assert pol_res["benchmark_country_ar"], "Missing benchmark_country_ar"
    assert pol_res["benchmark_project_title_ar"], "Missing benchmark_project_title_ar"
    assert pol_res["health_risk_assessment_ar"], "Missing health_risk_assessment_ar"
    assert pol_res["engineering_mitigation_protocol_ar"], "Missing engineering_mitigation_protocol_ar"

    # Zero emojis check across all fields
    for k, v in pol_res.items():
        if isinstance(v, str):
            assert not EMOJI_REGEX.search(v), f"Found emoji in pollution field '{k}': {v}"
        elif isinstance(v, list):
            for itm in v:
                if isinstance(itm, str):
                    assert not EMOJI_REGEX.search(itm), f"Found emoji in pollution list '{k}': {itm}"

    print(f"  -> Passed: Pollution Sentinel Live Synthesis:")
    print(f"     District: {pol_res['location_name_ar']}")
    print(f"     AQI: {pol_res['aqi_european']} | PM2.5: {pol_res['pm25_ugm3']} | UHI: +{pol_res['uhi_anomaly_c']} °C")
    print(f"     Hazard: {pol_res['dominant_hazard_title_ar']}")
    print(f"     Benchmark: {pol_res['benchmark_country_ar']}")
    print(f"     Project: {pol_res['benchmark_project_title_ar']}")


def main():
    print("=" * 70)
    print("EcoSensing AI — LocationIQ & Dedicated AI Agents Verification Suite")
    print("Project Manager: Ali Nihad Qadir (علي نهاد قادر)")
    print("=" * 70)

    try:
        test_zero_leaflet_solar_emoji()
        test_locationiq_forward_and_reverse()
        test_pedological_botanical_agent()
        test_global_pollution_research_agent()

        print("\n" + "=" * 70)
        print("[100% SUCCESS] ALL ARCHITECTURAL TESTS PASSED PERFECTLY!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n[VERIFICATION FAILED] AssertionError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[VERIFICATION ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
