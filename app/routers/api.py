"""
EcoSensing AI – FastAPI REST Router (Phase 1 Upgrade)
Exposes all backend engines as clean REST endpoints.

Academic Affiliation: Middle Technical University / Polytechnic College
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

import base64
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from app.config import sanitize_emojis, settings, strip_all_emojis
import datetime

from app.models.schemas import (
    ChatbotRequest,
    ComprehensiveInspectionRequest,
    ESP32IngestRequest,
    ESP32LockDepthRequest,
    ESP32SoilPayload,
    LabConsultRequest,
    LabResetRequest,
    LandInspectionRequest,
    SimulationRequest,
    SimulationResponse,
    SolarCalculationRequest,
    StartExperimentRequest,
)
from app.services.ai_engine import EcoSensingAIEngine
from app.services.chatbot_engine import IraqiContextChatbotEngine
from app.services.esp32_soil_bridge import ESP32SoilBridge
from app.services.experiment_logger import ExperimentLogger
from app.services.laboratory_vision_agent import LaboratoryVisionAgent
from app.services.model_evaluator import ModelEvaluator
from app.services.physics_engine import MicroclimatePhysicsEngine
from app.services.pollution_mitigation_agent import PollutionMitigationAgent
from app.services.simulation_engine import DynamicThermalSimulator
from app.services.solar_engine import SolarRooftopAndGeneratorEngine
from app.services.weather_geo_service import WeatherAndGeoIntelligenceService

router = APIRouter(prefix="/api", tags=["EcoSensing AI API"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = BASE_DIR / "static" / "samples"

# ─────────────────────────────────────────────────────────────────────────────
# PRESET BAGHDAD SECTORS (Purged for live dynamic search)
# ─────────────────────────────────────────────────────────────────────────────
BAGHDAD_SECTORS: List[Dict[str, Any]] = []

# ─────────────────────────────────────────────────────────────────────────────
# WI-FI WIRELESS ESP32 SOIL SENTINEL – IN-MEMORY STATE
# Holds the latest packet pushed by ESP32_SOIL_NODE_01 over HTTP POST.
# Arbitration rule: Wi-Fi data takes priority when is_fresh=True (< 15 s old).
# ─────────────────────────────────────────────────────────────────────────────

LATEST_WIFI_SOIL_READING: Dict[str, Any] = {
    "connected": False,
    "mode": "WIFI_WIRELESS",
    "soil_status": "WAITING_FOR_SIGNAL",
    "last_updated_utc": None,
    # Sensor fields – populated on first successful POST
    "device_id": None,
    "gpio_pin": None,
    "sample_count": None,
    "raw_adc": None,
    "filtered_adc": None,
    "voltage_mv": None,
    "moisture_pct": None,
    "calibration_status": None,
    "dry_ref_adc": None,
    "wet_ref_adc": None,
    "wifi_rssi": None,
    "data_classification": None,
}


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY HELPER – Green Corridor Nodes (kept for /simulate backward compat)
# ─────────────────────────────────────────────────────────────────────────────

def generate_green_corridor_nodes(
    center_lat: float,
    center_lng: float,
    area_dunums: float,
    recommended_trees: list,
    spacing_m: float = 6.5,
) -> Dict[str, Any]:
    meters_to_lat = 1.0 / 111_000.0
    meters_to_lng = 1.0 / (111_000.0 * math.cos(math.radians(center_lat)))
    side_m = math.sqrt(area_dunums * 2500.0)
    half_side_lat = (side_m / 2.0) * meters_to_lat
    half_side_lng = (side_m / 2.0) * meters_to_lng

    polygon_coords = [
        [center_lat - half_side_lat, center_lng - half_side_lng],
        [center_lat - half_side_lat, center_lng + half_side_lng],
        [center_lat + half_side_lat, center_lng + half_side_lng],
        [center_lat + half_side_lat, center_lng - half_side_lng],
    ]

    color_map = {
        "السدر (النبق)": {"color": "#1B4D3E", "key": "sidr"},
        "النيم الهندي": {"color": "#2D5A43", "key": "neem"},
        "البونسيانا الملكية": {"color": "#B45309", "key": "poinciana"},
        "الأكاسيا / الطلح الصحراوي": {"color": "#65A30D", "key": "acacia"},
    }

    plotted_nodes = []
    step_lat = (spacing_m * 1.1) * meters_to_lat
    step_lng = (spacing_m * 1.1) * meters_to_lng
    trees_queue: List[str] = []
    for plan in recommended_trees:
        trees_queue.extend([plan.tree_name_ar] * plan.tree_count)

    rows = max(2, int(side_m / (spacing_m * 1.1)))
    cols = max(2, int(side_m / (spacing_m * 1.1)))
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= len(trees_queue):
                break
            tree_name = trees_queue[idx]
            n_lat = (center_lat - half_side_lat) + (r + 0.5) * step_lat
            n_lng = (center_lng - half_side_lng) + (c + 0.5) * step_lng
            meta = color_map.get(tree_name, {"color": "#2D5A43", "key": "tree"})
            plotted_nodes.append({
                "lat": round(n_lat, 6),
                "lng": round(n_lng, 6),
                "name_ar": tree_name,
                "species_key": meta["key"],
                "color": meta["color"],
                "is_perimeter": (r == 0 or r == rows - 1 or c == 0 or c == cols - 1),
            })
            idx += 1

    return {
        "center": [center_lat, center_lng],
        "boundary_polygon": polygon_coords,
        "thermal_radius_m": round(side_m * 0.75, 1),
        "total_plotted": len(plotted_nodes),
        "tree_nodes": plotted_nodes,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health")
def get_health_status():
    """Verify system health, active AI model, and institutional metadata."""
    return {
        "status": "operational",
        "project_name": settings.PROJECT_NAME,
        "institution": settings.INSTITUTION,
        "author": settings.AUTHOR,
        "active_groq_model": settings.GROQ_MODEL,
        "active_groq_vision_model": settings.GROQ_VISION_MODEL,
        "is_groq_configured": settings.is_groq_configured(),
        "environment": settings.APP_ENV,
        "port": settings.PORT,
    }


@router.get("/baghdad-sectors")
def get_baghdad_sectors():
    """Return preset coordinates across Baghdad for interactive satellite mapping."""
    return {"sectors": BAGHDAD_SECTORS}


# ── LEGACY: Dynamic Simulation ────────────────────────────────────────────────

@router.post("/simulate")
def run_simulation(
    req: SimulationRequest,
    lat: float = Query(33.2625, description="Center latitude for green corridor"),
    lng: float = Query(44.3100, description="Center longitude for green corridor"),
):
    """
    Run dynamic microclimate simulation for any custom land area and baseline temperature.
    Returns full agronomic, botanical, carbon ROI, and green corridor vector geometry.
    """
    sim_result = DynamicThermalSimulator.run_simulation(req)
    spatial_corridor = generate_green_corridor_nodes(
        center_lat=lat,
        center_lng=lng,
        area_dunums=req.area_dunums,
        recommended_trees=sim_result.recommended_trees,
        spacing_m=sim_result.green_corridor_recommended_spacing_m,
    )
    response_data = sim_result.model_dump()
    response_data["spatial_corridor"] = spatial_corridor
    response_data["data_classification"] = "Predicted / Simulated Data"
    response_data["data_provenance"] = {
        "engine": "DynamicThermalSimulator",
        "inputs": {
            "area_dunums": req.area_dunums,
            "current_surface_temp_c": getattr(req, "current_surface_temp_c", None),
        },
        "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    return response_data


# ── NEW: Live Weather ─────────────────────────────────────────────────────────

@router.get("/weather")
def get_live_weather(
    lat: float = Query(33.3152, description="Latitude"),
    lon: float = Query(44.3661, description="Longitude"),
    location_name_ar: str = Query("بغداد", description="Arabic location name"),
):
    """
    Fetch real-time meteorological data from Open-Meteo API for any Baghdad/Iraq coordinate.
    Returns air temperature, soil temperature, surface LST, humidity, wind, solar radiation,
    and Iraqi dust/aerosol status. Falls back to calibrated seasonal model when offline.
    """
    try:
        weather = WeatherAndGeoIntelligenceService.get_live_weather(lat, lon, location_name_ar)
        weather_dict = weather.model_dump()
        weather_dict["data_classification"] = "Measured / External API Data"
        weather_dict["data_provenance"] = {
            "provider": "Open-Meteo Meteorological Weather API",
            "upstream_endpoint": "https://api.open-meteo.com/v1/forecast",
            "parameters": [
                "temperature_2m",
                "relative_humidity_2m",
                "soil_temperature_0cm",
                "soil_temperature_6cm",
                "surface_pressure",
                "shortwave_radiation",
                "wind_speed_10m",
                "wind_direction_10m",
            ],
            "target_coordinates": {"lat": lat, "lon": lon},
            "location_name_ar": location_name_ar,
            "fetch_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        return weather_dict
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Weather service error: {str(exc)}",
        )


# ── NEW: Live Pollution Sentinel (Copernicus CAMS & Benchmark Protocols) ─────

@router.get("/pollution-sentinel")
def get_pollution_sentinel(
    lat: float = Query(33.3152, description="Latitude"),
    lon: float = Query(44.3661, description="Longitude"),
    location_name: Optional[str] = Query(None, description="Location name"),
    location_name_ar: Optional[str] = Query(None, description="Arabic location name"),
):
    """
    Live Copernicus CAMS Atmospheric & Urban Heat Island Sentinel:
    - Real-time European AQI, PM2.5, PM10, NO2, SO2, and Surface UHI Anomaly
    - Open Global Scientific Research Synthesis via Groq Llama-3.3-70B
    - Returns full engineering buffer and medical risk mitigation specifications (Zero Emojis)
    """
    loc_name = location_name or location_name_ar or "بغداد"
    try:
        sentinel_data = WeatherAndGeoIntelligenceService.get_pollution_sentinel(
            lat=lat, lon=lon, location_name_ar=loc_name
        )
        if hasattr(sentinel_data, "model_dump"):
            sentinel_data = sentinel_data.model_dump()
        sentinel_data["data_classification"] = "Measured / External API Data"
        sentinel_data["data_provenance"] = {
            "provider": "Copernicus Atmosphere Monitoring Service (CAMS) / Open-Meteo Air Quality",
            "upstream_endpoint": "https://air-quality-api.open-meteo.com/v1/air-quality",
            "parameters": ["european_aqi", "pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "dust"],
            "target_coordinates": {"lat": lat, "lon": lon},
            "location_name_ar": loc_name,
            "fetch_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        return sanitize_emojis(sentinel_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pollution sentinel service error: {str(exc)}",
        )


# ── NEW: Place Search ─────────────────────────────────────────────────────────

@router.get("/search-places")
def search_places(
    q: str = Query(..., min_length=1, description="Search query in Arabic or English"),
):
    """
    LocationIQ Forward Search & Autocomplete (Baghdad Only).
    """
    try:
        results = WeatherAndGeoIntelligenceService.search_places(q)
        return sanitize_emojis({
            "query": q,
            "results": results,
            "count": len(results),
            "data_classification": "Measured / External API Data",
            "data_provenance": {
                "provider": "LocationIQ / OpenStreetMap Geocoding API",
                "query": q,
                "fetch_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Place search error: {str(exc)}",
        )


# ── NEW: Smart Land Inspection ────────────────────────────────────────────────

@router.post("/inspect-land")
def inspect_land(req: LandInspectionRequest):
    """
    Pedological Botanical Land Inspector (Agent 1):
    - Geodesic area in m² and dunums
    - Building, rooftop, asphalt rejection
    - Baghdad pedological soil profiling and Groq Llama-3.3-70B plant matching
    - Zero Emojis
    """
    try:
        result = WeatherAndGeoIntelligenceService.inspect_land(req)
        if hasattr(result, "model_dump"):
            result = result.model_dump()
        result["data_classification"] = "Measured / External API Data"
        result["data_provenance"] = {
            "provider": "Open-Meteo Land Telemetry + Baghdad Pedological Soil Survey",
            "target_coordinates": {"lat": req.lat, "lon": req.lon},
            "fetch_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        return sanitize_emojis(result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Land inspection error: {str(exc)}",
        )


# ── NEW: Solar Rooftop & Generator Amperage Calculator ───────────────────────

@router.post("/solar-calculate")
def calculate_solar(req: SolarCalculationRequest):
    """
    Iraqi Solar Rooftop & Generator Replacement Engine:
    - Geodesic or manual roof area
    - Computes panels required for target ampere delivery at 220V
    - Full IQD/USD financial ROI (panels cost, full system, generator savings, AC cooling bonus)
    - Environmental: diesel offset + CO₂ tonnes/year
    - Returns rich Arabic executive engineering report
    """
    try:
        result = SolarRooftopAndGeneratorEngine.calculate_solar_roi(req)
        result_dict = result.model_dump()
        result_dict["data_classification"] = "Predicted / Simulated Data"
        result_dict["data_provenance"] = {
            "engine": "SolarRooftopAndGeneratorEngine",
            "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        return result_dict
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Solar calculation error: {str(exc)}",
        )


# ── NEW: 3-Layer Context-Aware Iraqi Chatbot ──────────────────────────────────

@router.post("/chat")
def chat_with_advisor(req: ChatbotRequest):
    """
    3-Layer Zero-Hallucination Iraqi Context-Aware Chatbot:
    - Layer 1: Parses live screen telemetry (location, area, weather, soil, trees, pollution, diagnosis)
    - Layer 2: Iraqi agronomic, microclimate & pedological engineering knowledge base
    - Layer 3: Groq Llama-3.3-70B with strict telemetry-grounded system prompt
    - Responds in Iraqi engineering Arabic (Zero Emojis)
    """
    try:
        result = IraqiContextChatbotEngine.chat(req)
        if hasattr(result, "model_dump"):
            result = result.model_dump()
        return sanitize_emojis(result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chatbot error: {str(exc)}",
        )


# ── Universal 4-Scene Agro-Ecological Vision & Diagnostic Endpoints ───────────

@router.post("/v1/analyze-vision")
@router.post("/analyze-image")
@router.post("/analyze")
async def analyze_field_image(
    request: Request,
    image: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    sample_type: Optional[str] = Query(
        None, description="'dust', 'water_stress', 'healthy', 'turfgrass', or 'soil'"
    ),
    region_name: str = Form("بغداد - محطة الفحص الميداني"),
    session_id: str = Form("default_lab_session"),
    session_action: str = Form("NEW_SESSION"),
    soil_telemetry: Optional[str] = Form(None),
):
    """
    Universal 4-Scene Agro-Ecological Vision & Diagnostic Endpoint:
    - Accepts multipart/form-data with key 'image' (or 'file') or sample_type query param.
    - Also accepts application/json with 'image_base64' or 'image' data URL.
    - Executes OpenCV foreground isolation, CLAHE+JET thermal heatmaps & ExG spectral maps.
    - Runs Groq Vision / LPU with resilient deterministic fallback.
    - Maintains stateful multi-sample forensic laboratory sessions (Sample 1 -> Sample 2).
    - Returns comprehensive clinical JSON report across Leaves, Trees, Turfgrass & Soil.
    """
    content_type = request.headers.get("content-type", "")
    image_bytes: Optional[bytes] = None
    target_region: str = region_name
    target_session_id: str = session_id or "default_lab_session"
    target_session_action: str = session_action or "NEW_SESSION"
    parsed_soil: Optional[Dict[str, Any]] = None

    # Also check query parameters for session control
    if request.query_params.get("session_id"):
        target_session_id = request.query_params["session_id"]
    if request.query_params.get("session_action"):
        target_session_action = request.query_params["session_action"]

    if "application/json" in content_type:
        try:
            body = await request.json()
            b64_val = body.get("image_base64") or body.get("image") or body.get("file")
            if b64_val:
                if "," in b64_val:
                    b64_val = b64_val.split(",", 1)[1]
                image_bytes = base64.b64decode(b64_val)
            if body.get("region_name"):
                target_region = body["region_name"]
            if body.get("session_id"):
                target_session_id = body["session_id"]
            if body.get("session_action"):
                target_session_action = body["session_action"]
            if not sample_type and body.get("sample_type"):
                sample_type = body["sample_type"]
            if body.get("soil_telemetry"):
                raw_st = body["soil_telemetry"]
                parsed_soil = raw_st if isinstance(raw_st, dict) else json.loads(raw_st)
        except Exception:
            pass

    if parsed_soil is None and soil_telemetry:
        try:
            parsed_soil = json.loads(soil_telemetry) if isinstance(soil_telemetry, str) else soil_telemetry
        except Exception:
            parsed_soil = None

    # Dual-safety auto-hydration from ESP32SoilBridge if soil telemetry was omitted
    active_soil = parsed_soil or ESP32SoilBridge.get_status(probe_serial=False)

    if not image_bytes:
        upload_target = image or file
        if upload_target is not None and upload_target.filename:
            image_bytes = await upload_target.read()

    if not image_bytes and sample_type:
        st_clean = sample_type.lower().strip()
        sample_map = {
            "dust": SAMPLES_DIR / "iraqi_dust_leaf.jpg",
            "water_stress": SAMPLES_DIR / "water_stress_leaf.jpg",
            "water": SAMPLES_DIR / "water_stress_leaf.jpg",
            "healthy": SAMPLES_DIR / "healthy_control_leaf.jpg",
            "leaf": SAMPLES_DIR / "healthy_control_leaf.jpg",
            "tree": SAMPLES_DIR / "healthy_control_leaf.jpg",
            "turf": SAMPLES_DIR / "turfgrass_sample.jpg",
            "turfgrass": SAMPLES_DIR / "turfgrass_sample.jpg",
            "lawn": SAMPLES_DIR / "turfgrass_sample.jpg",
            "soil": SAMPLES_DIR / "soil_salinity_sample.jpg",
            "salinity": SAMPLES_DIR / "soil_salinity_sample.jpg",
        }
        sample_file = sample_map.get(st_clean)
        if sample_file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown sample_type '{sample_type}'. Valid: 'dust', 'water_stress', 'healthy', 'turfgrass', 'soil'.",
            )
        if not sample_file.exists():
            from scripts.generate_samples import main as gen_samples
            gen_samples()
        if sample_file.exists():
            image_bytes = sample_file.read_bytes()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided and no valid sample_type selected.",
        )

    try:
        diagnostic_result = EcoSensingAIEngine.analyze_field_sample(
            image_bytes=image_bytes,
            region_name=target_region,
            session_id=target_session_id,
            session_action=target_session_action,
            soil_telemetry=active_soil,
        )
        if isinstance(diagnostic_result, dict):
            diagnostic_result["data_classification"] = "Predicted / Simulated Data"
            diagnostic_result["data_provenance"] = {
                "engine": "LaboratoryVisionAgent (OpenCV + Vision AI)",
                "region_name": target_region,
                "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        return JSONResponse(status_code=status.HTTP_200_OK, content=diagnostic_result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing EcoSensing diagnostic pipeline: {str(exc)}",
        )


# ── Stateful Laboratory Session Management ───────────────────────────────────

@router.post("/v1/lab-session/reset")
@router.post("/lab-session/reset")
async def reset_lab_session(
    request: Request,
    session_id: Optional[str] = Query("default_lab_session"),
):
    """Reset a stateful forensic lab session to pristine baseline."""
    target_id = session_id or "default_lab_session"
    if "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
            if body.get("session_id"):
                target_id = body["session_id"]
        except Exception:
            pass
    reset_state = LaboratoryVisionAgent.reset_session(target_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "status": "ok",
        "message": "تم تصفير جلسة المختبر بنجاح",
        "session_state": sanitize_emojis(reset_state),
    })


@router.post("/v1/lab-session/consult")
@router.post("/lab-session/consult")
async def consult_lab_investigator(
    request: Request,
    req_body: Optional[LabConsultRequest] = None,
):
    """Interactive Clinical Laboratory Consultation with Full Session Evidence Memory."""
    sid = "default_lab_session"
    user_msg = ""
    history = None
    client_soil = None
    if req_body:
        sid = req_body.session_id or sid
        user_msg = req_body.user_message or req_body.message or req_body.question or ""
        history = req_body.conversation_history
        client_soil = req_body.soil_telemetry
    elif "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
            sid = body.get("session_id") or sid
            user_msg = body.get("user_message") or body.get("message") or body.get("question") or ""
            history = body.get("conversation_history")
            client_soil = body.get("soil_telemetry")
        except Exception:
            pass

    if not user_msg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_message is required")

    # Dual-safety auto-hydration: prioritize client telemetry, fall back to live bridge state
    active_soil = client_soil or ESP32SoilBridge.get_status(probe_serial=False)

    result = LaboratoryVisionAgent.consult_investigator(
        session_id=sid,
        user_message=user_msg,
        conversation_history=history,
        soil_telemetry=active_soil,
    )
    if isinstance(result, dict):
        result["data_classification"] = "Predicted / Simulated Data"
        result["data_provenance"] = {
            "engine": "LaboratoryVisionAgent.consult_investigator (Groq LLM)",
            "session_id": sid,
            "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(result))


@router.get("/v1/lab-session/state")
@router.get("/lab-session/state")
def get_lab_session_state(session_id: str = Query("default_lab_session")):
    """Get complete active state of a lab session."""
    state = LaboratoryVisionAgent.get_session_state(session_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(state))


# ── ESP32 Capacitive Soil Moisture Sentinel Gateway ──────────────────────────

@router.get("/v1/esp32/status")
@router.get("/esp32/status")
def get_esp32_status():
    """
    Query live soil moisture status with Wi-Fi-first / USB-serial fallback arbitration.

    Telemetry source priority:
      1. WIFI_WIRELESS  — LATEST_WIFI_SOIL_READING is_fresh=True (< 15 s since last POST).
         Exposes: moisture_pct, raw_adc, filtered_adc, voltage_mv, soil_status,
                  calibration_status, wifi_rssi, data_classification.
      2. USB_SERIAL     — Legacy ESP32SoilBridge COM-port reading (fallback when no fresh
                          Wi-Fi packet is present).
    """
    # Determine Wi-Fi freshness
    last_upd = LATEST_WIFI_SOIL_READING.get("last_updated_utc")
    wifi_is_fresh = False
    wifi_age_seconds: Optional[float] = None

    if last_upd:
        try:
            ts = datetime.datetime.fromisoformat(last_upd)
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            wifi_age_seconds = round((now_utc - ts).total_seconds(), 2)
            wifi_is_fresh = wifi_age_seconds < 15.0
        except Exception:
            pass

    if wifi_is_fresh:
        # ── Path A: Wi-Fi packet is fresh – return Wi-Fi telemetry ──
        wifi_data = dict(LATEST_WIFI_SOIL_READING)
        wifi_data["age_seconds"] = wifi_age_seconds
        wifi_data["is_fresh"] = True
        wifi_data["telemetry_source"] = "WIFI_WIRELESS"
        wifi_data["is_connected"] = True
        wifi_data["data_classification"] = "Measured Data (Raw + Filtered)"
        if not wifi_data.get("data_provenance"):
            wifi_data["data_provenance"] = {
                "source_node": wifi_data.get("device_id") or "ESP32_SOIL_NODE_01",
                "transport": "WIFI_WIRELESS",
                "sensor_model": "Capacitive Soil Moisture v1.2",
                "gpio_pin": wifi_data.get("gpio_pin", 32),
                "sample_count": wifi_data.get("sample_count", 32),
                "signal_processing": "32-sample trimmed mean (trim=4) + EMA(alpha=0.25)",
                "calibration_status": wifi_data.get("calibration_status", "FACTORY_DEFAULT"),
                "dry_ref_adc": wifi_data.get("dry_ref_adc", 2850.0),
                "wet_ref_adc": wifi_data.get("wet_ref_adc", 1150.0),
                "timestamp_utc": last_upd,
            }
        dev_id = wifi_data.get("device_id") or "ESP32_SOIL_NODE_01"
        wifi_data.setdefault("port", f"Wi-Fi ({dev_id})")
        wifi_data.setdefault("device_name", f"ESP32 Soil Sentinel ({dev_id})")
        # Alias fields for frontend backward compatibility (map moisture_pct → live_vwc_pct)
        m_pct = wifi_data.get("moisture_pct")
        wifi_data.setdefault("live_vwc_pct", m_pct)
        wifi_data.setdefault("vwc_pct", m_pct)
        raw_adc = wifi_data.get("raw_adc")
        filt_adc = wifi_data.get("filtered_adc")
        wifi_data.setdefault("adc_raw", int(filt_adc if filt_adc is not None else (raw_adc or 0)))
        volt_mv = wifi_data.get("voltage_mv")
        volt_v = round(volt_mv / 1000.0, 3) if volt_mv is not None else None
        wifi_data.setdefault("voltage_v", volt_v)
        wifi_status = wifi_data.get("soil_status") or "OPTIMAL_FIELD_CAPACITY"
        status_ar = ESP32SoilBridge.REGIME_LABELS_AR.get(
            wifi_status,
            ESP32SoilBridge.REGIME_LABELS_AR.get(wifi_status.upper(), wifi_status)
        )
        wifi_data["hydrological_status_ar"] = status_ar
        wifi_data.setdefault("latest_reading", {
            "vwc_pct": m_pct,
            "live_vwc_pct": m_pct,
            "voltage_v": volt_v,
            "adc_raw": wifi_data["adc_raw"],
            "hydrological_status_ar": status_ar,
        })
        # Mirror multi-depth profiling & gradient from hardware bridge state
        hw = ESP32SoilBridge.get_status(probe_serial=False)
        wifi_data.setdefault("depths", hw.get("depths"))
        wifi_data.setdefault("depth_profiles", hw.get("depth_profiles"))
        wifi_data.setdefault("locked_depths", hw.get("depth_profiles"))
        wifi_data.setdefault("vertical_gradient", hw.get("vertical_gradient"))
        wifi_data.setdefault("vertical_gradient_pct_per_cm", hw.get("vertical_gradient_pct_per_cm"))
        return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(wifi_data))

    # ── Path B: No fresh Wi-Fi packet – fall back to USB serial bridge ───────
    hw_status = ESP32SoilBridge.get_status()
    hw_status["telemetry_source"] = "USB_SERIAL_FALLBACK"
    hw_status["wifi_is_fresh"] = False
    hw_status["wifi_age_seconds"] = wifi_age_seconds
    hw_status["data_classification"] = "Measured Data (Raw + Filtered)"
    if not hw_status.get("data_provenance") and hw_status.get("connected"):
        hw_status["data_provenance"] = {
            "source_node": hw_status.get("device_name") or "ESP32_SOIL_SENTINEL",
            "transport": "USB_SERIAL",
            "sensor_model": "Capacitive Soil Moisture v1.2",
            "timestamp_utc": hw_status.get("last_telemetry_time"),
        }
    return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(hw_status))


@router.post("/v1/esp32/ingest")
@router.post("/esp32/ingest")
async def ingest_esp32_telemetry(
    request: Request,
    ingest_req: Optional[ESP32IngestRequest] = None,
):
    """
    Ingest direct telemetry from ESP32 via HTTP or Serial listener.
    Calculates physical Volumetric Water Content (theta_v %) for Mesopotamian soil.
    """
    adc = None
    v = None
    vwc = None
    port = None

    if ingest_req:
        adc = ingest_req.adc_raw
        v = ingest_req.voltage_v
        vwc = ingest_req.vwc_pct
        port = ingest_req.port
    elif "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
            adc = body.get("adc_raw")
            v = body.get("voltage_v") or body.get("raw_voltage")
            vwc = body.get("vwc_pct")
            port = body.get("port")
        except Exception:
            pass

    res = ESP32SoilBridge.ingest_telemetry(adc_raw=adc, voltage_v=v, vwc_pct=vwc, port=port)

    # Real-time scientific experimental logging (if session active)
    exp_logger = ExperimentLogger.get_instance()
    if exp_logger.active:
        exp_logger.log_packet(res, bridge_state=ESP32SoilBridge._state)

    return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(res))


@router.post("/v1/esp32/lock-depth")
@router.post("/esp32/lock-depth")
async def lock_esp32_depth(
    request: Request,
    lock_req: Optional[ESP32LockDepthRequest] = None,
    depth_key: Optional[str] = Query(None),
):
    """
    Lock sensor reading at specific depth ('surface_5cm', 'mid_15cm', 'root_25cm').
    Prioritizes live Wi-Fi telemetry when fresh (< 15s), falling back to USB Serial.
    Calculates vertical root-zone moisture gradient and updates session telemetry.
    """
    target_depth = depth_key
    custom_vwc = None
    sid = "default_lab_session"

    if lock_req:
        target_depth = getattr(lock_req, "depth_key", None) or getattr(lock_req, "depth", None) or target_depth
        custom_vwc = lock_req.vwc_pct
        sid = lock_req.session_id or sid
    elif "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
            target_depth = body.get("depth_key") or body.get("depth") or target_depth
            custom_vwc = body.get("vwc_pct")
            sid = body.get("session_id") or sid
        except Exception:
            pass

    if not target_depth:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="depth_key is required")

    # Normalize depth aliases (e.g. '5cm' -> 'surface_5cm')
    depth_alias_map = {
        "5cm": "surface_5cm", "surface": "surface_5cm", "surface_5cm": "surface_5cm",
        "15cm": "mid_15cm", "mid": "mid_15cm", "mid_15cm": "mid_15cm",
        "25cm": "root_25cm", "root": "root_25cm", "root_25cm": "root_25cm",
    }
    target_depth = depth_alias_map.get(target_depth.lower().strip(), target_depth)

    # Check if live Wi-Fi telemetry is fresh (< 15s)
    last_upd = LATEST_WIFI_SOIL_READING.get("last_updated_utc")
    wifi_is_fresh = False
    if last_upd:
        try:
            ts = datetime.datetime.fromisoformat(last_upd)
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            wifi_is_fresh = (now_utc - ts).total_seconds() < 15.0
        except Exception:
            pass

    # If no custom_vwc provided by caller, pull live moisture from fresh Wi-Fi reading
    if custom_vwc is None and wifi_is_fresh and LATEST_WIFI_SOIL_READING.get("moisture_pct") is not None:
        custom_vwc = float(LATEST_WIFI_SOIL_READING["moisture_pct"])

    # Synchronize Wi-Fi live state to hardware bridge state when Wi-Fi is active
    if wifi_is_fresh:
        if custom_vwc is not None:
            ESP32SoilBridge._state["live_vwc_pct"] = custom_vwc
        if LATEST_WIFI_SOIL_READING.get("voltage_mv") is not None:
            ESP32SoilBridge._state["voltage_v"] = round(LATEST_WIFI_SOIL_READING["voltage_mv"] / 1000.0, 3)
        adc = LATEST_WIFI_SOIL_READING.get("filtered_adc") or LATEST_WIFI_SOIL_READING.get("raw_adc") or 0
        ESP32SoilBridge._state["adc_raw"] = int(adc)
        ESP32SoilBridge._state["connected"] = True
        ESP32SoilBridge._state["port"] = f"Wi-Fi ({LATEST_WIFI_SOIL_READING.get('device_id', 'ESP32_SOIL_NODE_01')})"

    try:
        updated_hw = ESP32SoilBridge.lock_depth(depth_key=target_depth, custom_vwc=custom_vwc)
        session = LaboratoryVisionAgent.get_or_create_session(sid)
        session["esp32_telemetry"] = updated_hw

        if wifi_is_fresh:
            updated_hw["telemetry_source"] = "WIFI_WIRELESS"
            updated_hw["is_fresh"] = True
            updated_hw["device_id"] = LATEST_WIFI_SOIL_READING.get("device_id")
            updated_hw["moisture_pct"] = custom_vwc
            updated_hw["filtered_adc"] = LATEST_WIFI_SOIL_READING.get("filtered_adc")
            updated_hw["raw_adc"] = LATEST_WIFI_SOIL_READING.get("raw_adc")
            updated_hw["voltage_mv"] = LATEST_WIFI_SOIL_READING.get("voltage_mv")
            updated_hw["wifi_rssi"] = LATEST_WIFI_SOIL_READING.get("wifi_rssi")
            updated_hw["calibration_status"] = LATEST_WIFI_SOIL_READING.get("calibration_status")
            updated_hw["soil_status"] = LATEST_WIFI_SOIL_READING.get("soil_status")
            wifi_status = LATEST_WIFI_SOIL_READING.get("soil_status") or "OPTIMAL_FIELD_CAPACITY"
            status_ar = ESP32SoilBridge.REGIME_LABELS_AR.get(
                wifi_status,
                ESP32SoilBridge.REGIME_LABELS_AR.get(wifi_status.upper(), wifi_status)
            )
            updated_hw["hydrological_status_ar"] = status_ar
            if "latest_reading" in updated_hw:
                updated_hw["latest_reading"]["hydrological_status_ar"] = status_ar
                updated_hw["latest_reading"]["moisture_pct"] = custom_vwc

        updated_hw["data_classification"] = "Measured Data (Raw + Filtered)"
        if not updated_hw.get("data_provenance"):
            updated_hw["data_provenance"] = LATEST_WIFI_SOIL_READING.get("data_provenance")

        return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(updated_hw))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Wi-Fi Wireless ESP32 Soil Sentinel Push Endpoints ────────────────────────
# These endpoints receive telemetry from ESP32_SOIL_NODE_01 over the LAN Wi-Fi
# network, decoupled from the legacy USB serial bridge.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/v1/esp32/push")
@router.post("/esp32/push")
async def esp32_wifi_push(payload: ESP32SoilPayload):
    """
    Receive a live wireless telemetry packet from the ESP32 Soil Sentinel node
    (ESP32_SOIL_NODE_01) posted over HTTP from the local Wi-Fi subnet.

    - Validates the full ESP32SoilPayload Pydantic schema.
    - Synchronizes the incoming Wi-Fi telemetry directly into ESP32SoilBridge internal state.
    - Updates the in-memory LATEST_WIFI_SOIL_READING state atomically.
    - Attaches scientific data classification and provenance metadata.
    - Returns HTTP 200 with confirmation, received moisture_pct, classification, and provenance.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    provenance = {
        "source_node": payload.device_id,
        "transport": "WIFI_WIRELESS",
        "sensor_model": "Capacitive Soil Moisture v1.2",
        "gpio_pin": payload.gpio_pin,
        "sample_count": payload.sample_count,
        "signal_processing": "32-sample trimmed mean (trim=4) + EMA(alpha=0.25)",
        "calibration_status": payload.calibration_status,
        "dry_ref_adc": payload.dry_ref_adc,
        "wet_ref_adc": payload.wet_ref_adc,
        "timestamp_utc": now_utc,
    }

    LATEST_WIFI_SOIL_READING.update({
        "connected": True,
        "mode": "WIFI_WIRELESS",
        "telemetry_source": "WIFI_WIRELESS",
        "data_classification": "Measured Data (Raw + Filtered)",
        "data_provenance": provenance,
        "last_updated_utc": now_utc,
        # Sensor identity
        "device_id": payload.device_id,
        "gpio_pin": payload.gpio_pin,
        "sample_count": payload.sample_count,
        # Measurements
        "raw_adc": payload.raw_adc,
        "filtered_adc": payload.filtered_adc,
        "voltage_mv": payload.voltage_mv,
        "moisture_pct": payload.moisture_pct,
        "soil_status": payload.soil_status,
        # Calibration
        "calibration_status": payload.calibration_status,
        "dry_ref_adc": payload.dry_ref_adc,
        "wet_ref_adc": payload.wet_ref_adc,
        # Network
        "wifi_rssi": payload.wifi_rssi,
    })

    # Synchronize into ESP32SoilBridge state so ALL consumers (Agent 3, Hybrid AI, etc.) automatically receive live data
    sync_payload = payload.model_dump()
    sync_payload["timestamp_utc"] = now_utc
    ESP32SoilBridge.sync_wifi_telemetry(sync_payload)

    # Real-time scientific experimental logging (if session active)
    exp_logger = ExperimentLogger.get_instance()
    if exp_logger.active:
        exp_logger.log_packet(sync_payload, bridge_state=ESP32SoilBridge._state)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=sanitize_emojis({
            "status": "ok",
            "received_moisture_pct": payload.moisture_pct,
            "data_classification": "Measured Data (Raw + Filtered)",
            "data_provenance": provenance,
        }),
    )


