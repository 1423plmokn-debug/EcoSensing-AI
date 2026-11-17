"""
verify_upgrade_phase2.py
========================
Phase 2 UI Verification Suite for EcoSensing AI.
Tests that GET / serves valid upgraded HTML with all required IDs,
and all API endpoints respond correctly.

Academic Affiliation: Middle Technical University / Polytechnic College
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

import sys
import io
import time
import traceback

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

PASS = 0
FAIL = 0
results: list[tuple[str, bool, str, float]] = []

def register(name):
    def decorator(fn):
        def wrapper():
            global PASS, FAIL
            t0 = time.perf_counter()
            try:
                fn()
                elapsed = time.perf_counter() - t0
                results.append((name, True, '', elapsed))
                PASS += 1
                print(f"  [PASS] {name} [{elapsed:.2f}s]")
            except Exception as e:
                elapsed = time.perf_counter() - t0
                msg = str(e)
                results.append((name, False, msg, elapsed))
                FAIL += 1
                print(f"  [FAIL] {name} [{elapsed:.2f}s]")
                print(f"         {msg}")
        return wrapper
    return decorator


# ─── HTML Structure Tests ────────────────────────────────────────────────────

@register("HTML: GET / returns 200 OK")
def test_root_200():
    r = client.get('/')
    assert r.status_code == 200, f"Status {r.status_code}"

@register("HTML: Contains #workspaceDropdown")
def test_has_dropdown():
    r = client.get('/')
    assert 'id="workspaceDropdown"' in r.text or "id='workspaceDropdown'" in r.text, \
        "workspaceDropdown not found"

@register("HTML: Contains #workspace-afforestation")
def test_has_ws_afforestation():
    r = client.get('/')
    assert 'workspace-afforestation' in r.text, "workspace-afforestation not found"

@register("HTML: Contains #workspace-solar")
def test_has_ws_solar():
    r = client.get('/')
    assert 'workspace-solar' in r.text, "workspace-solar not found"

@register("HTML: Contains #workspace-vision")
def test_has_ws_vision():
    r = client.get('/')
    assert 'workspace-vision' in r.text, "workspace-vision not found"

@register("HTML: Contains #aiChatbotModal")
def test_has_chatbot_modal():
    r = client.get('/')
    assert 'aiChatbotModal' in r.text, "aiChatbotModal not found"

@register("HTML: Contains #aiChatbotFab")
def test_has_chatbot_fab():
    r = client.get('/')
    assert 'aiChatbotFab' in r.text, "aiChatbotFab not found"

@register("HTML: Contains #chatbotDragHeader (draggable header)")
def test_has_drag_header():
    r = client.get('/')
    assert 'chatbotDragHeader' in r.text, "chatbotDragHeader not found"

@register("HTML: Contains #afforestationMap Leaflet map")
def test_has_aff_map():
    r = client.get('/')
    assert 'afforestationMap' in r.text, "afforestationMap not found"

@register("HTML: Contains #solarMap")
def test_has_solar_map():
    r = client.get('/')
    assert 'solarMap' in r.text, "solarMap not found"

@register("HTML: Contains #afforestationSearchInput")
def test_has_aff_search():
    r = client.get('/')
    assert 'afforestationSearchInput' in r.text, "afforestationSearchInput not found"

@register("HTML: Contains #solarSearchInput")
def test_has_solar_search():
    r = client.get('/')
    assert 'solarSearchInput' in r.text, "solarSearchInput not found"

@register("HTML: Contains Google Hybrid Tile URL (Arabic labels)")
def test_has_google_hybrid():
    # Tile URL is defined in dashboard.js, not inline HTML
    r = client.get('/static/js/dashboard.js')
    assert 'lyrs=y' in r.text or 'google.com/vt' in r.text, \
        "Google hybrid tile URL not found in dashboard.js"

@register("HTML: Contains #drawPolygonBtn (polygon drawing)")
def test_has_draw_btn():
    r = client.get('/')
    assert 'drawPolygonBtn' in r.text, "drawPolygonBtn not found"

@register("HTML: Contains #scanLandBtn (AI scan)")
def test_has_scan_btn():
    r = client.get('/')
    assert 'scanLandBtn' in r.text, "scanLandBtn not found"

@register("HTML: Contains solar config inputs")
def test_has_solar_inputs():
    r = client.get('/')
    assert 'solar-amps' in r.text and 'solar-amp-price' in r.text and 'solar-months' in r.text, \
        "Solar config inputs not found"

@register("HTML: Contains sample buttons for Vision Lab")
def test_has_vision_samples():
    r = client.get('/')
    assert 'loadSample' in r.text, "loadSample function not found in page"

@register("CSS: JetBrains Mono font declared in stylesheet")
def test_has_jetbrains_mono():
    # Font is declared in style.css @import
    r = client.get('/static/css/style.css')
    assert 'JetBrains' in r.text or 'jetbrains' in r.text.lower(), "JetBrains Mono not found in style.css"

@register("CSS: IBM Plex Sans Arabic font declared in stylesheet")
def test_has_ibm_plex():
    # Font is declared in style.css @import
    r = client.get('/static/css/style.css')
    assert 'IBM Plex' in r.text or 'ibm-plex' in r.text.lower(), "IBM Plex Sans Arabic not found in style.css"

@register("HTML: Leaflet.js included")
def test_has_leaflet():
    r = client.get('/')
    assert 'leaflet' in r.text.lower(), "Leaflet.js not found"

@register("HTML: Chart.js included")
def test_has_chartjs():
    r = client.get('/')
    assert 'chart.js' in r.text.lower() or 'chart.umd' in r.text.lower(), "Chart.js not found"

@register("HTML: No Eastern Arabic numerals (١٢٣) — only Western")
def test_no_eastern_numerals():
    r = client.get('/')
    eastern = '١٢٣٤٥٦٧٨٩٠'
    found = [c for c in eastern if c in r.text]
    assert not found, f"Eastern Arabic numerals found: {''.join(found)}"

@register("HTML: No emoji in main UI (strict institutional rule)")
def test_no_emojis_in_ui():
    r = client.get('/')
    # Check for common emojis that should not appear in UI elements
    emoji_test = ['🌱', '☀️', '💧', '🔋', '📊', '🗺️', '🤖']
    found = [e for e in emoji_test if e in r.text]
    # Allow emojis only inside chatbot initial message if any
    assert len(found) == 0, f"Emojis found in UI: {', '.join(found)}"


# ─── API Endpoint Tests ──────────────────────────────────────────────────────

@register("API: GET /api/health returns 200")
def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200, f"Status {r.status_code}"
    assert r.json().get('status') == 'operational', f"Not operational: {r.json()}"

@register("API: GET /api/weather returns weather data")
def test_weather_api():
    r = client.get('/api/weather?lat=33.3152&lon=44.3661')
    assert r.status_code == 200, f"Status {r.status_code}"
    d = r.json()
    assert 'air_temp_c' in d and 'surface_lst_c' in d, f"Missing fields: {list(d.keys())}"
    print(f"    [INFO] Air: {d['air_temp_c']}°C | LST: {d['surface_lst_c']}°C")

@register("API: GET /api/search-places finds Baghdad place")
def test_search_places():
    r = client.get('/api/search-places?q=شارع فلسطين')
    assert r.status_code == 200, f"Status {r.status_code}"
    d = r.json()
    assert d.get('count', 0) > 0, "No results returned"
    print(f"    [INFO] Found {d['count']} results")

@register("API: POST /api/inspect-land returns suitability verdict")
def test_inspect_land():
    payload = {"lat": 33.3152, "lon": 44.3661, "location_name_ar": "بغداد"}
    r = client.post('/api/inspect-land', json=payload)
    assert r.status_code == 200, f"Status {r.status_code}: {r.text[:200]}"
    d = r.json()
    assert 'suitability_code' in d, f"suitability_code missing: {list(d.keys())}"
    print(f"    [INFO] Suitability: {d['suitability_code']} | Area: {d.get('total_selected_area_m2',0):.0f} m²")

@register("API: POST /api/solar-calculate returns ROI")
def test_solar_calculate():
    payload = {"required_amperes": 12, "roof_area_m2": 180, "months_count": 12}
    r = client.post('/api/solar-calculate', json=payload)
    assert r.status_code == 200, f"Status {r.status_code}: {r.text[:200]}"
    d = r.json()
    assert 'recommended_panels_count' in d, f"panels missing: {list(d.keys())}"
    assert 'payback_period_months' in d, "payback missing"
    print(f"    [INFO] Panels: {d['recommended_panels_count']} | Payback: {d['payback_period_months']:.1f} mo")

@register("API: POST /api/chat returns Arabic reply")
def test_chat():
    payload = {"message": "كيف أختار الأشجار المناسبة لبغداد؟", "active_section": "afforestation", "live_telemetry": {}}
    r = client.post('/api/chat', json=payload)
    assert r.status_code == 200, f"Status {r.status_code}"
    d = r.json()
    assert 'reply_ar' in d and len(d['reply_ar']) > 10, f"Reply too short: {d.get('reply_ar','')[:50]}"
    print(f"    [INFO] Engine: {d.get('engine_source','?')} | Reply: {d['reply_ar'][:60]}...")

@register("API: POST /api/analyze-image with dust sample")
def test_analyze_dust():
    r = client.post('/api/analyze-image?sample_type=dust')
    assert r.status_code == 200, f"Status {r.status_code}: {r.text[:200]}"
    d = r.json()
    assert 'pixel_metrics' in d or 'thermal_image_b64' in d or 'ai_prescription_ar' in d, \
        f"Expected analysis fields missing: {list(d.keys())}"
    print(f"    [INFO] Analysis keys: {list(d.keys())[:5]}")

@register("Static: GET /static/css/style.css returns CSS")
def test_static_css():
    r = client.get('/static/css/style.css')
    assert r.status_code == 200, f"Status {r.status_code}"
    assert '--navy' in r.text or 'card-25d' in r.text, "CSS variables not found"

@register("Static: GET /static/js/dashboard.js returns JS")
def test_static_js():
    r = client.get('/static/js/dashboard.js')
    assert r.status_code == 200, f"Status {r.status_code}"
    assert 'switchWorkspace' in r.text, "switchWorkspace function not found"

@register("Static: GET /static/js/dashboard.js has all key functions")
def test_js_functions():
    r = client.get('/static/js/dashboard.js')
    for fn in ['runLandInspection', 'calculateSolar', 'sendChatMessage', 'toggleChatbot', 'renderTreeChart', 'renderSolarResult']:
        assert fn in r.text, f"Function '{fn}' not found in dashboard.js"

@register("Static: Leaf samples exist and are accessible")
def test_leaf_samples():
    for sample in ['iraqi_dust_leaf.jpg', 'water_stress_leaf.jpg', 'healthy_control_leaf.jpg']:
        r = client.get(f'/static/samples/{sample}')
        assert r.status_code == 200, f"Sample {sample} not accessible: {r.status_code}"
        assert len(r.content) > 1000, f"Sample {sample} too small: {len(r.content)} bytes"


# ─── Run all tests ──────────────────────────────────────────────────────────

def main():
    print()
    print('══════════════════════════════════════════════════════════════')
    print('  EcoSensing AI — Phase 2 UI Upgrade Verification')
    print('  Polytechnic College | Middle Technical University')
    print('  Project Manager: Ali Nihad Qadir')
    print('══════════════════════════════════════════════════════════════')
    print()

    sections = [
        ('HTML Structure', [
            test_root_200, test_has_dropdown, test_has_ws_afforestation,
            test_has_ws_solar, test_has_ws_vision, test_has_chatbot_modal,
            test_has_chatbot_fab, test_has_drag_header, test_has_aff_map,
            test_has_solar_map, test_has_aff_search, test_has_solar_search,
            test_has_google_hybrid, test_has_draw_btn, test_has_scan_btn,
            test_has_solar_inputs, test_has_vision_samples,
            test_has_jetbrains_mono, test_has_ibm_plex,
            test_has_leaflet, test_has_chartjs,
            test_no_eastern_numerals, test_no_emojis_in_ui,
        ]),
        ('API Endpoints', [
            test_health, test_weather_api, test_search_places,
            test_inspect_land, test_solar_calculate, test_chat,
            test_analyze_dust,
        ]),
        ('Static Assets', [
            test_static_css, test_static_js, test_js_functions, test_leaf_samples,
        ]),
    ]

    for section_name, tests in sections:
        print(f'▶ {section_name}')
        for test_fn in tests:
            test_fn()
        print()

    total = PASS + FAIL
    print('══════════════════════════════════════════════════════════════')
    print(f'  Results: {PASS}/{total} PASSED  {"✅ 100% PASS RATE" if FAIL == 0 else f"❌ {FAIL} FAILED"}')
    print('══════════════════════════════════════════════════════════════')
    print()
    if FAIL == 0:
        print('✅ All Phase 2 UI tests passed!')
        print('   Dashboard: http://localhost:8000')
        print('   Workspaces: Afforestation | Solar | Vision Lab')
        print('   Chatbot: Floating draggable AI consultant')
    else:
        print(f'❌ {FAIL} tests failed. Review output above.')
    print()
    return FAIL

if __name__ == '__main__':
    sys.exit(main())
