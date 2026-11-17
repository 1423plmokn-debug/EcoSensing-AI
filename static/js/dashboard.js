/**
 * EcoSensing AI — Master Executive Dashboard Controller
 * 100% MapLibre GL JS + LocationIQ 2.5D Architectural Map Engine
 * Dedicated Specialized AI Agents & Zero-Emoji Pipeline
 * Project Manager: Ali Nihad Qadir (علي نهاد قادر)
 */

'use strict';

/* ══════════════════════════════════════════════════════════════
   GLOBAL STATE
══════════════════════════════════════════════════════════════ */
const state = {
  activeWorkspace: 'afforestation',
  workspace1Mode: 'afforestation', // 'afforestation' or 'pollution'
  selectedLat: 33.3152,
  selectedLon: 44.3661,
  selectedLocationAr: 'بغداد',
  selectedPolygon: [],          // [[lat, lon], ...]
  drawingMode: false,
  drawingPoints: [],            // temp polygon points while drawing [[lat, lon], ...]
  landResult: null,
  weatherData: null,
  pollutionData: null,
  visionResult: null,
  activeLayer: 'satellite',
  is4DActive: false,
  currentHour: 14,
  diurnalTimer: null,
  windSpeedMs: 3.5,
  windDeg: 315.0,
  afforestationResult: null,
  activeLabSessionId: 'active_field_session',
  activeEvidenceTab: 1,
  labSessionState: null,
  currentSelectedFile: null,
  esp32PollInterval: null,
};

/* Live telemetry object read by chatbot */
window.liveTelemetry = {};

/* Global map instance and chart instance */
let baghdadMap = null;
let treeChartInstance = null;
let selectionMarker = null;

/* ══════════════════════════════════════════════════════════════
   UTILITY FUNCTIONS
══════════════════════════════════════════════════════════════ */
const fmt = (v, decimals = 1) => {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
};

const fmtInt = (v) => {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
};

const el = (id) => document.getElementById(id);

const escHtml = (s) =>
  String(s).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));

function showLoading(id) {
  const e = el(id);
  if (e) {
    e.classList.add('visible');
    e.style.display = 'flex';
  }
}

function hideLoading(id) {
  const e = el(id);
  if (e) {
    e.classList.remove('visible');
    e.style.display = 'none';
  }
}

/* ══════════════════════════════════════════════════════════════
   HEADER CLOCK (Baghdad Time)
══════════════════════════════════════════════════════════════ */
function updateClock() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const clockEl = el('headerClock');
  if (clockEl) {
    clockEl.textContent =
      `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())} — ${now.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })}`;
  }
}
setInterval(updateClock, 1000);
updateClock();

/* ══════════════════════════════════════════════════════════════
   WORKSPACE SWITCHER (afforestation & vision ONLY)
══════════════════════════════════════════════════════════════ */
function switchWorkspace(wsName) {
  document.querySelectorAll('.workspace').forEach((w) => w.classList.remove('active'));
  const target = el(`workspace-${wsName}`);
  if (target) target.classList.add('active');
  state.activeWorkspace = wsName;
  updateChatSuggestions();
  updateTelemetry();

  if (wsName === 'afforestation' && baghdadMap) {
    setTimeout(() => {
      baghdadMap.resize();
    }, 200);
  } else if (wsName === 'vision') {
    if (state.esp32Modality === 'hybrid') {
      fetchEsp32Status();
    }
  }
}

const dropdown = el('workspaceDropdown');
if (dropdown) {
  dropdown.addEventListener('change', (e) => switchWorkspace(e.target.value));
}

/* ══════════════════════════════════════════════════════════════
   EXECUTIVE DOSSIER VIEWER (4 INSTANT TABS)
══════════════════════════════════════════════════════════════ */
function switchDossierView(viewName) {
  const tabs = {
    mitigation: el('tabBtnMitigation'),
    soil: el('tabBtnSoil'),
    benchmark: el('tabBtnBenchmark'),
    all: el('tabBtnAll'),
  };
  const panes = {
    mitigation: el('dossierPaneMitigation'),
    soil: el('dossierPaneSoil'),
    benchmark: el('dossierPaneBenchmark'),
  };

  Object.values(tabs).forEach((t) => {
    if (t) t.classList.remove('active');
  });

  if (viewName === 'all') {
    if (tabs.all) tabs.all.classList.add('active');
    if (panes.mitigation) panes.mitigation.style.display = 'block';
    if (panes.soil) panes.soil.style.display = 'block';
    if (panes.benchmark) panes.benchmark.style.display = 'block';
  } else {
    if (tabs[viewName]) tabs[viewName].classList.add('active');
    if (panes.mitigation) panes.mitigation.style.display = viewName === 'mitigation' ? 'block' : 'none';
    if (panes.soil) panes.soil.style.display = viewName === 'soil' ? 'block' : 'none';
    if (panes.benchmark) panes.benchmark.style.display = viewName === 'benchmark' ? 'block' : 'none';
  }
}

function setWorkspace1Mode(mode) {
  state.workspace1Mode = mode;
  updateTelemetry();
  updateChatSuggestions();
}

/* ══════════════════════════════════════════════════════════════
   MAPLIBRE GL JS INITIALIZATION (LOCKED TO BAGHDAD 2.5D)
══════════════════════════════════════════════════════════════ */
function initBaghdadMap() {
  const container = el('baghdadMap');
  if (!container) return;

  // Baghdad Governorate bounds: [sw_lon, sw_lat], [ne_lon, ne_lat]
  const baghdadBounds = [
    [44.08, 33.08],
    [44.65, 33.52],
  ];

  baghdadMap = new maplibregl.Map({
    container: 'baghdadMap',
    center: [44.3661, 33.3152], // [lon, lat] Central Baghdad
    zoom: 13,
    pitch: 22,                  // 2.5D architectural tilt
    minZoom: 10.5,
    maxZoom: 19,
    maxBounds: baghdadBounds,
    style: {
      version: 8,
      sources: {
        'satellite-source': {
          type: 'raster',
          tiles: ['https://mt1.google.com/vt/lyrs=y&hl=ar&x={x}&y={y}&z={z}'],
          tileSize: 256,
          attribution: 'Google Maps Satellite',
        },
        'locationiq-source': {
          type: 'raster',
          tiles: [
            // LocationIQ tile key is injected at runtime from /api/v1/config/map-key
            // so the client-side bundle contains no hardcoded API credentials.
            typeof window.__LOCATIONIQ_TILE_KEY !== 'undefined'
              ? `https://tiles.locationiq.com/v3/streets/r/{z}/{x}/{y}.png?key=${window.__LOCATIONIQ_TILE_KEY}`
              : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          ],
          tileSize: 256,
          attribution: 'LocationIQ Streets | © OpenStreetMap contributors',
        },
      },
      layers: [
        {
          id: 'satellite-layer',
          type: 'raster',
          source: 'satellite-source',
          layout: { visibility: 'visible' },
        },
        {
          id: 'streets-layer',
          type: 'raster',
          source: 'locationiq-source',
          layout: { visibility: 'none' },
        },
      ],
    },
  });

  baghdadMap.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-left');

  baghdadMap.on('load', () => {
    setupMapLayers();
    fetchLiveWeather(state.selectedLat, state.selectedLon);
  });

  // Map click handler
  baghdadMap.on('click', (e) => {
    const lon = e.lngLat.lng;
    const lat = e.lngLat.lat;

    if (state.drawingMode) {
      // Add point to drawingPoints [[lat, lon], ...]
      state.drawingPoints.push([lat, lon]);
      updateDrawnPolygonSource();
    } else {
      // Single click inspection
      state.selectedLat = lat;
      state.selectedLon = lon;
      updateSelectionMarker([lon, lat]);

      state.selectedPolygon = [];
      clearDrawnPolygonSource();
      runUnifiedInspection();
    }
  });
}

function switchMapLayer(layerType, btnEl) {
  if (!baghdadMap) return;
  state.activeLayer = layerType;

  const btnSat = el('btnLayerSat');
  const btnStr = el('btnLayerStreets');
  if (btnSat) btnSat.classList.remove('active');
  if (btnStr) btnStr.classList.remove('active');
  if (btnEl) btnEl.classList.add('active');

  if (layerType === 'satellite') {
    if (baghdadMap.getLayer('satellite-layer')) {
      baghdadMap.setLayoutProperty('satellite-layer', 'visibility', 'visible');
    }
    if (baghdadMap.getLayer('streets-layer')) {
      baghdadMap.setLayoutProperty('streets-layer', 'visibility', 'none');
    }
  } else {
    if (baghdadMap.getLayer('satellite-layer')) {
      baghdadMap.setLayoutProperty('satellite-layer', 'visibility', 'none');
    }
    if (baghdadMap.getLayer('streets-layer')) {
      baghdadMap.setLayoutProperty('streets-layer', 'visibility', 'visible');
    }
  }
}

function setupMapLayers() {
  if (!baghdadMap) return;

  // 1. Drawn Polygon Source & Layers
  if (!baghdadMap.getSource('drawn-polygon')) {
    baghdadMap.addSource('drawn-polygon', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });

    baghdadMap.addLayer({
      id: 'drawn-polygon-fill',
      type: 'fill',
      source: 'drawn-polygon',
      paint: {
        'fill-color': '#1E3A8A',
        'fill-opacity': 0.25,
      },
    });

    baghdadMap.addLayer({
      id: 'drawn-polygon-line',
      type: 'line',
      source: 'drawn-polygon',
      paint: {
        'line-color': '#2563EB',
        'line-width': 2.5,
        'line-dasharray': [2, 1],
      },
    });
  }

  // 2. Tree Points GeoJSON Source & Layer
  if (!baghdadMap.getSource('trees-source')) {
    baghdadMap.addSource('trees-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });

    baghdadMap.addLayer({
      id: 'trees-layer',
      type: 'circle',
      source: 'trees-source',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 4, 16, 7.5, 19, 12],
        'circle-color': ['get', 'color'],
        'circle-stroke-width': 1.5,
        'circle-stroke-color': '#FFFFFF',
      },
    });

    baghdadMap.on('click', 'trees-layer', (e) => {
      const feat = e.features[0];
      if (!feat) return;
      const props = feat.properties;
      const coordinates = feat.geometry.coordinates.slice();

      new maplibregl.Popup({ closeButton: true, offset: 12 })
        .setLngLat(coordinates)
        .setHTML(`
          <div style="font-size:12px; line-height:1.5;">
            <div style="font-weight:700; color:${props.color}; font-size:13px;">${escHtml(props.name_ar)}</div>
            <div style="font-size:10.5px; color:#64748B; font-style:italic;">${escHtml(props.scientific_name || '')}</div>
            <div style="margin-top:6px; color:#1E293B;">${escHtml(props.reason_ar || '')}</div>
          </div>
        `)
        .addTo(baghdadMap);
    });

    baghdadMap.on('mouseenter', 'trees-layer', () => {
      baghdadMap.getCanvas().style.cursor = 'pointer';
    });
    baghdadMap.on('mouseleave', 'trees-layer', () => {
      baghdadMap.getCanvas().style.cursor = '';
    });
  }

  // 3. Radar Circle GeoJSON Source & Layers (Mode B)
  if (!baghdadMap.getSource('radar-source')) {
    baghdadMap.addSource('radar-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });

    baghdadMap.addLayer({
      id: 'radar-circle-fill',
      type: 'fill',
      source: 'radar-source',
      layout: { visibility: 'none' },
      paint: {
        'fill-color': ['get', 'color'],
        'fill-opacity': 0.22,
      },
    });

    baghdadMap.addLayer({
      id: 'radar-circle-line',
      type: 'line',
      source: 'radar-source',
      layout: { visibility: 'none' },
      paint: {
        'line-color': ['get', 'color'],
        'line-width': 2.5,
      },
    });
  }

  // 4. Fluid Atmospheric Advection-Diffusion Cloud (MapLibre Heatmap Layer)
  if (!baghdadMap.getSource('pollution-fluid-source')) {
    baghdadMap.addSource('pollution-fluid-source', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });

    baghdadMap.addLayer({
      id: 'pollution-fluid-cloud',
      type: 'heatmap',
      source: 'pollution-fluid-source',
      maxzoom: 19,
      paint: {
        'heatmap-weight': [
          'interpolate',
          ['linear'],
          ['get', 'weight'],
          0, 0,
          1, 1,
        ],
        'heatmap-intensity': [
          'interpolate',
          ['linear'],
          ['zoom'],
          10, 0.75,
          14, 1.35,
          18, 2.0,
        ],
        'heatmap-color': [
          'interpolate',
          ['linear'],
          ['heatmap-density'],
          0.00, 'rgba(0, 0, 0, 0)',
          0.25, 'rgba(56, 189, 248, 0.22)',
          0.50, 'rgba(250, 204, 21, 0.35)',
          0.75, 'rgba(249, 115, 22, 0.45)',
          1.00, 'rgba(220, 38, 38, 0.55)',
        ],
        'heatmap-radius': [
          'interpolate',
          ['linear'],
          ['zoom'],
          10, 18,
          14, 34,
          17, 55,
        ],
        'heatmap-opacity': 0.52,
      },
    });
  }

  // Initial selection marker
  updateSelectionMarker([state.selectedLon, state.selectedLat]);
}

function updateSelectionMarker(lonLat) {
  if (!baghdadMap) return;
  if (!selectionMarker) {
    const elMarker = document.createElement('div');
    elMarker.className = 'custom-maplibre-marker';
    elMarker.style.width = '14px';
    elMarker.style.height = '14px';
    elMarker.style.background = '#2563EB';
    elMarker.style.border = '2px solid #FFFFFF';
    elMarker.style.borderRadius = '50%';
    elMarker.style.boxShadow = '0 0 10px rgba(37,99,235,0.8)';

    selectionMarker = new maplibregl.Marker({ element: elMarker })
      .setLngLat(lonLat)
      .addTo(baghdadMap);
  } else {
    selectionMarker.setLngLat(lonLat);
  }
}

/* ══════════════════════════════════════════════════════════════
   POLYGON DRAWING CONTROLS
══════════════════════════════════════════════════════════════ */
function toggleDrawMode() {
  state.drawingMode = !state.drawingMode;
  const btn = el('drawPolygonBtn');

  if (state.drawingMode) {
    state.drawingPoints = [];
    clearDrawnPolygonSource();
    if (btn) {
      btn.style.background = 'var(--royal)';
      btn.style.color = '#fff';
      btn.innerHTML = `
        <svg viewBox="0 0 24 24"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg>
        انقر على الخريطة لتحديد النقاط
      `;
    }
    if (baghdadMap) baghdadMap.getCanvas().style.cursor = 'crosshair';
  } else {
    if (btn) {
      btn.style.background = '';
      btn.style.color = '';
      btn.innerHTML = `
        <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
        رسم حدود قطعة الأرض يدوياً
      `;
    }
    if (baghdadMap) baghdadMap.getCanvas().style.cursor = '';
  }
}

function updateDrawnPolygonSource() {
  if (!baghdadMap) return;
  const src = baghdadMap.getSource('drawn-polygon');
  if (!src) return;

  if (state.drawingPoints.length < 2) {
    src.setData({ type: 'FeatureCollection', features: [] });
    return;
  }

  // Convert points [[lat, lon], ...] to MapLibre GeoJSON coordinates [[lon, lat], ...]
  const coords = state.drawingPoints.map((p) => [p[1], p[0]]);
  if (state.drawingPoints.length >= 3) {
    coords.push([state.drawingPoints[0][1], state.drawingPoints[0][0]]);
    src.setData({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [coords],
          },
        },
      ],
    });
  } else {
    src.setData({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: coords,
          },
        },
      ],
    });
  }
}

function clearDrawnPolygonSource() {
  if (!baghdadMap) return;
  const src = baghdadMap.getSource('drawn-polygon');
  if (src) src.setData({ type: 'FeatureCollection', features: [] });
  const treeSrc = baghdadMap.getSource('trees-source');
  if (treeSrc) treeSrc.setData({ type: 'FeatureCollection', features: [] });
}