@router.get("/v1/esp32/latest-wifi")
@router.get("/esp32/latest-wifi")
def esp32_latest_wifi():
    """
    Return the most recent wireless telemetry packet received from
    ESP32_SOIL_NODE_01 together with freshness metadata.

    - age_seconds: seconds elapsed since the last successful POST.
    - is_fresh: True when the reading is < 15 seconds old (suitable for
      dashboard arbitration; prefer over USB serial data when True).
    """
    last_upd = LATEST_WIFI_SOIL_READING.get("last_updated_utc")
    age_seconds: Optional[float] = None
    is_fresh = False

    if last_upd:
        try:
            ts = datetime.datetime.fromisoformat(last_upd)
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            age_seconds = round((now_utc - ts).total_seconds(), 2)
            is_fresh = age_seconds < 15.0
        except Exception:
            pass

    response_body = dict(LATEST_WIFI_SOIL_READING)
    response_body["age_seconds"] = age_seconds
    response_body["is_fresh"] = is_fresh
    response_body["data_classification"] = "Measured Data (Raw + Filtered)"
    if not response_body.get("data_provenance"):
        response_body["data_provenance"] = LATEST_WIFI_SOIL_READING.get("data_provenance")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=sanitize_emojis(response_body),
    )


# ── Scientific Experimental Logger & Multi-Sheet Excel/CSV Exporter ──────────

