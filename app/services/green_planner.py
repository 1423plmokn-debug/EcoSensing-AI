from typing import List, Dict
from app.models.schemas import TreeSpec, TreeAllocationPlan


class GreenCorridorPlanner:
    """
    Authoritative Botanical Agroforestry Selector & Green Corridor Planner for Iraq.
    Curates species proven to thrive in severe Iraqi microclimate conditions (heat > 45°C, high evapotranspiration, salinity).
    """

    # Authoritative Botanical Catalog of Iraqi Climate-Resilient Trees
    BOTANICAL_CATALOG: Dict[str, TreeSpec] = {
        "sidr": TreeSpec(
            name_ar="السدر (النبق)",
            name_en="Christ's Thorn Jujube",
            scientific_name="Ziziphus spina-christi",
            drought_tolerance="استثنائية (Extreme Drought Resilience)",
            salinity_tolerance="عالية جداً حتى 8000 PPM",
            water_liters_per_week=45.0,
            canopy_diameter_m=6.0,
            co2_kg_per_year=28.0,
            cooling_radius_m=7.5,
        ),
        "neem": TreeSpec(
            name_ar="النيم الهندي",
            name_en="Neem Tree",
            scientific_name="Azadirachta indica",
            drought_tolerance="عالية جداً (Very High)",
            salinity_tolerance="متوسطة إلى عالية",
            water_liters_per_week=55.0,
            canopy_diameter_m=7.0,
            co2_kg_per_year=32.0,
            cooling_radius_m=8.0,
        ),
        "poinciana": TreeSpec(
            name_ar="البونسيانا الملكية",
            name_en="Royal Poinciana / Flamboyant",
            scientific_name="Delonix regia",
            drought_tolerance="عالية (High)",
            salinity_tolerance="متوسطة",
            water_liters_per_week=70.0,
            canopy_diameter_m=9.0,
            co2_kg_per_year=35.0,
            cooling_radius_m=10.0,
        ),
        "acacia": TreeSpec(
            name_ar="الأكاسيا / الطلح الصحراوي",
            name_en="Blue-leaved Wattle / Desert Acacia",
            scientific_name="Acacia saligna / tortilis",
            drought_tolerance="قصوى تتحمل درجات حرارة فوق 50 مئوية",
            salinity_tolerance="عالية مع تثبيت النيتروجين الحيوي",
            water_liters_per_week=35.0,
            canopy_diameter_m=5.0,
            co2_kg_per_year=22.0,
            cooling_radius_m=6.5,
        ),
    }

    # Recommended agroforestry spacing for mixed canopy corridors
    RECOMMENDED_SPACING_M: float = 6.5

    @classmethod
    def plan_green_corridor(
        cls,
        area_dunums: float,
        lst_intensity_c: float = 44.5,
    ) -> List[TreeAllocationPlan]:
        """
        Calculate and optimize tree species allocation based on land area and thermal stress:
        - Density: 25 - 40 trees/dunum (calibrated to 30 trees/dunum at baseline 44.5 C).
        - Stratified microclimate allocation:
          * 40% السدر (Sidr): Windbreak, outer buffer, extreme salinity/drought shield.
          * 30% النيم (Neem): Mid-layer microclimate barrier & biological pest deterrent.
          * 20% البونسيانا (Poinciana): Broad umbrella canopy for core shade & urban cooling.
          * 10% الأكاسيا (Acacia): Boundary edge heat-break & soil nitrogen restoration.
        """
        # Dynamic agroforestry density scaling with heat severity
        # Baseline at 44.5 C is 30.0 trees/dunum
        temp_delta = lst_intensity_c - 44.5
        density_per_dunum = 30.0 + min(max(temp_delta * 1.5, -5.0), 10.0)
        density_per_dunum = round(density_per_dunum, 1)

        total_trees = max(4, int(round(area_dunums * density_per_dunum)))

        # Multi-layer agroforestry distribution
        count_sidr = int(round(total_trees * 0.40))
        count_neem = int(round(total_trees * 0.30))
        count_poinciana = int(round(total_trees * 0.20))
        # Ensure exact tree count conservation
        count_acacia = total_trees - (count_sidr + count_neem + count_poinciana)

        allocations: List[TreeAllocationPlan] = []

        species_mapping = [
            ("sidr", count_sidr),
            ("neem", count_neem),
            ("poinciana", count_poinciana),
            ("acacia", count_acacia),
        ]

        for key, count in species_mapping:
            spec = cls.BOTANICAL_CATALOG[key]
            total_water = round(count * spec.water_liters_per_week, 1)
            total_co2 = round(count * spec.co2_kg_per_year, 1)

            allocations.append(
                TreeAllocationPlan(
                    tree_name_ar=spec.name_ar,
                    tree_count=count,
                    total_weekly_water_liters=total_water,
                    total_co2_kg_year=total_co2,
                )
            )

        return allocations
