from typing import List, Dict, Any
from app.models.schemas import TreeAllocationPlan


class CarbonRoiCalculator:
    """
    Carbon Sequestration & Financial ROI Calculator for Iraqi Agroforestry & Micro-Irrigation.
    Integrates water-pumping energy savings, tariff avoidance, and Voluntary Carbon Market (VCM) credits.
    """

    # Economic parameters calibrated to Iraqi agricultural economics
    USD_TO_IQD_RATE: float = 1320.0
    WATER_SAVING_VALUE_IQD_PER_LITER: float = 2.5  # Pumping fuel, diesel, electricity, and treatment tariff
    VCM_CARBON_PRICE_USD_PER_TONNE: float = 18.0   # Voluntary Carbon Market benchmark credit price
    SOIL_CARBON_SEQUESTRATION_FACTOR: float = 1.15 # Additional 15% carbon retention from shaded, cooled soil biomass

    @classmethod
    def calculate_roi(
        cls,
        water_saved_liters_weekly: float,
        tree_plans: List[TreeAllocationPlan],
    ) -> Dict[str, float]:
        """
        Compute annual economic returns and carbon offset:
        - Annual water savings: 52 weeks * weekly liters saved * 2.5 IQD/L.
        - Total tree carbon sequestration + 15% soil microclimate retention factor.
        - Voluntary Carbon Market credits: $18 USD / metric tonne CO2.
        - Total financial yield expressed in both IQD and USD (1 USD = 1320 IQD).
        """
        # 1. Annual Water & Pumping Fuel Savings
        annual_water_saved_liters = water_saved_liters_weekly * 52.0
        annual_water_savings_iqd = annual_water_saved_liters * cls.WATER_SAVING_VALUE_IQD_PER_LITER

        # 2. Carbon Sequestration (Trees + Soil cooling bonus)
        trees_co2_kg = sum(plan.total_co2_kg_year for plan in tree_plans)
        total_co2_kg = trees_co2_kg * cls.SOIL_CARBON_SEQUESTRATION_FACTOR
        annual_co2_offset_tonnes = total_co2_kg / 1000.0

        # 3. Carbon Credit Value
        carbon_revenue_usd = annual_co2_offset_tonnes * cls.VCM_CARBON_PRICE_USD_PER_TONNE
        carbon_revenue_iqd = carbon_revenue_usd * cls.USD_TO_IQD_RATE

        # 4. Total Combined Financial Savings
        total_savings_iqd = annual_water_savings_iqd + carbon_revenue_iqd
        total_savings_usd = total_savings_iqd / cls.USD_TO_IQD_RATE

        return {
            "annual_co2_offset_tonnes": round(annual_co2_offset_tonnes, 2),
            "annual_financial_savings_iqd": round(total_savings_iqd, 2),
            "annual_financial_savings_usd": round(total_savings_usd, 2),
            "annual_water_savings_iqd": round(annual_water_savings_iqd, 2),
            "carbon_revenue_usd": round(carbon_revenue_usd, 2),
        }
