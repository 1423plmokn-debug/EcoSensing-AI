"""
Phase 2 Verification & Benchmark Suite
EcoSensing AI - Urban Microclimate & Field Sentinel
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Middle Technical University / Polytechnic College
"""

import sys
from pathlib import Path

# Force UTF-8 console output for Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from app.models.schemas import SimulationRequest
from app.services.simulation_engine import DynamicThermalSimulator
from app.services.green_planner import GreenCorridorPlanner


def run_phase2_verification():
    print("=" * 85)
    print("🌳 EcoSensing AI - Phase 2 Verification: Dynamic Simulation & Botanical Carbon ROI")
    print(f"🏛️  Institution: {settings.INSTITUTION}")
    print(f"👤 Project Manager: {settings.AUTHOR}")
    print("=" * 85)

    # --------------------------------------------------------------------------
    # SCENARIO 1: Primary Scientific Benchmark (6 Dunums, Baghdad Outskirts, 44.5 C)
    # --------------------------------------------------------------------------
    print("\n[SCENARIO 1] Primary Scientific Benchmark Farm (6 Dunums, 44.5°C Baseline)...")
    req1 = SimulationRequest(
        area_dunums=6.0,
        current_surface_temp_c=44.5,
        target_crop_type="mixed_orchard",
        target_governorate="Baghdad - Outskirts",
    )
    res1 = DynamicThermalSimulator.run_simulation(req1)

    print(f"  📍 Area: {res1.area_dunums} Dunums ({res1.area_m2:,.0f} m²)")
    print(f"  💧 Water Budget:")
    print(f"     - Conventional Baseline: {res1.baseline_weekly_water_liters:,.0f} L/week")
    print(f"     - EcoSensing Optimized:  {res1.optimized_weekly_water_liters:,.0f} L/week")
    print(f"     - Weekly Water Saved:    {res1.water_saved_liters_weekly:,.0f} L/week ({res1.water_saving_pct}%)")
    print(f"  🌡️ Thermal Mitigation (LST):")
    print(f"     - Before: {res1.lst_before_c}°C -> After: {res1.lst_after_c}°C (Cooling Drop: {res1.lst_drop_c}°C)")
    print(f"  🛡️ Early Crop Damage Risk: {res1.early_damage_before_pct}% -> {res1.early_damage_after_pct}%")
    print(f"  🌲 Botanical Allocation (Total: {sum(t.tree_count for t in res1.recommended_trees)} trees, Spacing: {res1.green_corridor_recommended_spacing_m}m):")
    for t in res1.recommended_trees:
        print(f"     * {t.tree_name_ar:<25}: {t.tree_count:>3} trees | Water: {t.total_weekly_water_liters:>6.0f} L/wk | CO2: {t.total_co2_kg_year:>6.0f} kg/yr")
    print(f"  💰 Carbon & Financial ROI:")
    print(f"     - Annual CO2 Offset: {res1.annual_co2_offset_tonnes} Metric Tonnes")
    print(f"     - Annual Savings:    {res1.annual_financial_savings_iqd:,.0f} IQD (${res1.annual_financial_savings_usd:,.2f} USD)")

    # Assertions for Scenario 1 matching benchmark requirements
    assert res1.area_m2 == 15000.0, f"Expected 15,000 m2, got {res1.area_m2}"
    assert res1.baseline_weekly_water_liters == 120000.0, f"Expected 120,000 L, got {res1.baseline_weekly_water_liters}"
    assert res1.optimized_weekly_water_liters == 74400.0, f"Expected 74,400 L, got {res1.optimized_weekly_water_liters}"
    assert res1.water_saved_liters_weekly == 45600.0, f"Expected 45,600 L, got {res1.water_saved_liters_weekly}"
    assert res1.water_saving_pct == 38.0, f"Expected 38.0%, got {res1.water_saving_pct}"
    assert res1.lst_drop_c == 2.7, f"Expected 2.7 C drop, got {res1.lst_drop_c}"
    assert res1.lst_after_c == 41.8, f"Expected 41.8 C, got {res1.lst_after_c}"
    assert res1.early_damage_after_pct < 5.0, f"Expected < 5.0% early damage, got {res1.early_damage_after_pct}"
    assert sum(t.tree_count for t in res1.recommended_trees) == 180, "Expected 180 total trees"
    print("  ✅ SCENARIO 1 PASSED: Exact benchmark numbers verified!")

    # --------------------------------------------------------------------------
    # SCENARIO 2: Small Urban Heat-Island Plot (1.5 Dunums, Baghdad Center, 47.0 C)
    # --------------------------------------------------------------------------
    print("\n[SCENARIO 2] Small Urban Heat Island (1.5 Dunums, Extreme 47.0°C)...")
    req2 = SimulationRequest(
        area_dunums=1.5,
        current_surface_temp_c=47.0,
        target_crop_type="urban_park_corridor",
        target_governorate="Baghdad - Karrada",
    )
    res2 = DynamicThermalSimulator.run_simulation(req2)

    print(f"  📍 Area: {res2.area_dunums} Dunums ({res2.area_m2:,.0f} m²)")
    print(f"  💧 Water: Saved {res2.water_saved_liters_weekly:,.0f} L/week ({res2.water_saving_pct}%)")
    print(f"  🌡️ Thermal Mitigation: {res2.lst_before_c}°C -> {res2.lst_after_c}°C (Cooling Drop: {res2.lst_drop_c}°C)")
    print(f"  🌲 Total Trees: {sum(t.tree_count for t in res2.recommended_trees)} trees")
    print(f"  💰 Financial Yield: {res2.annual_financial_savings_iqd:,.0f} IQD (${res2.annual_financial_savings_usd:,.2f} USD)")

    assert res2.area_m2 == 3750.0
    assert res2.lst_drop_c >= 2.7, "Extreme heat should yield at least 2.7 C cooling"
    assert res2.early_damage_after_pct < 5.0
    print("  ✅ SCENARIO 2 PASSED: Small urban plot scaled accurately!")

    # --------------------------------------------------------------------------
    # SCENARIO 3: Large Commercial Agroforestry Orchard (20 Dunums, 43.0 C)
    # --------------------------------------------------------------------------
    print("\n[SCENARIO 3] Large Commercial Agroforestry Orchard (20 Dunums, 43.0°C)...")
    req3 = SimulationRequest(
        area_dunums=20.0,
        current_surface_temp_c=43.0,
        target_crop_type="date_palm_mixed_citrus",
        target_governorate="Diyala / Baghdad Border",
    )
    res3 = DynamicThermalSimulator.run_simulation(req3)

    print(f"  📍 Area: {res3.area_dunums} Dunums ({res3.area_m2:,.0f} m²)")
    print(f"  💧 Water Budget:")
    print(f"     - Conventional Baseline: {res3.baseline_weekly_water_liters:,.0f} L/week")
    print(f"     - Weekly Water Saved:    {res3.water_saved_liters_weekly:,.0f} L/week ({res3.water_saving_pct}%)")
    print(f"  🌡️ Thermal Mitigation: {res3.lst_before_c}°C -> {res3.lst_after_c}°C (Cooling Drop: {res3.lst_drop_c}°C)")
    print(f"  🌲 Total Trees: {sum(t.tree_count for t in res3.recommended_trees)} trees")
    print(f"  💰 Financial Yield: {res3.annual_financial_savings_iqd:,.0f} IQD (${res3.annual_financial_savings_usd:,.2f} USD)")
    print(f"  📜 Executive Summary Sample:\n     \"{res3.executive_summary_ar[:140]}...\"")

    assert res3.area_m2 == 50000.0
    assert res3.water_saved_liters_weekly > 140000.0
    assert res3.annual_co2_offset_tonnes > 15.0
    print("  ✅ SCENARIO 3 PASSED: Commercial scale orchard simulated flawlessly!")

    # --------------------------------------------------------------------------
    # Botanical Catalog Validation
    # --------------------------------------------------------------------------
    print("\n[BOTANICAL CATALOG AUDIT]")
    for key, spec in GreenCorridorPlanner.BOTANICAL_CATALOG.items():
        print(f"  ✓ {spec.name_ar} ({spec.scientific_name}): {spec.water_liters_per_week} L/wk, {spec.co2_kg_per_year} kg CO2/yr, Canopy {spec.canopy_diameter_m}m")

    print("\n" + "=" * 85)
    print("🎯 PHASE 2 VERIFICATION COMPLETE: ALL BENCHMARKS & DYNAMIC ENGINES PASSED 100%!")
    print("=" * 85)


if __name__ == "__main__":
    run_phase2_verification()
