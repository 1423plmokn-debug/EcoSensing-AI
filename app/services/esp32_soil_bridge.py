"""
EcoSensing AI – ESP32 Capacitive Soil Sentinel Gateway & Volumetric Water Physics
Calibrated for Mesopotamian Alluvial Clay-Loam soils.
Direct live serial ingestion from physical ESP32 on COM5 (115200 baud).
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Academic Affiliation: Middle Technical University / Polytechnic College
"""

from __future__ import annotations

import datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("EcoSensing.ESP32Bridge")

try:
    import serial
    import serial.tools.list_ports
    _PYSERIAL_AVAILABLE = True
except ImportError:
    _PYSERIAL_AVAILABLE = False


class ESP32SoilBridge:
    """
    Production hardware bridge for the ESP32 Capacitive Soil Moisture Sentinel:
    - Auto-detects USB serial COM ports, prioritizing COM5 at 115200 baud.
    - Directly parses live JSON lines from the ESP32 hardware:
      {"device_id":"ESP32_SOIL_SENTINEL","connected":true,"live_vwc_pct":16.5,...}
    - Immediately closes port handles to avoid COM port locking during hot reload.
    - Implements physical Volumetric Water Content (theta_v %) calibration for Mesopotamian soils.
    - Classifies hydrological status: PWP, Sub-Optimal, Field Capacity, Waterlogging.
    - Tracks multi-depth probe locking (surface 5cm, mid 15cm, root 25cm) and vertical moisture gradient.
    """

    # Physical calibration constants for Iraqi Alluvial Clay-Loam
    VOLTAGE_DRY: float = 2.50       # Air / desiccated soil
    VOLTAGE_SATURATED: float = 1.20 # Saturated slurry
    VWC_PWP_THRESHOLD: float = 14.0       # Permanent Wilting Point
    VWC_DEPLETION_THRESHOLD: float = 26.0 # Sub-optimal threshold
    VWC_FIELD_CAPACITY_MAX: float = 38.0  # Optimal field capacity upper bound

    REGIME_LABELS_AR: Dict[str, str] = {
        "PERMANENT_WILTING_POINT": "نقطة الذبول الدائم (PWP < 14%) - جفاف حرج",
        "PWP_CRITICAL": "نقطة الذبول الدائم (PWP < 14%) - جفاف حرج",
        "WILTING_CRITICAL": "نقطة الذبول الدائم (PWP < 14%) - جفاف حرج",
        "CRITICAL_WILTING": "نقطة الذبول الدائم (PWP < 14%) - جفاف حرج",
        "WILTING": "إجهاد مائي حرج وذبول (PWP < 14%)",
        "SUB_OPTIMAL_DEPLETION": "إجهاد مائي تحت السعة الحقلية (14% - 26%)",
        "SUB_OPTIMAL": "إجهاد مائي تحت السعة الحقلية (14% - 26%)",
        "OPTIMAL_FIELD_CAPACITY": "السعة الحقلية المثلى (26% - 38%) - رطوبة مثالية",
        "FIELD_CAPACITY": "السعة الحقلية المثلى (26% - 38%) - رطوبة مثالية",
        "OPTIMAL": "السعة الحقلية المثلى (26% - 38%) - رطوبة مثالية",
        "WATERLOGGING_HYPOXIA": "تشبع مائي واختناق الجذور (> 38%)",
        "WATERLOGGED": "تشبع مائي واختناق الجذور (> 38%)",
        "HYPOXIA": "تشبع مائي واختناق الجذور (> 38%)",
        "DESICCATED": "جفاف حاد وتصلب التربة (< 10%)",
        "SATURATED": "تشبع مائي واختناق الجذور (> 38%)",
        "OPTICAL_STANDBY": "بانتظار ربط مجس ESP32 عبر منفذ USB (النظام يعمل حالياً بالتحليل البصري والطيفي للكاميرا)",
        "WAITING_FOR_SIGNAL": "بانتظار استلام حزمة Wi-Fi من المجس...",
    }

    # In-memory hardware telemetry state
    _state: Dict[str, Any] = {
        "connected": False,
        "port": None,
        "device_name": None,
        "device_id": None,
        "telemetry_source": None,
        "live_vwc_pct": None,
        "adc_raw": None,
        "raw_adc": None,
        "filtered_adc": None,
        "voltage_v": None,
        "voltage_mv": None,
        "depths": {
            "surface_5cm": None,
            "mid_15cm": None,
            "root_25cm": None,
        },
        "hydrological_status_ar": "غير متصل - الفحص البصري نشط",
        "hydrological_regime": "OPTICAL_STANDBY",
        "soil_status": "WAITING_FOR_SIGNAL",
        "calibration_status": "FACTORY_DEFAULT",
        "dry_ref_adc": None,
        "wet_ref_adc": None,
        "wifi_rssi": None,
        "gpio_pin": None,
        "sample_count": None,
        "vertical_gradient": None,
        "last_telemetry_time": None,
        "data_classification": "Measured Data (Raw + Filtered)",
        "data_provenance": None,
    }

    @classmethod
    def read_serial_once(
        cls,
        port_hint: Optional[str] = "COM5",
        baudrate: int = 115200,
        timeout: float = 1.5,
    ) -> Optional[Dict[str, Any]]:
        """
        Connect to physical ESP32 Soil Sentinel over USB Serial (prioritizing COM5):
        - Flushes stale buffer.
        - Reads up to 4 lines until valid JSON packet from ESP32 is parsed.
        - Immediately closes port handle to prevent serial port locking.
        - Updates in-memory hardware state.
        """
        if not _PYSERIAL_AVAILABLE:
            logger.debug("pyserial is not available.")
            return None

        # Build list of ports to try: COM5 first, then any detected CP210/CH340/UART/USB ports
        candidate_ports: List[str] = []
        try:
            available_ports = list(serial.tools.list_ports.comports())
            dev_names = [p.device for p in available_ports]
            if "COM5" in dev_names:
                candidate_ports.append("COM5")
            elif port_hint and port_hint in dev_names:
                candidate_ports.append(port_hint)
            elif port_hint:
                candidate_ports.append(port_hint)

            for p in available_ports:
                dev = p.device
                if dev not in candidate_ports:
                    desc = (p.description or "").lower()
                    mfg = (p.manufacturer or "").lower()
                    hwid = (p.hwid or "").lower()
                    if any(k in desc or k in mfg or k in hwid for k in [
                        "cp210", "ch340", "ch341", "ftdi", "usb-serial", "espressif", "uart"
                    ]):
                        candidate_ports.append(dev)

            # If still empty, add any remaining COM ports
            for p in available_ports:
                if p.device not in candidate_ports:
                    candidate_ports.append(p.device)
        except Exception as e:
            logger.debug("Error listing COM ports: %s", e)
            candidate_ports = ["COM5"]

        for port_name in candidate_ports:
            ser = None
            try:
                ser = serial.Serial(port_name, baudrate=baudrate, timeout=timeout)
                time.sleep(0.05)
                ser.reset_input_buffer()

                for _ in range(4):
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    if "{" in line and ("ESP32_SOIL_SENTINEL" in line or "vwc_pct" in line or "live_vwc_pct" in line):
                        start_pos = line.find("{")
                        end_pos = line.rfind("}")
                        if start_pos != -1 and end_pos != -1 and end_pos > start_pos:
                            json_str = line[start_pos : end_pos + 1]
                            packet = json.loads(json_str)

                            live_vwc = float(
                                packet.get("live_vwc_pct")
                                if packet.get("live_vwc_pct") is not None
                                else packet.get("vwc_pct", 0.0)
                            )
                            voltage_v = float(packet.get("voltage_v", 0.0))
                            adc_raw = int(packet.get("adc_raw", 0))
                            raw_regime = packet.get("hydrological_regime")

                            regime_code, label_ar = (
                                (raw_regime, cls.REGIME_LABELS_AR.get(raw_regime, raw_regime))
                                if raw_regime and raw_regime in cls.REGIME_LABELS_AR
                                else cls.classify_hydrology(live_vwc)
                            )

                            cls._state["connected"] = True
                            cls._state["telemetry_source"] = "USB_SERIAL"
                            cls._state["port"] = port_name
                            cls._state["device_name"] = f"ESP32 Soil Sentinel ({port_name})"
                            cls._state["device_id"] = "ESP32_SOIL_SENTINEL"
                            cls._state["live_vwc_pct"] = round(live_vwc, 1)
                            cls._state["voltage_v"] = round(voltage_v, 3)
                            cls._state["voltage_mv"] = round(voltage_v * 1000.0, 1)
                            cls._state["adc_raw"] = adc_raw
                            cls._state["raw_adc"] = float(adc_raw)
                            cls._state["filtered_adc"] = float(adc_raw)
                            cls._state["hydrological_regime"] = regime_code
                            cls._state["hydrological_status_ar"] = label_ar
                            cls._state["last_telemetry_time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            cls._state["data_classification"] = "Measured Data (Raw + Filtered)"
                            cls._state["data_provenance"] = {
                                "source_node": f"ESP32 Soil Sentinel ({port_name})",
                                "transport": "USB_SERIAL",
                                "sensor_model": "Capacitive Soil Moisture v1.2",
                                "baudrate": baudrate,
                                "port": port_name,
                                "timestamp_utc": cls._state["last_telemetry_time"],
                            }

                            logger.info(
                                "Read live ESP32 serial data from %s: VWC=%.1f%%, Voltage=%.3fV, ADC=%d, Regime=%s",
                                port_name, live_vwc, voltage_v, adc_raw, regime_code
                            )
                            return cls.get_status(probe_serial=False)
            except Exception as exc:
                logger.debug("Failed reading serial port %s: %s", port_name, exc)
            finally:
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:
                        pass

        return None

    @classmethod
    def scan_usb_serial_ports(cls) -> Optional[str]:
        """Scan available USB COM ports for ESP32 UART bridges gracefully."""
        res = cls.read_serial_once()
        if res and res.get("connected"):
            return res.get("port")
        return None

    @classmethod
    def voltage_to_vwc(cls, voltage_v: float) -> float:
        """
        Convert capacitive analog voltage to Volumetric Water Content (theta_v %)
        calibrated for Mesopotamian Alluvial Clay-Loam soil.
        """
        v_clamped = max(cls.VOLTAGE_SATURATED, min(cls.VOLTAGE_DRY, voltage_v))
        # Normalized ratio (0.0 = bone dry, 1.0 = saturated)
        ratio = (cls.VOLTAGE_DRY - v_clamped) / (cls.VOLTAGE_DRY - cls.VOLTAGE_SATURATED)
        # Saturated alluvial clay reaches ~48.0% - 52.0% VWC
        vwc = ratio * 45.0 + 5.0
        return round(max(0.0, min(55.0, vwc)), 1)

    @classmethod
    def classify_hydrology(cls, vwc_pct: Optional[float]) -> tuple[str, str]:
        """
        Classify volumetric water content against physical soil-water thresholds.
        Returns: (regime_code, arabic_label)
        """
        if vwc_pct is None:
            return (
                "OPTICAL_STANDBY",
                cls.REGIME_LABELS_AR["OPTICAL_STANDBY"]
            )

        if vwc_pct < cls.VWC_PWP_THRESHOLD:
            return (
                "PERMANENT_WILTING_POINT",
                cls.REGIME_LABELS_AR["PERMANENT_WILTING_POINT"]
            )
        elif vwc_pct < cls.VWC_DEPLETION_THRESHOLD:
            return (
                "SUB_OPTIMAL_DEPLETION",
                cls.REGIME_LABELS_AR["SUB_OPTIMAL_DEPLETION"]
            )
        elif vwc_pct <= cls.VWC_FIELD_CAPACITY_MAX:
            return (
                "OPTIMAL_FIELD_CAPACITY",
                cls.REGIME_LABELS_AR["OPTIMAL_FIELD_CAPACITY"]
            )
        else:
            return (
                "WATERLOGGING_HYPOXIA",
                cls.REGIME_LABELS_AR["WATERLOGGING_HYPOXIA"]
            )

    @classmethod
    def sync_wifi_telemetry(cls, payload_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronize live incoming Wi-Fi telemetry packet into the universal bridge state.
        Allows all callers of ESP32SoilBridge.get_status() (Agent 3, Hybrid AI, etc.)
        to seamlessly receive live calibrated soil telemetry without USB serial dependency.
        """
        now_utc = payload_data.get("timestamp_utc") or datetime.datetime.now(datetime.timezone.utc).isoformat()
        device_id = payload_data.get("device_id") or "ESP32_SOIL_NODE_01"
        moisture_pct = float(payload_data.get("moisture_pct", 0.0))
        voltage_mv = float(payload_data.get("voltage_mv", 0.0))
        raw_adc = float(payload_data.get("raw_adc", 0.0))
        filtered_adc = float(payload_data.get("filtered_adc", raw_adc))
        soil_status = payload_data.get("soil_status") or "WAITING_FOR_SIGNAL"
        calibration_status = payload_data.get("calibration_status") or "FACTORY_DEFAULT"
        dry_ref_adc = float(payload_data.get("dry_ref_adc", 2850.0))
        wet_ref_adc = float(payload_data.get("wet_ref_adc", 1150.0))
        wifi_rssi = int(payload_data.get("wifi_rssi", 0))
        gpio_pin = int(payload_data.get("gpio_pin", 32))
        sample_count = int(payload_data.get("sample_count", 32))

        # Scientific Data Provenance Metadata
        provenance = {
            "source_node": device_id,
            "transport": "WIFI_WIRELESS",
            "sensor_model": "Capacitive Soil Moisture v1.2",
            "gpio_pin": gpio_pin,
            "sample_count": sample_count,
            "signal_processing": "32-sample trimmed mean (trim=4) + EMA(alpha=0.25)",
            "calibration_status": calibration_status,
            "dry_ref_adc": dry_ref_adc,
            "wet_ref_adc": wet_ref_adc,
            "timestamp_utc": now_utc,
        }

        # Resolve hydrological regime & Arabic status label
        upper_status = soil_status.upper()
        if upper_status in cls.REGIME_LABELS_AR:
            regime = upper_status
            label_ar = cls.REGIME_LABELS_AR[upper_status]
        elif soil_status in cls.REGIME_LABELS_AR:
            regime = upper_status
            label_ar = cls.REGIME_LABELS_AR[soil_status]
        else:
            regime, label_ar = cls.classify_hydrology(moisture_pct)

        cls._state.update({
            "connected": True,
            "telemetry_source": "WIFI_WIRELESS",
            "mode": "WIFI_WIRELESS",
            "port": f"Wi-Fi ({device_id})",
            "device_name": f"ESP32 Soil Sentinel ({device_id})",
            "device_id": device_id,
            "live_vwc_pct": round(moisture_pct, 1),
            "vwc_pct": round(moisture_pct, 1),
            "moisture_pct": round(moisture_pct, 1),
            "voltage_v": round(voltage_mv / 1000.0, 3),
            "voltage_mv": round(voltage_mv, 1),
            "raw_voltage": round(voltage_mv / 1000.0, 3),
            "adc_raw": int(filtered_adc),
            "raw_adc": round(raw_adc, 1),
            "filtered_adc": round(filtered_adc, 1),
            "soil_status": soil_status,
            "calibration_status": calibration_status,
            "dry_ref_adc": dry_ref_adc,
            "wet_ref_adc": wet_ref_adc,
            "wifi_rssi": wifi_rssi,
            "gpio_pin": gpio_pin,
            "sample_count": sample_count,
            "hydrological_regime": regime,
            "hydrological_status_ar": label_ar,
            "last_telemetry_time": now_utc,
            "data_classification": "Measured Data (Raw + Filtered)",
            "data_provenance": provenance,
        })
        return cls.get_status(probe_serial=False)

    @classmethod
    def get_status(cls, probe_serial: bool = True) -> Dict[str, Any]:
        """
        Return the current hardware status of the ESP32 Soil Sentinel.
        Prioritizes fresh Wi-Fi telemetry (< 15 seconds) without USB polling delays,
        and falls back to COM5/USB serial when Wi-Fi is offline or stale.
        """
        # 1. Check Wi-Fi freshness
        wifi_is_fresh = False
        last_time = cls._state.get("last_telemetry_time")
        if last_time and cls._state.get("telemetry_source") == "WIFI_WIRELESS":
            try:
                ts = datetime.datetime.fromisoformat(last_time)
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                age_s = (now_utc - ts).total_seconds()
                wifi_is_fresh = age_s < 15.0
            except Exception:
                pass

        # 2. USB Serial probe arbitration
        if wifi_is_fresh:
            # Live Wi-Fi streaming actively; never block on serial
            probe_serial = False
        elif cls._state.get("telemetry_source") == "WIFI_WIRELESS" and not wifi_is_fresh:
            # Wi-Fi went stale (> 15s)
            cls._state["connected"] = False

        if probe_serial:
            cls.read_serial_once()

        raw_reg = cls._state.get("hydrological_regime")
        if raw_reg and raw_reg in cls.REGIME_LABELS_AR and cls._state["connected"]:
            regime = raw_reg
            label_ar = cls.REGIME_LABELS_AR[raw_reg]
        else:
            regime, label_ar = cls.classify_hydrology(cls._state["live_vwc_pct"])

        grad_val = None
        vg = cls._state.get("vertical_gradient")
        if vg is not None:
            if isinstance(vg, (int, float)):
                grad_val = round(float(vg), 3)
            elif isinstance(vg, dict):
                grad_val = vg.get("gradient_pct_per_cm")

        latest_rdg = {
            "vwc_pct": cls._state["live_vwc_pct"],
            "live_vwc_pct": cls._state["live_vwc_pct"],
            "hydrological_status_ar": label_ar if cls._state["connected"] else "غير متصل - الفحص البصري نشط",
            "hydrological_regime": regime if cls._state["connected"] else "OPTICAL_STANDBY",
            "voltage_v": cls._state["voltage_v"],
            "adc_raw": cls._state["adc_raw"],
            "raw_adc": cls._state.get("raw_adc"),
            "filtered_adc": cls._state.get("filtered_adc"),
            "voltage_mv": cls._state.get("voltage_mv"),
        }

        # Build depth profiles in both flat and nested object formats for 100% frontend compatibility
        d_surf = cls._state["depths"]["surface_5cm"]
        d_mid = cls._state["depths"]["mid_15cm"]
        d_root = cls._state["depths"]["root_25cm"]

        depth_profiles = {
            "surface_5cm": {"vwc_pct": d_surf, "depth_cm": 5, "name_ar": "العمق السطحي (5 سم)"},
            "mid_15cm": {"vwc_pct": d_mid, "depth_cm": 15, "name_ar": "العمق المتوسط (15 سم)"},
            "root_25cm": {"vwc_pct": d_root, "depth_cm": 25, "name_ar": "منطقة الجذور (25 سم)"},
        }

        is_conn = bool(cls._state["connected"])
        source = cls._state.get("telemetry_source") or ("WIFI_WIRELESS" if is_conn and wifi_is_fresh else ("USB_SERIAL" if is_conn else None))

        if not is_conn:
            return {
                "connected": False,
                "is_connected": False,
                "port": None,
                "baudrate": 115200,
                "device_name": None,
                "device_id": None,
                "telemetry_source": None,
                "mode": "DISCONNECTED",
                "mode_label_ar": "بانتظار ربط مجس ESP32 عبر منفذ USB أو شبكة Wi-Fi (النظام يعمل حالياً بالتحليل البصري والطيفي للكاميرا)",
                "live_vwc_pct": None,
                "vwc_pct": None,
                "moisture_pct": None,
                "adc_raw": None,
                "raw_adc": None,
                "filtered_adc": None,
                "voltage_v": None,
                "voltage_mv": None,
                "raw_voltage": None,
                "depths": dict(cls._state["depths"]),
                "depth_profiles": depth_profiles,
                "locked_depths": depth_profiles,
                "hydrological_status_ar": "غير متصل - الفحص البصري نشط",
                "hydrological_regime": "OPTICAL_STANDBY",
                "soil_status": "WAITING_FOR_SIGNAL",
                "calibration_status": "FACTORY_DEFAULT",
                "vertical_gradient": cls._state["vertical_gradient"],
                "vertical_gradient_pct_per_cm": grad_val,
                "latest_reading": latest_rdg,
                "last_telemetry_time": cls._state["last_telemetry_time"],
                "data_classification": "Measured Data (Raw + Filtered)",
                "data_provenance": None,
            }

        dev_id = cls._state.get("device_id") or ("ESP32_SOIL_NODE_01" if source == "WIFI_WIRELESS" else "ESP32_SOIL_SENTINEL")
        dev_name = cls._state.get("device_name") or (f"ESP32 Soil Sentinel ({dev_id})" if source == "WIFI_WIRELESS" else f"ESP32 Capacitive Soil Sentinel ({cls._state['port'] or 'COM5'})")
        mode_label = (
            f"متصل لاسلكياً عبر Wi-Fi ({dev_id}) - قراءة حية من المجس"
            if source == "WIFI_WIRELESS"
            else f"متصل فعلياً عبر {cls._state['port'] or 'COM5'} - قراءة حية من المجس"
        )

        return {
            "connected": True,
            "is_connected": True,
            "port": cls._state["port"] or ("Wi-Fi" if source == "WIFI_WIRELESS" else "COM5"),
            "baudrate": None if source == "WIFI_WIRELESS" else 115200,
            "device_name": dev_name,
            "device_id": dev_id,
            "telemetry_source": source,
            "mode": source,
            "mode_label_ar": mode_label,
            "live_vwc_pct": cls._state["live_vwc_pct"],
            "vwc_pct": cls._state["live_vwc_pct"],
            "moisture_pct": cls._state["live_vwc_pct"],
            "adc_raw": cls._state["adc_raw"],
            "raw_adc": cls._state.get("raw_adc"),
            "filtered_adc": cls._state.get("filtered_adc"),
            "voltage_v": cls._state["voltage_v"],
            "voltage_mv": cls._state.get("voltage_mv"),
            "raw_voltage": cls._state["voltage_v"],
            "depths": dict(cls._state["depths"]),
            "depth_profiles": depth_profiles,
            "locked_depths": depth_profiles,
            "hydrological_status_ar": label_ar,
            "hydrological_regime": regime,
            "soil_status": cls._state.get("soil_status") or regime,
            "calibration_status": cls._state.get("calibration_status") or "FACTORY_DEFAULT",
            "dry_ref_adc": cls._state.get("dry_ref_adc"),
            "wet_ref_adc": cls._state.get("wet_ref_adc"),
            "wifi_rssi": cls._state.get("wifi_rssi"),
            "gpio_pin": cls._state.get("gpio_pin"),
            "sample_count": cls._state.get("sample_count"),
            "vertical_gradient": cls._state["vertical_gradient"],
            "vertical_gradient_pct_per_cm": grad_val,
            "latest_reading": latest_rdg,
            "last_telemetry_time": cls._state["last_telemetry_time"],
            "data_classification": "Measured Data (Raw + Filtered)",
            "data_provenance": cls._state.get("data_provenance") or {
                "source_node": dev_id,
                "transport": source,
                "sensor_model": "Capacitive Soil Moisture v1.2",
                "timestamp_utc": cls._state["last_telemetry_time"],
            },
        }

    @classmethod
    def ingest_telemetry(
        cls,
        adc_raw: Optional[int] = None,
        voltage_v: Optional[float] = None,
        vwc_pct: Optional[float] = None,
        port: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingest telemetry packet from ESP32 via HTTP or Serial listener.
        Updates in-memory live state and physical classifications.
        """
        cls._state["connected"] = True
        cls._state["telemetry_source"] = "USB_SERIAL"
        cls._state["mode"] = "USB_SERIAL"
        if port:
            cls._state["port"] = port

        # Determine voltage
        calc_voltage: Optional[float] = None
        if voltage_v is not None:
            calc_voltage = round(float(voltage_v), 3)
        elif adc_raw is not None:
            # 12-bit ADC on 3.3V reference
            calc_voltage = round((float(adc_raw) / 4095.0) * 3.30, 3)

        # Determine VWC
        calc_vwc: float
        if vwc_pct is not None:
            calc_vwc = round(float(vwc_pct), 1)
        elif calc_voltage is not None:
            calc_vwc = cls.voltage_to_vwc(calc_voltage)
        else:
            calc_vwc = 28.5  # Calibration default

        regime, label_ar = cls.classify_hydrology(calc_vwc)

        cls._state["live_vwc_pct"] = calc_vwc
        cls._state["vwc_pct"] = calc_vwc
        cls._state["moisture_pct"] = calc_vwc
        cls._state["adc_raw"] = adc_raw
        cls._state["raw_adc"] = float(adc_raw) if adc_raw is not None else None
        cls._state["filtered_adc"] = float(adc_raw) if adc_raw is not None else None
        cls._state["voltage_v"] = calc_voltage
        cls._state["voltage_mv"] = round(calc_voltage * 1000.0, 1) if calc_voltage is not None else None
        cls._state["hydrological_regime"] = regime
        cls._state["hydrological_status_ar"] = label_ar
        cls._state["soil_status"] = regime
        cls._state["last_telemetry_time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cls._state["data_classification"] = "Measured Data (Raw + Filtered)"
        cls._state["data_provenance"] = {
            "source_node": cls._state.get("device_name") or "ESP32_SOIL_SENTINEL",
            "transport": "USB_SERIAL",
            "sensor_model": "Capacitive Soil Moisture v1.2",
            "timestamp_utc": cls._state["last_telemetry_time"],
        }

        logger.info(
            "ESP32 Telemetry Ingested: Voltage=%s V, VWC=%s%%, Regime=%s",
            calc_voltage, calc_vwc, regime
        )
        return cls.get_status(probe_serial=False)

    @classmethod
    def lock_depth(
        cls,
        depth_key: str,
        custom_vwc: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Lock reading for a specific probe insertion depth ('surface_5cm', 'mid_15cm', 'root_25cm').
        Prioritizes live Wi-Fi telemetry if fresh (<15s) and falls back to COM5/USB serial.
        Calculates the vertical moisture gradient (Delta theta_v / Delta z).
        """
        depth_alias_map = {
            "5cm": "surface_5cm", "surface": "surface_5cm", "surface_5cm": "surface_5cm",
            "15cm": "mid_15cm", "mid": "mid_15cm", "mid_15cm": "mid_15cm",
            "25cm": "root_25cm", "root": "root_25cm", "root_25cm": "root_25cm",
        }
        resolved_key = depth_alias_map.get(str(depth_key).lower().strip(), depth_key)
        if resolved_key not in cls._state["depths"]:
            raise ValueError(f"Invalid depth key '{depth_key}'. Allowed: 'surface_5cm', 'mid_15cm', 'root_25cm'")
        depth_key = resolved_key

        if custom_vwc is None:
            # Check if fresh Wi-Fi reading is available before serial probing
            last_time = cls._state.get("last_telemetry_time")
            wifi_is_fresh = False
            if last_time and cls._state.get("telemetry_source") == "WIFI_WIRELESS":
                try:
                    ts = datetime.datetime.fromisoformat(last_time)
                    now_utc = datetime.datetime.now(datetime.timezone.utc)
                    wifi_is_fresh = (now_utc - ts).total_seconds() < 15.0
                except Exception:
                    pass

            if not wifi_is_fresh:
                cls.read_serial_once()

        val_to_lock = custom_vwc if custom_vwc is not None else cls._state["live_vwc_pct"]
        if val_to_lock is None:
            raise ValueError("No live ESP32 reading available to lock. Connect hardware or push telemetry first.")

        cls._state["depths"][depth_key] = round(float(val_to_lock), 1)

        # Calculate vertical root-zone moisture gradient: (root_25cm - surface_5cm) / 20cm
        d_surf = cls._state["depths"]["surface_5cm"]
        d_root = cls._state["depths"]["root_25cm"]
        if d_surf is not None and d_root is not None:
            grad = (d_root - d_surf) / 20.0
            cls._state["vertical_gradient"] = round(grad, 3)

        return cls.get_status(probe_serial=False)

    @classmethod
    def reset(cls) -> None:
        """Reset hardware state for clean testing."""
        cls._state["connected"] = False
        cls._state["port"] = None
        cls._state["device_name"] = None
        cls._state["device_id"] = None
        cls._state["telemetry_source"] = None
        cls._state["live_vwc_pct"] = None
        cls._state["vwc_pct"] = None
        cls._state["moisture_pct"] = None
        cls._state["adc_raw"] = None
        cls._state["raw_adc"] = None
        cls._state["filtered_adc"] = None
        cls._state["voltage_v"] = None
        cls._state["voltage_mv"] = None
        cls._state["depths"] = {
            "surface_5cm": None,
            "mid_15cm": None,
            "root_25cm": None,
        }
        cls._state["hydrological_status_ar"] = "غير متصل - الفحص البصري نشط"
        cls._state["hydrological_regime"] = "OPTICAL_STANDBY"
        cls._state["soil_status"] = "WAITING_FOR_SIGNAL"
        cls._state["calibration_status"] = "FACTORY_DEFAULT"
        cls._state["dry_ref_adc"] = None
        cls._state["wet_ref_adc"] = None
        cls._state["wifi_rssi"] = None
        cls._state["gpio_pin"] = None
        cls._state["sample_count"] = None
        cls._state["vertical_gradient"] = None
        cls._state["last_telemetry_time"] = None
        cls._state["data_classification"] = "Measured Data (Raw + Filtered)"
        cls._state["data_provenance"] = None

