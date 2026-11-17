"""
EcoSensing AI – Solar Rooftop & Iraqi Generator Amperage Engine
Full ROI, environmental, and financial analysis for Baghdad rooftop solar installations.

Academic Affiliation: Middle Technical University / Polytechnic College
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

import logging
import math
from typing import List

from app.models.schemas import (
    LiveWeatherResponse,
    SolarCalculationRequest,
    SolarCalculationResponse,
)

logger = logging.getLogger("EcoSensing.SolarEngine")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS – Iraqi Solar & Economic Context
# ─────────────────────────────────────────────────────────────────────────────
_USABLE_ROOF_RATIO: float = 0.72       # Deduct parapets, water tanks, corridors
_M2_PER_PANEL: float = 2.6             # 550W Mono-PERC with tilt row-spacing
_BAGHDAD_PEAK_SUN_HOURS: float = 5.8   # Daily peak sun hours (annual average)
_INVERTER_EFFICIENCY: float = 0.88     # Hybrid inverter efficiency
_TEMP_DERATING: float = 0.90           # Iraqi summer temperature derating factor
_VOLTS_IRAQI: float = 220.0            # Iraqi single-phase grid voltage
_IQD_PER_USD: float = 1320.0           # IQD/USD exchange rate
_AC_SAVING_PCT: float = 0.18           # AC energy saved from roof shading
_ROOF_SHADING_TEMP_DROP_C: float = 3.2 # Roof slab temperature drop from shading
_AC_MONTHLY_COST_IQD: float = 85_000.0 # Avg Iraqi household monthly AC cost (IQD)
_DIESEL_G_PER_KWH: float = 0.28        # Litres of diesel per kWh avoided
_CO2_KG_PER_LITRE_DIESEL: float = 2.68 # kg CO₂ per litre of diesel burned

# 1 kW = 1000 W; at 220 V: A = W / V = 1000/220 ≈ 4.545 A
_KW_PER_AMPERE_220V: float = _VOLTS_IRAQI / 1000.0  # 0.22 kW/A

_EARTH_RADIUS_M: float = 6_371_000.0


def _geodesic_polygon_area_m2(coords: List[List[float]]) -> float:
    """Spherical excess formula for geodesic polygon area (m²)."""
    if len(coords) < 3:
        return 0.0
    n = len(coords)
    pts = [(math.radians(c[0]), math.radians(c[1])) for c in coords]
    total = 0.0
    for i in range(n):
        j = (i + 1) % n
        lat1, lon1 = pts[i]
        lat2, lon2 = pts[j]
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return abs(total) * _EARTH_RADIUS_M ** 2 / 2.0


class SolarRooftopAndGeneratorEngine:
    """
    Iraqi Solar Rooftop ROI Engine:
    - Geodesic or manual roof area
    - Panel count for target ampere delivery
    - Full IQD/USD financial projections
    - Generator subscription replacement analysis
    - CO₂ and diesel offset calculation
    - Rich Arabic executive report
    """

    @classmethod
    def calculate_solar_roi(cls, req: SolarCalculationRequest) -> SolarCalculationResponse:
        """
        Main calculation pipeline for rooftop solar ROI.
        """
        # ── 1. Determine roof area ────────────────────────────────────────────
        if len(req.polygon_coords) >= 3:
            roof_area_m2 = round(_geodesic_polygon_area_m2(req.polygon_coords), 2)
        else:
            roof_area_m2 = req.roof_area_m2

        usable_roof_area_m2 = round(roof_area_m2 * _USABLE_ROOF_RATIO, 2)

        # ── 2. Panel capacity ─────────────────────────────────────────────────
        max_panels_roof_capacity = int(usable_roof_area_m2 // _M2_PER_PANEL)

        # ── 3. Panels needed for target amperes ──────────────────────────────
        # Load in kW at 220V: kW = A × V / 1000 = A × 0.22
        target_kw = req.required_amperes * _KW_PER_AMPERE_220V
        # Account for inverter efficiency & temperature derating
        effective_factor = _INVERTER_EFFICIENCY * _TEMP_DERATING
        # Effective power per panel (kW)
        panel_kw = (req.panel_wattage_w / 1000.0) * effective_factor
        # Panels needed
        recommended_panels_count = max(1, math.ceil(target_kw / panel_kw))
        # Clamp to what the roof can hold
        recommended_panels_count = min(recommended_panels_count, max_panels_roof_capacity)

        roof_sufficient_for_target = (max_panels_roof_capacity >= recommended_panels_count)

        # ── 4. Generation metrics ─────────────────────────────────────────────
        system_capacity_kw = round(recommended_panels_count * req.panel_wattage_w / 1000.0, 3)
        # Effective generation per day (kWh) – rated × efficiency factors × peak sun hours
        daily_generation_kwh = round(system_capacity_kw * effective_factor * _BAGHDAD_PEAK_SUN_HOURS, 2)
        monthly_generation_kwh = round(daily_generation_kwh * 30.44, 2)

        # Delivered amperes at 220V
        delivered_kw = system_capacity_kw * effective_factor
        generated_amperes_iraqi_220v = round(delivered_kw * 1000.0 / _VOLTS_IRAQI, 2)

        # ── 5. Financial calculations (IQD & USD) ───────────────────────────
        total_panels_cost_iqd = round(recommended_panels_count * req.panel_unit_price_iqd, 0)
        # Full system = panels × 1.35 (inverter, mounting, cabling, labour)
        total_system_estimated_cost_iqd = round(total_panels_cost_iqd * 1.35, 0)
        total_system_estimated_cost_usd = round(total_system_estimated_cost_iqd / _IQD_PER_USD, 2)

        # Generator subscription savings
        generator_subscription_saved_iqd = round(
            req.required_amperes * req.ampere_price_iqd * req.months_count, 0
        )

        # Direct generator subscription savings
        total_financial_savings_period_iqd = generator_subscription_saved_iqd
        total_financial_savings_period_usd = round(
            total_financial_savings_period_iqd / _IQD_PER_USD, 2
        )

        # Clean payback period based on direct generator savings (months)
        monthly_savings = req.required_amperes * req.ampere_price_iqd
        payback_period_months = round(
            total_system_estimated_cost_iqd / max(monthly_savings, 1.0), 1
        )

        # ── 6. Environmental impact ──────────────────────────────────────────
        # Annual kWh avoided from generator
        annual_kwh_avoided = daily_generation_kwh * 365.0
        diesel_fuel_offset_liters = round(annual_kwh_avoided * _DIESEL_G_PER_KWH, 1)
        carbon_offset_tonnes_yr = round(
            diesel_fuel_offset_liters * _CO2_KG_PER_LITRE_DIESEL / 1000.0, 3
        )

        # ── 7. Live weather ──────────────────────────────────────────────────
        try:
            from app.services.weather_geo_service import WeatherAndGeoIntelligenceService
            weather = WeatherAndGeoIntelligenceService.get_live_weather(req.lat, req.lon)
        except Exception as exc:
            logger.warning("Weather fetch failed in solar engine: %s", exc)
            from app.services.weather_geo_service import WeatherAndGeoIntelligenceService
            weather = WeatherAndGeoIntelligenceService.get_live_weather.__func__(
                WeatherAndGeoIntelligenceService, req.lat, req.lon
            )

        # ── 8. Arabic executive report (Zero Emojis) ─────────────────────────
        executive_solar_report_ar = cls._build_arabic_report(
            req=req,
            roof_area_m2=roof_area_m2,
            usable_roof_area_m2=usable_roof_area_m2,
            max_panels_roof_capacity=max_panels_roof_capacity,
            recommended_panels_count=recommended_panels_count,
            roof_sufficient_for_target=roof_sufficient_for_target,
            system_capacity_kw=system_capacity_kw,
            generated_amperes_iraqi_220v=generated_amperes_iraqi_220v,
            daily_generation_kwh=daily_generation_kwh,
            monthly_generation_kwh=monthly_generation_kwh,
            total_panels_cost_iqd=total_panels_cost_iqd,
            total_system_estimated_cost_iqd=total_system_estimated_cost_iqd,
            total_system_estimated_cost_usd=total_system_estimated_cost_usd,
            generator_subscription_saved_iqd=generator_subscription_saved_iqd,
            total_financial_savings_period_iqd=total_financial_savings_period_iqd,
            total_financial_savings_period_usd=total_financial_savings_period_usd,
            payback_period_months=payback_period_months,
            diesel_fuel_offset_liters=diesel_fuel_offset_liters,
            carbon_offset_tonnes_yr=carbon_offset_tonnes_yr,
        )

        return SolarCalculationResponse(
            roof_area_m2=roof_area_m2,
            usable_roof_area_m2=usable_roof_area_m2,
            max_panels_roof_capacity=max_panels_roof_capacity,
            recommended_panels_count=recommended_panels_count,
            roof_sufficient_for_target=roof_sufficient_for_target,
            system_capacity_kw=system_capacity_kw,
            generated_amperes_iraqi_220v=generated_amperes_iraqi_220v,
            daily_generation_kwh=daily_generation_kwh,
            monthly_generation_kwh=monthly_generation_kwh,
            total_panels_cost_iqd=total_panels_cost_iqd,
            total_system_estimated_cost_iqd=total_system_estimated_cost_iqd,
            total_system_estimated_cost_usd=total_system_estimated_cost_usd,
            generator_subscription_saved_iqd=generator_subscription_saved_iqd,
            roof_shading_temp_drop_c=0.0,
            ac_cooling_bonus_saved_iqd=0.0,
            total_financial_savings_period_iqd=total_financial_savings_period_iqd,
            total_financial_savings_period_usd=total_financial_savings_period_usd,
            payback_period_months=payback_period_months,
            diesel_fuel_offset_liters=diesel_fuel_offset_liters,
            carbon_offset_tonnes_yr=carbon_offset_tonnes_yr,
            weather=weather,
            executive_solar_report_ar=executive_solar_report_ar,
        )

    @staticmethod
    def _build_arabic_report(
        req: SolarCalculationRequest,
        roof_area_m2: float,
        usable_roof_area_m2: float,
        max_panels_roof_capacity: int,
        recommended_panels_count: int,
        roof_sufficient_for_target: bool,
        system_capacity_kw: float,
        generated_amperes_iraqi_220v: float,
        daily_generation_kwh: float,
        monthly_generation_kwh: float,
        total_panels_cost_iqd: float,
        total_system_estimated_cost_iqd: float,
        total_system_estimated_cost_usd: float,
        generator_subscription_saved_iqd: float,
        total_financial_savings_period_iqd: float,
        total_financial_savings_period_usd: float,
        payback_period_months: float,
        diesel_fuel_offset_liters: float,
        carbon_offset_tonnes_yr: float,
    ) -> str:
        roof_status = "كافية لاستيعاب اللوحات المطلوبة بالكامل" if roof_sufficient_for_target else \
            "المساحة غير كافية بالكامل - ينصح بتوسيع مساحة التثبيت أو تقليل الأمبيرات المطلوبة"

        return (
            f"--------------------------------------------------\n"
            f"التقرير الهندسي والمالي - منظومة الطاقة الشمسية للأسطح\n"
            f"منصة EcoSensing AI - بغداد، العراق\n"
            f"--------------------------------------------------\n\n"
            f"[1] مساحات السطح:\n"
            f"  - المساحة الإجمالية للسطح: {roof_area_m2:,.1f} م2\n"
            f"  - المساحة الصافية للاستخدام (مع خصم الارتدادات): {usable_roof_area_m2:,.1f} م2\n"
            f"  - أقصى سعة استيعابية للسطح: {max_panels_roof_capacity} لوحة\n"
            f"  - تقييم السطح: {roof_status}\n\n"
            f"[2] متطلبات الطاقة والتوليد الفعلي:\n"
            f"  - الأمبيرات المستهدفة (استبدال المولدة الأهلية): {req.required_amperes:.1f} أمبير\n"
            f"  - عدد ألواح الطاقة الشمسية (550W): {recommended_panels_count} لوحة\n"
            f"  - قدرة المنظومة الإجمالية: {system_capacity_kw:.2f} كيلوواط\n"
            f"  - الأمبيرات الناتجة الفعلية (220V): {generated_amperes_iraqi_220v:.2f} أمبير\n"
            f"  - التوليد اليومي (بغداد - 5.8 ساعة ذروة): {daily_generation_kwh:.2f} كيلوواط/ساعة\n"
            f"  - التوليد الشهري التقديري: {monthly_generation_kwh:.2f} كيلوواط/ساعة\n\n"
            f"[3] التحليل المالي وتوفير اشتراك المولدة:\n"
            f"  - كلفة الألواح الشمسية: {total_panels_cost_iqd:,.0f} دينار عراقي\n"
            f"  - كلفة المنظومة الكاملة (مع العاكس والكابلات والهياكل): {total_system_estimated_cost_iqd:,.0f} دينار عراقي (${total_system_estimated_cost_usd:,.2f})\n"
            f"  - التوفير المالي من اشتراك المولدة الأهلية خلال {req.months_count} شهر: {generator_subscription_saved_iqd:,.0f} دينار عراقي (${total_financial_savings_period_usd:,.2f})\n"
            f"  - فترة استرداد رأس المال: {payback_period_months:.1f} شهر\n\n"
            f"[4] الأثر البيئي السنوي:\n"
            f"  - ديزل المولدة الموفر سنوياً: {diesel_fuel_offset_liters:,.1f} لتر/سنة\n"
            f"  - الكربون المعادل الممتص: {carbon_offset_tonnes_yr:.3f} طن CO2/سنة\n"
            f"--------------------------------------------------"
        )
