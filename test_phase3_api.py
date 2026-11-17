"""
Phase 3 Verification & Integration Suite: FastAPI Endpoints & Static Delivery
EcoSensing AI - Urban Microclimate & Field Sentinel
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Middle Technical University / Polytechnic College
"""

import sys
from pathlib import Path

# Force UTF-8 on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app


def run_phase3_verification():
    print("=" * 85)
    print("🌐 EcoSensing AI - Phase 3 Verification: FastAPI Endpoints & Geospatial API")
    print("=" * 85)

    client = TestClient(app)

    # 1. Test GET /
    print("\n[TEST 1] Testing Root Route (GET /) Serving Dashboard HTML...")
    res_root = client.get("/")
    assert res_root.status_code == 200, f"Expected 200, got {res_root.status_code}"
    assert "EcoSensing AI" in res_root.text, "Dashboard title missing in HTML"
    assert "baghdadMap" in res_root.text, "Map container missing in HTML"
    print("  ✓ Root route successfully serves 2.5D Institutional Dashboard!")

    # 2. Test GET /api/health
    print("\n[TEST 2] Testing System Health (GET /api/health)...")
    res_health = client.get("/api/health")
    assert res_health.status_code == 200, f"Expected 200, got {res_health.status_code}"
    health_data = res_health.json()
    print(f"  ✓ Status: {health_data['status']}")
    print(f"  ✓ Active Model: {health_data['active_gemini_model']}")
    print(f"  ✓ Cloud Configured: {health_data['is_cloud_gemini_configured']}")
    print(f"  ✓ Project: {health_data['project_name']}")
    assert health_data["status"] == "operational"

    # 3. Test GET /api/baghdad-sectors
    print("\n[TEST 3] Testing Baghdad Geo-Sectors (GET /api/baghdad-sectors)...")
    res_sec = client.get("/api/baghdad-sectors")
    assert res_sec.status_code == 200
    sectors = res_sec.json().get("sectors", [])
    assert len(sectors) == 5, f"Expected 5 sectors, got {len(sectors)}"
    for s in sectors:
        print(f"  ✓ Sector: {s['name_ar']} -> [{s['lat']}, {s['lng']}] | Baseline LST: {s['baseline_lst_c']}°C")

    # 4. Test POST /api/simulate (Benchmark 6 Dunums, 44.5 C)
    print("\n[TEST 4] Testing Dynamic Simulation API (POST /api/simulate)...")
    sim_payload = {
        "area_dunums": 6.0,
        "current_surface_temp_c": 44.5,
        "target_crop_type": "mixed_orchard",
        "target_governorate": "Baghdad",
    }
    res_sim = client.post("/api/simulate?lat=33.2625&lng=44.3100", json=sim_payload)
    assert res_sim.status_code == 200, f"Simulation failed: {res_sim.text}"
    sim_data = res_sim.json()
    print(f"  ✓ Area: {sim_data['area_dunums']} Dunums ({sim_data['area_m2']} m²)")
    print(f"  ✓ Water Saving: {sim_data['water_saved_liters_weekly']} L/wk ({sim_data['water_saving_pct']}%)")
    print(f"  ✓ LST Drop: {sim_data['lst_drop_c']}°C (From {sim_data['lst_before_c']}°C to {sim_data['lst_after_c']}°C)")
    print(f"  ✓ Annual ROI: {sim_data['annual_financial_savings_iqd']:,.0f} IQD (${sim_data['annual_financial_savings_usd']:,.2f} USD)")
    assert sim_data["water_saving_pct"] == 38.0
    assert sim_data["lst_drop_c"] == 2.7
    assert "spatial_corridor" in sim_data
    assert len(sim_data["spatial_corridor"]["tree_nodes"]) > 0
    print(f"  ✓ Geospatial Tree Nodes Plotted: {len(sim_data['spatial_corridor']['tree_nodes'])} trees with coordinates")

    # 5. Test POST /api/analyze-image (Sample: dust)
    print("\n[TEST 5] Testing Multimodal CV & AI Diagnosis (POST /api/analyze-image?sample_type=dust)...")
    res_cv_dust = client.post("/api/analyze-image?sample_type=dust")
    assert res_cv_dust.status_code == 200, f"CV analysis failed: {res_cv_dust.text}"
    cv_data_dust = res_cv_dust.json()
    assert cv_data_dust["thermal_image_b64"].startswith("data:image/jpeg;base64,")
    assert cv_data_dust["spectral_image_b64"].startswith("data:image/jpeg;base64,")
    ai_dust = cv_data_dust["ai_analysis"]
    print(f"  ✓ Diagnosis: {ai_dust.get('diagnosis_code')} - {ai_dust.get('diagnosis_title_ar')}")
    print(f"  ✓ Dust Accumulation: {ai_dust.get('dust_accumulation_pct')}%")
    print(f"  ✓ Engine Source: {cv_data_dust.get('engine_source')}")

    # 6. Test POST /api/analyze-image (Sample: water_stress)
    print("\n[TEST 6] Testing Multimodal CV & AI Diagnosis (POST /api/analyze-image?sample_type=water_stress)...")
    res_cv_water = client.post("/api/analyze-image?sample_type=water_stress")
    assert res_cv_water.status_code == 200, f"CV analysis failed: {res_cv_water.text}"
    cv_data_water = res_cv_water.json()
    ai_water = cv_data_water["ai_analysis"]
    print(f"  ✓ Diagnosis: {ai_water.get('diagnosis_code')} - {ai_water.get('diagnosis_title_ar')}")
    print(f"  ✓ Water Stress Index: {ai_water.get('water_stress_index_pct')}%")

    print("\n" + "=" * 85)
    print("🎯 ALL FASTAPI REST ENDPOINTS VERIFIED & PASSING WITH ZERO ERRORS!")
    print("=" * 85)


if __name__ == "__main__":
    run_phase3_verification()
