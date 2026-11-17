"""
EcoSensing AI – Weather & Geo-Intelligence Service
Master Geo-Engine with LocationIQ Autocomplete & Reverse Geocoding locked strictly to Baghdad.
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

import json as _json
import logging
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.config import sanitize_emojis, settings, strip_all_emojis
from app.models.schemas import LandInspectionRequest, LiveWeatherResponse

import time

logger = logging.getLogger("EcoSensing.WeatherGeo")

_BAGHDAD_TZ = timezone(timedelta(hours=3))

# Baghdad seasonal defaults
_BAGHDAD_SEASONAL = {
    1: 11.0, 2: 14.5, 3: 20.0, 4: 26.5, 5: 33.5,
    6: 38.5, 7: 42.0, 8: 42.5, 9: 37.5, 10: 29.0,
    11: 20.0, 12: 13.0,
}
_BAGHDAD_HUMIDITY = {
    1: 72, 2: 65, 3: 52, 4: 42, 5: 28, 6: 18,
    7: 16, 8: 16, 9: 20, 10: 32, 11: 55, 12: 68,
}
_BAGHDAD_WIND = {
    1: 18, 2: 20, 3: 22, 4: 20, 5: 25, 6: 28,
    7: 26, 8: 24, 9: 18, 10: 15, 11: 16, 12: 17,
}
_BAGHDAD_SOLAR = {
    1: 160, 2: 210, 3: 280, 4: 360, 5: 440, 6: 490,
    7: 470, 8: 450, 9: 390, 10: 290, 11: 190, 12: 150,
}


def _fetch_json(url: str, timeout: float = 3.5, retries: int = 1) -> Optional[Any]:
    """Urllib-based JSON fetcher with standard browser User-Agent, timeout, and 429 backoff."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "EcoSensingAI/2.0 (Middle Technical University, Baghdad)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return _json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            if he.code == 429 and attempt < retries:
                time.sleep(0.6)
                continue
            logger.debug("HTTP fetch error for %s: %s", url, he)
            return None
        except Exception as exc:
            if attempt < retries:
                time.sleep(0.3)
                continue
            logger.debug("HTTP fetch failed for %s: %s", url, exc)
            return None
    return None


