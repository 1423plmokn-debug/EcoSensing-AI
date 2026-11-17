"""
EcoSensing AI - Urban Microclimate & Field Sentinel
Pydantic Schemas — Phase 1 Upgrade
Academic Affiliation: Middle Technical University / Polytechnic College /
  Department of Electronic Engineering Technologies and Artificial Intelligence
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY SCHEMAS (preserved for backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────

class TreeSpec(BaseModel):
    """Botanical specifications for climate-resilient Iraqi tree species."""
    name_ar: str = Field(..., description="Arabic common name")
    name_en: str = Field(..., description="English common name")
    scientific_name: str = Field(..., description="Binomial botanical name")
    drought_tolerance: str = Field(..., description="Drought resistance level")
    salinity_tolerance: str = Field(..., description="Soil and water salinity tolerance")
    water_liters_per_week: float = Field(..., ge=0.0, description="Average water requirement per tree per week in liters")
    canopy_diameter_m: float = Field(..., gt=0.0, description="Mature canopy crown diameter in meters")
    co2_kg_per_year: float = Field(..., ge=0.0, description="Annual carbon dioxide sequestration per tree in kg")
    cooling_radius_m: float = Field(..., gt=0.0, description="Microclimate thermal mitigation influence radius in meters")


class SimulationRequest(BaseModel):
    """Dynamic simulation parameters supporting any custom land area and thermal baseline."""
    area_dunums: float = Field(6.0, gt=0.0, description="Land area in Iraqi dunums (1 dunum = 2,500 m²)")
    current_surface_temp_c: float = Field(44.5, ge=20.0, le=60.0, description="Baseline land surface temperature in Celsius")
    target_crop_type: str = Field("mixed_orchard", description="Target agricultural crop or green corridor type")
    target_governorate: str = Field("Baghdad", description="Target Iraqi governorate")


class TreeAllocationPlan(BaseModel):
    """Allocation distribution and resource footprint for an allocated tree species."""
    tree_name_ar: str = Field(..., description="Arabic name of allocated tree species")
    tree_count: int = Field(..., ge=0, description="Allocated number of trees")
    total_weekly_water_liters: float = Field(..., ge=0.0, description="Total weekly irrigation requirement in liters")
    total_co2_kg_year: float = Field(..., ge=0.0, description="Total annual CO2 sequestration in kg")


class SimulationResponse(BaseModel):
    """Unified dynamic simulation, water conservation, thermal mitigation, and ROI response."""
    area_dunums: float = Field(..., description="Land area in dunums")
    area_m2: float = Field(..., description="Land area in square meters (area_dunums * 2500)")
    baseline_weekly_water_liters: float = Field(..., description="Conventional flood irrigation weekly water usage in liters")
    optimized_weekly_water_liters: float = Field(..., description="EcoSensing precision micro-irrigation weekly usage in liters")
    water_saved_liters_weekly: float = Field(..., description="Volume of water saved weekly in liters")
    water_saving_pct: float = Field(..., description="Percentage of irrigation water saved")
    lst_before_c: float = Field(..., description="Baseline surface temperature before intervention in Celsius")
    lst_after_c: float = Field(..., description="Simulated cooled surface temperature after intervention in Celsius")
    lst_drop_c: float = Field(..., description="Thermal reduction drop in Celsius")
    early_damage_before_pct: float = Field(..., description="Crop stress & damage risk before intervention (%)")
    early_damage_after_pct: float = Field(..., description="Crop stress & damage risk after intervention (%)")
    annual_co2_offset_tonnes: float = Field(..., description="Net annual carbon offset in metric tonnes")
    annual_financial_savings_iqd: float = Field(..., description="Annual economic savings in Iraqi Dinars (IQD)")
    annual_financial_savings_usd: float = Field(..., description="Annual economic savings converted to USD ($1 = 1320 IQD)")
    recommended_trees: List[TreeAllocationPlan] = Field(..., description="Species-specific agroforestry tree allocation breakdown")
    green_corridor_recommended_spacing_m: float = Field(..., description="Optimal agroforestry planting spacing in meters")
    executive_summary_ar: str = Field(..., description="Comprehensive Arabic engineering executive summary")


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 UPGRADE: LIVE WEATHER & GEOCODING SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class LiveWeatherResponse(BaseModel):
    """Real-time meteorological data for any Baghdad/Iraq coordinate."""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    location_name_ar: str = Field(..., description="Arabic location name")
    air_temp_c: float = Field(..., description="Air temperature at 2m height (°C)")
    soil_temp_c: float = Field(..., description="Soil surface temperature (°C)")
    surface_lst_c: float = Field(..., description="Land Surface Temperature – thermal urban surface (°C)")
    relative_humidity_pct: float = Field(..., description="Relative humidity (%)")
    wind_speed_kmh: float = Field(..., description="Wind speed at 10m (km/h)")
    solar_radiation_wm2: float = Field(..., description="Shortwave solar radiation (W/m²)")
    dust_aerosol_status_ar: str = Field(..., description="Iraqi dust/aerosol condition in Arabic")
    timestamp_str: str = Field(..., description="ISO-8601 timestamp string")
    source: str = Field(..., description="Data source identifier")


class PollutionTelemetry(BaseModel):
    """
    Live Copernicus CAMS Atmospheric & Urban Heat Island Sentinel Telemetry
    with International Engineering Mitigation Benchmark Protocols.
    """
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    location_name_ar: str = Field(..., description="Arabic location name")
    aqi_european: int = Field(..., description="European Air Quality Index (0-100+)")
    aqi_status_ar: str = Field(..., description="European AQI condition in Arabic")
    aqi_color_hex: str = Field(..., description="Color hex code for AQI badge")
    pm10_ugm3: float = Field(..., description="Particulate Matter PM10 (µg/m³)")
    pm10_status_ar: str = Field(..., description="PM10 status description in Arabic")
    pm25_ugm3: float = Field(..., description="Fine Particulate Matter PM2.5 (µg/m³)")
    pm25_status_ar: str = Field(..., description="PM2.5 status description in Arabic")
    no2_ugm3: float = Field(..., description="Nitrogen Dioxide NO₂ (µg/m³)")
    so2_ugm3: float = Field(..., description="Sulphur Dioxide SO₂ (µg/m³)")
    surface_lst_c: float = Field(..., description="Thermal surface temperature (°C)")
    uhi_anomaly_c: float = Field(..., description="Urban Heat Island thermal anomaly (°C)")
    dominant_hazard_code: str = Field(..., description="'INDUSTRIAL_PM25' | 'URBAN_HEAT_STAGNATION' | 'DUST_STORM_PM10'")
    benchmark_country_code: str = Field(..., description="'SINGAPORE' | 'GERMANY' | 'UAE_CHINA'")
    benchmark_country_ar: str = Field(..., description="Country and institution name in Arabic")
    benchmark_project_title_ar: str = Field(..., description="Project / scientific protocol title in Arabic")
    health_risk_assessment_ar: str = Field(..., description="Medical & public health impact statement in Arabic")
    engineering_mitigation_protocol_ar: str = Field(..., description="Step-by-step engineering buffer protocol in Arabic")
    recommended_buffer_specs_ar: str = Field(..., description="Green buffer dimensions & design specifications in Arabic")
    target_species_ar: List[str] = Field(..., description="Optimal agroforestry species for mitigation")
    expected_pm_reduction_pct: float = Field(..., description="Expected particulate matter reduction percentage")
    expected_lst_drop_c: float = Field(..., description="Expected microclimate surface cooling in °C")



# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 UPGRADE: SMART LAND SUITABILITY SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class LandInspectionRequest(BaseModel):
    """Request payload for smart land suitability analysis."""
    lat: float = Field(..., description="Centre latitude of the parcel")
    lon: float = Field(..., description="Centre longitude of the parcel")
    polygon_coords: List[List[float]] = Field(
        default=[],
        description="Ordered list of [lat, lon] vertices defining the parcel polygon (3+ points for geodesic area)"
    )
    location_name_ar: str = Field("بغداد", description="Human-readable Arabic place name")
    custom_area_m2: Optional[float] = Field(
        None, ge=1.0,
        description="Override area in m² when no polygon is drawn (e.g. single-click point inspection)"
    )


class LandInspectionResponse(BaseModel):
    """Comprehensive smart land-use suitability analysis result."""
    lat: float
    lon: float
    location_name_ar: str

    # Area metrics
    total_selected_area_m2: float = Field(..., description="Total inspected area in square metres")
    total_selected_area_dunums: float = Field(..., description="Total inspected area in Iraqi dunums (÷2500)")

    # Land-use breakdown
    building_road_coverage_pct: float = Field(..., description="Percentage covered by buildings / roads")
    existing_green_coverage_pct: float = Field(..., description="Percentage already vegetated")
    plantable_barren_coverage_pct: float = Field(..., description="Percentage of open barren plantable land")

    # Net plantable
    net_plantable_area_m2: float = Field(..., description="Net plantable area (m²)")
    net_plantable_area_dunums: float = Field(..., description="Net plantable area (dunums)")

    # Suitability verdict
    suitability_code: str = Field(
        ...,
        description="One of: SUITABLE_BARREN_LAND | REJECTED_BUILDING_OR_ROAD | PARTIAL_PERIMETER_ONLY | EXISTING_GREEN_OPTIMIZE"
    )
    suitability_title_ar: str = Field(..., description="Short Arabic verdict title")
    suitability_explanation_ar: str = Field(..., description="Full Arabic engineering explanation")

    can_plant_trees: bool = Field(..., description="Whether direct tree planting is feasible")
    suggest_solar_rooftop_mode: bool = Field(..., description="Whether solar rooftop mode is recommended instead")

    # Embedded sub-responses
    weather: Optional[LiveWeatherResponse] = None
    simulation: Optional[SimulationResponse] = Field(None, description="Simulation metrics (only when can_plant_trees=True)")

    # Pedological & Botanical Fields (Agent 1)
    soil_profile: Optional[Dict[str, Any]] = None
    soil_type_title_ar: Optional[str] = None
    soil_salinity_ece_dsm: Optional[float] = None
    soil_ph: Optional[float] = None
    soil_remediation_protocol_ar: Optional[str] = None
    selected_species: Optional[List[Dict[str, Any]]] = None
    agronomic_executive_report_ar: Optional[str] = None
    live_soil_telemetry: Optional[Dict[str, Any]] = None
    geojson_trees: Optional[Dict[str, Any]] = None

    # Geospatial planting nodes (empty when rejected)
    valid_tree_nodes: List[Dict[str, Any]] = Field(
        default=[],
        description="Geospatial planting nodes distributed inside barren polygon (never on rooftops)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 UPGRADE: SOLAR ROOFTOP & GENERATOR AMPERAGE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class SolarCalculationRequest(BaseModel):
    """Solar rooftop & Iraqi generator amperage calculation request."""
    lat: float = Field(33.3152, description="Latitude for solar irradiance lookup")
    lon: float = Field(44.3661, description="Longitude for solar irradiance lookup")
    roof_area_m2: float = Field(180.0, gt=0.0, description="Gross roof area (m²) – overridden by polygon if provided")
    polygon_coords: List[List[float]] = Field(
        default=[],
        description="Optional polygon drawn on map to derive exact roof area geodesically"
    )
    required_amperes: float = Field(12.0, gt=0.0, description="Target generator ampere subscription to replace (A)")
    ampere_price_iqd: float = Field(15000.0, gt=0.0, description="Monthly cost per ampere from neighborhood generator (IQD)")
    months_count: int = Field(12, ge=1, le=60, description="Number of months for financial savings projection")
    panel_unit_price_iqd: float = Field(165000.0, gt=0.0, description="Unit price of one 550W panel (IQD)")
    panel_wattage_w: int = Field(550, gt=0, description="Rated wattage of each solar panel (W)")


class SolarCalculationResponse(BaseModel):
    """Full solar rooftop ROI, generator replacement, and environmental impact report."""
    roof_area_m2: float = Field(..., description="Input gross roof area (m²)")
    usable_roof_area_m2: float = Field(..., description="Usable area after parapets/tanks/corridors (×0.72)")

    max_panels_roof_capacity: int = Field(..., description="Maximum panels the roof can physically hold")
    recommended_panels_count: int = Field(..., description="Panels required to deliver target amperes")
    roof_sufficient_for_target: bool = Field(..., description="Whether the roof can fit the recommended panel count")

    system_capacity_kw: float = Field(..., description="Total rated system capacity (kW)")
    generated_amperes_iraqi_220v: float = Field(..., description="Amperes delivered at 220V Iraqi grid")

    daily_generation_kwh: float = Field(..., description="Daily energy generation (kWh, Baghdad 5.8 peak-sun-hours)")
    monthly_generation_kwh: float = Field(..., description="Monthly energy generation (kWh)")

    total_panels_cost_iqd: float = Field(..., description="Pure panel cost (IQD)")
    total_system_estimated_cost_iqd: float = Field(..., description="Full system cost including inverter/mounting/cabling (IQD)")
    total_system_estimated_cost_usd: float = Field(..., description="Full system cost in USD (÷1320)")

    generator_subscription_saved_iqd: float = Field(..., description="Generator subscription savings over the period (IQD)")
    roof_shading_temp_drop_c: float = Field(3.2, description="Roof slab cooling from panel shading (°C)")
    ac_cooling_bonus_saved_iqd: float = Field(..., description="Air-conditioning savings from cooler roof slab (IQD)")
    total_financial_savings_period_iqd: float = Field(..., description="Total financial savings over the period (IQD)")
    total_financial_savings_period_usd: float = Field(..., description="Total financial savings in USD")

    payback_period_months: float = Field(..., description="System payback period (months)")

    diesel_fuel_offset_liters: float = Field(..., description="Neighbourhood generator diesel saved (litres)")
    carbon_offset_tonnes_yr: float = Field(..., description="Annual CO₂ prevented (tonnes/year)")

    weather: LiveWeatherResponse
    executive_solar_report_ar: str = Field(..., description="Rich Arabic engineering summary")


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 UPGRADE: 3-LAYER CONTEXT-AWARE CHATBOT SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ChatbotRequest(BaseModel):
    """Iraqi context-aware chatbot request carrying live screen telemetry."""
    message: str = Field(..., description="User's question in Arabic or English")
    active_section: str = Field(
        "afforestation",
        description="Active UI tab: 'afforestation' | 'solar' | 'vision'"
    )
    live_telemetry: Dict[str, Any] = Field(
        default={},
        description="Live screen data: selected location, area, weather, simulation, solar metrics, diagnosis, etc."
    )
    history: List[Dict[str, Any]] = Field(
        default=[],
        description="Conversation history list of {role, content} dicts"
    )


class ChatbotResponse(BaseModel):
    """Chatbot reply with section detection and grounded context verification."""
    reply_ar: str = Field(..., description="Full Arabic (or bilingual) reply from the chatbot")
    active_section_detected: str = Field(..., description="Detected/confirmed active UI section")
    context_verified: bool = Field(..., description="True when live_telemetry data was successfully grounded")
    suggested_questions: List[str] = Field(
        default=[],
        description="3 follow-up questions to prompt the user"
    )
    engine_source: str = Field(..., description="'LIVE_GEMINI' | 'DETERMINISTIC_FALLBACK'")


class PlaceSearchResult(BaseModel):
    """Geocoding place search item."""
    name_ar: str
    lat: float
    lon: float
    display_name: str
    type: str = "landmark"


class PlaceSearchResponse(BaseModel):
    """Geocoding place search results list."""
    query: str
    count: int
    results: List[PlaceSearchResult]


# Convenient aliases
LandSuitabilityResponse = LandInspectionResponse
ChatRequest = ChatbotRequest
ChatResponse = ChatbotResponse
ChatMessage = Dict[str, Any]


class ComprehensiveInspectionRequest(BaseModel):
    """Unified concurrent parcel inspection request for Agents 1, 2, and 3."""
    lat: float = Field(33.3152, description="Latitude")
    lon: float = Field(44.3661, description="Longitude")
    polygon_coords: List[List[float]] = Field(default_factory=list, description="Optional boundary coordinates")
    location_name_ar: Optional[str] = Field(None, description="Location/neighborhood name in Arabic")
    custom_area_m2: Optional[float] = Field(None, description="Optional area in m²")
    weather_data: Optional[Dict[str, Any]] = Field(None, description="Optional pre-fetched weather/telemetry")
    soil_telemetry: Optional[Dict[str, Any]] = Field(None, description="Synchronized ESP32 hardware soil telemetry")


class LabConsultRequest(BaseModel):
    """Interactive Clinical Laboratory Consultation Request."""
    session_id: str = Field("active_field_session", description="Unique session ID")
    user_message: Optional[str] = Field(None, description="User follow-up message or diagnostic observation")
    message: Optional[str] = Field(None, description="Alias for user_message")
    question: Optional[str] = Field(None, description="Alias for user_message")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Client conversation history")
    soil_telemetry: Optional[Dict[str, Any]] = Field(None, description="Synchronized ESP32 hardware soil telemetry")


class LabResetRequest(BaseModel):
    """Reset lab session request."""
    session_id: str = Field("active_field_session", description="Session ID to reset")


class ESP32IngestRequest(BaseModel):
    """ESP32 Telemetry Ingestion Request."""
    adc_raw: Optional[int] = Field(None, description="Raw 12-bit ADC reading (0-4095)")
    voltage_v: Optional[float] = Field(None, description="Analog voltage in Volts (1.20 - 2.50V)")
    vwc_pct: Optional[float] = Field(None, description="Direct Volumetric Water Content (%)")
    port: Optional[str] = Field(None, description="COM port identifier")


class ESP32LockDepthRequest(BaseModel):
    """Lock probe reading at specific depth."""
    depth_key: Optional[str] = Field(None, description="'surface_5cm', 'mid_15cm', or 'root_25cm'")
    depth: Optional[str] = Field(None, description="Alias for depth_key")
    vwc_pct: Optional[float] = Field(None, description="Optional reading, uses live VWC if omitted")
    session_id: Optional[str] = Field("active_field_session", description="Target session ID")


# ─────────────────────────────────────────────────────────────────────────────
# WI-FI WIRELESS ESP32 SOIL SENTINEL – PUSH PAYLOAD SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class ESP32SoilPayload(BaseModel):
    """
    Wireless Wi-Fi telemetry payload pushed by the ESP32 Soil Sentinel node
    (device_id: ESP32_SOIL_NODE_01) over HTTP POST to /api/v1/esp32/push.

    Field-calibrated for Mesopotamian Alluvial Clay-Loam soils.
    All ADC values are 12-bit (0–4095) on the GPIO-32 input channel.
    """
    device_id: str = Field("ESP32_SOIL_NODE_01", description="Unique hardware node identifier")
    gpio_pin: int = Field(32, description="GPIO pin used for ADC sampling (default: GPIO 32)")
    sample_count: int = Field(32, description="Number of ADC samples averaged per reading")

    # Live sensor measurements
    raw_adc: float = Field(..., description="Unfiltered 12-bit ADC value (0–4095)")
    filtered_adc: float = Field(..., description="Moving-average filtered ADC value")
    voltage_mv: float = Field(..., description="Sensor analog voltage in millivolts")
    moisture_pct: float = Field(..., description="Soil moisture percentage (0–100%)")
    soil_status: str = Field(..., description="Human-readable soil moisture status label")

    # Calibration metadata
    calibration_status: str = Field("FACTORY_DEFAULT", description="Calibration state: FACTORY_DEFAULT | USER_CALIBRATED")
    dry_ref_adc: float = Field(2850.0, description="ADC reference value for 0% moisture (dry)")
    wet_ref_adc: float = Field(1150.0, description="ADC reference value for 100% moisture (saturated)")

    # Network diagnostics
    wifi_rssi: int = Field(0, description="Wi-Fi signal strength in dBm (negative; 0 = not reported)")


class StartExperimentRequest(BaseModel):
    """Payload to start a real-time scientific experiment logging session."""
    experiment_name: str = Field("Soil_Calibration_Run_01", description="Identifier for this experimental run")
    notes: Optional[str] = Field(None, description="Optional researcher notes")