@router.post("/v1/experiments/start")
@router.post("/experiments/start")
async def start_experiment_session(
    request: Request,
    req_body: Optional[StartExperimentRequest] = None,
):
    """Start recording real-time sensor packets for a named experimental session."""
    exp_name = "Soil_Calibration_Run_01"
    notes = None
    if req_body:
        exp_name = req_body.experiment_name or exp_name
        notes = req_body.notes
    elif "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
            exp_name = body.get("experiment_name") or exp_name
            notes = body.get("notes")
        except Exception:
            pass

    logger_inst = ExperimentLogger.get_instance()
    status_dict = logger_inst.start_experiment(experiment_name=exp_name, notes=notes)
    return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(status_dict))


@router.post("/v1/experiments/stop")
@router.post("/experiments/stop")
async def stop_experiment_session():
    """Stop active experimental session, compute descriptive statistics, and generate publication-grade Excel."""
    logger_inst = ExperimentLogger.get_instance()
    status_dict = logger_inst.stop_experiment()
    status_dict["evaluation_summary"] = ModelEvaluator.evaluate_all()
    return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(status_dict))


@router.get("/v1/experiments/status")
@router.get("/experiments/status")
def get_experiment_session_status():
    """Query live experimental session status, sample counter, and recent files."""
    logger_inst = ExperimentLogger.get_instance()
    return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(logger_inst.get_status()))


