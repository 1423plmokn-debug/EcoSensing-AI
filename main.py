"""
EcoSensing AI – Root Entry Point & Wi-Fi Soil Sentinel Gateway
Academic Affiliation: Middle Technical University / Polytechnic College /
  Department of Electronic Engineering Technologies and Artificial Intelligence
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from app.main import (
    app,
    ESP32SoilPayload,
    LATEST_WIFI_SOIL_READING,
    esp32_wifi_push,
    esp32_latest_wifi,
)

__all__ = [
    "app",
    "ESP32SoilPayload",
    "LATEST_WIFI_SOIL_READING",
    "esp32_wifi_push",
    "esp32_latest_wifi",
]

if __name__ == "__main__":
    import uvicorn
    # LAN Network Binding: host="0.0.0.0" and port=8000 so the ESP32 on the
    # local Wi-Fi subnet (e.g. 192.168.0.x) can push telemetry to http://<HOST_IP>:8000/api/v1/esp32/push
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