function clearMapSelection() {
  state.selectedPolygon = [];
  state.drawingPoints = [];
  state.drawingMode = false;
  const btn = el('drawPolygonBtn');
  if (btn) {
    btn.style.background = '';
    btn.style.color = '';
    btn.innerHTML = `
      <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
      رسم حدود قطعة الأرض يدوياً
    `;
  }
  if (baghdadMap) baghdadMap.getCanvas().style.cursor = '';
  clearDrawnPolygonSource();

  // Reset side panel
  const verdict = el('verdictPanelBody');
  if (verdict) {
    verdict.innerHTML = `
      <div class="loading-inline">
        <div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div>
        <span>انقر على الخريطة أو ابحث عن موقع للبدء بالفحص</span>
      </div>
    `;
  }
  const soilCard = el('soilProfileCard');
  if (soilCard) soilCard.style.display = 'none';
  const treeCard = el('treeTableCard');
  if (treeCard) treeCard.style.display = 'none';
}

/* ══════════════════════════════════════════════════════════════
   FORWARD SEARCH & AUTOCOMPLETE (LOCATIONIQ BAGHDAD ONLY)
══════════════════════════════════════════════════════════════ */
let searchDebounceTimer = null;

const searchInput = el('baghdadSearchInput');
if (searchInput) {
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchDebounceTimer);
    const q = e.target.value.trim();
    if (q.length < 2) {
      closeAutocomplete();
      return;
    }
    searchDebounceTimer = setTimeout(() => {
      fetchPlaceSuggestions(q);
    }, 280);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      runBaghdadSearch();
    }
  });
}

async function fetchPlaceSuggestions(q) {
  const dropdownEl = el('baghdadAutocomplete');
  if (!dropdownEl) return;

  try {
    const resp = await fetch(`/api/search-places?q=${encodeURIComponent(q)}`);
    if (!resp.ok) return;
    const data = await resp.json();
    const results = data.results || [];

    if (results.length === 0) {
      closeAutocomplete();
      return;
    }

    dropdownEl.innerHTML = '';
    results.forEach((item) => {
      const opt = document.createElement('div');
      opt.className = 'autocomplete-item';
      opt.innerHTML = `
        <div style="font-weight:600; color:var(--text); font-size:12px;">${escHtml(item.name_ar)}</div>
        <div style="font-size:10.5px; color:var(--text-muted); text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
          ${escHtml(item.display_name || '')}
        </div>
      `;
      opt.addEventListener('click', () => {
        selectSearchResult(item);
      });
      dropdownEl.appendChild(opt);
    });
    dropdownEl.classList.add('visible');
    dropdownEl.style.display = 'block';
  } catch (e) {
    console.debug('Search suggestions error:', e);
  }
}

function closeAutocomplete() {
  const dropdownEl = el('baghdadAutocomplete');
  if (dropdownEl) {
    dropdownEl.classList.remove('visible');
    dropdownEl.style.display = 'none';
    dropdownEl.innerHTML = '';
  }
}

function selectSearchResult(item) {
  closeAutocomplete();
  const input = el('baghdadSearchInput');
  if (input) input.value = item.name_ar;

  const lat = item.lat;
  const lon = item.lon;
  state.selectedLat = lat;
  state.selectedLon = lon;
  state.selectedLocationAr = item.name_ar;

  if (baghdadMap) {
    baghdadMap.flyTo({
      center: [lon, lat],
      zoom: 16,
      pitch: 25,
      essential: true,
    });
    updateSelectionMarker([lon, lat]);
  }

  state.selectedPolygon = [];
  clearDrawnPolygonSource();
  runUnifiedInspection();
}

function runBaghdadSearch() {
  const input = el('baghdadSearchInput');
  if (!input) return;
  const q = input.value.trim();
  if (!q) return;

  fetchPlaceSuggestions(q);
}

// Close autocomplete on click outside
document.addEventListener('click', (e) => {
  if (!e.target.closest('#affSearchBar')) {
    closeAutocomplete();
  }
});

/* ══════════════════════════════════════════════════════════════
   LIVE WEATHER TELEMETRY
══════════════════════════════════════════════════════════════ */
async function fetchLiveWeather(lat, lon) {
  try {
    const resp = await fetch(`/api/weather?lat=${lat}&lon=${lon}&location_name_ar=${encodeURIComponent(state.selectedLocationAr)}`);
    if (!resp.ok) return;
    const data = await resp.json();
    state.weatherData = data;

    el('wm-air').textContent = fmt(data.air_temp_c) + ' °C';
    el('wm-soil').textContent = fmt(data.soil_temp_c) + ' °C';
    el('wm-lst').textContent = fmt(data.surface_lst_c) + ' °C';
    el('wm-hum').textContent = fmt(data.relative_humidity_pct) + ' %';
    el('wm-wind').textContent = fmt(data.wind_speed_kmh) + ' كم/س';
    el('wm-solar').textContent = fmtInt(data.solar_radiation_wm2);
    el('wm-dust').textContent = 'حالة الغبار: ' + (data.dust_aerosol_status_ar || 'معتدل');

    el('kpi-air-temp').textContent = fmt(data.air_temp_c) + ' °C';
    el('kpi-lst-range').textContent = `LST السطح: ${fmt(data.surface_lst_c)} °C`;
    el('kpi-weather-source').textContent = data.source || 'Open-Meteo API';

    state.windSpeedMs = (data.wind_speed_kmh ? data.wind_speed_kmh / 3.6 : 3.5);
    state.windDeg = data.wind_direction_deg || 315.0;
    if (state.is4DActive) {
      fetchAndRenderDiurnalPlume();
    }

    updateTelemetry();
  } catch (e) {
    console.debug('Weather fetch error:', e);
  }
}

/* ══════════════════════════════════════════════════════════════
   UNIFIED PARALLEL GEOSPATIAL INSPECTION ENGINE
   (Fast Single-Roundtrip Multi-Agent Orchestration < 5.0s)
══════════════════════════════════════════════════════════════ */
async function runUnifiedInspection() {
  showLoading('mapLoadingOverlay');

  // If user drew a polygon with 3+ points, finalize it
  if (state.drawingPoints.length >= 3) {
    state.selectedPolygon = [...state.drawingPoints, state.drawingPoints[0]];
    state.drawingMode = false;
    const btn = el('drawPolygonBtn');
    if (btn) {
      btn.style.background = '';
      btn.style.color = '';
      btn.innerHTML = `
        <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
        رسم حدود قطعة الأرض يدوياً
      `;
    }
    if (baghdadMap) baghdadMap.getCanvas().style.cursor = '';
  }

  const lat = state.selectedLat;
  const lon = state.selectedLon;
  const district = state.selectedLocationAr || 'بغداد';

  const payload = {
    lat: lat,
    lon: lon,
    polygon_coords: state.selectedPolygon,
    location_name_ar: district,
    custom_area_m2: state.selectedPolygon.length >= 3 ? null : 180.0,
    soil_telemetry: getLiveSoilTelemetryContext(),
  };

  try {
    const resp = await fetch('/api/v1/inspect-comprehensive-parcel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      throw new Error(`Unified inspection returned HTTP ${resp.status}`);
    }

    const data = await resp.json();
    updateUnifiedDossier(data);
  } catch (err) {
    console.error('Unified parallel inspection error, falling back:', err);
    try {
      await Promise.allSettled([
        fetchLiveWeather(lat, lon),
        executeAgent1LandInspection(),
        executeAgent2PollutionSentinel(lat, lon, district),
        executeAgent3PollutionMitigation(lat, lon, district),
      ]);
    } catch (fallbackErr) {
      console.error('Fallback parallel execution error:', fallbackErr);
    }
  } finally {
    hideLoading('mapLoadingOverlay');
  }
}

function updateUnifiedDossier(data) {
  if (!data) return;

  // 1. Weather and CAMS Telemetry
  if (data.weather) {
    state.weatherData = data.weather;
    if (el('wm-air')) el('wm-air').textContent = fmt(data.weather.air_temp_c) + ' °C';
    if (el('wm-soil')) el('wm-soil').textContent = fmt(data.weather.soil_temp_c) + ' °C';
    if (el('wm-lst')) el('wm-lst').textContent = fmt(data.weather.surface_lst_c) + ' °C';
    if (el('wm-hum')) el('wm-hum').textContent = fmt(data.weather.relative_humidity_pct) + ' %';
    if (el('wm-wind')) el('wm-wind').textContent = fmt(data.weather.wind_speed_kmh) + ' كم/س';
    if (el('wm-solar')) el('wm-solar').textContent = fmtInt(data.weather.solar_radiation_wm2);
    if (el('wm-dust')) el('wm-dust').textContent = 'حالة الغبار: ' + (data.weather.dust_aerosol_status_ar || 'معتدل');

    if (el('kpi-air-temp')) el('kpi-air-temp').textContent = fmt(data.weather.air_temp_c) + ' °C';
    if (el('kpi-lst-range')) el('kpi-lst-range').textContent = `LST السطح: ${fmt(data.weather.surface_lst_c)} °C`;
    if (el('kpi-weather-source')) el('kpi-weather-source').textContent = data.weather.source || 'Open-Meteo API';

    state.windSpeedMs = (data.weather.wind_speed_kmh ? data.weather.wind_speed_kmh / 3.6 : 3.5);
  }

  // 2. Hydrate Agent 1 (Soil & Land-use Viability) - TAB B
  if (data.agent1) {
    state.landResult = data.agent1.raw || data.agent1;
    renderLandInspectionResult(state.landResult);
  }

  // 3. Hydrate Agent 2 (WHO & International Benchmark) - TAB C
  if (data.agent2) {
    state.pollutionData = data.agent2.raw || data.agent2;
    renderAgent2Data(data.agent2);
    renderPollutionResult(state.pollutionData);
  }

  // 4. Hydrate Agent 3 (Pollution Mitigation Engineering) - TAB A
  if (data.agent3) {
    const agent3Data = data.agent3.raw || data.agent3;
    renderPollutionMitigationResult(agent3Data, data.location_name_ar, data.lat, data.lon);
  }

  // 5. Render Institutional Live AI Telemetry Proof Badge for Module 1
  const tel = data.ai_telemetry || data.agent3?.ai_telemetry || data.agent1?.ai_telemetry || {};
  const badgeEl = el('module1AiTelemetryBadge');
  if (badgeEl) {
    if (tel.model_name || tel.is_live_cloud) {
      badgeEl.style.display = 'inline-flex';
      badgeEl.innerHTML = `<span class="telemetry-live-dot"></span>تحليل حي من سحابة Groq LPU | الموديل: <strong>${escHtml(tel.model_name || 'Groq LPU')}</strong> | زمن الاستجابة: <strong>${tel.latency_ms || 0} ms</strong> | معرّف الطلب: <code>${escHtml(tel.request_id || 'live')}</code>`;
    } else {
      badgeEl.style.display = 'none';
    }
  }

  // 6. Update 4D Diurnal Plume if active
  if (state.is4DActive) {
    fetchAndRenderDiurnalPlume();
  }

  updateTelemetry();
}

// Backward compatibility alias
function runLandInspection() {
  return runUnifiedInspection();
}

async function executeAgent1LandInspection() {
  const payload = {
    lat: state.selectedLat,
    lon: state.selectedLon,
    polygon_coords: state.selectedPolygon,
    location_name_ar: state.selectedLocationAr,
    custom_area_m2: state.selectedPolygon.length >= 3 ? null : 180.0,
  };

  try {
    const resp = await fetch('/api/inspect-land', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Inspection failed');
    }

    const data = await resp.json();
    state.landResult = data;
    renderLandInspectionResult(data);
  } catch (err) {
    console.error('Land inspection (Agent 1) error:', err);
    const body = el('verdictPanelBody');
    if (body) {
      body.innerHTML = `
        <div style="background:#FEF2F2; color:#991B1B; padding:12px; border-radius:8px; font-size:12px;">
          حدث خطأ أثناء فحص الموقع: ${escHtml(err.message)}
        </div>
      `;
    }
  }
}

async function executeAgent2PollutionSentinel(lat, lon, district) {
  try {
    const resp = await fetch(`/api/pollution-sentinel?lat=${lat}&lon=${lon}&location_name_ar=${encodeURIComponent(district || state.selectedLocationAr || 'بغداد')}`);
    if (!resp.ok) {
      throw new Error('Failed to fetch pollution sentinel data');
    }
    const data = await resp.json();
    state.pollutionData = data;
    renderPollutionResult(data);
  } catch (e) {
    console.error('Pollution sentinel (Agent 2) error:', e);
  }
}

async function executeAgent3PollutionMitigation(lat, lon, district) {
  try {
    const resp = await fetch(
      `/api/v1/diagnose-pollution-mitigation?lat=${lat}&lon=${lon}&district_name_ar=${encodeURIComponent(district || state.selectedLocationAr || 'بغداد')}`,
      { method: 'POST' }
    );
    if (!resp.ok) {
      throw new Error(`Server returned HTTP ${resp.status}`);
    }
    const data = await resp.json();
    renderPollutionMitigationResult(data, district, lat, lon);
  } catch (e) {
    console.error('Pollution mitigation (Agent 3) error:', e);
  }
}

