"""
EcoSensing AI – Test Suite for Live Copernicus CAMS Pollution Sentinel & International Benchmark Protocols
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

import sys
import unittest
from fastapi.testclient import TestClient

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.main import app
from app.services.weather_geo_service import WeatherAndGeoIntelligenceService
from app.models.schemas import PollutionTelemetry


class TestPollutionSentinelSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_al_dora_refinery_singapore_benchmark(self):
        """Test Al-Dora refinery industrial hub matches Singapore Nano-Filtration Benchmark."""
        resp = self.client.get(
            "/api/pollution-sentinel?lat=33.2750&lon=44.4050&location_name_ar=مصفى الدورة الصناعي"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Validate schema adherence
        telemetry = PollutionTelemetry(**data)
        self.assertEqual(telemetry.dominant_hazard_code, "INDUSTRIAL_PM25")
        self.assertEqual(telemetry.benchmark_country_code, "SINGAPORE")
        self.assertIn("سنغافورة", telemetry.benchmark_country_ar)
        self.assertIn("الفلترة النانوية الحيوية", telemetry.benchmark_project_title_ar)
        self.assertEqual(telemetry.expected_pm_reduction_pct, 48.0)
        self.assertEqual(telemetry.expected_lst_drop_c, 2.8)
        self.assertTrue(any("النيم" in s for s in telemetry.target_species_ar))
        self.assertTrue(telemetry.pm25_ugm3 > 0)
        self.assertTrue(telemetry.aqi_european > 0)
        print("✓ Test 1 Passed: Al-Dora Refinery -> SINGAPORE Bio-Nanofiltration Protocol")

    def test_02_central_baghdad_germany_benchmark(self):
        """Test Central Baghdad / Mohamed Al-Qasim matches Germany Urban Ventilation Corridor Benchmark."""
        resp = self.client.get(
            "/api/pollution-sentinel?lat=33.3280&lon=44.4120&location_name_ar=قلب بغداد / سريع محمد القاسم"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        telemetry = PollutionTelemetry(**data)
        self.assertEqual(telemetry.dominant_hazard_code, "URBAN_HEAT_STAGNATION")
        self.assertEqual(telemetry.benchmark_country_code, "GERMANY")
        self.assertIn("ألمانيا", telemetry.benchmark_country_ar)
        self.assertIn("ممرات التهوية الحضرية", telemetry.benchmark_project_title_ar)
        self.assertEqual(telemetry.expected_pm_reduction_pct, 35.0)
        self.assertEqual(telemetry.expected_lst_drop_c, 3.1)
        self.assertTrue(any("البونسيانا" in s for s in telemetry.target_species_ar))
        self.assertTrue(telemetry.uhi_anomaly_c > 0)
        print("✓ Test 2 Passed: Central Baghdad -> GERMANY Urban Ventilation Corridors Protocol")

    def test_03_abu_ghraib_uae_china_benchmark(self):
        """Test Western Baghdad / Abu Ghraib matches UAE-China 40% Optical Porosity Bioshield Benchmark."""
        resp = self.client.get(
            "/api/pollution-sentinel?lat=33.3050&lon=44.2050&location_name_ar=مدخل العاصمة الغربي / أبو غريب"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        telemetry = PollutionTelemetry(**data)
        self.assertEqual(telemetry.dominant_hazard_code, "DUST_STORM_PM10")
        self.assertEqual(telemetry.benchmark_country_code, "UAE_CHINA")
        self.assertIn("الإمارات والصين", telemetry.benchmark_country_ar)
        self.assertIn("40%", telemetry.benchmark_project_title_ar)
        self.assertEqual(telemetry.expected_pm_reduction_pct, 65.0)
        self.assertEqual(telemetry.expected_lst_drop_c, 2.5)
        self.assertTrue(any("السدر" in s for s in telemetry.target_species_ar))
        print("✓ Test 3 Passed: Abu Ghraib -> UAE & CHINA 40% Optical Porosity Bioshield Protocol")

    def test_04_chatbot_with_pollution_telemetry(self):
        """Test Iraqi dialect Chatbot answers questions accurately when pollution telemetry is present."""
        pollution_payload = {
            "message": "شنو هو بروتوكول سنغافورة لمصفى الدورة وشنو مواصفات الحزام؟",
            "active_section": "afforestation",
            "live_telemetry": {
                "workspace": "afforestation",
                "location": "مصفى الدورة الصناعي",
                "pollution_data": {
                    "location_name_ar": "مصفى الدورة الصناعي",
                    "aqi_european": 55,
                    "pm25_ugm3": 28.5,
                    "dominant_hazard_code": "INDUSTRIAL_PM25",
                    "benchmark_country_code": "SINGAPORE",
                    "benchmark_country_ar": "🇸🇬 سنغافورة وجامعة لانكستر البريطانية",
                    "benchmark_project_title_ar": "بروتوكول الفلترة النانوية الحيوية والأحزمة الإسفينية",
                    "recommended_buffer_specs_ar": "حزام عازل بعرض 35 إلى 50 متراً بمحيط المنشأة الصناعية.",
                    "target_species_ar": ["النيم الهندي", "الكاليبتوس", "السدر"],
                    "expected_pm_reduction_pct": 48.0,
                    "expected_lst_drop_c": 2.8,
                }
            },
            "history": []
        }
        resp = self.client.post("/api/chat", json=pollution_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("reply_ar", data)
        reply = data["reply_ar"]
        self.assertTrue(len(reply) > 20)
        print("✓ Test 4 Passed: Iraqi Chatbot successfully integrated with pollution telemetry!")
        print(f"Chatbot Reply snippet: {reply[:120]}...")


if __name__ == "__main__":
    unittest.main()

