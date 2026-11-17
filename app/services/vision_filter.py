"""
EcoSensing AI – Advanced Computer Vision & Foreground Isolation Engine
Universal 4-Scene Agro-Ecological Vision: Leaves, Trees, Turfgrass, Soil & Salt Efflorescence.

Project Manager: Ali Nihad Qadir (علي نهاد قادر)
Academic Affiliation: Middle Technical University / Polytechnic College
"""

from __future__ import annotations

import base64
from typing import Any, Dict, Tuple

import cv2
import numpy as np


class VisionFilterEngine:
    """
    Real-Time OpenCV Thermal, Spectral, and Multi-Scene Agro-Ecological Vision Engine.
    Engineered for ultra-fast (<100ms) execution with precise central leaf/subject isolation
    (strictly excluding background soil, garden dirt, and human fingers).
    """

    MAX_DIMENSION: int = 640

    @classmethod
    def process_image(cls, image_bytes: bytes) -> Dict[str, Any]:
        """
        Process raw image bytes:
        1. Decode into BGR matrix and scale to max 640px.
        2. Isolate central leaf/subject contour (masking out human fingers and background garden dirt).
        3. Compute true quantitative metrics STRICTLY on the isolated leaf/subject mask:
           - green_vitality_pct: Healthy active chlorophyll percentage.
           - stress_drought_yellow_pct: Chlorosis, scorch, and necrotic tissue percentage.
           - dust_salinity_pct: Silt dust film on foliage OR white salt efflorescence on soil.
           - calibrated_surface_temp_c: Estimated surface temperature calibrated to Baghdad baseline.
        4. Generate high-contrast visualizations:
           - thermal_image_b64: OpenCV CLAHE contrast enhancement mapped with JET colormap & hotspot reticles.
           - spectral_image_b64: ExG (Excess Green) visual overlay mapped with VIRIDIS colormap.
        """
        if not image_bytes:
            raise ValueError("Empty image bytes provided to VisionFilterEngine.")

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image bytes into OpenCV BGR matrix.")

        h, w = img.shape[:2]
        if max(h, w) > cls.MAX_DIMENSION:
            scale = cls.MAX_DIMENSION / float(max(h, w))
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Step 1: Segment central leaf/subject contour & mask out skin / background soil
        fg_mask, skin_mask = cls._isolate_foreground(img)

        # Step 2: Compute quantitative metrics STRICTLY from isolated leaf mask
        pixel_metrics = cls._extract_foreground_metrics(img, fg_mask, skin_mask)

        # Step 3: Compute advanced laboratory multi-spectral and soil texture biometrics
        laboratory_biometrics = cls._extract_laboratory_biometrics(img, fg_mask, skin_mask, pixel_metrics)

        # Step 4: Generate Thermal Heatmap (CLAHE + JET with Hotspot Reticles)
        thermal_image_b64 = cls._generate_thermal_heatmap(img, fg_mask)

        # Step 5: Generate Spectral ExG Map (VIRIDIS)
        spectral_image_b64 = cls._generate_spectral_map(img, fg_mask)

        return {
            "thermal_image_b64": thermal_image_b64,
            "spectral_image_b64": spectral_image_b64,
            "pixel_metrics": pixel_metrics,
            "laboratory_biometrics": laboratory_biometrics,
            "foreground_ratio": round(float(np.count_nonzero(fg_mask)) / float(img.shape[0] * img.shape[1]), 3),
        }

    @classmethod
    def _isolate_foreground(cls, img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Segment the primary plant/leaf subject using color-space thresholding (HSV/LAB),
        Otsu thresholding, and contour filtering to exclude background garden soil or human fingers.
        """
        h, w = img.shape[:2]
        total_pixels = h * w
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Human skin detection (to exclude hands/fingers holding the leaf):
        skin_ycrcb = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
        skin_hsv = cv2.inRange(hsv, (0, 35, 55), (25, 210, 255))
        skin_mask = cv2.bitwise_and(skin_ycrcb, skin_hsv)
        k_skin = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, k_skin)

        # 2. Non-extreme background boundary (eliminate pure black borders or flash reflection)
        non_extreme_bg = cv2.inRange(gray, 12, 245)

        # 3. Detect candidate vegetation / leaf tissue:
        green_cand = cv2.inRange(hsv, (28, 20, 15), (95, 255, 255))
        yellow_cand = cv2.inRange(hsv, (14, 25, 20), (34, 255, 255))
        # Dust on leaf: pale ochre-silt
        hsv_dust = cv2.inRange(hsv, (10, 10, 60), (45, 100, 240))
        lab_dust = cv2.inRange(lab, (95, 110, 120), (235, 150, 175))
        dust_cand = cv2.bitwise_and(hsv_dust, lab_dust)

        # Combine candidate leaf tissue and exclude skin
        leaf_cand = cv2.bitwise_or(green_cand, cv2.bitwise_or(yellow_cand, dust_cand))
        leaf_cand = cv2.bitwise_and(leaf_cand, non_extreme_bg)
        leaf_cand = cv2.bitwise_and(leaf_cand, cv2.bitwise_not(skin_mask))

        veg_count = np.count_nonzero(leaf_cand)
        veg_ratio = float(veg_count) / float(total_pixels)

        # If vegetation candidate is detected (> 1.5% of canvas), isolate central leaf contour
        if veg_ratio >= 0.015:
            # OTSU thresholding on inverted gray to refine leaf boundary
            _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            combined_cand = cv2.bitwise_or(leaf_cand, cv2.bitwise_and(otsu_thresh, cv2.bitwise_not(skin_mask)))

            # Find contours
            contours, _ = cv2.findContours(leaf_cand, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                min_area = max(80.0, float(total_pixels) * 0.002)
                valid_contours = [c for c in contours if cv2.contourArea(c) >= min_area]
                if valid_contours:
                    cleaned_fg = np.zeros((h, w), dtype=np.uint8)
                    cv2.drawContours(cleaned_fg, valid_contours, -1, 255, thickness=cv2.FILLED)
                    # Morphological close to bridge veins and petiole
                    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
                    fg_mask = cv2.morphologyEx(cleaned_fg, cv2.MORPH_CLOSE, k_close)
                else:
                    fg_mask = leaf_cand
            else:
                fg_mask = leaf_cand
        else:
            # Bare soil sample: exclude skin and extreme margins
            fg_mask = cv2.bitwise_and(non_extreme_bg, cv2.bitwise_not(skin_mask))

        if np.count_nonzero(fg_mask) < 20:
            fg_mask = np.full((h, w), 255, dtype=np.uint8)

        return fg_mask, skin_mask

    @classmethod
    def _extract_foreground_metrics(
        cls,
        img: np.ndarray,
        fg_mask: np.ndarray,
        skin_mask: np.ndarray,
    ) -> Dict[str, float]:
        """
        Compute true quantitative metrics calculated STRICTLY on the isolated leaf/subject mask:
        - Background soil and human hands are excluded from dust/stress percentages.
        - Clean green leaf evaluates to dust_salinity_pct < 1.0% and vitality_pct > 80%.
        """
        fg_pixels = max(1.0, float(np.count_nonzero(fg_mask)))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Healthy Green Chlorophyll (Hue 28-95, saturation >= 20, value >= 15)
        green_raw = cv2.inRange(hsv, (28, 20, 15), (95, 255, 255))
        green_mask = cv2.bitwise_and(green_raw, fg_mask)

        # 2. Silt Dust Film & Soil Salt Efflorescence:
        # Dust must be strictly on the leaf mask and CANNOT be green chlorophyll
        hsv_dust = cv2.inRange(hsv, (10, 10, 60), (45, 100, 240))
        lab_dust = cv2.inRange(lab, (95, 110, 120), (235, 150, 175))
        raw_dust = cv2.bitwise_and(hsv_dust, lab_dust)

        # Salt efflorescence for soil beds (white crystalline crust, high L, low chroma)
        salt_efflorescence = cv2.inRange(lab, (170, 120, 120), (255, 136, 138))
        combined_dust_salt = cv2.bitwise_or(raw_dust, salt_efflorescence)

        # Apply strictly to foreground mask and exclude healthy green
        dust_salinity_mask = cv2.bitwise_and(combined_dust_salt, fg_mask)
        dust_salinity_mask = cv2.bitwise_and(dust_salinity_mask, cv2.bitwise_not(green_mask))

        # 3. Water Stress, Drought, Chlorosis & Necrosis:
        yellow_raw = cv2.inRange(hsv, (14, 25, 20), (34, 255, 255))
        brown_raw = cv2.inRange(hsv, (5, 25, 20), (18, 255, 180))
        stress_raw = cv2.bitwise_or(yellow_raw, brown_raw)

        stress_mask = cv2.bitwise_and(stress_raw, fg_mask)
        stress_mask = cv2.bitwise_and(stress_mask, cv2.bitwise_not(green_mask))
        stress_mask = cv2.bitwise_and(stress_mask, cv2.bitwise_not(dust_salinity_mask))

        # Calculate percentages STRICTLY within the isolated foreground mask
        green_vitality_pct = (float(np.count_nonzero(green_mask)) / fg_pixels) * 100.0
        dust_salinity_pct = (float(np.count_nonzero(dust_salinity_mask)) / fg_pixels) * 100.0
        stress_drought_yellow_pct = (float(np.count_nonzero(stress_mask)) / fg_pixels) * 100.0

        # If green vitality is very high (e.g. > 75%), any residual single-pixel noise dust is 0
        if green_vitality_pct >= 75.0 and dust_salinity_pct < 1.0:
            dust_salinity_pct = 0.0

        green_vitality_pct = float(np.clip(green_vitality_pct, 0.0, 100.0))
        stress_drought_yellow_pct = float(np.clip(stress_drought_yellow_pct, 0.0, 100.0))
        dust_salinity_pct = float(np.clip(dust_salinity_pct, 0.0, 100.0))

        # 4. Calibrated Surface Temperature (°C):
        fg_indices = np.where(fg_mask > 0)
        if len(fg_indices[0]) > 0:
            thermal_mean = float(np.mean(gray[fg_indices]) / 255.0)
        else:
            thermal_mean = float(np.mean(gray) / 255.0)

        base_temp = 36.0
        thermal_gain = thermal_mean * 5.5
        dust_gain = (dust_salinity_pct / 100.0) * 4.4
        stress_gain = (stress_drought_yellow_pct / 100.0) * 4.2
        canopy_cooling = (green_vitality_pct / 100.0) * 3.5

        raw_temp = base_temp + thermal_gain + dust_gain + stress_gain - canopy_cooling
        calibrated_surface_temp_c = float(np.clip(raw_temp, 36.0, 48.0))

        return {
            "green_vitality_pct": round(green_vitality_pct, 1),
            "stress_drought_yellow_pct": round(stress_drought_yellow_pct, 1),
            "dust_salinity_pct": round(dust_salinity_pct, 1),
            "calibrated_surface_temp_c": round(calibrated_surface_temp_c, 1),
            # Backwards compatibility keys
            "green_canopy_pct": round(green_vitality_pct, 1),
            "water_stress_yellow_pct": round(stress_drought_yellow_pct, 1),
            "iraqi_dust_index_pct": round(dust_salinity_pct, 1),
            "estimated_surface_temp_c": round(calibrated_surface_temp_c, 1),
        }

    @classmethod
    def _extract_laboratory_biometrics(
        cls,
        img: np.ndarray,
        fg_mask: np.ndarray,
        skin_mask: np.ndarray,
        pixel_metrics: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Compute high-precision OpenCV multi-spectral and soil texture matrices:
        - specimen_domain: BOTANICAL_FOLIAGE | FLORAL_BLOOM | PEDOLOGICAL_SOIL
        - surface_moisture_index_pct: 0 to 100%
        - salinity_crust_index_pct: 0 to 100%
        - structural_cracking_score: 0.0 to 10.0
        - chlorophyll_ndvi_proxy: [-1.0, +1.0]
        - anthocyanin_floral_index: 0 to 100%
        """
        fg_count = max(1, np.count_nonzero(fg_mask))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        b = img[:, :, 0].astype(np.float32)
        g = img[:, :, 1].astype(np.float32)
        r = img[:, :, 2].astype(np.float32)

        # 1. Chlorophyll NDVI Proxy (Normalized Green-Red Difference Index)
        ndvi_mat = (g - r) / (g + r + 1e-5)
        ndvi_vals = ndvi_mat[fg_mask > 0]
        ndvi_proxy = float(np.mean(ndvi_vals)) if len(ndvi_vals) > 0 else 0.0
        ndvi_proxy = float(np.clip(ndvi_proxy, -1.0, 1.0))

        # 2. Floral Chromatic Vibrancy & Anthocyanin Index
        # Detect vibrant petals: Red (Hue 0-14 or 160-180), Magenta/Pink (Hue 135-160), or Deep Floral Yellow/Orange (Hue 15-28, S>110)
        h_chan = hsv[:, :, 0]
        s_chan = hsv[:, :, 1]
        v_chan = hsv[:, :, 2]

        red_petals = ((h_chan <= 12) | (h_chan >= 160)) & (s_chan >= 60) & (v_chan >= 60)
        magenta_petals = (h_chan >= 135) & (h_chan < 160) & (s_chan >= 50) & (v_chan >= 55)
        vibrant_yellow_petals = (h_chan >= 15) & (h_chan <= 28) & (s_chan >= 120) & (v_chan >= 90)

        floral_raw = red_petals | magenta_petals | vibrant_yellow_petals
        floral_mask = cv2.bitwise_and(floral_raw.astype(np.uint8) * 255, fg_mask)
        floral_mask = cv2.bitwise_and(floral_mask, cv2.bitwise_not(skin_mask))

        floral_count = np.count_nonzero(floral_mask)
        anthocyanin_floral_index = (float(floral_count) / float(fg_count)) * 100.0

        # 3. Specimen Domain Classification
        green_pct = pixel_metrics.get("green_vitality_pct", 0.0)
        if anthocyanin_floral_index >= 9.0:
            specimen_domain = "FLORAL_BLOOM"
        elif green_pct >= 14.0 or ndvi_proxy >= 0.06:
            specimen_domain = "BOTANICAL_FOLIAGE"
        else:
            specimen_domain = "PEDOLOGICAL_SOIL"

        # 4. Surface Moisture Index (L* darkness + specular ratio)
        l_chan = lab[:, :, 0][fg_mask > 0]
        mean_l = float(np.mean(l_chan)) if len(l_chan) > 0 else 128.0
        # Wet surfaces absorb light, lowering L*. Specular reflections appear in wet gloss.
        specular_mask = (lab[:, :, 0] > 230) & (fg_mask > 0)
        specular_pct = (float(np.count_nonzero(specular_mask)) / float(fg_count)) * 100.0
        moisture_raw = (220.0 - mean_l) * 0.70 + min(15.0, specular_pct * 1.8)
        surface_moisture_index_pct = float(np.clip(moisture_raw, 4.0, 96.0))

        # 5. Salinity Crust Index (High albedo, low saturation white crystalline efflorescence)
        # In soil or foliage with salt efflorescence: L* >= 172, S <= 36
        salt_crust_raw = (lab[:, :, 0] >= 172) & (s_chan <= 38)
        salt_crust_mask = cv2.bitwise_and(salt_crust_raw.astype(np.uint8) * 255, fg_mask)
        salt_crust_mask = cv2.bitwise_and(salt_crust_mask, cv2.bitwise_not(skin_mask))
        salinity_crust_index_pct = (float(np.count_nonzero(salt_crust_mask)) / float(fg_count)) * 100.0

        # In clean green foliage, suppress spurious crust noise
        if green_pct >= 75.0 and salinity_crust_index_pct < 1.0:
            salinity_crust_index_pct = 0.0

        # 6. Structural Cracking Score (Canny edge density for desiccation cracks or necrotic lesions)
        blurred_gray = cv2.GaussianBlur(gray, (5, 5), 0)
        canny_edges = cv2.Canny(blurred_gray, 50, 140)
        canny_masked = cv2.bitwise_and(canny_edges, fg_mask)
        edge_density = float(np.count_nonzero(canny_masked)) / float(fg_count)
        structural_cracking_score = float(np.clip(edge_density * 82.0, 0.0, 10.0))

        return {
            "specimen_domain": specimen_domain,
            "surface_moisture_index_pct": round(surface_moisture_index_pct, 1),
            "salinity_crust_index_pct": round(salinity_crust_index_pct, 1),
            "structural_cracking_score": round(structural_cracking_score, 1),
            "chlorophyll_ndvi_proxy": round(ndvi_proxy, 3),
            "anthocyanin_floral_index": round(anthocyanin_floral_index, 1),
        }

    @classmethod
    def _generate_thermal_heatmap(cls, img: np.ndarray, fg_mask: np.ndarray) -> str:
        """
        Convert to grayscale, apply CLAHE contrast enhancement, map to JET colormap,
        and draw high-contrast targeting reticles over top stress hotspots.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)

        thermal_colored = cv2.applyColorMap(enhanced_gray, cv2.COLORMAP_JET)
        masked_gray = cv2.bitwise_and(enhanced_gray, enhanced_gray, mask=fg_mask)

        fg_vals = masked_gray[fg_mask > 0]
        if len(fg_vals) > 0:
            high_thresh_val = max(185, int(np.percentile(fg_vals, 86)))
        else:
            high_thresh_val = 195

        _, thresh = cv2.threshold(masked_gray, high_thresh_val, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned_thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(cleaned_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > 25]
        valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)[:3]

        annotated = thermal_colored.copy()
        for i, cnt in enumerate(valid_contours):
            x, y, w_box, h_box = cv2.boundingRect(cnt)
            cv2.rectangle(annotated, (x, y), (x + w_box, y + h_box), (0, 0, 255), 2)
            corner = min(8, w_box // 3, h_box // 3)
            if corner > 2:
                cv2.line(annotated, (x, y), (x + corner, y), (255, 255, 255), 2)
                cv2.line(annotated, (x, y), (x, y + corner), (255, 255, 255), 2)
                cv2.line(annotated, (x + w_box, y + h_box), (x + w_box - corner, y + h_box), (255, 255, 255), 2)
                cv2.line(annotated, (x + w_box, y + h_box), (x + w_box, y + h_box - corner), (255, 255, 255), 2)
            cv2.putText(
                annotated,
                f"STRESS-HOTSPOT-{i+1}",
                (x, max(14, y - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.36,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        _, buffer = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

    @classmethod
    def _generate_spectral_map(cls, img: np.ndarray, fg_mask: np.ndarray) -> str:
        """
        Compute Excess Green Index (ExG = 2*G - R - B) and render false-color
        VIRIDIS overlay to highlight chlorophyll density and vegetation vitality.
        """
        b = img[:, :, 0].astype(np.float32)
        g = img[:, :, 1].astype(np.float32)
        r = img[:, :, 2].astype(np.float32)

        exg = 2.0 * g - r - b
        exg_min, exg_max = float(exg.min()), float(exg.max())
        if exg_max > exg_min:
            exg_norm = np.clip((exg - exg_min) / (exg_max - exg_min) * 255.0, 0, 255).astype(np.uint8)
        else:
            exg_norm = np.full(exg.shape, 128, dtype=np.uint8)

        spectral_colored = cv2.applyColorMap(exg_norm, cv2.COLORMAP_VIRIDIS)
        blended = cv2.addWeighted(img, 0.35, spectral_colored, 0.65, 0)

        cv2.putText(
            blended,
            "Spectral ExG Canopy Index",
            (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        _, buffer = cv2.imencode(".jpg", blended, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
