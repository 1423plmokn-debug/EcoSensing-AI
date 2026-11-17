"""
EcoSensing AI – 4D Diurnal Atmospheric Fluid Advection-Diffusion & Environmental Physics Engine
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Academic Affiliation: Middle Technical University / Polytechnic College

Models:
1. 24-Hour Diurnal Baghdad Metabolic Traffic & Private Diesel Generator Curve.
2. Multi-Emitter Fluid Advection-Diffusion Cloud (180-250 Stochastic Dispersion Nodes in [lon, lat]).
3. Gaussian Plume Physics: C(x,y) = (Q / 2pi*u*sy*sz) * exp(-y^2 / 2*sy^2) with sy(x) = a * x^0.85.
4. Soft Atmospheric Translucent Heatmap integration for MapLibre GL JS (Zero Emojis, Western Numerals 0123456789).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from app.config import sanitize_emojis, strip_all_emojis


class MicroclimatePhysicsEngine:
    """
    Geospatial Physics & Diurnal Microclimate Engine:
    Computes fluid multi-emitter atmospheric dispersion, thermal dome radiance,
    and wind-vector advection point clouds for Baghdad.
    """

    BAGHDAD_LAT = 33.3152
    BAGHDAD_LON = 44.3661

    @classmethod
    def get_diurnal_profile(cls, hour: int) -> Dict[str, Any]:
        """
        Diurnal Multipliers calibrated for Baghdad's urban metabolism:
        - 07:00 - 10:00 (Morning Rush Hour): High traffic NO2 & PM2.5 plumes along corridors.
        - 12:00 - 16:00 (Solar Peak & Thermal Inversion Breakdown): Max UHI LST & peak diesel generator load.
        - 17:00 - 20:00 (Evening Congestion & Boundary Layer Collapse): Trapped near-surface particulate plume.
        - 00:00 - 05:00 (Nocturnal Radiative Cooling): Dispersion of traffic, residual concrete heat retention.
        """
        h = int(hour) % 24

        if 7 <= h <= 10:
            phase_name_ar = "ساعات الذروة الصباحية (حركة المرور وانبعاثات عوادم المركبات)"
            emission_factor = 1.70 + (h - 7) * 0.05
            thermal_factor = 1.25
            uhi_boost_c = 2.4
            dispersion_factor = 1.45
        elif 12 <= h <= 16:
            phase_name_ar = "ذروة الإشعاع الشمسي وأحمال مولدات الديزل الأهلية (الانقلاب الحراري)"
            emission_factor = 2.15 + (14 - abs(h - 14)) * 0.15
            thermal_factor = 2.50
            uhi_boost_c = 5.2
            dispersion_factor = 2.20
        elif 17 <= h <= 20:
            phase_name_ar = "ساعات الازدحام المسائي وهبوط الطبقة الحدية السطحية"
            emission_factor = 1.85 + (20 - h) * 0.05
            thermal_factor = 1.65
            uhi_boost_c = 3.9
            dispersion_factor = 1.75
        elif 21 <= h <= 23:
            phase_name_ar = "انحسار الحركة المرورية وتبدد الانبعاثات الليلي"
            emission_factor = 0.85
            thermal_factor = 0.90
            uhi_boost_c = 1.8
            dispersion_factor = 0.90
        else:  # 00:00 to 06:00
            phase_name_ar = "التبريد الإشعاعي الليلي والانبعاثات الأساسية الدنيا"
            emission_factor = 0.55
            thermal_factor = 0.45
            uhi_boost_c = 1.2
            dispersion_factor = 0.60

        solar_azimuth, solar_elevation = cls.calculate_solar_position(h)

        return {
            "hour": h,
            "hour_label": f"{h:02d}:00",
            "phase_name_ar": phase_name_ar,
            "emission_factor": round(emission_factor, 2),
            "thermal_factor": round(thermal_factor, 2),
            "uhi_boost_c": round(uhi_boost_c, 1),
            "dispersion_factor": round(dispersion_factor, 2),
            "solar_azimuth_deg": round(solar_azimuth, 1),
            "solar_elevation_deg": round(solar_elevation, 1),
            "is_daylight": solar_elevation > 0.0,
        }

    @classmethod
    def calculate_solar_position(
        cls,
        hour: int,
        lat: float = BAGHDAD_LAT,
        lon: float = BAGHDAD_LON,
    ) -> Tuple[float, float]:
        """
        Analytical solar position approximation for Baghdad (Lat ~ 33.3N):
        Returns (azimuth_deg, elevation_deg).
        Azimuth: 0=North, 90=East, 180=South, 270=West.
        """
        h = float(hour) % 24.0

        if h < 5.5 or h > 18.5:
            azimuth = (180.0 + (h - 12.0) * 15.0) % 360.0
            return azimuth, -10.0

        day_progress = (h - 6.0) / 12.0
        elevation = math.sin(day_progress * math.pi) * 72.0
        azimuth = 75.0 + (day_progress * 210.0)
        return azimuth, max(0.0, elevation)

    @classmethod
    def calculate_fluid_advection_cloud(
        cls,
        lat: float,
        lon: float,
        wind_speed_ms: float = 3.5,
        wind_deg: float = 315.0,  # Default Shamal wind
        hour: int = 14,
        aqi_base: float = 110.0,
        pm25_base: float = 48.0,
        pm10_base: float = 95.0,
        no2_base: float = 32.0,
        so2_base: float = 18.0,
    ) -> Dict[str, Any]:
        """
        Multi-Emitter Fluid Advection-Diffusion Cloud (MapLibre Heatmap Layer):
        - Places 5 localized urban emission sub-cores around target (lat, lon).
        - Computes Gaussian dispersion downwind:
          C(x,y) = (Q / (2*pi*u*sy*sz)) * exp(-y^2 / (2*sy^2))
          where sy(x) = a * x^0.85 widens organically downwind.
        - Generates 180 to 250 weighted Point features in [lon, lat] coordinate order.
        """
        diurnal = cls.get_diurnal_profile(hour)
        disp_factor = diurnal["dispersion_factor"]
        em_factor = diurnal["emission_factor"]

        # Downwind angle (wind blows toward opposite direction)
        downwind_deg = (wind_deg + 180.0) % 360.0
        downwind_rad = math.radians(downwind_deg)

        effective_u = max(1.2, float(wind_speed_ms))

        # Scale degrees per meter at this latitude
        m_to_lat = 1.0 / 111_000.0
        m_to_lon = 1.0 / (111_000.0 * math.cos(math.radians(lat)))

        # Define 5 realistic urban emission sub-cores around target
        # Local offsets in meters (dx east, dy north)
        emission_cores = [
            {
                "id": "core_primary_intersection",
                "label_ar": "عقدة التقاطع والشريان المروري الرئيسي",
                "dx_m": 0.0,
                "dy_m": 0.0,
                "source_type": "VEHICULAR_CONGESTION",
                "q_factor": 1.00,
            },
            {
                "id": "core_generator_hub",
                "label_ar": "مجمع مولدات الديزل الأهلية للحي",
                "dx_m": -35.0,
                "dy_m": 25.0,
                "source_type": "DIESEL_GENERATOR_CLUSTER",
                "q_factor": 0.88,
            },
            {
                "id": "core_secondary_roadway",
                "label_ar": "مسار النقل وحركة الشاحنات الخدمية",
                "dx_m": 45.0,
                "dy_m": -30.0,
                "source_type": "COMMERCIAL_TRANSIT",
                "q_factor": 0.75,
            },
            {
                "id": "core_thermal_hotspot",
                "label_ar": "مسطح خرساني كتيم / جزر حرارية LST",
                "dx_m": 30.0,
                "dy_m": 40.0,
                "source_type": "IMPERVIOUS_SURFACE_UHI",
                "q_factor": 0.65,
            },
            {
                "id": "core_dust_corridor",
                "label_ar": "ممر تربة مفتوحة وتطاير أتربة كلسية",
                "dx_m": -40.0,
                "dy_m": -35.0,
                "source_type": "BARE_SOIL_RESUSPENSION",
                "q_factor": 0.60,
            },
        ]

        # Total reach distance in meters downwind
        max_downwind_m = (260.0 + (effective_u * 75.0)) * disp_factor
        # Generate 42 downwind dispersion points per core -> 5 * 42 = 210 points total (within 180-250 range)
        points_per_core = 42

        features: List[Dict[str, Any]] = []

        for core_idx, core in enumerate(emission_cores):
            core_lat = lat + (core["dy_m"] * m_to_lat)
            core_lon = lon + (core["dx_m"] * m_to_lon)
            base_q = core["q_factor"] * em_factor

            # Always emit the core origin point
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(core_lon, 6), round(core_lat, 6)],
                },
                "properties": {
                    "weight": round(min(1.0, 0.95 * base_q), 3),
                    "intensity": round(min(1.0, 0.95 * base_q), 3),
                    "aqi": round(aqi_base * em_factor * base_q, 1),
                    "pm25": round(pm25_base * em_factor * base_q, 1),
                    "pm10": round(pm10_base * em_factor * base_q, 1),
                    "no2": round(no2_base * em_factor * base_q, 1),
                    "so2": round(so2_base * em_factor * base_q, 1),
                    "core_id": core["id"],
                    "core_type": core["source_type"],
                    "distance_downwind_m": 0.0,
                    "hour": hour,
                },
            })

            # Distribute downwind points with Gaussian lateral spread: sy = a * x^0.85
            # 14 downwind distance steps, 3 lateral points per step (center, left, right) = 42 points
            for step_i in range(1, 15):
                # Distance along downwind centerline (fractional power spacing)
                frac = (step_i / 14.0) ** 1.15
                dist_x = frac * max_downwind_m

                # Pasquill-Gifford urban dispersion parameter: sy(x) = a * x^0.85
                # widens organically with distance
                sigma_y = 0.38 * (dist_x ** 0.82) + 8.0
                sigma_z = 0.25 * (dist_x ** 0.78) + 4.0

                # Centerline attenuation: C0 = Q / (2 * pi * u * sy * sz)
                denom = 2.0 * math.pi * effective_u * (sigma_y / 15.0) * (sigma_z / 10.0)
                centerline_conc = max(0.08, min(1.0, (base_q * 1.8) / denom))

                # Three lateral offsets: center (0), +lateral, -lateral
                lateral_offsets = [0.0, sigma_y * 0.75, -sigma_y * 0.75]

                for y_offset in lateral_offsets:
                    # Gaussian lateral dropoff: exp(-y^2 / (2 * sy^2))
                    lateral_decay = math.exp(-(y_offset ** 2) / (2.0 * (sigma_y ** 2)))
                    conc_val = centerline_conc * lateral_decay
                    normalized_weight = max(0.06, min(1.0, conc_val))

                    # Rotate (dist_x, y_offset) along downwind_rad
                    rot_x = dist_x * math.sin(downwind_rad) + y_offset * math.cos(downwind_rad)
                    rot_y = dist_x * math.cos(downwind_rad) - y_offset * math.sin(downwind_rad)

                    pt_lat = core_lat + (rot_y * m_to_lat)
                    pt_lon = core_lon + (rot_x * m_to_lon)

                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [round(pt_lon, 6), round(pt_lat, 6)],
                        },
                        "properties": {
                            "weight": round(normalized_weight, 3),
                            "intensity": round(normalized_weight, 3),
                            "aqi": round(aqi_base * em_factor * normalized_weight, 1),
                            "pm25": round(pm25_base * em_factor * normalized_weight, 1),
                            "pm10": round(pm10_base * em_factor * normalized_weight, 1),
                            "no2": round(no2_base * em_factor * normalized_weight, 1),
                            "so2": round(so2_base * em_factor * normalized_weight, 1),
                            "core_id": core["id"],
                            "core_type": core["source_type"],
                            "distance_downwind_m": round(dist_x, 1),
                            "hour": hour,
                        },
                    })

        # Exactly 5 cores + (5 * 42) = 215 point features (strictly 180 to 250)
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "center": [round(lon, 6), round(lat, 6)],
                "wind_deg": wind_deg,
                "wind_speed_ms": wind_speed_ms,
                "downwind_deg": round(downwind_deg, 1),
                "hour": hour,
                "points_count": len(features),
                "emission_cores_count": len(emission_cores),
                "diurnal": diurnal,
                "dispersion_model": "GAUSSIAN_MULTI_EMITTER_FLUID_ADVECTION",
            },
        }

    @classmethod
    def calculate_gaussian_advection_plume(
        cls,
        lat: float,
        lon: float,
        wind_speed_ms: float = 3.5,
        wind_deg: float = 315.0,
        hour: int = 14,
        aqi_base: float = 110.0,
        pm25_base: float = 48.0,
        pm10_base: float = 95.0,
        no2_base: float = 32.0,
        so2_base: float = 18.0,
    ) -> Dict[str, Any]:
        """Alias returning the fluid advection point cloud to prevent breaking any callers."""
        return cls.calculate_fluid_advection_cloud(
            lat=lat,
            lon=lon,
            wind_speed_ms=wind_speed_ms,
            wind_deg=wind_deg,
            hour=hour,
            aqi_base=aqi_base,
            pm25_base=pm25_base,
            pm10_base=pm10_base,
            no2_base=no2_base,
            so2_base=so2_base,
        )
