import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import sanitize_emojis, settings, strip_all_emojis
from app.routers.api import router as api_router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
SAMPLES_DIR = STATIC_DIR / "samples"


class EmojiSanitizedJSONResponse(JSONResponse):
    """Custom JSONResponse ensuring all strings are stripped of emojis."""
    def render(self, content: Any) -> bytes:
        sanitized = sanitize_emojis(content)
        return super().render(sanitized)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure static directories and benchmark sample assets exist upon startup."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    dust_sample = SAMPLES_DIR / "iraqi_dust_leaf.jpg"
    water_sample = SAMPLES_DIR / "water_stress_leaf.jpg"

    if not dust_sample.exists() or not water_sample.exists():
        try:
            from scripts.generate_samples import main as gen_samples
            gen_samples()
        except Exception as e:
            print(f"[EcoSensing Startup] Note: Sample generation warning: {e}")

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Urban Microclimate & Field Sentinel - Middle Technical University / Iraq",
    version="2.0.0",
    lifespan=lifespan,
    default_response_class=EmojiSanitizedJSONResponse,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def emoji_sanitization_middleware(request, call_next):
    """Intercept all HTTP responses and recursively purge any emoji from JSON payloads."""
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        body = [chunk async for chunk in response.body_iterator]
        body_bytes = b"".join(body)
        try:
            parsed = json.loads(body_bytes.decode("utf-8"))
            sanitized = sanitize_emojis(parsed)
            sanitized_bytes = json.dumps(sanitized, ensure_ascii=False).encode("utf-8")
            headers = dict(response.headers)
            headers["content-length"] = str(len(sanitized_bytes))
            return Response(
                content=sanitized_bytes,
                status_code=response.status_code,
                headers=headers,
                media_type="application/json",
            )
        except Exception:
            return Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )
    return response


# Include API Router
app.include_router(api_router)

# Re-export Wi-Fi Soil Sentinel schema & in-memory state for root/direct consumption
from app.routers.api import (
    ESP32SoilPayload,
    LATEST_WIFI_SOIL_READING,
    esp32_latest_wifi,
    esp32_wifi_push,
)

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serve the 2.5D Institutional Dashboard single page application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "project": settings.PROJECT_NAME,
        "author": settings.AUTHOR,
        "message": "Dashboard UI compiling... Please check /static/index.html",
    }


if __name__ == "__main__":
    import uvicorn
    # LAN Network Binding: host="0.0.0.0" and port=8000 so the ESP32 on the
    # local Wi-Fi subnet (e.g. 192.168.0.x) can push telemetry to http://<HOST_IP>:8000/api/v1/esp32/push
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
