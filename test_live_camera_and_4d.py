"""
EcoSensing AI – Verification Suite for Live Camera Console, 4D Fluid Cloud & AI Mitigation Agent
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Academic Affiliation: Middle Technical University / Polytechnic College

Verification Tasks:
1. REST API /api/v1/analyze-vision (Module 2 100% Intact):
   - Clean green leaf (status_code == "OPTIMAL_HEALTH", dust_coverage_pct < 2.0)
   - Dusty leaf (status_code == "DUST_SUFFOCATION")
   - Floral bloom & saline soil (lab_report completeness & soil indices)
2. 4D Fluid Atmospheric Dispersion Cloud (Module 1):
   - Stochastic advection-diffusion point cloud ([lon, lat] GeoJSON Point features between 180 and 250)
   - Point weights and multi-core dispersion
3. Groq AI Pollution Source Attribution & Integrated Mitigation Agent:
   - /api/v1/diagnose-pollution-mitigation returning full structured dossier
   - Site typology, 100% source attribution, engineering remedies, strict afforestation feasibility
4. Frontend Integrity & Zero Emojis:
   - MapLibre heatmap layer 'pollution-fluid-cloud'
   - #btnDiagnosePollution and #pollutionMitigationCard
   - Zero hardcoded orange polygon / blind tree cylinder stamping
   - Zero Unicode emojis across all HTML, CSS, JS, and Python
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

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app

client = TestClient(app)

EMOJI_REGEX = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\U0001f1e6-\U0001f1ff\u2300-\u23ff\u2b50\u200d\ufe0f]"
)


def create_synthetic_image(r: int, g: int, b: int, size: tuple = (160, 160)) -> bytes:
    img = Image.new("RGB", size, color=(r, g, b))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def test_v1_analyze_vision_green_leaf():
    """Verify clean green leaf returns OPTIMAL_HEALTH and low dust."""
    print("  Testing /api/v1/analyze-vision with clean green leaf...")
    green_bytes = create_synthetic_image(34, 139, 34)

    resp = client.post(
        "/api/v1/analyze-vision",
        files={"image": ("clean_leaf.jpg", green_bytes, "image/jpeg")},
        data={"region_name": "بغداد - محطة الفحص الميداني"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # Core assertions
    assert data.get("status_code") == "OPTIMAL_HEALTH", f"Expected OPTIMAL_HEALTH, got {data.get('status_code')}"
    assert float(data.get("dust_coverage_pct", 10.0)) < 2.0, f"Expected dust < 2.0, got {data.get('dust_coverage_pct')}"

    # Required response keys
    expected_keys = [
        "status_code", "status_label_ar", "dust_coverage_pct", "chlorosis_pct",
        "necrosis_pct", "health_index", "rgb_image", "thermal_image",
        "spectral_image", "ai_diagnosis_ar", "engine_source", "inference_latency_s",
        "lab_report", "sample_category"
    ]
    for key in expected_keys:
        assert key in data, f"Missing key '{key}' in response"

    assert data["sample_category"] in ["LEAF", "TREE", "TURFGRASS", "SOIL"]
    print("    [PASS] Clean green leaf: status_code == OPTIMAL_HEALTH, dust < 2.0%")


def test_v1_analyze_vision_dusty_leaf():
    """Verify dusty leaf returns DUST_SUFFOCATION."""
    print("  Testing /api/v1/analyze-vision with dusty leaf...")
    dust_path = Path("static/samples/iraqi_dust_leaf.jpg")
    if dust_path.exists():
        dust_bytes = dust_path.read_bytes()
    else:
        # Synthetic dusty leaf: green base with yellow-gray dust overlay
        arr = np.zeros((160, 160, 3), dtype=np.uint8)
        arr[:, :] = [185, 175, 140]  # Dusty ochre-silt
        arr[30:130, 30:130] = [80, 120, 60]  # Suffocated muted green
        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        dust_bytes = buf.getvalue()

    resp = client.post(
        "/api/v1/analyze-vision",
        files={"image": ("dust_leaf.jpg", dust_bytes, "image/jpeg")},
        data={"region_name": "بغداد - الدورة"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()

    assert data.get("status_code") == "DUST_SUFFOCATION", f"Expected DUST_SUFFOCATION, got {data.get('status_code')}"
    assert "رش ضبابي" in data.get("irrigation_recommendation_ar", "")
    print("    [PASS] Dusty leaf: status_code == DUST_SUFFOCATION")


def test_v1_analyze_vision_floral_and_soil():
    """Verify open-taxonomy lab report completeness for floral bloom and saline soil."""
    print("  Testing /api/v1/analyze-vision with floral bloom & saline soil...")

    # 1. Floral bloom (Jouri Rose / Red-Pink Petals)
    floral_bytes = create_synthetic_image(220, 25, 80)
    resp_floral = client.post(
        "/api/v1/analyze-vision",
        files={"image": ("floral_rose.jpg", floral_bytes, "image/jpeg")},
    )
    assert resp_floral.status_code == 200
    data_floral = resp_floral.json()
    lab_floral = data_floral.get("lab_report", {})

    assert "scientific_name" in lab_floral, "Missing scientific_name in lab_report"
    assert "arabic_common_name" in lab_floral, "Missing arabic_common_name in lab_report"
    assert "specimen_category" in lab_floral, "Missing specimen_category in lab_report"
    assert "pathology_and_deficiency" in lab_floral, "Missing pathology in lab_report"
    assert "remediation_protocol" in lab_floral, "Missing remediation in lab_report"
    assert "surface_moisture_index_pct" in lab_floral, "Missing moisture index"
    assert "salinity_crust_index_pct" in lab_floral, "Missing salinity crust index"
    print(f"    [PASS] Floral specimen: {lab_floral.get('arabic_common_name')} ({lab_floral.get('scientific_name')})")

    # 2. Saline Soil Sample
    soil_bytes = create_synthetic_image(215, 210, 195)
    resp_soil = client.post(
        "/api/v1/analyze-vision",
        files={"image": ("saline_soil.jpg", soil_bytes, "image/jpeg")},
    )
    assert resp_soil.status_code == 200
    data_soil = resp_soil.json()
    lab_soil = data_soil.get("lab_report", {})

    assert "scientific_name" in lab_soil
    assert "arabic_common_name" in lab_soil
    assert data_soil.get("sample_category") == "SOIL"
    print(f"    [PASS] Soil specimen: {lab_soil.get('arabic_common_name')} (Salinity crust: {lab_soil.get('salinity_crust_index_pct')}%)")


def test_4d_fluid_atmospheric_dispersion_cloud():
    """Verify 4D diurnal multi-emitter fluid dispersion point cloud (180-250 points, [lon, lat])."""
    print("  Testing 4D fluid advection point cloud...")

    # Diurnal Plume at solar peak hour 14
    resp = client.post("/api/physics/diurnal-plume?lat=33.3152&lon=44.3661&wind_speed_ms=4.2&wind_deg=315.0&hour=14")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    geojson = resp.json()

    assert geojson.get("type") == "FeatureCollection"
    features = geojson.get("features", [])
    count = len(features)
    assert 180 <= count <= 250, f"Expected 180 to 250 dispersion nodes, got {count}"

    # Verify each feature is a Point with coordinates in [lon, lat] order
    for idx, feat in enumerate(features[:10]):
        assert feat.get("geometry", {}).get("type") == "Point"
        coord = feat["geometry"]["coordinates"]
        lon, lat = coord[0], coord[1]
        assert 43.5 <= lon <= 45.5, f"Expected longitude ~44.x, got {lon} at idx {idx}"
        assert 32.5 <= lat <= 34.5, f"Expected latitude ~33.x, got {lat} at idx {idx}"
        assert "weight" in feat.get("properties", {}), "Feature missing 'weight' property"
        w = feat["properties"]["weight"]
        assert 0.0 <= w <= 1.0, f"Weight out of bounds: {w}"

    print(f"    [PASS] Fluid Point Cloud (Hour 14): {count} stochastic nodes in [lon, lat] format with valid weights")


def test_groq_ai_pollution_mitigation_agent():
    """Verify /api/v1/diagnose-pollution-mitigation returns complete structured dossier."""
    print("  Testing /api/v1/diagnose-pollution-mitigation endpoint...")

    resp = client.post(
        "/api/v1/diagnose-pollution-mitigation?lat=33.3152&lon=44.3661&district_name_ar=بغداد - الكرادة"
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    dossier = resp.json()

    # Required dossier sections
    required_keys = [
        "site_typology_ar",
        "emission_source_breakdown",
        "engineering_mitigation_plan",
        "afforestation_feasibility",
        "projected_impact_metrics",
    ]
    for k in required_keys:
        assert k in dossier, f"Missing key '{k}' in mitigation dossier"

    # Verify emission breakdown sums to approx 100%
    breakdown = dossier["emission_source_breakdown"]
    if isinstance(breakdown, list):
        total_pct = sum(float(item.get("percentage", 0)) for item in breakdown)
    elif isinstance(breakdown, dict):
        total_pct = sum(float(v) for v in breakdown.values())
    else:
        total_pct = 0.0
    assert 90.0 <= total_pct <= 110.0, f"Source percentages must sum to ~100%, got {total_pct}"

    # Verify engineering remedies exist and are non-empty
    eng_plan = dossier["engineering_mitigation_plan"]
    assert isinstance(eng_plan, list) and len(eng_plan) >= 2, "Expected at least 2 engineering remedies"

    # Verify afforestation feasibility structure
    feas = dossier["afforestation_feasibility"]
    assert "is_viable" in feas or "is_planting_viable" in feas
    assert "strict_placement_rule_ar" in feas or "prescribed_species_and_placement" in feas
    assert "target_canopy_coverage_pct" in feas or "recommended_canopy_target_pct" in feas

    # Verify projected impact metrics
    imp = dossier["projected_impact_metrics"]
    assert "expected_pm_reduction_pct" in imp
    assert "expected_lst_cooling_c" in imp
    assert "nox_sox_abatement_pct" in imp

    source_names = [item.get("source_ar") for item in breakdown] if isinstance(breakdown, list) else list(breakdown.keys())
    print(f"    [PASS] Pollution Mitigation Dossier: Typology='{dossier['site_typology_ar'][:30]}...', Sources={source_names}")


def test_frontend_code_integrity():
    """Verify HTML & JS contain all required controls, mode switcher, heatmap, and zero emojis."""
    print("  Testing static/index.html & static/js/dashboard.js integrity...")

    html = Path("static/index.html").read_text(encoding="utf-8")
    js = Path("static/js/dashboard.js").read_text(encoding="utf-8")

    # 1. Mode Switcher & Lab Console
    assert "tabVisionUpload" in html and "tabVisionLiveCamera" in html
    assert "btnStartCamera" in html and "btnStopCamera" in html and "btnCaptureAnalyze" in html
    assert "labCertificatePanel" in html

    # 2. Camera Controls & ZERO auto-start rule
    assert "let cameraStream = null;" in js or "cameraStream = null" in js
    assert "startCamera();" not in js[js.find("DOMContentLoaded"):]

    # 3. 4D Diurnal simulation controls & New Mitigation Card
    assert "diurnalSimulationBar" in html
    assert "btnToggle4D" in html
    assert "hourSlider" in html
    assert "btnPlayDiurnal" in html
    assert "btnDiagnosePollution" in html, "Missing #btnDiagnosePollution in index.html"
    assert "pollutionMitigationCard" in html, "Missing #pollutionMitigationCard in index.html"
    assert "pm-typology" in html and "pm-sources-container" in html and "pm-engineering-list" in html

    # 4. MapLibre Heatmap layer 'pollution-fluid-cloud'
    assert "pollution-fluid-cloud" in js, "Missing 'pollution-fluid-cloud' heatmap layer in dashboard.js"
    assert "pollution-fluid-source" in js, "Missing 'pollution-fluid-source' geojson source in dashboard.js"
    assert "triggerPollutionMitigationDiagnosis" in js, "Missing triggerPollutionMitigationDiagnosis in dashboard.js"

    # 5. Verify removal of old rigid orange oval polygon layer from setupMapLayers
    assert "gaussian-plume-fill" not in js, "Old rigid 'gaussian-plume-fill' layer still in dashboard.js"

    # 6. Zero Emojis check in static and service files
    check_files = [
        Path("static/index.html"),
        Path("static/js/dashboard.js"),
        Path("static/css/style.css"),
        Path("app/services/pollution_mitigation_agent.py"),
        Path("app/services/physics_engine.py"),
        Path("app/routers/api.py"),
    ]
    for filepath in check_files:
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            matches = EMOJI_REGEX.findall(content)
            assert len(matches) == 0, f"Found {len(matches)} emojis in {filepath.name}"

    print("    [PASS] Frontend code integrity: Heatmap Layer, AI Mitigation Card, Zero Auto-Start, Zero Emojis")


def test_unified_command_center_and_usb_camera():
    """Verify Unified Command Center layout, 4-tab dossier viewer, and preferred USB camera logic."""
    print("  Testing Unified Command Center, Executive Dossier tabs, and USB camera prioritization...")

    html = Path("static/index.html").read_text(encoding="utf-8")
    js = Path("static/js/dashboard.js").read_text(encoding="utf-8")
    css = Path("static/css/style.css").read_text(encoding="utf-8")

    # 1. Docked toolbar and zero absolute overlap
    assert "diurnal-docked-toolbar" in html
    assert ".diurnal-docked-toolbar" in css

    # 2. Unified Command Banner & Executive Dossier Viewer with 4 Instant Tabs
    assert "unified-cmd-banner" in html
    assert "unifiedDossierTabs" in html
    assert "tabBtnMitigation" in html
    assert "tabBtnSoil" in html
    assert "tabBtnBenchmark" in html
    assert "tabBtnAll" in html

    assert "dossierPaneMitigation" in html
    assert "dossierPaneSoil" in html
    assert "dossierPaneBenchmark" in html

    # 3. JavaScript Tab Switcher and Unified Inspection Engine
    assert "function switchDossierView" in js
    assert "function runUnifiedInspection" in js
    assert "function executeAgent1LandInspection" in js
    assert "function executeAgent2PollutionSentinel" in js
    assert "function executeAgent3PollutionMitigation" in js

    # 4. USB 1080p Camera Prioritization & Persistence
    assert "btnSwitchUsbCamera" in html
    assert "function selectPreferredExternalCamera" in js
    assert "function switchPreferredUsbCamera" in js
    assert "preferred_usb_camera_id" in js
    assert "1920" in js and "1080" in js

    # 5. Parallel Multi-Agent execution test (Agents 1, 2, and 3)
    resp_agent1 = client.post(
        "/api/inspect-land",
        json={
            "lat": 33.3152,
            "lon": 44.3661,
            "polygon_coords": [],
            "location_name_ar": "بغداد - الكرادة",
            "custom_area_m2": 180.0,
        },
    )
    assert resp_agent1.status_code == 200, f"Agent 1 failed: {resp_agent1.text}"
    data1 = resp_agent1.json()
    assert "soil_analysis" in data1 or "tree_recommendations" in data1 or "can_plant_trees" in data1

    resp_agent2 = client.get(
        "/api/pollution-sentinel?lat=33.3152&lon=44.3661&location_name_ar=بغداد - الكرادة"
    )
    assert resp_agent2.status_code == 200, f"Agent 2 failed: {resp_agent2.text}"
    data2 = resp_agent2.json()
    assert "aqi_european" in data2 and "benchmark_country_ar" in data2

    resp_agent3 = client.post(
        "/api/v1/diagnose-pollution-mitigation?lat=33.3152&lon=44.3661&district_name_ar=بغداد - الكرادة"
    )
    assert resp_agent3.status_code == 200, f"Agent 3 failed: {resp_agent3.text}"
    data3 = resp_agent3.json()
    assert "site_typology_ar" in data3 and "emission_source_breakdown" in data3

    print("    [PASS] Unified Command Center: 4 Dossier Tabs, USB Camera Prioritization, Multi-Agent Parallel Execution")


def main():
    print("=" * 75)
    print("  EcoSensing AI – Live Camera, 4D Fluid Cloud & AI Mitigation Test Suite")
    print("=" * 75)
    t0 = time.perf_counter()

    tests = [
        test_v1_analyze_vision_green_leaf,
        test_v1_analyze_vision_dusty_leaf,
        test_v1_analyze_vision_floral_and_soil,
        test_4d_fluid_atmospheric_dispersion_cloud,
        test_groq_ai_pollution_mitigation_agent,
        test_frontend_code_integrity,
        test_unified_command_center_and_usb_camera,
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
    print("=" * 75)
    print(f"  Summary: {passed} PASSED, {failed} FAILED in {dt:.2f}s")
    print("=" * 75)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