class WeatherAndGeoIntelligenceService:
    """
    EcoSensing Geo-Intelligence Service:
    1. LocationIQ Autocomplete Search (locked strictly to Baghdad)
    2. LocationIQ Reverse Geocoding
    3. Live Weather via Open-Meteo API
    4. Delegation to PedologicalBotanicalAgent and GlobalPollutionResearchAgent
    """

    # ── Live Weather ──────────────────────────────────────────────────────────

    @classmethod
    def get_live_weather(
        cls,
        lat: float,
        lon: float,
        location_name_ar: str = "بغداد",
    ) -> LiveWeatherResponse:
        """Fetch real-time weather from Open-Meteo API with fallback."""
        now_baghdad = datetime.now(_BAGHDAD_TZ)
        timestamp_str = now_baghdad.isoformat()
        month = now_baghdad.month

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
            f"shortwave_radiation,soil_temperature_0cm"
            f"&timezone=Asia/Baghdad"
        )
        weather_data = _fetch_json(url, timeout=3.0)

        if weather_data and "current" in weather_data:
            current = weather_data["current"]
            air_temp = float(current.get("temperature_2m", _BAGHDAD_SEASONAL[month]))
            rh = float(current.get("relative_humidity_2m", _BAGHDAD_HUMIDITY[month]))
            wind = float(current.get("wind_speed_10m", _BAGHDAD_WIND[month]))
            radiation = float(current.get("shortwave_radiation", _BAGHDAD_SOLAR[month]))
            soil_t = float(current.get("soil_temperature_0cm", air_temp + 2.5))
            source = "OPEN_METEO_LIVE"
        else:
            source = "BAGHDAD_SEASONAL_CALIBRATION"
            air_temp = _BAGHDAD_SEASONAL[month]
            rh = float(_BAGHDAD_HUMIDITY[month])
            wind = float(_BAGHDAD_WIND[month])
            radiation = float(_BAGHDAD_SOLAR[month])
            soil_t = round(air_temp + 3.0, 1)

        radiation_factor = (radiation / 100.0) * 1.6
        wind_cooling = (wind / 10.0) * 0.4
        surface_lst = round(air_temp + radiation_factor - wind_cooling, 1)
        dust_status = cls._dust_status_ar(rh, wind, month)

        return LiveWeatherResponse(
            lat=round(lat, 6),
            lon=round(lon, 6),
            location_name_ar=strip_all_emojis(location_name_ar),
            air_temp_c=round(air_temp, 1),
            soil_temp_c=round(soil_t, 1),
            surface_lst_c=max(round(surface_lst, 1), round(air_temp, 1)),
            relative_humidity_pct=round(rh, 1),
            wind_speed_kmh=round(wind, 1),
            solar_radiation_wm2=round(radiation, 1),
            dust_aerosol_status_ar=strip_all_emojis(dust_status),
            timestamp_str=timestamp_str,
            source=source,
        )

    @staticmethod
    def _dust_status_ar(rh: float, wind: float, month: int) -> str:
        """Return Arabic dust/aerosol status without any emoji."""
        if rh < 20 and wind > 24:
            return "عاصفة غبارية شديدة - ترسبات سلتية كثيفة على الغطاء النباتي"
        if rh < 30 and wind > 18:
            return "عاصفة غبارية متوسطة - غبار عراقي مرتفع"
        if rh < 40 or (month in [5, 6, 7, 8, 9] and wind > 12):
            return "تلوث هوائي خفيف إلى متوسط - غبار معلق"
        return "جودة هواء مقبولة - مستوى غبار منخفض"

    # ── LocationIQ Forward Search & Autocomplete (Baghdad Only) ───────────────

    @classmethod
    def search_places(cls, query: str) -> List[Dict[str, Any]]:
        """
        LocationIQ Forward Search & Autocomplete strictly locked to Baghdad:
        1. Check if raw GPS coordinates (lat, lon). If within Baghdad (33.08-33.52, 44.08-44.65), return immediately.
        2. Call LocationIQ Autocomplete API bounded to Baghdad viewbox.
        """
        q_clean = query.strip().strip("()[]{}")
        if not q_clean:
            return []

        # 1. Raw GPS Coordinate Parser
        coord_match = re.search(r"^([+-]?\d+(?:\.\d+)?)[,\s\t]+([+-]?\d+(?:\.\d+)?)$", q_clean)
        if coord_match:
            try:
                c_lat = float(coord_match.group(1))
                c_lon = float(coord_match.group(2))
                # Check if inside Baghdad Governorate bounds
                if 33.08 <= c_lat <= 33.52 and 44.08 <= c_lon <= 44.65:
                    return [{
                        "name_ar": f"إحداثيات جغرافية مباشرة في بغداد [{c_lat:.4f}, {c_lon:.4f}]",
                        "display_name": f"إحداثيات بغداد [{c_lat:.4f}, {c_lon:.4f}]",
                        "lat": round(c_lat, 6),
                        "lon": round(c_lon, 6),
                        "type": "coordinates",
                        "source": "DIRECT_COORDINATES",
                    }]
            except (ValueError, TypeError):
                pass

        # 2. LocationIQ Autocomplete API locked strictly to Baghdad
        api_key = settings.LOCATIONIQ_API_KEY or ""
        encoded_q = urllib.parse.quote(q_clean)
        # viewbox=sw_lon,ne_lat,ne_lon,sw_lat -> 44.08,33.52,44.65,33.08
        url = (
            f"https://api.locationiq.com/v1/autocomplete"
            f"?key={api_key}&q={encoded_q}&countrycodes=iq"
            f"&viewbox=44.08,33.52,44.65,33.08&bounded=1&limit=6&accept-language=ar"
        )

        results: List[Dict[str, Any]] = []
        data = _fetch_json(url, timeout=3.5)

        if data and isinstance(data, list):
            for item in data:
                try:
                    lat = float(item["lat"])
                    lon = float(item["lon"])
                    # Verify coordinates lie within Baghdad boundary
                    if 33.08 <= lat <= 33.52 and 44.08 <= lon <= 44.65:
                        display = strip_all_emojis(item.get("display_name", ""))
                        first_name = display.split(",")[0].strip() or display
                        results.append({
                            "name_ar": first_name,
                            "display_name": display,
                            "lat": round(lat, 6),
                            "lon": round(lon, 6),
                            "type": item.get("type", "place"),
                            "source": "LOCATIONIQ_AUTOCOMPLETE",
                        })
                except (KeyError, ValueError, TypeError):
                    continue

        # Fallback to general Baghdad search if bounded returned empty
        if not results:
            url_unbounded = (
                f"https://api.locationiq.com/v1/autocomplete"
                f"?key={api_key}&q={encoded_q}%20بغداد&countrycodes=iq"
                f"&limit=4&accept-language=ar"
            )
            data_unb = _fetch_json(url_unbounded, timeout=3.5)
            if data_unb and isinstance(data_unb, list):
                for item in data_unb:
                    try:
                        lat = float(item["lat"])
                        lon = float(item["lon"])
                        if 33.05 <= lat <= 33.60 and 44.00 <= lon <= 44.75:
                            display = strip_all_emojis(item.get("display_name", ""))
                            first_name = display.split(",")[0].strip() or display
                            results.append({
                                "name_ar": first_name,
                                "display_name": display,
                                "lat": round(lat, 6),
                                "lon": round(lon, 6),
                                "type": item.get("type", "place"),
                                "source": "LOCATIONIQ_FALLBACK",
                            })
                    except (KeyError, ValueError, TypeError):
                        continue

        return sanitize_emojis(results[:6])

    # ── Pollution Sentinel Delegation (Agent 2) ───────────────────────────────

    @classmethod
    def get_pollution_sentinel(
        cls,
        lat: float,
        lon: float,
        location_name_ar: str = "بغداد",
    ) -> Dict[str, Any]:
        """Delegate directly to GlobalPollutionResearchAgent (Agent 2)."""
        from app.services.pollution_agent import GlobalPollutionResearchAgent
        return GlobalPollutionResearchAgent.get_pollution_sentinel(
            lat=lat, lon=lon, location_name=location_name_ar
        )

    # ── Smart Land Inspection Delegation (Agent 1) ────────────────────────────

    @classmethod
    def inspect_land(cls, req: LandInspectionRequest) -> Dict[str, Any]:
        """Delegate directly to PedologicalBotanicalAgent (Agent 1)."""
        from app.services.pedological_agent import PedologicalBotanicalAgent
        return PedologicalBotanicalAgent.inspect_land(req)