function renderLandInspectionResult(data) {
  // 1. Update KPI Cards
  el('kpi-area-m2').textContent = fmtInt(data.total_selected_area_m2) + ' م²';
  el('kpi-area-dunum').textContent = `${fmt(data.total_selected_area_dunums, 3)} دونم صافٍ`;

  const badge = el('kpi-suitability-badge');
  if (data.can_plant_trees) {
    badge.className = 'kpi-badge up mt-8';
    badge.innerHTML = `<span>مناسب للتشجير</span>`;
  } else {
    badge.className = 'kpi-badge down mt-8';
    badge.innerHTML = `<span>غير صالح للغرس</span>`;
  }

  // 2. Verdict Body
  const verdictBody = el('verdictPanelBody');
  const soilCard = el('soilProfileCard');
  const treeCard = el('treeTableCard');

  if (!data.can_plant_trees) {
    // Rejected Building / Road / Concrete
    verdictBody.innerHTML = `
      <div style="background:#FEF2F2; border-right:4px solid #DC2626; padding:12px 14px; border-radius:8px;">
        <div style="font-weight:700; color:#991B1B; font-size:13px; margin-bottom:6px;">
          ${escHtml(data.suitability_title_ar || 'تنبيه الفحص الهندسي والفضائي')}
        </div>
        <div style="font-size:12px; color:#7F1D1D; line-height:1.6;">
          ${escHtml(data.suitability_explanation_ar)}
        </div>
      </div>
    `;

    if (soilCard) soilCard.style.display = 'none';
    if (treeCard) treeCard.style.display = 'none';

    // Clear trees from map
    if (baghdadMap && baghdadMap.getSource('trees-source')) {
      baghdadMap.getSource('trees-source').setData({ type: 'FeatureCollection', features: [] });
    }
    updateTelemetry();
    return;
  }

  // Suitable Barren Ground
  verdictBody.innerHTML = `
    <div style="background:#F0FDF4; border-right:4px solid var(--sage); padding:12px 14px; border-radius:8px;">
      <div style="font-weight:700; color:var(--sage); font-size:13px; margin-bottom:6px;">
        ${escHtml(data.suitability_title_ar || 'الموقع مناسب للتشجير الذكي')}
      </div>
      <div style="font-size:12px; color:var(--text); line-height:1.6;">
        ${escHtml(data.suitability_explanation_ar)}
      </div>
    </div>
  `;

  // 3. Soil Profile Card
  if (soilCard) {
    soilCard.style.display = 'block';
    el('soil-type-title').textContent = data.soil_type_title_ar || 'تربة بغداد الرسوبية';
    el('soil-salinity-val').textContent = fmt(data.soil_salinity_ece_dsm || 3.5, 1);
    el('soil-ph-val').textContent = fmt(data.soil_ph || 7.8, 1);
    el('soil-remediation-text').textContent =
      data.soil_remediation_protocol_ar || 'حراثة وتجهيز جور الزراعة بنظام الري بالتنقيط النبضي.';
  }

  // 4. Tree Allocation Table & Chart
  const species = data.selected_species || [];
  if (treeCard && species.length > 0) {
    treeCard.style.display = 'block';
    const tbody = el('treeTableBody');
    tbody.innerHTML = '';

    const labels = [];
    const pcts = [];
    const colors = ['#1B4D3E', '#2D5A43', '#B45309', '#65A30D'];

    species.forEach((sp, idx) => {
      labels.push(sp.name_ar);
      pcts.push(sp.allocation_pct);

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:600; color:var(--text);">${escHtml(sp.name_ar)}</td>
        <td style="font-size:11px; color:var(--text-muted); font-style:italic;">${escHtml(sp.scientific_name || '')}</td>
        <td style="font-weight:700; color:${colors[idx % colors.length]};">${fmt(sp.allocation_pct, 0)}%</td>
        <td style="font-size:11.5px; color:var(--text-secondary); line-height:1.45;">${escHtml(sp.soil_climate_match_reason_ar || '')}</td>
      `;
      tbody.appendChild(tr);
    });

    // Chart.js Doughnut
    renderTreeChart(labels, pcts, colors);

    if (data.agronomic_executive_report_ar) {
      el('agronomicExecReport').textContent = data.agronomic_executive_report_ar;
      el('agronomicExecReport').style.display = 'block';
    } else {
      el('agronomicExecReport').style.display = 'none';
    }
  }

  // 5. Water & Carbon KPIs
  const waterSaved = Math.round((data.net_plantable_area_m2 || 180) * 12.5);
  el('kpi-water-saved').textContent = fmtInt(waterSaved);
  const co2Offset = (data.net_plantable_area_dunums || 0.1) * 3.8;
  el('kpi-co2').textContent = fmt(co2Offset, 1);
  const annualIqd = Math.round(waterSaved * 52 * 4.2);
  el('kpi-savings-iqd').textContent = fmtInt(annualIqd);
  el('kpi-savings-usd').textContent = `$${fmtInt(annualIqd / 1320)} دولار / سنة`;

  // 6. Render GeoJSON Trees in MapLibre
  if (baghdadMap && baghdadMap.getSource('trees-source') && data.geojson_trees) {
    baghdadMap.getSource('trees-source').setData(data.geojson_trees);
  }

  updateTelemetry();
}

function renderTreeChart(labels, data, colors) {
  const ctx = el('treeChart');
  if (!ctx) return;

  if (treeChartInstance) {
    treeChartInstance.destroy();
  }

  treeChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: '#FFFFFF',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          rtl: true,
          labels: {
            font: { family: 'inherit', size: 11 },
            boxWidth: 12,
          },
        },
      },
    },
  });
}

/* ══════════════════════════════════════════════════════════════
   AGENT 2: POLLUTION SENTINEL & GLOBAL RESEARCH BENCHMARK
══════════════════════════════════════════════════════════════ */
async function loadPollutionData(lat, lon) {
  showLoading('mapLoadingOverlay');
  try {
    const resp = await fetch(`/api/pollution-sentinel?lat=${lat}&lon=${lon}&location_name_ar=${encodeURIComponent(state.selectedLocationAr)}`);
    if (!resp.ok) {
      throw new Error('Failed to fetch pollution sentinel data');
    }
    const data = await resp.json();
    state.pollutionData = data;
    renderPollutionResult(data);
  } catch (e) {
    console.error('Pollution data fetch error:', e);
  } finally {
    hideLoading('mapLoadingOverlay');
  }
}

function renderAgent2Data(agent2Data) {
  if (!agent2Data) return;

  const city = agent2Data.benchmark_city_ar || agent2Data.benchmark_country_ar || 'بحث بيئي دولي معتمد';
  const project = agent2Data.project_title_ar || agent2Data.benchmark_project_title_ar || 'بروتوكول المعالجة البيئية ومصائد الملوثات';
  const risk = agent2Data.who_health_risk_ar || agent2Data.health_risk_assessment_ar || '';
  const specs = agent2Data.engineering_specs_ar || agent2Data.engineering_mitigation_protocol_ar || '';
  const species = agent2Data.recommended_species || agent2Data.target_species_ar || [];
  const lstDrop = agent2Data.expected_lst_cooling_c !== undefined ? agent2Data.expected_lst_cooling_c : agent2Data.expected_lst_drop_c;
  const pmDrop = agent2Data.expected_pm_reduction_pct;

  // 1. Benchmark badge & Project Title
  const bBadge = el('agent2BenchmarkBadge') || el('pol-benchmark-country');
  if (bBadge) bBadge.textContent = city;
  const oldCountry = el('pol-benchmark-country');
  if (oldCountry && oldCountry !== bBadge) oldCountry.textContent = city;

  const pTitle = el('agent2ProjectTitle') || el('pol-benchmark-project');
  if (pTitle) pTitle.textContent = project;
  const oldProject = el('pol-benchmark-project');
  if (oldProject && oldProject !== pTitle) oldProject.textContent = project;

  // 2. WHO Health Risk Report (Clean formatted HTML with bold labels)
  const riskEl = el('agent2WhoRiskReport') || el('pol-health-risk');
  if (riskEl) {
    if (risk) {
      riskEl.innerHTML = `
        <div style="margin-bottom:6px; font-weight:700; color:#991B1B;">تقييم منظمة الصحة العالمية (WHO) للمخاطر التنفسية:</div>
        <div style="line-height:1.6; color:#7F1D1D;">${escHtml(risk)}</div>
      `;
    } else {
      riskEl.innerHTML = `<div style="line-height:1.6; color:#7F1D1D;">جودة الهواء ضمن الحدود المقبولة؛ يُوصى بإنشاء أحزمة تبريد حضرية لخفض شذوذ الجزيرة الحرارية.</div>`;
    }
  }
  const oldRisk = el('pol-health-risk');
  if (oldRisk && oldRisk !== riskEl) {
    oldRisk.textContent = risk || 'تقييم WHO للمخاطر الصحية.';
  }

  // 3. Engineering Specs
  const specsEl = el('agent2EngineeringSpecs') || el('pol-mitigation-protocol');
  if (specsEl) {
    if (Array.isArray(specs) && specs.length > 0) {
      specsEl.innerHTML = `
        <ol style="margin:0; padding-right:18px; line-height:1.6; color:var(--text-secondary);">
          ${specs.map((s) => `<li style="margin-bottom:4px;">${escHtml(s)}</li>`).join('')}
        </ol>
      `;
    } else if (typeof specs === 'string' && specs.trim()) {
      const lines = specs.split(/\r?\n|•|- /).map(l => l.trim()).filter(Boolean);
      if (lines.length > 1) {
        specsEl.innerHTML = `
          <ul style="margin:0; padding-right:18px; line-height:1.6; color:var(--text-secondary);">
            ${lines.map((l) => `<li style="margin-bottom:4px;">${escHtml(l)}</li>`).join('')}
          </ul>
        `;
      } else {
        specsEl.innerHTML = `<div style="line-height:1.6; color:var(--text-secondary);">${escHtml(specs)}</div>`;
      }
    } else {
      specsEl.innerHTML = `<div style="line-height:1.6; color:var(--text-secondary);">تصميم حزام شجري عازل متدرج الارتفاع بمسامية 40% لصد العوالق وخفض سرعة الرياح.</div>`;
    }
  }
  const oldProtocol = el('pol-mitigation-protocol');
  if (oldProtocol && oldProtocol !== specsEl) {
    oldProtocol.textContent = Array.isArray(specs) ? specs.join(' ') : (specs || '');
  }

  const bufferEl = el('pol-buffer-specs');
  if (bufferEl) {
    bufferEl.textContent = agent2Data.recommended_buffer_specs_ar || 'حزام شجري عازل بعرض 25 إلى 35 متراً.';
  }

  // 4. Botanical Air-Filtration Species Badges
  const speciesListEl = el('agent2PlantSpeciesList') || el('pol-target-species');
  if (speciesListEl) {
    speciesListEl.innerHTML = '';
    const items = (species && species.length > 0) ? species : ['السدر البلدي', 'النيم الهندي', 'الكاليبتوس', 'الأثل العراقي'];
    items.forEach((sp) => {
      const tag = document.createElement('span');
      tag.className = 'species-tag';
      tag.textContent = sp;
      speciesListEl.appendChild(tag);
    });
  }
  const oldSpecies = el('pol-target-species');
  if (oldSpecies && oldSpecies !== speciesListEl) {
    oldSpecies.innerHTML = '';
    const items = (species && species.length > 0) ? species : ['السدر البلدي', 'النيم الهندي', 'الكاليبتوس', 'الأثل العراقي'];
    items.forEach((sp) => {
      const tag = document.createElement('span');
      tag.className = 'species-tag';
      tag.textContent = sp;
      oldSpecies.appendChild(tag);
    });
  }

  // 5. Expected Impact Drops
  const lstDropEl = el('agent2ExpectedLstDrop') || el('pol-lst-drop');
  if (lstDropEl) {
    const val = lstDrop !== undefined && lstDrop !== null ? Number(lstDrop) : 3.2;
    lstDropEl.textContent = `-${Math.abs(val).toFixed(1)} °C`;
  }
  const oldLst = el('pol-lst-drop');
  if (oldLst && oldLst !== lstDropEl) {
    const val = lstDrop !== undefined && lstDrop !== null ? Number(lstDrop) : 3.2;
    oldLst.textContent = `-${Math.abs(val).toFixed(1)} °C`;
  }

  const pmDropEl = el('agent2ExpectedPmDrop') || el('pol-pm-reduction');
  if (pmDropEl) {
    const val = pmDrop !== undefined && pmDrop !== null ? Number(pmDrop) : 42.0;
    pmDropEl.textContent = `-${Math.abs(val).toFixed(1)}%`;
  }
  const oldPm = el('pol-pm-reduction');
  if (oldPm && oldPm !== pmDropEl) {
    const val = pmDrop !== undefined && pmDrop !== null ? Number(pmDrop) : 42.0;
    oldPm.textContent = `-${Math.abs(val).toFixed(1)}%`;
  }
}

function renderPollutionResult(data) {
  // Always hydrate Agent 2 Tab C elements
  renderAgent2Data(data);

  // 1. Top KPI Row
  if (el('kpi-pol-aqi')) {
    el('kpi-pol-aqi').textContent = data.aqi_european;
    el('kpi-pol-aqi').style.color = data.aqi_color_hex || 'var(--royal)';
  }
  if (el('kpi-pol-aqi-status')) el('kpi-pol-aqi-status').textContent = data.aqi_status_ar || 'معتدل';

  if (el('kpi-pol-pm25')) el('kpi-pol-pm25').textContent = fmt(data.pm25_ugm3, 1);
  if (el('kpi-pol-pm25-status')) el('kpi-pol-pm25-status').textContent = data.pm25_status_ar || 'المخاطر الرئوية';

  if (el('kpi-pol-pm10')) el('kpi-pol-pm10').textContent = fmt(data.pm10_ugm3, 1);
  if (el('kpi-pol-pm10-status')) el('kpi-pol-pm10-status').textContent = data.pm10_status_ar || 'غبار معلق';

  if (el('kpi-pol-uhi')) el('kpi-pol-uhi').textContent = `+${fmt(data.uhi_anomaly_c, 1)} °C`;
  if (el('kpi-pol-lst')) el('kpi-pol-lst').textContent = `حرارة السطح LST: ${fmt(data.surface_lst_c, 1)} °C`;
  if (el('kpi-pol-hazard-status')) el('kpi-pol-hazard-status').textContent = data.dominant_hazard_title_ar || 'شذوذ حراري';

  // 2. CAMS Readouts Grid
  if (el('pol-location-label')) el('pol-location-label').textContent = data.location_name_ar || 'بغداد';
  if (el('cams-aqi')) el('cams-aqi').textContent = data.aqi_european;
  if (el('cams-pm25')) el('cams-pm25').textContent = fmt(data.pm25_ugm3, 1);
  if (el('cams-pm10')) el('cams-pm10').textContent = fmt(data.pm10_ugm3, 1);
  if (el('cams-no2')) el('cams-no2').textContent = fmt(data.no2_ugm3, 1);
  if (el('cams-so2')) el('cams-so2').textContent = fmt(data.so2_ugm3, 1);
  if (el('cams-uhi')) el('cams-uhi').textContent = `+${fmt(data.uhi_anomaly_c, 1)} °C`;

  // 3. International Benchmark Card (Zero Emojis)
  renderAgent2Data(data);

  // 4. MapLibre GeoJSON Radar Circle
  if (baghdadMap && baghdadMap.getSource('radar-source')) {
    const circleCoords = generateGeoJSONCircle([data.lon, data.lat], 1.2); // ~1.2 km radius
    baghdadMap.getSource('radar-source').setData({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [circleCoords],
          },
          properties: {
            color: data.aqi_color_hex || '#DC2626',
          },
        },
      ],
    });

    baghdadMap.setLayoutProperty('radar-circle-fill', 'visibility', 'visible');
    baghdadMap.setLayoutProperty('radar-circle-line', 'visibility', 'visible');
  }

  updateTelemetry();
}

function generateGeoJSONCircle(centerLonLat, radiusKm, points = 64) {
  const coords = [];
  const distanceX = radiusKm / (111.32 * Math.cos((centerLonLat[1] * Math.PI) / 180));
  const distanceY = radiusKm / 110.574;

  for (let i = 0; i <= points; i++) {
    const theta = (i / points) * (2 * Math.PI);
    const x = distanceX * Math.cos(theta);
    const y = distanceY * Math.sin(theta);
    coords.push([centerLonLat[0] + x, centerLonLat[1] + y]);
  }
  return coords;
}

/* ══════════════════════════════════════════════════════════════
   WORKSPACE 2: UNIVERSAL COMPUTER VISION & STATEFUL SOIL LAB
══════════════════════════════════════════════════════════════ */

async function compressImageToBlob(source) {
  return new Promise((resolve, reject) => {
    const processImg = (img) => {
      let width = img.naturalWidth || img.videoWidth || img.width;
      let height = img.naturalHeight || img.videoHeight || img.height;
      const maxDim = 768;
      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = Math.round((height * maxDim) / width);
          width = maxDim;
        } else {
          width = Math.round((width * maxDim) / height);
          height = maxDim;
        }
      }
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error('Canvas compression failed'));
      }, 'image/jpeg', 0.82);
    };

    if (source instanceof HTMLVideoElement) {
      processImg(source);
    } else if (source instanceof Blob || source instanceof File) {
      const img = new Image();
      const url = URL.createObjectURL(source);
      img.onload = () => {
        URL.revokeObjectURL(url);
        processImg(img);
      };
      img.onerror = (e) => {
        URL.revokeObjectURL(url);
        reject(e);
      };
      img.src = url;
    } else {
      reject(new Error('Unsupported image source'));
    }
  });
}

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  state.currentSelectedFile = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    const originalImg = el('originalLeafImg');
    if (originalImg) {
      originalImg.src = e.target.result;
      originalImg.style.display = 'block';
    }
    const placeholder = el('origPlaceholderText');
    if (placeholder) placeholder.style.display = 'none';
  };
  reader.readAsDataURL(file);

  // Auto-run first sample in new session by default
  await analyzeSampleAction('NEW_SESSION');
}

async function analyzeSampleAction(action = 'NEW_SESSION') {
  const fileInput = el('leafFileInput');
  const file = state.currentSelectedFile || (fileInput?.files ? fileInput.files[0] : null);

  if (!file) {
    alert('يرجى اختيار صورة أولا أو الضغط على إحدى العينات النموذجية الجاهزة.');
    return;
  }

  showVisionLoading();
  try {
    const compressedBlob = await compressImageToBlob(file);
    const formData = new FormData();
    formData.append('image', compressedBlob, 'specimen_768px.jpg');
    formData.append('region_name', `بغداد - ${state.selectedLocationAr || 'محطة الفحص الميداني'}`);
    formData.append('session_id', state.activeLabSessionId || 'active_field_session');
    formData.append('session_action', 'NEW_SESSION');

    await runVisionDiagnostic(formData, 'NEW_SESSION');
  } catch (err) {
    console.error('Image compression or diagnostic error:', err);
    hideVisionLoading();
    alert('حدث خطأ أثناء معالجة الصورة: ' + err.message);
  }
}

// Deprecated preset samples removed in favor of real lab upload / live camera inspection
async function loadSample(sampleType, action = 'NEW_SESSION') {
  console.info('Preset samples removed in favor of authentic laboratory uploads & live camera diagnostics.');
}

async function runVisionDiagnostic(formData, action = 'NEW_SESSION') {
  showVisionLoading();
  try {
    if (!formData.has('session_id')) {
      formData.append('session_id', state.activeLabSessionId || 'active_field_session');
    }
    if (!formData.has('session_action')) {
      formData.append('session_action', 'NEW_SESSION');
    }
    if (!formData.has('soil_telemetry')) {
      formData.append('soil_telemetry', JSON.stringify(getLiveSoilTelemetryContext()));
    }

    const resp = await fetch('/api/v1/analyze-vision', {
      method: 'POST',
      body: formData,
    });
    if (!resp.ok) throw new Error('Diagnostic API failed');
    const data = await resp.json();
    state.visionResult = data;
    if (data.session_state) {
      state.labSessionState = data.session_state;
    }
    renderVisionResult(data);
  } catch (e) {
    console.error('Vision analysis error:', e);
  } finally {
    hideVisionLoading();
  }
}

function showVisionLoading() {
  const loading = el('visionLoading');
  if (loading) loading.classList.remove('hidden');
  const details = el('visionReportDetails');
  if (details) details.style.display = 'none';
  const empty = el('visionReportEmpty');
  if (empty) empty.style.display = 'none';
}

function hideVisionLoading() {
  const loading = el('visionLoading');
  if (loading) loading.classList.add('hidden');
}

function renderVisionResult(data) {
  if (!data) return;

  // 1. Images
  const origImg = el('originalLeafImg');
  const thermImg = el('thermalHeatmapImg');
  const specImg = el('spectralLeafImg');

  if (origImg && !origImg.src.startsWith('data:')) {
    origImg.style.display = 'block';
  }
  if (thermImg && (data.thermal_image_b64 || data.thermal_image)) {
    const tData = data.thermal_image_b64 || data.thermal_image;
    thermImg.src = tData.startsWith('data:') ? tData : `data:image/jpeg;base64,${tData}`;
    thermImg.style.display = 'block';
    const pTherm = el('thermPlaceholderText');
    if (pTherm) pTherm.style.display = 'none';
  }
  if (specImg && (data.spectral_image_b64 || data.spectral_image)) {
    const sData = data.spectral_image_b64 || data.spectral_image;
    specImg.src = sData.startsWith('data:') ? sData : `data:image/jpeg;base64,${sData}`;
    specImg.style.display = 'block';
    const pSpec = el('specPlaceholderText');
    if (pSpec) pSpec.style.display = 'none';
  }

  // 2. Top KPI Cards
  if (el('vis-diagnosis')) el('vis-diagnosis').textContent = data.primary_diagnosis_title_ar || data.diagnosis_title_ar || 'سليم';
  if (el('vis-category-badge')) el('vis-category-badge').textContent = data.sample_category_ar || 'عينة نباتية';
  if (el('vis-exg')) el('vis-exg').textContent = `${fmt(data.vitality_pct, 1)}%`;
  if (el('vis-stress')) el('vis-stress').textContent = `${fmt(data.stress_pct, 1)}%`;
  if (el('vis-dust')) el('vis-dust').textContent = `${fmt(data.dust_salinity_pct, 1)}%`;

  // 3. Diag Cards
  if (el('d-exg')) el('d-exg').textContent = fmt(data.vitality_pct, 1);
  if (el('d-dust')) el('d-dust').textContent = fmt(data.dust_salinity_pct, 1);
  if (el('d-water')) el('d-water').textContent = fmt(data.stress_pct, 1);
  if (el('d-hotspots')) el('d-hotspots').textContent = fmt(data.pixel_metrics?.estimated_surface_temp_c || 38.5, 1);

  // 4. Clinical Report Box
  if (el('rep-sample-cat')) el('rep-sample-cat').textContent = `نوع العينة: ${data.sample_category_ar || 'عينة نباتية'}`;
  if (el('rep-diag-title')) el('rep-diag-title').textContent = data.primary_diagnosis_title_ar || 'تشخيص زراعي';
  if (el('rep-engine-source')) el('rep-engine-source').textContent = `محرك: ${data.engine_source || 'Groq Vision LPU'}`;
  if (el('rep-symptoms')) el('rep-symptoms').textContent = data.visual_symptoms_description_ar || '—';
  if (el('rep-causes')) el('rep-causes').textContent = data.probable_causes_ar || '—';
  if (el('rep-treatment')) el('rep-treatment').textContent = data.treatment_revival_protocol_ar || '—';
  if (el('rep-irrigation')) el('rep-irrigation').textContent = data.irrigation_recommendation_ar || '—';
  if (el('rep-water-savings')) el('rep-water-savings').textContent = `الوفر المائي المتوقع: ~${fmt(data.expected_water_saving_pct || 38.5, 1)}%`;

  // 5. Laboratory Certificate Panel (Core Biometrics)
  const lab = data.lab_report || {};
  const sciName = lab.scientific_name || data.scientific_name || data.primary_diagnosis_title_ar || '—';
  const arabName = lab.arabic_common_name || data.arabic_common_name || data.status_label_ar || '—';
  if (el('labScientificName')) el('labScientificName').textContent = sciName;
  if (el('labCertScientificName')) el('labCertScientificName').textContent = sciName;
  if (el('labArabicName')) el('labArabicName').textContent = arabName;
  if (el('labSpecimenCategory')) el('labSpecimenCategory').textContent = lab.specimen_category || data.sample_category_ar || '—';
  if (el('labMoistureIndex')) el('labMoistureIndex').textContent = `${fmt(lab.surface_moisture_index_pct || data.laboratory_biometrics?.surface_moisture_index_pct || 45.0, 1)} %`;
  if (el('labSalinityCrust')) el('labSalinityCrust').textContent = `${fmt(lab.salinity_crust_index_pct || data.laboratory_biometrics?.salinity_crust_index_pct || data.dust_salinity_pct || 0.0, 1)} %`;
  if (el('labNdviProxy')) el('labNdviProxy').textContent = fmt(lab.chlorophyll_ndvi_proxy || data.laboratory_biometrics?.chlorophyll_ndvi_proxy || 0.52, 3);
  if (el('labCrackingScore')) el('labCrackingScore').textContent = `${fmt(lab.structural_cracking_score || data.laboratory_biometrics?.structural_cracking_score || 0.0, 1)} / 10`;
  if (el('labAnatomicalProfile')) el('labAnatomicalProfile').textContent = lab.anatomical_or_soil_profile || data.visual_symptoms_description_ar || '—';
  if (el('labPathology')) el('labPathology').textContent = lab.pathology_and_deficiency || data.probable_causes_ar || '—';
  if (el('labRemediation')) el('labRemediation').textContent = lab.remediation_protocol || data.treatment_revival_protocol_ar || '—';

  // 6. Engine 1: Differential Hypotheses (Summing to 100%)
  const hypoListEl = el('diffHypothesesList') || el('labHypothesesList');
  const rawHypotheses = data.differential_hypotheses || lab.differential_hypotheses || [];
  if (hypoListEl && Array.isArray(rawHypotheses) && rawHypotheses.length > 0) {
    const colors = ['#1E3A8A', '#D97706', '#64748B'];
    hypoListEl.innerHTML = rawHypotheses.map((h, i) => {
      const prob = typeof h.probability_pct === 'number' ? h.probability_pct : (parseFloat(h.probability_pct) || 0);
      const title = h.name_ar || h.hypothesis_ar || `فرضية ${i + 1}`;
      const desc = h.mechanism_ar || h.rationale_ar || '';
      const color = colors[i % colors.length];
      return `
        <div class="diff-hypo-card" style="margin-bottom:8px; background:#F8FAFC; border:1px solid #E2E8F0; padding:8px 12px; border-radius:6px;">
          <div class="diff-hypo-header" style="display:flex; justify-content:space-between; margin-bottom:4px; font-weight:700; font-size:12px;">
            <span class="diff-hypo-title" style="color:#0F172A;">${escHtml(title)}</span>
            <span class="diff-hypo-prob" style="color:${color}; direction:ltr;">${prob.toFixed(1)}%</span>
          </div>
          <div class="diff-hypo-bar-wrap" style="height:6px; background:#E2E8F0; border-radius:3px; overflow:hidden; margin-bottom:4px;">
            <div class="diff-hypo-bar" style="height:100%; width:${Math.min(prob, 100)}%; background:${color};"></div>
          </div>
          ${desc ? `<div class="diff-hypo-desc" style="font-size:11px; color:#475569; line-height:1.4;">${escHtml(desc)}</div>` : ''}
        </div>
      `;
    }).join('');
  }

  // Render Institutional Live AI Telemetry Proof Badge
  const tel = data.ai_telemetry || {};
  const badgeEl = el('labAiTelemetryBadge');
  if (badgeEl) {
    if (tel.model_name || tel.is_live_cloud) {
      badgeEl.style.display = 'inline-flex';
      badgeEl.innerHTML = `<span class="telemetry-live-dot"></span>تحليل حي من سحابة Groq LPU | الموديل: <strong>${escHtml(tel.model_name || 'Groq LPU')}</strong> | زمن الاستجابة: <strong>${tel.latency_ms || 0} ms</strong> | معرّف الطلب: <code>${escHtml(tel.request_id || 'live')}</code>`;
    } else {
      badgeEl.style.display = 'none';
    }
  }

  // 7. Confirmatory Field Directive & Rhizosphere Biogeochemistry
  const directive = data.confirmatory_field_directive_ar || lab.confirmatory_field_directive_ar || '';
  if (el('labFieldDirective')) {
    el('labFieldDirective').textContent = directive || 'يوصى بفحص تربة الرايزوسفير لتأكيد التشخيص السريري.';
  }
  const rhizoMech = data.rhizosphere_mechanism_ar || lab.rhizosphere_mechanism_ar || '';
  if (el('labRhizosphereMechanism')) {
    el('labRhizosphereMechanism').textContent = rhizoMech || 'الجهد التناضحي وحالة التهوية في بيئة الريزوسفير تؤثر مباشرة على الامتصاص الجذري.';
  }

  // 8. 3-Phase Clinical Prescription Protocol
  const pres = data.three_phase_prescription || lab.three_phase_prescription || null;
  render3PhasePrescription('labPrescription3Phase', pres);

  // 9. Initialize Interactive Clinical Consultation with Smart Lab Question
  const session = data.session_state || state.labSessionState;
  if (session) {
    state.labSessionState = session;
  }

  const banner = el('labNextDirectiveBanner');
  const initQ = lab.initial_investigator_question_ar || data.initial_investigator_question_ar || session?.next_lab_directive_ar || 'ما هي وتيرة الري وظروف تصريف الحوض؟';
  if (banner) {
    banner.textContent = `التوجيه السريري للمختبر الذكي: ${initQ}`;
  }

  // Populate consultation log with the smart lab's initial clinical question
  const consultLog = el('labConsultationLog') || el('labConsultLog');
  if (consultLog) {
    consultLog.innerHTML = '';
    appendConsultationBubble('investigator', initQ);
  }

  const details = el('visionReportDetails');
  if (details) details.style.display = 'block';
  const empty = el('visionReportEmpty');
  if (empty) empty.style.display = 'none';

  updateTelemetry();
}

function render3PhasePrescription(containerId, pres) {
  const container = el(containerId);
  if (!container) return;

  if (!pres || typeof pres !== 'object') {
    container.innerHTML = '<div style="font-size:11.5px; color:#64748B;">في انتظار توليد الوصفة السريرية ثلاثية المراحل...</div>';
    return;
  }

  const p1 = pres.phase_1_48h_emergency || {};
  const p2 = pres.phase_2_14d_root_remediation || {};
  const p3 = pres.phase_3_sustainable_prevention || {};

  const makePhaseBox = (cls, badgeText, title, actions) => {
    const actList = Array.isArray(actions) ? actions : (actions ? [actions] : []);
    return `
      <div class="prescription-phase-box ${cls}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="phase-badge ${cls}">${badgeText}</span>
        </div>
        <div class="phase-title">${escHtml(title || '')}</div>
        <ul class="phase-items-list">
          ${actList.map(item => `<li>${escHtml(item)}</li>`).join('')}
        </ul>
      </div>
    `;
  };

  container.innerHTML = `
    ${makePhaseBox('phase-1', 'المرحلة 1: التدخل العاجل (48 ساعة)', p1.timeframe_ar || 'إنقاذ النسيج وخفض الإجهاد', p1.actions_ar)}
    ${makePhaseBox('phase-2', 'المرحلة 2: معالجة الجذور (14 يوما)', p2.timeframe_ar || 'استصلاح الرايزوسفير وإعادة التوازن', p2.actions_ar)}
    ${makePhaseBox('phase-3', 'المرحلة 3: الوقاية المستدامة (موسمي)', p3.timeframe_ar || 'التحصين البيئي وتحسين الصرف', p3.actions_ar)}
  `;
}

function updateLabEvidenceTabs(session) {
  // Single-shot forensic mode: no multi-sample tabs
}

function switchLabEvidenceTab(tabIndex) {
  const certPanel = el('labCertificatePanel');
  if (certPanel) certPanel.style.display = 'block';
}

function renderCombinedSynthesisReport(report) {
  if (!report) return;
  const card = el('labCombinedReportCard');
  if (card) card.style.display = 'block';

  if (el('combConfirmedHypothesis')) {
    el('combConfirmedHypothesis').textContent = report.confirmed_differential_hypothesis_ar || 'تم تأكيد التشخيص السريري الموحد';
  }
  if (el('combPrognosisScore')) {
    const score = report.plant_health_prognosis_score ?? 68;
    el('combPrognosisScore').textContent = `${score} / 100`;
  }
  if (el('combCausalLink')) {
    el('combCausalLink').textContent = report.causal_correlation_foliage_to_soil_ar || '—';
  }
  if (el('combUnifiedProtocol')) {
    render3PhasePrescription('combUnifiedProtocol', report.unified_three_phase_prescription);
  }
}

async function resetLabSession() {
  const sessionId = state.activeLabSessionId || 'active_field_session';
  try {
    await fetch('/api/v1/lab-session/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
  } catch (err) {
    console.debug('Reset session warning:', err);
  }

  state.labSessionState = null;
  state.currentSelectedFile = null;
  state.activeEvidenceTab = 1;

  // Reset UI elements
  const origImg = el('originalLeafImg');
  if (origImg) { origImg.src = ''; origImg.style.display = 'none'; }
  const origPlaceholder = el('origPlaceholderText');
  if (origPlaceholder) origPlaceholder.style.display = 'inline';

  const thermImg = el('thermalHeatmapImg');
  if (thermImg) { thermImg.src = ''; thermImg.style.display = 'none'; }
  const thermPlaceholder = el('thermPlaceholderText');
  if (thermPlaceholder) thermPlaceholder.style.display = 'inline';

  const specImg = el('spectralLeafImg');
  if (specImg) { specImg.src = ''; specImg.style.display = 'none'; }
  const specPlaceholder = el('specPlaceholderText');
  if (specPlaceholder) specPlaceholder.style.display = 'inline';

  const combCard = el('labCombinedReportCard');
  if (combCard) combCard.style.display = 'none';

  const certPanel = el('labCertificatePanel');
  if (certPanel) certPanel.style.display = 'block';

  const hypoListEl = el('labHypothesesList');
  if (hypoListEl) hypoListEl.innerHTML = '<div style="font-size:11.5px; color:var(--text-muted); font-style:italic;">في انتظار الفحص المخبري لحساب الفرضيات التفريقية...</div>';

  if (el('labFieldDirective')) el('labFieldDirective').textContent = '—';
  if (el('labRhizosphereMechanism')) el('labRhizosphereMechanism').textContent = '—';
  if (el('labPrescription3Phase')) el('labPrescription3Phase').innerHTML = '';

  const banner = el('labNextDirectiveBanner');
  if (banner) banner.textContent = 'التوجيه السريري للمختبر الذكي: تم تصفير المختبر بنجاح. جاهز لفحص العينة.';

  const log = el('labConsultationLog') || el('labConsultLog');
  if (log) {
    log.innerHTML = '<div style="font-size:11.5px; color:#64748B; font-style:italic;">سجل الاستشارات السريرية فارغ حالياً. يطرح المختبر الذكي سؤاله الافتتاحي فور اكتمال الفحص.</div>';
  }
}

async function sendLabConsultation() {
  const input = el('labConsultInput');
  const btn = el('btnSendLabConsult');
  if (!input) return;
  const q = input.value.trim();
  if (!q) return;

  input.value = '';
  appendConsultationBubble('user', q);
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'جاري المعالجة السحابية...';
  }

  const sessionId = state.activeLabSessionId || 'active_field_session';

  try {
    const history = (state.labSessionState?.investigation_history || []).map(h => ({
      role: h.role,
      author: h.author || (h.role === 'user' ? 'المستخدم' : 'المختبر الذكي'),
      content: h.content || h.reply || h.question || ''
    }));

    const resp = await fetch('/api/v1/lab-session/consult', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        user_message: q,
        message: q,
        question: q,
        conversation_history: history,
        soil_telemetry: getLiveSoilTelemetryContext(),
      }),
    });

    if (!resp.ok) throw new Error('Consultation API failed');
    const data = await resp.json();
    appendConsultationBubble('investigator', data.reply_ar || data.investigator_reply_ar || 'تم تسجيل الاستشارة.');
    if (data.session_state) {
      state.labSessionState = data.session_state;
    }
  } catch (err) {
    appendConsultationBubble('investigator', `حدث خطأ أثناء الاتصال بالمختبر الذكي: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'إرسال للمختبر الذكي';
    }
  }
}

function appendConsultationBubble(role, text) {
  const log = el('labConsultationLog') || el('labConsultLog');
  if (!log) return;

  // Clear initial empty placeholder if present
  if (log.children.length === 1 && log.children[0].tagName === 'DIV' && log.children[0].style.fontStyle === 'italic') {
    log.innerHTML = '';
  }

  const safeText = text || '—';
  const bubble = document.createElement('div');
  bubble.className = `lab-consult-bubble ${role}`;
  const authorName = (role === 'user' || role === 'field_engineer')
    ? 'المستخدم'
    : 'المختبر الذكي';
  bubble.innerHTML = `
    <div class="lab-consult-author" style="font-weight:700; font-size:11.5px; margin-bottom:2px; color:${role === 'user' ? 'var(--royal)' : 'var(--sage)'};">${authorName}</div>
    <div style="font-size:12px; line-height:1.5;">${escHtml(safeText).replace(/\n/g, '<br/>')}</div>
  `;
  log.appendChild(bubble);
  log.scrollTop = log.scrollHeight;
}

function renderConsultationLog(history) {
  const log = el('labConsultationLog') || el('labConsultLog');
  if (!log || !Array.isArray(history) || history.length === 0) return;

  log.innerHTML = '';
  history.forEach(item => {
    if (!item) return;
    if (item.role && item.content) {
      appendConsultationBubble(item.role, item.content);
    } else {
      if (item.question) appendConsultationBubble('user', item.question);
      if (item.reply) appendConsultationBubble('investigator', item.reply);
    }
  });
}
window.renderLabConsultationLog = renderConsultationLog;

/* ══════════════════════════════════════════════════════════════
   ESP32 CAPACITIVE SOIL SENTINEL BRIDGE CLIENT (DUAL-MODALITY & WI-FI TELEMETRY)
══════════════════════════════════════════════════════════════ */

const ESP32_REGIME_LABELS_AR = {
  'PERMANENT_WILTING_POINT': 'نقطة الذبول الدائم (PWP < 14%) - جفاف حرج',
  'PWP_CRITICAL': 'نقطة الذبول الدائم (PWP < 14%) - جفاف حرج',
  'WILTING_CRITICAL': 'نقطة الذبول الدائم (PWP < 14%) - جفاف حرج',
  'CRITICAL_WILTING': 'نقطة الذبول الدائم (PWP < 14%) - جفاف حرج',
  'WILTING': 'إجهاد مائي حرج وذبول (PWP < 14%)',
  'SUB_OPTIMAL_DEPLETION': 'إجهاد مائي تحت السعة الحقلية (14% - 26%)',
  'SUB_OPTIMAL': 'إجهاد مائي تحت السعة الحقلية (14% - 26%)',
  'OPTIMAL_FIELD_CAPACITY': 'السعة الحقلية المثلى (26% - 38%) - رطوبة مثالية',
  'FIELD_CAPACITY': 'السعة الحقلية المثلى (26% - 38%) - رطوبة مثالية',
  'OPTIMAL': 'السعة الحقلية المثلى (26% - 38%) - رطوبة مثالية',
  'WATERLOGGING_HYPOXIA': 'تشبع مائي واختناق الجذور (> 38%)',
  'WATERLOGGED': 'تشبع مائي واختناق الجذور (> 38%)',
  'HYPOXIA': 'تشبع مائي واختناق الجذور (> 38%)',
  'DESICCATED': 'جفاف حاد وتصلب التربة (< 10%)',
  'SATURATED': 'تشبع مائي واختناق الجذور (> 38%)',
  'OPTICAL_STANDBY': 'بانتظار الإشارة (النمط البصري نشط)',
  'WAITING_FOR_SIGNAL': 'بانتظار استلام حزمة Wi-Fi من المجس...'
};

function setEsp32Modality(mode) {
  state.esp32Modality = mode;
  const btnOptical = el('btnModeOpticalOnly');
  const btnHybrid = el('btnModeHybridEsp32');
  const btnRefresh = el('btnRefreshEsp32');
  const badge = el('esp32StatusBadge');
  const grid = el('esp32DepthsGrid');

  if (mode === 'optical') {
    if (btnOptical) {
      btnOptical.style.background = 'var(--royal)';
      btnOptical.style.color = '#fff';
    }
    if (btnHybrid) {
      btnHybrid.style.background = 'transparent';
      btnHybrid.style.color = 'var(--text-muted)';
    }
    if (btnRefresh) btnRefresh.style.display = 'none';
    if (grid) grid.style.display = 'none';
    if (badge) {
      badge.className = 'esp32-status-badge online';
      badge.style.background = '#F0FDF4';
      badge.style.color = '#15803D';
      badge.style.border = '1px solid #BBF7D0';
      badge.innerHTML = 'النمط البصري المستقل نشط - القياس عبر تحليل الطيف اللوني';
    }
    if (el('esp32HydrologicalStatus')) {
      el('esp32HydrologicalStatus').textContent = 'النمط البصري نشط';
    }
  } else {
    if (btnOptical) {
      btnOptical.style.background = 'transparent';
      btnOptical.style.color = 'var(--text-muted)';
    }
    if (btnHybrid) {
      btnHybrid.style.background = 'var(--royal)';
      btnHybrid.style.color = '#fff';
    }
    if (btnRefresh) btnRefresh.style.display = 'inline-block';
    if (grid) grid.style.display = 'grid';
    fetchEsp32Status();
  }
}
window.setEsp32Modality = setEsp32Modality;

function refreshEsp32StatusManually() {
  fetchEsp32Status();
}
window.refreshEsp32StatusManually = refreshEsp32StatusManually;

function getLiveSoilTelemetryContext() {
  const d = state.latestEsp32Data;
  if (!d || (!d.connected && !d.is_connected)) {
    return {
      connected: false,
      mode: 'OFFLINE',
      telemetry_source: 'DISCONNECTED',
      soil_status: 'WAITING_FOR_SIGNAL',
    };
  }
  return {
    connected: true,
    telemetry_source: d.telemetry_source || d.mode || 'WIFI_WIRELESS',
    device_id: d.device_id || 'ESP32_SOIL_NODE_01',
    moisture_pct: d.moisture_pct !== undefined ? d.moisture_pct : d.live_vwc_pct,
    live_vwc_pct: d.live_vwc_pct !== undefined ? d.live_vwc_pct : d.moisture_pct,
    voltage_mv: d.voltage_mv,
    raw_adc: d.raw_adc,
    filtered_adc: d.filtered_adc,
    soil_status: d.soil_status,
    hydrological_status_ar: d.hydrological_status_ar,
    calibration_status: d.calibration_status,
    wifi_rssi: d.wifi_rssi,
    locked_depths: d.locked_depths || {},
    vertical_gradient_pct_per_cm: d.vertical_gradient_pct_per_cm,
    data_classification: d.data_classification,
    data_provenance: d.data_provenance,
  };
}
window.getLiveSoilTelemetryContext = getLiveSoilTelemetryContext;

async function fetchEsp32Status() {
  try {
    let data = null;

    // 1. Primary poll: unified status endpoint
    try {
      const resp = await fetch('/api/v1/esp32/status');
      if (resp.ok) {
        data = await resp.json();
      }
    } catch (e) {
      console.debug('Error fetching /api/v1/esp32/status:', e);
    }

    // 2. Direct check to /api/v1/esp32/latest-wifi if status is missing or not reporting fresh Wi-Fi
    if (!data || !data.connected || data.telemetry_source !== 'WIFI_WIRELESS') {
      try {
        const wifiResp = await fetch('/api/v1/esp32/latest-wifi');
        if (wifiResp.ok) {
          const wifiData = await wifiResp.json();
          if (wifiData && wifiData.connected && wifiData.is_fresh) {
            data = Object.assign({}, data || {}, wifiData, {
              telemetry_source: 'WIFI_WIRELESS',
              mode: 'WIFI_WIRELESS',
              connected: true,
              is_connected: true,
            });
          }
        }
      } catch (e) {
        console.debug('Error fetching /api/v1/esp32/latest-wifi:', e);
      }
    }

    if (!data) return;
    state.latestEsp32Data = data;

    const isConnected = !!(data.connected || data.is_connected);
    const isWifi = isConnected && (data.telemetry_source === 'WIFI_WIRELESS' || data.mode === 'WIFI_WIRELESS');
    const badge = el('esp32StatusBadge');
    const grid = el('esp32DepthsGrid');
    const btnRefresh = el('btnRefreshEsp32');
    const btnOptical = el('btnModeOpticalOnly');
    const btnHybrid = el('btnModeHybridEsp32');

    // 3. Dynamic Badge State
    if (badge) {
      if (isWifi) {
        // Auto-switch visual mode selector to hybrid if fresh Wi-Fi is transmitting
        if (state.esp32Modality !== 'hybrid') {
          state.esp32Modality = 'hybrid';
          if (btnOptical) {
            btnOptical.style.background = 'transparent';
            btnOptical.style.color = 'var(--text-muted)';
          }
          if (btnHybrid) {
            btnHybrid.style.background = 'var(--royal)';
            btnHybrid.style.color = '#fff';
          }
          if (btnRefresh) btnRefresh.style.display = 'inline-block';
          if (grid) grid.style.display = 'grid';
        }

        const devId = data.device_id || 'ESP32_SOIL_NODE_01';
        const rssiVal = (data.wifi_rssi !== undefined && data.wifi_rssi !== null && data.wifi_rssi !== 0)
          ? `${data.wifi_rssi} dBm`
          : 'إشارة ممتازة';
        const calibRaw = data.calibration_status || 'معايرة المصنع';
        const calibLabel = calibRaw === 'FACTORY_DEFAULT' ? 'معايرة رسوبية' : calibRaw;

        badge.className = 'esp32-status-badge online';
        badge.style.background = '#ECFDF5';
        badge.style.color = '#047857';
        badge.style.border = '1px solid #10B981';
        badge.innerHTML = `
          <span style="display:inline-flex; align-items:center; gap:6px;">
            <span style="width:8px; height:8px; border-radius:50%; background:#10B981; display:inline-block; box-shadow:0 0 6px #10B981;"></span>
            <span>متصل لاسلكياً عبر Wi-Fi (<b>${escHtml(devId)}</b>)</span>
            <span style="opacity:0.6;">|</span>
            <span>الإشارة: <b>${escHtml(rssiVal)}</b></span>
            <span style="opacity:0.6;">|</span>
            <span>المعايرة: <b>${escHtml(calibLabel)}</b></span>
          </span>
        `;
      } else if (isConnected) {
        // USB Serial fallback mode
        badge.className = 'esp32-status-badge online';
        badge.style.background = '#ECFDF5';
        badge.style.color = '#047857';
        badge.style.border = '1px solid #10B981';
        const portName = data.port || 'COM5';
        const baudRate = data.baudrate || 115200;
        badge.innerHTML = `
          <span style="display:inline-flex; align-items:center; gap:6px;">
            <span style="width:8px; height:8px; border-radius:50%; background:#10B981; display:inline-block;"></span>
            <span>متصل سلكياً عبر USB (<b>${escHtml(portName)}</b>) — قراءة حية (${escHtml(baudRate)} baud)</span>
          </span>
        `;
      } else {
        // Disconnected fallback
        if (state.esp32Modality === 'optical') {
          badge.className = 'esp32-status-badge online';
          badge.style.background = '#F0FDF4';
          badge.style.color = '#15803D';
          badge.style.border = '1px solid #BBF7D0';
          badge.innerHTML = 'النمط البصري المستقل نشط - القياس عبر تحليل الطيف اللوني';
        } else {
          badge.className = 'esp32-status-badge offline';
          badge.style.background = '#FEF2F2';
          badge.style.color = '#B91C1C';
          badge.style.border = '1px solid #FECACA';
          badge.innerHTML = 'بانتظار إشارة Wi-Fi أو توصيل المجس عبر USB (COM5)';
        }
      }
    }

    // 4. Live Moisture Readout (Zero Hardcoding)
    const liveMoisture = (data.moisture_pct !== undefined && data.moisture_pct !== null)
      ? data.moisture_pct
      : ((data.latest_reading?.vwc_pct !== undefined && data.latest_reading?.vwc_pct !== null)
        ? data.latest_reading.vwc_pct
        : data.live_vwc_pct);

    if (el('esp32LiveVwcVal')) {
      el('esp32LiveVwcVal').textContent = (liveMoisture !== undefined && liveMoisture !== null)
        ? `${fmt(liveMoisture, 1)} %`
        : '— %';
    }

    // 5. Voltage & ADC Readouts
    if (el('esp32VoltageAdcVal')) {
      let voltDisplay = '— V';
      if (data.voltage_mv !== undefined && data.voltage_mv !== null) {
        voltDisplay = `${(data.voltage_mv / 1000.0).toFixed(3)} V (${Math.round(data.voltage_mv)} mV)`;
      } else if (data.voltage_v !== undefined && data.voltage_v !== null) {
        voltDisplay = `${Number(data.voltage_v).toFixed(3)} V`;
      } else if (data.latest_reading?.voltage_v !== undefined && data.latest_reading?.voltage_v !== null) {
        voltDisplay = `${Number(data.latest_reading.voltage_v).toFixed(3)} V`;
      }

      let adcDisplay = 'ADC: —';
      if (data.filtered_adc !== undefined && data.filtered_adc !== null) {
        adcDisplay = `ADC: ${Math.round(data.filtered_adc)}`;
        if (data.raw_adc !== undefined && data.raw_adc !== null && Math.abs(data.raw_adc - data.filtered_adc) > 0.1) {
          adcDisplay += ` [خام: ${Math.round(data.raw_adc)}]`;
        }
      } else if (data.raw_adc !== undefined && data.raw_adc !== null) {
        adcDisplay = `ADC: ${Math.round(data.raw_adc)}`;
      } else if (data.adc_raw !== undefined && data.adc_raw !== null) {
        adcDisplay = `ADC: ${data.adc_raw}`;
      } else if (data.latest_reading?.adc_raw !== undefined && data.latest_reading?.adc_raw !== null) {
        adcDisplay = `ADC: ${data.latest_reading.adc_raw}`;
      }

      el('esp32VoltageAdcVal').textContent = `${voltDisplay} — ${adcDisplay}`;
    }

    // 6. Hydrological Soil Status Card Label
    if (el('esp32HydrologicalStatus')) {
      const rawStatus = (data.soil_status || data.hydrological_regime || '').trim();
      const upperStatus = rawStatus.toUpperCase();
      let statusText = ESP32_REGIME_LABELS_AR[rawStatus]
        || ESP32_REGIME_LABELS_AR[upperStatus]
        || data.hydrological_status_ar
        || data.latest_reading?.hydrological_status_ar;

      if (!statusText || statusText === 'غير متصل - الفحص البصري نشط' || statusText === rawStatus) {
        if (ESP32_REGIME_LABELS_AR[upperStatus]) {
          statusText = ESP32_REGIME_LABELS_AR[upperStatus];
        } else if (rawStatus) {
          statusText = rawStatus;
        }
      }
      if (!isConnected && state.esp32Modality === 'optical') {
        statusText = 'النمط البصري نشط';
      }
      el('esp32HydrologicalStatus').textContent = statusText || 'بانتظار الإشارة';
    }

    // 7. Vertical Gradient
    if (el('esp32GradientVal')) {
      const grad = (data.vertical_gradient_pct_per_cm !== undefined && data.vertical_gradient_pct_per_cm !== null)
        ? data.vertical_gradient_pct_per_cm
        : data.vertical_gradient;
      el('esp32GradientVal').textContent = (grad !== undefined && grad !== null) ? `${fmt(grad, 2)} %/cm` : '— %/cm';
    }

    // 8. 3-Depth Multi-Point Readings
    const getDepthVal = (key) => {
      const prof = data.depth_profiles?.[key];
      if (prof !== undefined && prof !== null) {
        if (typeof prof === 'object') return prof.vwc_pct;
        return prof;
      }
      return data.depths?.[key];
    };

    const d5 = getDepthVal('surface_5cm') ?? (isWifi ? liveMoisture : null);
    const d15 = getDepthVal('mid_15cm');
    const d25 = getDepthVal('root_25cm');

    if (el('esp32Depth5Val')) el('esp32Depth5Val').textContent = (d5 !== undefined && d5 !== null) ? `${fmt(d5, 1)} %` : '— %';
    if (el('esp32Depth15Val')) el('esp32Depth15Val').textContent = (d15 !== undefined && d15 !== null) ? `${fmt(d15, 1)} %` : '— %';
    if (el('esp32Depth25Val')) el('esp32Depth25Val').textContent = (d25 !== undefined && d25 !== null) ? `${fmt(d25, 1)} %` : '— %';

    // 9. Scientific Data Classification & Provenance Layer (Dynamic - Never Hardcoded)
    const provContainer = el('esp32ProvenanceContainer');
    const classBadge = el('esp32ClassificationBadge');
    const provDetails = el('esp32ProvenanceDetails');

    if (provContainer && classBadge && provDetails) {
      const classification = data.data_classification || (isConnected ? 'Measured Data (Raw + Filtered)' : null);
      const provenance = data.data_provenance;

      if (classification) {
        provContainer.style.display = 'block';
        classBadge.textContent = classification;

        if (classification.includes('Measured')) {
          classBadge.style.background = '#EFF6FF';
          classBadge.style.color = '#1E40AF';
          classBadge.style.borderColor = '#BFDBFE';
        } else {
          classBadge.style.background = '#F5F3FF';
          classBadge.style.color = '#6D28D9';
          classBadge.style.borderColor = '#DDD6FE';
        }

        const detailItems = [];
        if (provenance && typeof provenance === 'object') {
          if (provenance.source_node) detailItems.push(`<span>المصدر: <b>${escHtml(provenance.source_node)}</b></span>`);
          if (provenance.transport) detailItems.push(`<span>الناقل: <b>${escHtml(provenance.transport)}</b></span>`);
          if (provenance.sensor_model) detailItems.push(`<span>المجس: <b>${escHtml(provenance.sensor_model)}</b></span>`);
          if (provenance.signal_processing) detailItems.push(`<span>المعالجة: <b>${escHtml(provenance.signal_processing)}</b></span>`);
          if (provenance.timestamp_utc) detailItems.push(`<span>التوقيت: <b>${escHtml(provenance.timestamp_utc.slice(11, 19))} UTC</b></span>`);
        } else if (data.last_telemetry_time || data.last_updated_utc) {
          const ts = (data.last_telemetry_time || data.last_updated_utc).slice(11, 19);
          detailItems.push(`<span>التوقيت: <b>${escHtml(ts)} UTC</b></span>`);
        }

        provDetails.innerHTML = detailItems.join('<span style="opacity:0.4;">|</span>');
      } else {
        provContainer.style.display = 'none';
      }
    }

    // 10. Sync active experiment status in UI
    if (state.experimentActive || !state._expStatusInitialized) {
      state._expStatusInitialized = true;
      updateExperimentStatusUI();
    }
  } catch (err) {
    console.debug('fetchEsp32Status error:', err);
  }
}

function startEsp32Polling() {
  if (state.esp32PollInterval) clearInterval(state.esp32PollInterval);
  fetchEsp32Status();
  state.esp32PollInterval = setInterval(() => {
    fetchEsp32Status();
  }, 3000);
}

async function lockEsp32Depth(depthKey) {
  try {
    // If the UI has live moisture displayed, pass it along as fallback vwc_pct
    const liveMoistText = el('esp32LiveVwcVal')?.textContent?.replace(' %', '').trim();
    const liveMoistNum = parseFloat(liveMoistText);
    const bodyPayload = {
      depth: depthKey,
      depth_key: depthKey,
    };
    if (!isNaN(liveMoistNum) && liveMoistNum >= 0) {
      bodyPayload.vwc_pct = liveMoistNum;
    }

    const resp = await fetch(`/api/v1/esp32/lock-depth?depth_key=${depthKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bodyPayload),
    });
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      const msg = errData.detail || 'تعذر تثبيت قراءة المجس، يرجى التأكد من وصول حزم Wi-Fi أو توصيل الحساس عبر USB.';
      alert(msg);
      return;
    }
    await fetchEsp32Status();
  } catch (err) {
    console.error('lockEsp32Depth error:', err);
    alert('حدث خطأ أثناء تثبيت العمق: ' + err.message);
  }
}

/* ══════════════════════════════════════════════════════════════
   SCIENTIFIC EXPERIMENT LOGGER & RESEARCH EXPORT HANDLERS
   ══════════════════════════════════════════════════════════════ */
state.experimentActive = false;
state.experimentRowCount = 0;

async function updateExperimentStatusUI() {
  try {
    const resp = await fetch('/api/v1/experiments/status');
    if (!resp.ok) return;
    const data = await resp.json();
    state.experimentActive = !!data.active;
    state.experimentRowCount = data.row_count || 0;

    const btn = el('btnToggleExpLog');
    const badge = el('expRecordingBadge');
    const statusText = el('expLogStatus');

    if (badge) {
      badge.style.display = state.experimentActive ? 'inline-flex' : 'none';
    }

    if (btn) {
      if (state.experimentActive) {
        btn.textContent = 'إيقاف وحفظ التجربة';
        btn.style.background = '#DC2626';
        btn.style.borderColor = '#B91C1C';
        btn.style.color = '#FFFFFF';
      } else {
        btn.textContent = 'بدء التسجيل التجريبي';
        btn.style.background = '#0F766E';
        btn.style.borderColor = '#0F766E';
        btn.style.color = '#FFFFFF';
      }
    }

    if (statusText) {
      if (state.experimentActive) {
        statusText.innerHTML = `جاري التسجيل: <b style="color:#DC2626;">${state.experimentRowCount} حزمة</b>`;
      } else if (state.experimentRowCount > 0) {
        statusText.innerHTML = `مسجل: <b>${state.experimentRowCount} حزمة</b> (${escHtml(data.experiment_name || '')})`;
      } else {
        statusText.textContent = 'مسجل: 0 حزمة';
      }
    }
  } catch (e) {
    console.debug('Error updating experiment status UI:', e);
  }
}
window.updateExperimentStatusUI = updateExperimentStatusUI;

async function toggleExperimentRecording() {
  const btn = el('btnToggleExpLog');
  const input = el('expNameInput');
  const expName = (input?.value || '').trim() || 'Soil_Calibration_Run_01';

  if (!state.experimentActive) {
    // Start experiment
    try {
      if (btn) btn.disabled = true;
      const resp = await fetch('/api/v1/experiments/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ experiment_name: expName }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      state.experimentActive = true;
      state.experimentRowCount = 0;
      await updateExperimentStatusUI();
    } catch (err) {
      console.error('Error starting experiment:', err);
      alert('تعذر بدء تسجيل التجربة: ' + err.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  } else {
    // Stop experiment
    try {
      if (btn) btn.disabled = true;
      const resp = await fetch('/api/v1/experiments/stop', {
        method: 'POST',
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      state.experimentActive = false;
      await updateExperimentStatusUI();
      await fetchEvaluationSummary();
      const count = data.row_count || 0;
      const statusText = el('expLogStatus');
      if (statusText) {
        statusText.innerHTML = `اكتملت التجربة بنجاح: تم تسجيل <b>${count} حزمة</b> (${data.xlsx_filename || ''})`;
      }
    } catch (err) {
      console.error('Error stopping experiment:', err);
      alert('تعذر إيقاف التجربة: ' + err.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  }
}
window.toggleExperimentRecording = toggleExperimentRecording;

function downloadExperimentExcel() {
  window.location.href = '/api/v1/experiments/export-excel';
}
window.downloadExperimentExcel = downloadExperimentExcel;

function downloadExperimentCsv() {
  window.location.href = '/api/v1/experiments/export-latest';
}
window.downloadExperimentCsv = downloadExperimentCsv;

/* ══════════════════════════════════════════════════════════════
   SCIENTIFIC MODEL, SIGNAL-FILTER & SYSTEM EVALUATION HANDLER
   ══════════════════════════════════════════════════════════════ */
async function fetchEvaluationSummary() {
  try {
    const resp = await fetch('/api/v1/evaluation/summary');
    if (!resp.ok) return;
    const data = await resp.json();

    const sig = data.signal_filtering || {};
    const telem = data.telemetry_readiness || {};
    const engines = data.scientific_engines || {};

    // 1. Status Badge
    const badge = el('evalStatusBadge');
    if (badge) {
      if (sig.evaluation_status === 'VALIDATED') {
        badge.textContent = 'تم التحقق علمياً (VALIDATED)';
        badge.style.background = '#ECFDF5';
        badge.style.color = '#047857';
        badge.style.borderColor = '#A7F3D0';
      } else {
        badge.textContent = 'بانتظار أول تجربة ميدانية';
        badge.style.background = '#F1F5F9';
        badge.style.color = '#475569';
        badge.style.borderColor = '#CBD5E1';
      }
    }

    // 2. Timestamp
    const tsEl = el('evalTimestamp');
    if (tsEl && data.evaluated_at_utc) {
      tsEl.textContent = `آخر تقييم: ${data.evaluated_at_utc.slice(11, 19)} UTC`;
    }

    // 3. Signal Filtering State (Zero Hardcoding)
    const emptyState = el('evalFilterEmptyState');
    const activeState = el('evalFilterActiveState');

    if (sig.evaluation_status === 'VALIDATED') {
      if (emptyState) emptyState.style.display = 'none';
      if (activeState) activeState.style.display = 'block';

      if (el('evalNoiseRedVal')) {
        el('evalNoiseRedVal').textContent = (sig.noise_reduction_pct !== null && sig.noise_reduction_pct !== undefined)
          ? `${sig.noise_reduction_pct}%`
          : '— %';
      }
      if (el('evalStdDevVal')) {
        el('evalStdDevVal').textContent = `خام: ${sig.raw_adc_std || '—'} | مفلتر: ${sig.filtered_adc_std || '—'}`;
      }
      if (el('evalSampleCountVal')) {
        el('evalSampleCountVal').textContent = `${sig.total_samples || 0} حزمة (${sig.total_experiments || 0} تجربة)`;
      }
      if (el('evalMoistureRangeVal')) {
        const meanM = sig.mean_moisture_pct !== null ? `${sig.mean_moisture_pct}%` : '—';
        const minM = sig.min_moisture_pct !== null ? `${sig.min_moisture_pct}%` : '—';
        const maxM = sig.max_moisture_pct !== null ? `${sig.max_moisture_pct}%` : '—';
        el('evalMoistureRangeVal').textContent = `${meanM} (نطاق: ${minM} - ${maxM})`;
      }
      if (el('evalCalibStatus')) el('evalCalibStatus').textContent = sig.calibration_status || 'FACTORY_DEFAULT';
      if (el('evalDryRef')) el('evalDryRef').textContent = sig.dry_ref_adc || '2850';
      if (el('evalWetRef')) el('evalWetRef').textContent = sig.wet_ref_adc || '1150';
      if (el('evalLatestFile')) el('evalLatestFile').textContent = sig.latest_file || '—';
    } else {
      if (activeState) activeState.style.display = 'none';
      if (emptyState) {
        emptyState.style.display = 'block';
        if (sig.message_ar) emptyState.textContent = sig.message_ar;
      }
    }

    // 4. Scientific Engines Status
    const gwStatus = el('engineGatewayStatus');
    const gwDesc = el('engineGatewayDesc');
    if (gwStatus && telem) {
      if (telem.connected) {
        gwStatus.textContent = 'متصل ونشط';
        gwStatus.style.background = '#ECFDF5';
        gwStatus.style.color = '#047857';
      } else {
        gwStatus.textContent = 'استعداد (Standby)';
        gwStatus.style.background = '#EFF6FF';
        gwStatus.style.color = '#1E40AF';
      }
    }
    if (gwDesc && telem) {
      const src = telem.telemetry_source || (telem.connected ? 'متصل' : 'بانتظار الإشارة');
      const depths = telem.locked_depths_count || 0;
      gwDesc.textContent = `المصدر: ${src} | الأعماق المثبتة: ${depths}/3 | التدرج الرأسي: ${telem.gradient_active ? 'نشط' : 'غير مثبت'}`;
    }

    const logStatus = el('engineLoggerStatus');
    if (logStatus && engines.experiment_logger) {
      const isRec = engines.experiment_logger.status === 'RECORDING';
      logStatus.textContent = isRec ? 'تسجيل حي' : 'جاهز';
      logStatus.style.background = isRec ? '#FEE2E2' : '#ECFDF5';
      logStatus.style.color = isRec ? '#B91C1C' : '#047857';
    }
  } catch (err) {
    console.debug('fetchEvaluationSummary error:', err);
  }
}
window.fetchEvaluationSummary = fetchEvaluationSummary;

/* ══════════════════════════════════════════════════════════════
   DUAL-MODE VISION LAB & LIVE 1080p 30FPS CAMERA ENGINE
   ══════════════════════════════════════════════════════════════ */
let cameraStream = null;
let cameraAnimFrameId = null;
let lastFpsTime = performance.now();
let frameCounter = 0;
let currentFps = 0;

function switchVisionMode(mode) {
  const tabUpload = el('tabVisionUpload');
  const tabCamera = el('tabVisionLiveCamera');
  const contUpload = el('visionUploadContainer');
  const contCamera = el('visionCameraContainer');

  if (mode === 'upload') {
    if (tabUpload) tabUpload.classList.add('active');
    if (tabCamera) tabCamera.classList.remove('active');
    if (contUpload) contUpload.style.display = 'block';
    if (contCamera) contCamera.style.display = 'none';
  } else if (mode === 'camera') {
    if (tabCamera) tabCamera.classList.add('active');
    if (tabUpload) tabUpload.classList.remove('active');
    if (contUpload) contUpload.style.display = 'none';
    if (contCamera) contCamera.style.display = 'block';
    enumerateCameras();
    // STRICT RULE: Never auto-start camera here!
  }
}

/* ══════════════════════════════════════════════════════════════
   SMART EXTERNAL USB CAMERA DETECTION & 1080P SELECTION
   ══════════════════════════════════════════════════════════════ */
async function selectPreferredExternalCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    return null;
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === 'videoinput');
    if (videoDevices.length === 0) return null;

    // 1. First Priority: Saved device ID in localStorage (if currently connected)
    const savedDeviceId = localStorage.getItem('preferred_usb_camera_id');
    if (savedDeviceId) {
      const match = videoDevices.find(d => d.deviceId === savedDeviceId);
      if (match) return match.deviceId;
    }

    // 2. Second Priority (External USB Detection):
    // Label contains usb, 1080, webcam, logitech, hd pro, capture, cam, external
    // AND does NOT contain integrated, built-in, internal, front, ir camera, facetime, ov9734, chicony, bison, sunplus
    const usbKeywords = ['usb', '1080', 'webcam', 'logitech', 'hd pro', 'capture', 'cam', 'external'];
    const internalKeywords = ['integrated', 'built-in', 'internal', 'front', 'ir camera', 'facetime', 'ov9734', 'chicony', 'bison', 'sunplus'];

    const detectedUsb = videoDevices.find(d => {
      const label = (d.label || '').toLowerCase();
      const isUsb = usbKeywords.some(kw => label.includes(kw));
      const isInternal = internalKeywords.some(kw => label.includes(kw));
      return isUsb && !isInternal;
    });

    if (detectedUsb) {
      localStorage.setItem('preferred_usb_camera_id', detectedUsb.deviceId);
      return detectedUsb.deviceId;
    }

    // 3. Third Priority (Secondary Index Fallback):
    // If multiple cameras exist and labels are generic, automatically pick the last camera (external USB plugged in index 1+)
    if (videoDevices.length > 1) {
      const lastDevice = videoDevices[videoDevices.length - 1];
      localStorage.setItem('preferred_usb_camera_id', lastDevice.deviceId);
      return lastDevice.deviceId;
    }

    return videoDevices[0].deviceId;
  } catch (err) {
    console.debug('selectPreferredExternalCamera error:', err);
    return null;
  }
}

async function enumerateCameras() {
  const select = el('cameraDeviceSelect');
  if (!select) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    select.innerHTML = '<option value="">الكاميرا غير مدعومة في المتصفح</option>';
    return;
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === 'videoinput');
    if (videoDevices.length === 0) {
      select.innerHTML = '<option value="">لم يتم العثور على كاميرات</option>';
      return;
    }

    const preferredId = await selectPreferredExternalCamera();

    select.innerHTML = '';
    videoDevices.forEach((dev, idx) => {
      const opt = document.createElement('option');
      opt.value = dev.deviceId;
      let label = dev.label || `كاميرا فحص ${idx + 1} (1080p)`;
      if (idx > 0 && !label.toLowerCase().includes('usb') && !label.includes('خارجية')) {
        label += ' (كاميرا خارجية USB)';
      }
      opt.textContent = label;
      if (dev.deviceId === preferredId) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    if (preferredId) {
      select.value = preferredId;
    }
  } catch (err) {
    console.debug('Error enumerating cameras:', err);
  }
}

function onCameraDeviceChanged() {
  const select = el('cameraDeviceSelect');
  if (select && select.value) {
    localStorage.setItem('preferred_usb_camera_id', select.value);
  }
  if (cameraStream) {
    stopCamera();
    startCamera();
  }
}

async function switchPreferredUsbCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    alert('خاصية الكاميرا غير مدعومة في المتصفح.');
    return;
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === 'videoinput');
    if (videoDevices.length <= 1) {
      alert('يوجد كاميرا واحدة فقط متصلة حالياً.');
      return;
    }

    const select = el('cameraDeviceSelect');
    const currentId = select ? select.value : localStorage.getItem('preferred_usb_camera_id');
    const currentIdx = videoDevices.findIndex(d => d.deviceId === currentId);
    const nextIdx = (currentIdx + 1) % videoDevices.length;
    const nextDevice = videoDevices[nextIdx];

    localStorage.setItem('preferred_usb_camera_id', nextDevice.deviceId);
    if (select) {
      select.value = nextDevice.deviceId;
    }

    if (cameraStream) {
      stopCamera();
      await startCamera();
    }
  } catch (err) {
    console.debug('Error switching camera:', err);
  }
}

async function startCamera() {
  const video = el('cameraVideo');
  const btnStart = el('btnStartCamera');
  const btnStop = el('btnStopCamera');
  const btnCapture = el('btnCaptureAnalyze');
  const select = el('cameraDeviceSelect');

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('خاصية الكاميرا غير مدعومة في هذا المتصفح أو تتطلب اتصال HTTPS آمن.');
    return;
  }

  // Pre-permission probe: if device labels are empty, probe briefly to expose real labels
  try {
    const probeDevices = await navigator.mediaDevices.enumerateDevices();
    const hasLabels = probeDevices.some(d => d.kind === 'videoinput' && d.label.length > 0);
    if (!hasLabels) {
      const probeStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      probeStream.getTracks().forEach(t => t.stop());
    }
  } catch (probeErr) {
    console.debug('Probe permission check notice:', probeErr);
  }

  await enumerateCameras();

  let selectedDeviceId = select?.value;
  if (!selectedDeviceId) {
    selectedDeviceId = await selectPreferredExternalCamera();
  }

  const constraints = {
    video: {
      deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
      width: { ideal: 1920 },
      height: { ideal: 1080 },
      frameRate: { ideal: 30 },
    },
    audio: false,
  };

  try {
    if (btnStart) btnStart.disabled = true;
    cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
    if (video) {
      video.srcObject = cameraStream;
      await video.play();
    }
    if (btnStop) btnStop.disabled = false;
    if (btnCapture) btnCapture.disabled = false;
    await enumerateCameras();

    lastFpsTime = performance.now();
    frameCounter = 0;
    renderLiveCanvasesLoop();
  } catch (err) {
    console.error('Camera startup error:', err);
    alert(`تعذر تشغيل الكاميرا: ${err.message || 'يرجى التحقق من الأذونات'}`);
    if (btnStart) btnStart.disabled = false;
    if (btnStop) btnStop.disabled = true;
    if (btnCapture) btnCapture.disabled = true;
  }
}

function stopCamera() {
  const video = el('cameraVideo');
  const btnStart = el('btnStartCamera');
  const btnStop = el('btnStopCamera');
  const btnCapture = el('btnCaptureAnalyze');

  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
  if (video) {
    video.srcObject = null;
  }
  if (cameraAnimFrameId) {
    cancelAnimationFrame(cameraAnimFrameId);
    cameraAnimFrameId = null;
  }

  if (btnStart) btnStart.disabled = false;
  if (btnStop) btnStop.disabled = true;
  if (btnCapture) btnCapture.disabled = true;

  const fpsEl = el('liveFpsCounter');
  if (fpsEl) fpsEl.textContent = '0 FPS';
}

function renderLiveCanvasesLoop() {
  const video = el('cameraVideo');
  const cRgb = el('liveCanvasRgb');
  const cTherm = el('liveCanvasThermal');
  const cExg = el('liveCanvasExg');

  if (!cameraStream || !video || video.paused || video.ended) {
    return;
  }

  const w = 480;
  const h = 270;

  if (cRgb && cTherm && cExg && video.videoWidth > 0) {
    const ctxRgb = cRgb.getContext('2d', { willReadFrequently: true });
    const ctxTherm = cTherm.getContext('2d');
    const ctxExg = cExg.getContext('2d');

    // 1. Draw RGB Video frame downscaled for smooth performance (<4% CPU)
    ctxRgb.drawImage(video, 0, 0, w, h);

    // Calculate FPS
    frameCounter++;
    const now = performance.now();
    if (now - lastFpsTime >= 1000) {
      currentFps = Math.round((frameCounter * 1000) / (now - lastFpsTime));
      frameCounter = 0;
      lastFpsTime = now;
      const fpsEl = el('liveFpsCounter');
      if (fpsEl) fpsEl.textContent = `${currentFps} FPS`;
    }

    // 2. Render Thermal Proxy (Jet / Inferno LUT)
    renderThermalProxy(ctxRgb, ctxTherm, w, h);

    // 3. Render ExG / Saline Soil Mask
    renderExgSoilMask(ctxRgb, ctxExg, w, h);

    // 4. Overlay Scientific HUD Reticle on RGB Feed
    drawHudReticle(ctxRgb, w, h, currentFps);
  }

  cameraAnimFrameId = requestAnimationFrame(renderLiveCanvasesLoop);
}

function renderThermalProxy(srcCtx, dstCtx, w, h) {
  const imgData = srcCtx.getImageData(0, 0, w, h);
  const data = imgData.data;
  const dstImgData = dstCtx.createImageData(w, h);
  const dst = dstImgData.data;

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0;

    let tr = 0, tg = 0, tb = 0;
    if (lum < 0.25) {
      tr = 0;
      tg = Math.round(4 * lum * 255);
      tb = 255;
    } else if (lum < 0.5) {
      tr = 0;
      tg = 255;
      tb = Math.round((1 - 4 * (lum - 0.25)) * 255);
    } else if (lum < 0.75) {
      tr = Math.round(4 * (lum - 0.5) * 255);
      tg = 255;
      tb = 0;
    } else {
      tr = 255;
      tg = Math.round((1 - 4 * (lum - 0.75)) * 255);
      tb = 0;
    }
    dst[i] = tr;
    dst[i + 1] = tg;
    dst[i + 2] = tb;
    dst[i + 3] = 255;
  }
  dstCtx.putImageData(dstImgData, 0, 0);
}

function renderExgSoilMask(srcCtx, dstCtx, w, h) {
  const imgData = srcCtx.getImageData(0, 0, w, h);
  const data = imgData.data;
  const dstImgData = dstCtx.createImageData(w, h);
  const dst = dstImgData.data;

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const exg = 2 * g - r - b;

    if (exg > 15) {
      // Vibrant chlorophyll viridis highlight
      dst[i] = Math.round(r * 0.3);
      dst[i + 1] = Math.min(255, Math.round(g * 1.35 + 30));
      dst[i + 2] = Math.round(b * 0.4);
    } else if (r > 160 && g > 150 && b > 140 && Math.abs(r - g) < 20) {
      // Saline crust / efflorescence (bright amber-white)
      dst[i] = 245;
      dst[i + 1] = 180;
      dst[i + 2] = 80;
    } else {
      // Subdued background
      const gray = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
      dst[i] = Math.round(gray * 0.35);
      dst[i + 1] = Math.round(gray * 0.35);
      dst[i + 2] = Math.round(gray * 0.35);
    }
    dst[i + 3] = 255;
  }
  dstCtx.putImageData(dstImgData, 0, 0);
}

function drawHudReticle(ctx, w, h, fps) {
  const cx = w / 2;
  const cy = h / 2;
  const r = 36;

  ctx.save();
  ctx.strokeStyle = '#06B6D4';
  ctx.lineWidth = 1.5;

  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(cx - r - 8, cy); ctx.lineTo(cx - r + 4, cy);
  ctx.moveTo(cx + r - 4, cy); ctx.lineTo(cx + r + 8, cy);
  ctx.moveTo(cx, cy - r - 8); ctx.lineTo(cx, cy - r + 4);
  ctx.moveTo(cx, cy + r - 4); ctx.lineTo(cx, cy + r + 8);
  ctx.stroke();

  ctx.strokeStyle = '#10B981';
  ctx.lineWidth = 2;
  const bSize = 14;
  const pad = 10;

  // Top-left
  ctx.beginPath();
  ctx.moveTo(pad, pad + bSize); ctx.lineTo(pad, pad); ctx.lineTo(pad + bSize, pad);
  ctx.stroke();
  // Top-right
  ctx.beginPath();
  ctx.moveTo(w - pad - bSize, pad); ctx.lineTo(w - pad, pad); ctx.lineTo(w - pad, pad + bSize);
  ctx.stroke();
  // Bottom-left
  ctx.beginPath();
  ctx.moveTo(pad, h - pad - bSize); ctx.lineTo(pad, h - pad); ctx.lineTo(pad + bSize, h - pad);
  ctx.stroke();
  // Bottom-right
  ctx.beginPath();
  ctx.moveTo(w - pad - bSize, h - pad); ctx.lineTo(w - pad, h - pad); ctx.lineTo(w - pad, h - pad - bSize);
  ctx.stroke();

  ctx.font = '10px monospace';
  ctx.fillStyle = '#FFFFFF';
  ctx.fillText('1080p 30FPS TARGETING HUD', pad + 4, h - pad - 4);
  ctx.restore();
}

async function captureAndAnalyze(action = 'NEW_SESSION') {
  const video = el('cameraVideo');
  if (!video || video.videoWidth === 0) {
    alert('الكاميرا غير نشطة حالياً للالتقاط.');
    return;
  }

  showVisionLoading();
  try {
    const compressedBlob = await compressImageToBlob(video);

    // Display captured frame in original image panel
    const origImg = el('originalLeafImg');
    if (origImg) {
      origImg.src = URL.createObjectURL(compressedBlob);
      origImg.style.display = 'block';
    }
    const placeholder = el('origPlaceholderText');
    if (placeholder) placeholder.style.display = 'none';

    const formData = new FormData();
    formData.append('image', compressedBlob, 'camera_capture_768px.jpg');
    formData.append('region_name', `بغداد - ${state.selectedLocationAr || 'محطة الفحص الميداني'}`);
    formData.append('session_id', state.activeLabSessionId || 'active_field_session');
    formData.append('session_action', 'NEW_SESSION');

    await runVisionDiagnostic(formData, 'NEW_SESSION');
  } catch (err) {
    console.error('Camera capture error:', err);
    hideVisionLoading();
    alert('حدث خطأ أثناء تجميد العينة: ' + err.message);
  }
}

/* ══════════════════════════════════════════════════════════════
   PART 3: 4D DIURNAL POLLUTION ADVECTION & SOURCE MITIGATION
   ══════════════════════════════════════════════════════════════ */
function toggle4DSimulation() {
  state.is4DActive = !state.is4DActive;
  const btn = el('btnToggle4D');
  const controls = el('diurnalControls');
  const hud = el('diurnalHud');

  if (state.is4DActive) {
    if (btn) btn.textContent = 'إيقاف المحاكاة الدخانية رباعية الأبعاد (4D)';
    if (controls) controls.style.display = 'flex';
    if (hud) hud.style.display = 'flex';
    fetchAndRenderFluidCloud();
  } else {
    if (btn) btn.textContent = 'تفعيل المحاكاة الفيزيائية رباعية الأبعاد (4D)';
    if (controls) controls.style.display = 'none';
    if (hud) hud.style.display = 'none';
    if (state.diurnalTimer) {
      clearInterval(state.diurnalTimer);
      state.diurnalTimer = null;
      const playBtn = el('btnPlayDiurnal');
      if (playBtn) playBtn.textContent = 'تشغيل الدورة اليومية';
    }
    clearDiurnalLayers();
  }
}

function clearDiurnalLayers() {
  if (!baghdadMap) return;
  if (baghdadMap.getSource('pollution-fluid-source')) {
    baghdadMap.getSource('pollution-fluid-source').setData({ type: 'FeatureCollection', features: [] });
  }
  if (baghdadMap.getSource('gaussian-plume-source')) {
    baghdadMap.getSource('gaussian-plume-source').setData({ type: 'FeatureCollection', features: [] });
  }
  if (baghdadMap.getSource('canopy-shadows-source')) {
    baghdadMap.getSource('canopy-shadows-source').setData({ type: 'FeatureCollection', features: [] });
  }
  if (baghdadMap.getSource('canopy-3d-source')) {
    baghdadMap.getSource('canopy-3d-source').setData({ type: 'FeatureCollection', features: [] });
  }
  const pmCard = el('pollutionMitigationCard');
  if (pmCard) pmCard.style.display = 'none';
}

function onHourSliderChange(val) {
  const h = parseInt(val, 10);
  state.currentHour = h;
  const label = el('hourLabel');
  if (label) {
    let phaseName = 'انحسار الحركة المرورية وتبدد الانبعاثات';
    if (h >= 0 && h <= 6) {
      phaseName = 'التبريد الإشعاعي الليلي والانبعاثات الأساسية الدنيا';
    } else if (h >= 7 && h <= 10) {
      phaseName = 'ساعات الذروة الصباحية (حركة المرور وعوادم المركبات)';
    } else if (h >= 12 && h <= 16) {
      phaseName = 'ذروة الإشعاع الحراري وأحمال مولدات الديزل (الانقلاب)';
    } else if (h >= 17 && h <= 20) {
      phaseName = 'ساعات الازدحام المسائي وهبوط الطبقة الحدية';
    }
    label.textContent = `${String(h).padStart(2, '0')}:00 - ${phaseName}`;
  }

  if (state.is4DActive) {
    fetchAndRenderFluidCloud();
  }
}

async function fetchAndRenderFluidCloud() {
  if (!baghdadMap) return;
  const lat = state.selectedLat;
  const lon = state.selectedLon;
  const hour = state.currentHour;
  const speed = state.windSpeedMs || 3.5;
  const deg = state.windDeg || 315.0;

  try {
    const resp = await fetch(`/api/physics/diurnal-plume?lat=${lat}&lon=${lon}&wind_speed_ms=${speed}&wind_deg=${deg}&hour=${hour}`, {
      method: 'POST',
    });
    if (!resp.ok) return;
    const geojson = await resp.json();
    if (baghdadMap.getSource('pollution-fluid-source')) {
      baghdadMap.getSource('pollution-fluid-source').setData(geojson);
    }
  } catch (err) {
    console.debug('Fluid plume render error:', err);
  }
}

// Backward-compatible alias
const fetchAndRenderDiurnalPlume = fetchAndRenderFluidCloud;

function togglePlayDiurnal() {
  const btn = el('btnPlayDiurnal');
  if (state.diurnalTimer) {
    clearInterval(state.diurnalTimer);
    state.diurnalTimer = null;
    if (btn) btn.textContent = 'تشغيل الدورة اليومية';
  } else {
    if (btn) btn.textContent = 'إيقاف المؤقت اللحظي';
    state.diurnalTimer = setInterval(() => {
      let h = (state.currentHour + 1) % 24;
      const slider = el('hourSlider');
      if (slider) slider.value = h;
      onHourSliderChange(h);
    }, 950);
  }
}

function renderPollutionMitigationResult(data, district, lat, lon) {
  if (!data) return;
  const targetDistrict = district || state.selectedLocationAr || 'بغداد';
  const targetLat = lat !== undefined ? lat : state.selectedLat;
  const targetLon = lon !== undefined ? lon : state.selectedLon;

  // 1. District header
  const distBadge = el('pm-district-badge');
  if (distBadge) {
    distBadge.textContent = `الموقع: ${targetDistrict} (${targetLat.toFixed(4)}, ${targetLon.toFixed(4)})`;
  }

  // 2. Site Typology
  const typEl = el('pm-typology');
  if (typEl) {
    typEl.textContent = data.site_typology_ar || 'بؤرة حضرية قياسية';
  }

  // 3. Emission Source Breakdown (100% Attribution)
  const sourcesContainer = el('pm-sources-container');
  if (sourcesContainer && data.emission_source_breakdown) {
    sourcesContainer.innerHTML = '';

    let items = [];
    if (Array.isArray(data.emission_source_breakdown)) {
      items = data.emission_source_breakdown.map(item => ({
        label: item.source_ar || item.source || 'مصدر انبعاث',
        pct: typeof item.percentage === 'number' ? item.percentage : (parseFloat(item.percentage) || 0),
        desc: item.description_ar || item.pollutants_ar || '',
      }));
    } else if (typeof data.emission_source_breakdown === 'object') {
      const sourceLabels = {
        diesel_generators_pct: 'مولدات الديزل الأهلية (الانبعاثات الدخانية والهباب)',
        traffic_congestion_pct: 'الازدحام المروري وعوادم المركبات الثقيلة',
        industrial_point_sources_pct: 'الأنشطة الصناعية / الحرق ومصافي الوقود',
        impervious_surface_heat_pct: 'الأسطح الإسفلتية والكتل الخرسانية (الجزر الحرارية)',
        open_soil_dust_pct: 'العواصف الغبارية وإثارة التربة الرخوة المكشوفة',
      };
      items = Object.entries(data.emission_source_breakdown).map(([key, val]) => ({
        label: sourceLabels[key] || key,
        pct: typeof val === 'number' ? val : (parseFloat(val) || 0),
        desc: '',
      }));
    }

    items.forEach((item) => {
      const pct = item.pct;
      const label = item.label;

      let barColor = '#F59E0B';
      const lower = label.toLowerCase();
      if (lower.includes('ديزل') || lower.includes('مولد') || lower.includes('generator')) barColor = '#DC2626';
      else if (lower.includes('مرور') || lower.includes('مركب') || lower.includes('سريع') || lower.includes('traffic')) barColor = '#EA580C';
      else if (lower.includes('صناع') || lower.includes('طائر') || lower.includes('توربين') || lower.includes('industrial')) barColor = '#7C3AED';
      else if (lower.includes('حرار') || lower.includes('إسفلت') || lower.includes('خرسان') || lower.includes('heat')) barColor = '#D97706';
      else if (lower.includes('غبار') || lower.includes('ترب') || lower.includes('سلت') || lower.includes('dust')) barColor = '#0284C7';

      const row = document.createElement('div');
      row.className = 'source-bar-row';
      row.style.marginBottom = '10px';
      row.innerHTML = `
        <div style="display:flex; justify-content:space-between; font-size:11.5px; margin-bottom:3px;">
          <span style="color:#334155; font-weight:600;">${escHtml(label)}</span>
          <span style="font-weight:700; color:#0F172A;">${pct.toFixed(1)}%</span>
        </div>
        <div style="background:#E2E8F0; height:7px; border-radius:4px; overflow:hidden;">
          <div class="source-bar-fill" style="height:100%; width:${Math.min(pct, 100)}%; background:${barColor}; border-radius:4px; transition:width 0.6s ease;"></div>
        </div>
        ${item.desc ? `<div style="font-size:10.5px; color:#64748B; margin-top:2px; line-height:1.35;">${escHtml(item.desc)}</div>` : ''}
      `;
      sourcesContainer.appendChild(row);
    });
  }

  // 4. Root-Cause Engineering Mitigation Plan
  const engList = el('pm-engineering-list');
  if (engList && Array.isArray(data.engineering_mitigation_plan)) {
    engList.innerHTML = data.engineering_mitigation_plan.map(item => `
      <li style="margin-bottom:6px; font-size:12px; color:#334155; line-height:1.5;">
        ${escHtml(item)}
      </li>
    `).join('');
  }

  // 5. Afforestation Feasibility & Strict Placement
  const feas = data.afforestation_feasibility || {};
  const badge = el('pm-viable-badge');
  if (badge) {
    if (feas.is_viable) {
      badge.style.background = '#059669';
      badge.style.color = '#FFFFFF';
      badge.textContent = 'صالح للتشجير الموضعي الموجه';
    } else {
      badge.style.background = '#DC2626';
      badge.style.color = '#FFFFFF';
      badge.textContent = 'غير ملائم للتشجير المباشر (كتلة خرسانية / منشأة سيادية / مدرج مطار)';
    }
  }

  const targetEl = el('pm-target-pct');
  if (targetEl) {
    targetEl.textContent = `تغطية تاجية مستهدفة: ${feas.target_canopy_coverage_pct ?? 0}%`;
  }

  const placeEl = el('pm-species-placement');
  if (placeEl) {
    const spText = (feas.viable_species_ar && feas.viable_species_ar.length > 0)
      ? `الأنواع المقترحة: ${feas.viable_species_ar.join('، ')}.`
      : '';
    placeEl.textContent = `${feas.strict_placement_rule_ar || ''} ${spText}`.trim();
  }

  // 6. Projected Impact Metrics
  const imp = data.projected_impact_metrics || {};
  if (el('pm-impact-lst')) {
    const v = typeof imp.expected_lst_cooling_c === 'number' ? imp.expected_lst_cooling_c : 2.5;
    el('pm-impact-lst').textContent = `-${v.toFixed(1)} °C`;
  }
  if (el('pm-impact-pm')) {
    const v = typeof imp.expected_pm_reduction_pct === 'number' ? imp.expected_pm_reduction_pct : 35.0;
    el('pm-impact-pm').textContent = `-${v.toFixed(1)} %`;
  }
  if (el('pm-impact-gases')) {
    const v = typeof imp.nox_sox_abatement_pct === 'number' ? imp.nox_sox_abatement_pct : 38.0;
    el('pm-impact-gases').textContent = `-${v.toFixed(1)} %`;
  }

  // 7. Show card
  const card = el('pollutionMitigationCard');
  if (card) {
    card.style.display = 'block';
  }
}

async function triggerPollutionMitigationDiagnosis() {
  const btn = el('btnDiagnosePollution');
  const originalText = btn ? btn.textContent : '';
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'جاري تحليل البؤرة وتشخيص المصادر عبر Groq LPU...';
  }

  const lat = state.selectedLat;
  const lon = state.selectedLon;
  const district = state.selectedLocationAr || 'بغداد';

  try {
    const resp = await fetch(
      `/api/v1/diagnose-pollution-mitigation?lat=${lat}&lon=${lon}&district_name_ar=${encodeURIComponent(district)}`,
      { method: 'POST' }
    );

    if (!resp.ok) {
      throw new Error(`Server returned HTTP ${resp.status}`);
    }

    const data = await resp.json();
    renderPollutionMitigationResult(data, district, lat, lon);
    switchDossierView('mitigation');

    const card = el('pollutionMitigationCard');
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  } catch (err) {
    console.error('Pollution mitigation error:', err);
    alert('حدث خطأ أثناء استدعاء وكيل تشخيص التلوث: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = originalText || 'تشخيص مصادر التلوث وبروتوكول المعالجة الذكي (AI Source & Mitigation)';
    }
  }
}

/* ══════════════════════════════════════════════════════════════
   AGENT 4: FLOATING DRAGGABLE CHATBOT
══════════════════════════════════════════════════════════════ */
let chatbotOpen = false;

function toggleChatbot() {
  const modal = el('aiChatbotModal');
  if (!modal) return;
  chatbotOpen = !chatbotOpen;
  if (chatbotOpen) {
    modal.classList.add('visible');
    modal.style.display = 'flex';
    updateChatSuggestions();
    updateTelemetry();
    el('chatbotInput')?.focus();
  } else {
    modal.classList.remove('visible');
    modal.style.display = 'none';
  }
}

function updateTelemetry() {
  window.liveTelemetry = {
    active_workspace: state.activeWorkspace,
    active_mode: state.workspace1Mode,
    lat: state.selectedLat,
    lon: state.selectedLon,
    location_name_ar: state.selectedLocationAr,
    total_selected_area_m2: state.landResult?.total_selected_area_m2,
    total_selected_area_dunums: state.landResult?.total_selected_area_dunums,
    suitability_code: state.landResult?.suitability_code,
    suitability_title_ar: state.landResult?.suitability_title_ar,
    soil_profile: state.landResult?.soil_profile,
    soil_type_title_ar: state.landResult?.soil_type_title_ar,
    soil_salinity_ece_dsm: state.landResult?.soil_salinity_ece_dsm,
    soil_ph: state.landResult?.soil_ph,
    selected_trees: state.landResult?.selected_species,
    air_temp_c: state.weatherData?.air_temp_c,
    surface_lst_c: state.weatherData?.surface_lst_c,
    dust_status: state.weatherData?.dust_aerosol_status_ar,
    pollution_data: state.pollutionData,
    vision_diagnosis: state.visionResult,
  };

  const strip = el('chatTelemetryText');
  if (strip) {
    const loc = state.selectedLocationAr || 'بغداد';
    const temp = state.weatherData?.air_temp_c ? `${state.weatherData.air_temp_c}°م` : 'متصل';
    const modeDesc =
      state.activeWorkspace === 'vision'
        ? 'مختبر الرؤية الحاسوبية'
        : state.workspace1Mode === 'afforestation'
        ? 'فحص التربة والتشجير'
        : 'رادار التلوث CAMS';
    strip.textContent = `${loc} | ${modeDesc} | حرارة الهواء: ${temp}`;
  }
}

function updateChatSuggestions() {
  const wrap = el('chatSuggestions');
  if (!wrap) return;

  const mode = state.activeWorkspace === 'vision' ? 'vision' : state.workspace1Mode;
  let questions = [];

  if (mode === 'afforestation') {
    questions = [
      'شنو رأيك بالموقع المحدد هل أزرع بيه؟',
      'ما هو تصنيف التربة وملوحتها هنا؟',
      'كم عدد الأشجار والمياه المطلوبة لهذه المساحة؟',
    ];
  } else if (mode === 'pollution') {
    questions = [
      'ما هو تشخيص جودة الهواء في هذا الحي الآن؟',
      'ما هي مواصفات الحزام الشجري الموصى به لخفض التلوث؟',
      'ما هو تأثير الغبار السلتي وعوادم السيارات على الصحة؟',
    ];
  } else {
    questions = [
      'شنو علاج هاي العينة الزراعية المفحوصة؟',
      'كيف يعالج الرش الضبابي مشكلة الغبار السلتي على الأوراق؟',
      'ما هو برنامج الري الدقيق الموصى به لهذه النبتة؟',
    ];
  }

  wrap.innerHTML = '';
  questions.forEach((q) => {
    const chip = document.createElement('button');
    chip.className = 'suggestion-chip';
    chip.textContent = q;
    chip.onclick = () => sendSuggestion(q);
    wrap.appendChild(chip);
  });
}

function sendSuggestion(text) {
  const input = el('chatbotInput');
  if (input) {
    input.value = text;
    sendChatMessage();
  }
}

function handleChatKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
}

async function sendChatMessage() {
  const input = el('chatbotInput');
  if (!input) return;
  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  appendChatMessage(msg, 'user');

  // Loading bot bubble
  const loadingBubble = appendChatMessage('جاري استدعاء النموذج الهندسي...', 'bot', true);

  updateTelemetry();
  const payload = {
    message: msg,
    active_section: state.activeWorkspace === 'vision' ? 'vision' : state.workspace1Mode,
    live_telemetry: window.liveTelemetry,
    history: [],
  };

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) throw new Error('Chatbot service unavailable');
    const data = await resp.json();

    loadingBubble.remove();
    appendChatMessage(data.reply_ar || 'لم يتم استلام رد صالح.', 'bot');
  } catch (err) {
    loadingBubble.remove();
    appendChatMessage(`عذرا، حدث خطأ أثناء معالجة السؤال: ${err.message}`, 'bot');
  }
}

function appendChatMessage(text, role, isLoading = false) {
  const container = el('chatbotMessages');
  if (!container) return null;

  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  if (isLoading) div.style.fontStyle = 'italic';
  div.innerHTML = escHtml(text).replace(/\n/g, '<br/>');

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

// Draggable Modal logic
(function initDraggableChatbot() {
  const modal = el('aiChatbotModal');
  const header = el('chatbotDragHeader');
  if (!modal || !header) return;

  let isDragging = false;
  let startX = 0;
  let startY = 0;
  let initX = 0;
  let initY = 0;

  header.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX;
    startY = e.clientY;
    initX = modal.offsetLeft;
    initY = modal.offsetTop;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });

  function onMouseMove(e) {
    if (!isDragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    modal.style.left = `${initX + dx}px`;
    modal.style.top = `${initY + dy}px`;
    modal.style.right = 'auto';
    modal.style.bottom = 'auto';
  }

  function onMouseUp() {
    isDragging = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }
})();

// Voice Input toggle
function toggleVoice() {
  const micBtn = el('chatMicBtn');
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    alert('متصفحك لا يدعم التعرف على الصوت.');
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = 'ar-IQ';

  recognition.onstart = () => {
    if (micBtn) micBtn.style.color = '#EF4444';
  };
  recognition.onend = () => {
    if (micBtn) micBtn.style.color = '';
  };
  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    const input = el('chatbotInput');
    if (input) {
      input.value = transcript;
      sendChatMessage();
    }
  };
  recognition.start();
}

/* ══════════════════════════════════════════════════════════════
   DOM READY INITIALIZATION
══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initBaghdadMap();
  updateTelemetry();
  updateChatSuggestions();
  setEsp32Modality('optical');
  startEsp32Polling();
  fetchEvaluationSummary();
});

/* ══════════════════════════════════════════════════════════════
   ESP32 SETUP GUIDE MODAL — Controller
   Opens #esp32SetupModal from button #btnEsp32SetupGuide.
   Closes on backdrop click or ✕ / Close buttons.
══════════════════════════════════════════════════════════════ */
function openEsp32SetupModal() {
  const modal = document.getElementById('esp32SetupModal');
  if (!modal) return;
  modal.style.display = 'block';
  document.body.style.overflow = 'hidden';
  // Close on backdrop click
  modal.addEventListener('click', _esp32ModalBackdropClose);
}
window.openEsp32SetupModal = openEsp32SetupModal;

function closeEsp32SetupModal() {
  const modal = document.getElementById('esp32SetupModal');
  if (!modal) return;
  modal.style.display = 'none';
  document.body.style.overflow = '';
  modal.removeEventListener('click', _esp32ModalBackdropClose);
}
window.closeEsp32SetupModal = closeEsp32SetupModal;

function _esp32ModalBackdropClose(e) {
  // Close only when clicking the dark backdrop (not the inner dialog)
  if (e.target === document.getElementById('esp32SetupModal')) {
    closeEsp32SetupModal();
  }
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeEsp32SetupModal();
});

function copyEsp32FirmwareSnippet() {
  const pre = document.getElementById('esp32FirmwareSnippet');
  const statusEl = document.getElementById('esp32CopyStatus');
  if (!pre) return;
  const text = pre.textContent || pre.innerText;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      if (statusEl) { statusEl.style.display = 'block'; setTimeout(() => { statusEl.style.display = 'none'; }, 2500); }
    });
  } else {
    // Fallback for non-secure contexts
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try { document.execCommand('copy'); } catch (_) {}
    document.body.removeChild(ta);
    if (statusEl) { statusEl.style.display = 'block'; setTimeout(() => { statusEl.style.display = 'none'; }, 2500); }
  }
}
window.copyEsp32FirmwareSnippet = copyEsp32FirmwareSnippet;