@router.get("/v1/experiments/export-excel")
@router.get("/experiments/export-excel")
def export_experiment_excel():
    """Generate and download publication-grade 2-sheet .xlsx research workbook."""
    logger_inst = ExperimentLogger.get_instance()
    path = logger_inst.export_excel()
    if not path or not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No experiment workbook found. Start and stop an experiment first.",
        )
    return FileResponse(
        path=path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


@router.get("/v1/experiments/export-latest")
@router.get("/experiments/export-latest")
@router.get("/v1/experiments/export-csv")
@router.get("/experiments/export-csv")
def export_experiment_csv():
    """Download the granular raw UTF-8-SIG CSV backing store for the current or latest session."""
    logger_inst = ExperimentLogger.get_instance()
    path = logger_inst.get_latest_csv_path()
    if not path or not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No raw CSV experiment log found. Start an experiment first.",
        )
    return FileResponse(
        path=path,
        filename=path.name,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


# ── Scientific Model, Filter & System Validation Endpoints ───────────────────

@router.get("/v1/evaluation/summary")
@router.get("/evaluation/summary")
def get_evaluation_summary():
    """
    Dynamic scientific validation summary computed 100% locally from genuine on-disk
    experiment CSVs in reports/experiments/, physical multi-depth state, and models inventory.
    Strictly zero hardcoding, zero synthetic fallback numbers, zero AI tokens.
    """
    evaluation = ModelEvaluator.evaluate_all()
    return JSONResponse(status_code=status.HTTP_200_OK, content=sanitize_emojis(evaluation))


# ── 4D Diurnal Physics & Auto-Afforestation Endpoints ────────────────────────

@router.post("/physics/diurnal-plume")
@router.post("/v1/physics/diurnal-plume")
def get_diurnal_advection_plume(
    lat: float = Query(33.3152, description="Latitude"),
    lon: float = Query(44.3661, description="Longitude"),
    wind_speed_ms: float = Query(3.5, description="Wind speed in m/s"),
    wind_deg: float = Query(315.0, description="Wind direction degrees"),
    hour: int = Query(14, ge=0, le=23, description="Hour of the day 0-23"),
    aqi_base: float = Query(110.0, description="Base AQI"),
    pm25_base: float = Query(48.0, description="Base PM2.5"),
    pm10_base: float = Query(95.0, description="Base PM10"),
):
    """
    Compute downwind Gaussian advection-diffusion plume for any hour (0-23) in Baghdad.
    Returns GeoJSON FeatureCollection with [lon, lat] coordinates for MapLibre GL JS.
    """
    try:
        plume_geojson = MicroclimatePhysicsEngine.calculate_gaussian_advection_plume(
            lat=lat,
            lon=lon,
            wind_speed_ms=wind_speed_ms,
            wind_deg=wind_deg,
            hour=hour,
            aqi_base=aqi_base,
            pm25_base=pm25_base,
            pm10_base=pm10_base,
        )
        if isinstance(plume_geojson, dict):
            plume_geojson["data_classification"] = "Predicted / Simulated Data"
            plume_geojson["data_provenance"] = {
                "engine": "MicroclimatePhysicsEngine.calculate_gaussian_advection_plume",
                "inputs": {
                    "lat": lat,
                    "lon": lon,
                    "wind_speed_ms": wind_speed_ms,
                    "wind_deg": wind_deg,
                    "hour": hour,
                    "aqi_base": aqi_base,
                    "pm25_base": pm25_base,
                    "pm10_base": pm10_base,
                },
                "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        return sanitize_emojis(plume_geojson)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing diurnal advection plume: {str(exc)}",
        )


@router.post("/physics/auto-afforestation")
@router.post("/v1/physics/auto-afforestation")
def get_auto_afforestation_shelterbelt(
    lat: float = Query(33.3152, description="Center latitude"),
    lon: float = Query(44.3661, description="Center longitude"),
    wind_deg: float = Query(315.0, description="Wind direction degrees"),
    hour: int = Query(14, ge=0, le=23, description="Hour of the day 0-23"),
):
    """
    AI Automatic Tree Belt Placement & Microclimate Mitigation:
    Generates 35 to 60 tree nodes in an aerodynamic windbreak perpendicular to prevailing wind,
    with 3D extruded canopy cylinders, dynamic solar shadows, and comparative metrics HUD.
    """
    try:
        result = MicroclimatePhysicsEngine.generate_auto_afforestation_shelterbelt(
            lat=lat,
            lon=lon,
            wind_deg=wind_deg,
            hour=hour,
        )
        if isinstance(result, dict):
            result["data_classification"] = "Predicted / Simulated Data"
            result["data_provenance"] = {
                "engine": "MicroclimatePhysicsEngine.generate_auto_afforestation_shelterbelt",
                "inputs": {
                    "lat": lat,
                    "lon": lon,
                    "wind_deg": wind_deg,
                    "hour": hour,
                },
                "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        return sanitize_emojis(result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating auto-afforestation shelterbelt: {str(exc)}",
        )


# ── Groq AI Pollution Attribution & Integrated Mitigation Agent ──────────────

@router.post("/v1/diagnose-pollution-mitigation")
@router.get("/v1/diagnose-pollution-mitigation")
async def diagnose_pollution_mitigation(
    lat: float = Query(33.3152, description="Latitude"),
    lon: float = Query(44.3661, description="Longitude"),
    district_name_ar: Optional[str] = Query(None, description="District / Landmark name in Arabic"),
    land_use_tag: Optional[str] = Query("urban", description="Land use classification"),
    is_built_up: Optional[bool] = Query(False, description="Whether location is a built-up building/runway"),
    impervious_pct: Optional[float] = Query(65.0, description="Impervious surface percentage"),
    bare_soil_pct: Optional[float] = Query(20.0, description="Bare soil percentage"),
):
    """
    Groq AI Pollution Source Attribution & Integrated Mitigation Agent:
    - Root-cause engineering diagnosis of diesel generators, traffic, impervious UHI, and dust
    - Contextual site typology classification (airports, highways, dense residential)
    - Realistic selective afforestation feasibility (strict rejection of planting on buildings/runways)
    - Zero Emojis and Western Numerals 0123456789
    """
    try:
        # Resolve real district name if not provided
        resolved_district = district_name_ar
        if not resolved_district or resolved_district in ["بغداد", ""]:
            try:
                places = WeatherAndGeoIntelligenceService.reverse_geocode(lat, lon)
                if places and isinstance(places, dict):
                    resolved_district = (
                        places.get("address", {}).get("suburb")
                        or places.get("address", {}).get("neighbourhood")
                        or places.get("address", {}).get("road")
                        or places.get("display_name", "").split(",")[0]
                        or "بغداد"
                    )
            except Exception:
                resolved_district = "بغداد"

        # Fetch live Copernicus CAMS and Open-Meteo telemetry
        live_telemetry: Dict[str, Any] = {}
        try:
            weather = WeatherAndGeoIntelligenceService.get_live_weather(lat, lon, resolved_district)
            live_telemetry["temp_c"] = weather.air_temp_c
            live_telemetry["lst_c"] = weather.surface_lst_c
            live_telemetry["wind_speed_ms"] = (weather.wind_speed_kmh / 3.6) if weather.wind_speed_kmh else 3.5
            live_telemetry["wind_dir_deg"] = getattr(weather, "wind_direction_deg", 315.0)
            live_telemetry["humidity_pct"] = weather.relative_humidity_pct
        except Exception:
            live_telemetry["temp_c"] = 38.0
            live_telemetry["lst_c"] = 43.5
            live_telemetry["wind_speed_ms"] = 3.5
            live_telemetry["wind_dir_deg"] = 315.0
            live_telemetry["humidity_pct"] = 22.0

        try:
            sentinel = WeatherAndGeoIntelligenceService.get_pollution_sentinel(lat, lon, resolved_district)
            live_telemetry["aqi"] = getattr(sentinel, "european_aqi", 110.0)
            live_telemetry["pm25"] = getattr(sentinel, "pm2_5_ugm3", 45.0)
            live_telemetry["pm10"] = getattr(sentinel, "pm10_ugm3", 92.0)
            live_telemetry["no2"] = getattr(sentinel, "no2_ugm3", 34.0)
            live_telemetry["so2"] = getattr(sentinel, "so2_ugm3", 18.0)
        except Exception:
            live_telemetry["aqi"] = 110.0
            live_telemetry["pm25"] = 45.0
            live_telemetry["pm10"] = 92.0
            live_telemetry["no2"] = 34.0
            live_telemetry["so2"] = 18.0

        dossier = PollutionMitigationAgent.diagnose_mitigation(
            lat=lat,
            lon=lon,
            district_name_ar=resolved_district,
            land_use_tag=land_use_tag or "urban",
            telemetry=live_telemetry,
            is_built_up=is_built_up or False,
            impervious_pct=impervious_pct or 65.0,
            bare_soil_pct=bare_soil_pct or 20.0,
        )
        if isinstance(dossier, dict):
            dossier["data_classification"] = "Predicted / Simulated Data"
            dossier["data_provenance"] = {
                "engine": "PollutionMitigationAgent (Groq Llama-3.3-70B)",
                "district_name_ar": resolved_district,
                "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        return sanitize_emojis(dossier)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pollution mitigation diagnostic error: {str(exc)}",
        )


# ── Unified Comprehensive Parcel Inspection (Parallel Orchestration) ────────

@router.post("/v1/inspect-comprehensive-parcel")
@router.get("/v1/inspect-comprehensive-parcel")
@router.post("/inspect-comprehensive-parcel")
@router.get("/inspect-comprehensive-parcel")
async def inspect_comprehensive_parcel(
    request: Request,
    lat: float = Query(33.3152, description="Latitude"),
    lon: float = Query(44.3661, description="Longitude"),
    location_name_ar: Optional[str] = Query(None, description="Location name in Arabic"),
    custom_area_m2: Optional[float] = Query(None, description="Custom area in m²"),
):
    """
    Unified Comprehensive Parcel Inspection Engine:
    Concurrently executes Agent 1 (Soil & Planting Viability), Agent 2 (WHO & Global Research),
    and Agent 3 (Pollution Mitigation Engineering) in parallel with shared pre-fetched telemetry
    and < 5.0s guaranteed response time.
    """
    try:
        body_data: Dict[str, Any] = {}
        if request.method == "POST":
            try:
                body_data = await request.json()
            except Exception:
                body_data = {}

        req_lat = float(body_data.get("lat", lat))
        req_lon = float(body_data.get("lon", lon))
        req_polygon = body_data.get("polygon_coords") or []
        req_loc = body_data.get("location_name_ar") or location_name_ar or "بغداد"
        req_area = body_data.get("custom_area_m2") or custom_area_m2
        req_weather = body_data.get("weather_data")
        req_soil = body_data.get("soil_telemetry") or ESP32SoilBridge.get_status(probe_serial=False)

        result = await EcoSensingAIEngine.inspect_comprehensive_parcel_concurrent(
            lat=req_lat,
            lon=req_lon,
            polygon_coords=req_polygon,
            location_name_ar=req_loc,
            custom_area_m2=req_area,
            weather_data=req_weather,
            soil_telemetry=req_soil,
        )
        if isinstance(result, dict):
            result["data_classification"] = "Predicted / Simulated Data"
            result["data_provenance"] = {
                "engine": "EcoSensingAIEngine.inspect_comprehensive_parcel_concurrent",
                "location_name_ar": req_loc,
                "generation_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        return sanitize_emojis(result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comprehensive parcel inspection error: {str(exc)}",
        )
