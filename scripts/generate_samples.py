# -*- coding: utf-8 -*-
"""
EcoSensing AI - High-Resolution Botanical Leaf Sample Generator
Generates photorealistic serrated plant leaves with authentic venation,
chlorophyll texture, and Iraqi-climate stress signatures.

Academic Affiliation: Middle Technical University / Polytechnic College
Project Manager: Ali Nihad Qadir (علي نهاد قادر)
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import cv2
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def ensure_samples_dir() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    samples_dir = base_dir / "static" / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    return samples_dir


def _draw_leaf_blade(
    canvas: np.ndarray,
    cx: int,
    cy: int,
    length: int,
    width_ratio: float,
    angle_deg: float,
    base_color_bgr: tuple,
) -> np.ndarray:
    """
    Draw a cordate/lanceolate leaf blade with serrated margin using a
    parametric spline approximation rendered as a filled polygon.
    Returns a mask of the drawn leaf region.
    """
    h, w = canvas.shape[:2]
    pts: list = []
    n_pts = 300
    for i in range(n_pts):
        t = (i / n_pts) * 2 * math.pi
        # Lanceolate base shape
        sin_t = math.sin(t)
        cos_t = math.cos(t)
        sin_half = math.sin(t / 2.0)
        cos_half = math.cos(t / 2.0)
        abs_sin_half = abs(sin_half)

        r_w = (length * width_ratio / 2.0) * sin_t

        # Add serrations: high-frequency perturbation on margin
        n_serr = 24
        serr_amp = length * 0.025
        serration = serr_amp * math.sin(n_serr * t)

        # Leaf tip taper – use abs to avoid complex numbers from fractional power
        tip_factor = abs_sin_half ** 0.6

        x_raw = r_w * tip_factor + serration * cos_t
        # Midrib: use abs_cos_half ** 1.3 safely
        abs_cos_half = abs(cos_half)
        y_raw = (-(length / 2.0) * (abs_cos_half ** 1.3) * tip_factor
                 + serration * sin_t)

        # Rotate
        angle_rad = math.radians(angle_deg)
        x_rot = x_raw * math.cos(angle_rad) - y_raw * math.sin(angle_rad)
        y_rot = x_raw * math.sin(angle_rad) + y_raw * math.cos(angle_rad)

        pts.append([int(cx + x_rot), int(cy + y_rot)])

    poly = np.array(pts, dtype=np.int32).reshape(-1, 1, 2)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(canvas, [poly], base_color_bgr)
    cv2.fillPoly(mask, [poly], 255)
    return mask


def _draw_venation(
    canvas: np.ndarray,
    cx: int,
    cy: int,
    length: int,
    width_ratio: float,
    angle_deg: float,
    vein_color_bgr: tuple,
):
    """
    Draw primary midrib, secondary veins, and tertiary capillary venation.
    """
    angle_rad = math.radians(angle_deg)

    def rot(dx, dy):
        return (
            int(cx + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)),
            int(cy + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)),
        )

    # Primary midrib
    base_pt = rot(0, length // 2 - 10)
    tip_pt = rot(0, -(length // 2) + 15)
    cv2.line(canvas, base_pt, tip_pt, vein_color_bgr, 3, cv2.LINE_AA)

    # Secondary veins (bilateral, alternating)
    n_secondary = 10
    for i in range(n_secondary):
        t = (i + 0.5) / n_secondary
        y_mid = (length // 2 - 10) - int(t * (length - 25))
        # Half-width at this position (elliptic taper)
        hw = int((length * width_ratio / 2) * math.sin(t * math.pi) * 0.82)

        for side in [-1, 1]:
            x_start = 0
            x_end = side * hw
            y_droop = int(hw * 0.25 * side)  # slight downward droop

            p1 = rot(x_start, y_mid)
            p2 = rot(x_end, y_mid + y_droop)
            cv2.line(canvas, p1, p2, vein_color_bgr, 1, cv2.LINE_AA)

            # Tertiary capillaries from secondary
            for k in range(4):
                frac = (k + 1) / 5.0
                px = int(x_start + frac * (x_end - x_start))
                py = int(y_mid + frac * y_droop)
                tx = int(px + side * 18)
                ty = int(py - 8 + k * 5)
                cv2.line(canvas, rot(px, py), rot(tx, ty), vein_color_bgr, 1, cv2.LINE_AA)


def _add_cellular_texture(
    canvas: np.ndarray,
    mask: np.ndarray,
    h_center: float,
    v_offset: float = 0.0,
    intensity: float = 1.0,
):
    """
    Apply organic chlorophyll variation gradient and subtle specular highlight
    inside the leaf mask to simulate cellular photosynthetic zones.
    """
    h, w = canvas.shape[:2]
    # Create a radial gradient texture layer
    Y, X = np.mgrid[0:h, 0:w]
    dist = np.sqrt((X - w * h_center) ** 2 + (Y - h // 2 + v_offset) ** 2)
    max_dist = np.sqrt(w ** 2 + h ** 2)
    # Normalise to [0, 1]
    norm = (dist / max_dist).astype(np.float32)
    # Soft Gaussian-like variation: darker at edges, lighter midrib zone
    grad = (np.exp(-norm * 3.0) * 40 * intensity).astype(np.int16)

    for c in range(3):
        ch = canvas[:, :, c].astype(np.int16)
        ch[mask > 0] += grad[mask > 0]
        canvas[:, :, c] = np.clip(ch, 0, 255).astype(np.uint8)

    # Subtle specular highlight (top-left corner of leaf)
    spec_center = (int(w * 0.38), int(h * 0.30))
    spec_layer = np.zeros_like(canvas)
    cv2.ellipse(spec_layer, spec_center, (60, 35), -25, 0, 360, (30, 30, 30), -1)
    spec_layer = cv2.GaussianBlur(spec_layer, (61, 61), 25)
    canvas[mask > 0] = np.clip(
        canvas[mask > 0].astype(np.int16) + spec_layer[mask > 0].astype(np.int16) * 0.5,
        0, 255
    ).astype(np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 1 – Iraqi Dust Accumulation
# ─────────────────────────────────────────────────────────────────────────────

def create_dusty_leaf_image(output_path: Path):
    """
    Realistic green leaf partially covered by granular ochre-gray Iraqi dust
    storm silt particles. Dust Accumulation scenario.
    """
    rng = np.random.default_rng(seed=42)
    width, height = 720, 720
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    # Deep shadowed background
    canvas[:] = (22, 20, 16)

    cx, cy = 360, 370
    length = 480
    angle_deg = -15.0

    # ── Base healthy leaf blade ──
    base_green = (28, 148, 42)          # BGR vivid chlorophyll green
    mask = _draw_leaf_blade(canvas, cx, cy, length, 0.48, angle_deg, base_green)

    # ── Secondary chlorophyll gradient zone ──
    inner_mask = _draw_leaf_blade(
        canvas.copy(), cx + 12, cy - 18, int(length * 0.78), 0.40, angle_deg, (35, 168, 52)
    )
    blend = canvas.copy()
    cv2.fillPoly(blend, [np.array(
        [[cx + 12, cy - 18]], dtype=np.int32
    )], (35, 168, 52))

    # Apply cellular texture
    _add_cellular_texture(canvas, mask, h_center=0.50, v_offset=30, intensity=1.2)

    # ── Primary venation network ──
    _draw_venation(canvas, cx, cy, length, 0.48, angle_deg, (18, 105, 28))

    # ── Petiole stem ──
    stem_tip = (int(cx + 0), int(cy + length // 2 - 5))
    stem_base = (int(cx + 10), int(cy + length // 2 + 55))
    cv2.line(canvas, stem_tip, stem_base, (16, 88, 24), 5, cv2.LINE_AA)

    # ── Iraqi dust silt layer ──
    # Primary dust coverage: coarse ochre-gray (kaolinite color BGR ≈ 110, 145, 175)
    dust_color = (110, 148, 178)
    dust_canvas = canvas.copy()

    # Draw dust as irregular polygon patches simulating settled silt
    dust_mask = np.zeros((height, width), dtype=np.uint8)
    # Main dust body covers ~70% of leaf
    dust_poly_pts = []
    n_dust_pts = 120
    for i in range(n_dust_pts):
        t = (i / n_dust_pts) * 2 * math.pi
        r = (length * 0.30 + rng.uniform(-20, 20) * abs(math.sin(t * 3)))
        r2 = (length * 0.22 * abs(math.cos(t * 0.5)))
        x_d = int(cx + (r + r2) * math.cos(t) * 0.75)
        y_d = int(cy + (r + r2) * math.sin(t) * 0.60 - 20)
        dust_poly_pts.append([x_d, y_d])
    dust_poly = np.array(dust_poly_pts, dtype=np.int32)
    cv2.fillPoly(dust_canvas, [dust_poly], dust_color)
    cv2.fillPoly(dust_mask, [dust_poly], 255)

    # Clip dust to leaf boundary
    dust_mask = cv2.bitwise_and(dust_mask, mask)

    # Add fine-grained particulate noise on dust region
    noise = rng.normal(0, 14, (height, width, 3)).astype(np.int16)
    noisy_dust = np.clip(dust_canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Blend: 80% dust, 20% original green visible underneath
    canvas[dust_mask > 0] = cv2.addWeighted(
        canvas[dust_mask > 0], 0.20,
        noisy_dust[dust_mask > 0], 0.80,
        0
    )

    # Scatter individual granular dust particles (fine silt specks)
    n_specks = 2200
    speck_xs = rng.integers(0, width, n_specks)
    speck_ys = rng.integers(0, height, n_specks)
    for sx, sy in zip(speck_xs, speck_ys):
        if mask[sy, sx] > 0:
            color_var = (
                int(np.clip(110 + rng.integers(-25, 25), 60, 190)),
                int(np.clip(148 + rng.integers(-25, 25), 100, 210)),
                int(np.clip(178 + rng.integers(-25, 25), 130, 230)),
            )
            radius = rng.integers(1, 4)
            cv2.circle(canvas, (int(sx), int(sy)), int(radius), color_var, -1, cv2.LINE_AA)

    # Slight Gaussian blur to fuse dust naturally
    blurred = cv2.GaussianBlur(canvas, (5, 5), 1.2)
    canvas[mask > 0] = cv2.addWeighted(canvas[mask > 0], 0.60, blurred[mask > 0], 0.40, 0)

    cv2.imwrite(str(output_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
    size_kb = output_path.stat().st_size // 1024
    print(f"[OK] Generated: {output_path.name} ({size_kb} KB) - Dust Accumulation leaf")


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 2 – Root Water Stress / Chlorosis
# ─────────────────────────────────────────────────────────────────────────────

def create_water_stressed_leaf_image(output_path: Path):
    """
    Realistic leaf showing interveinal chlorosis yellowing and dry marginal
    necrosis (brown tips). Root Water Stress scenario.
    """
    rng = np.random.default_rng(seed=17)
    width, height = 720, 720
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[:] = (25, 22, 18)

    cx, cy = 355, 375
    length = 490
    angle_deg = 12.0

    # ── Base chlorotic yellow blade (severe water stress color) ──
    chlorosis_yellow = (18, 195, 235)   # BGR vivid amber-yellow
    mask = _draw_leaf_blade(canvas, cx, cy, length, 0.46, angle_deg, chlorosis_yellow)

    # ── Add interveinal green patches (residual chlorophyll islands) ──
    green_patches = [
        (cx - 60, cy + 80, 55, 80),
        (cx + 45, cy + 110, 40, 65),
        (cx - 30, cy + 170, 35, 55),
    ]
    for (px, py, pax, pay) in green_patches:
        green_region_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.ellipse(green_region_mask, (px, py), (pax, pay), angle_deg, 0, 360, 255, -1)
        green_region_mask = cv2.bitwise_and(green_region_mask, mask)
        if green_region_mask.any():
            # Create a solid green patch canvas
            green_patch = np.zeros_like(canvas)
            cv2.ellipse(green_patch, (px, py), (pax, pay), angle_deg, 0, 360, (30, 145, 42), -1)
            # Blend existing (yellow) with green patch 60/40
            canvas_copy = canvas.copy()
            blended = cv2.addWeighted(canvas_copy, 0.40, green_patch, 0.60, 0)
            canvas[green_region_mask > 0] = blended[green_region_mask > 0]

    # ── Apply cellular texture (reduced, simulates drought) ──
    _add_cellular_texture(canvas, mask, h_center=0.52, v_offset=-20, intensity=0.7)

    # ── Dry necrotic margins (crisp brown: BGR 20, 68, 135) ──
    necrosis_brown = (20, 68, 135)
    necrotic_regions = [
        # Leaf apex
        (int(cx + 5 * math.sin(math.radians(angle_deg))),
         int(cy - length // 2 + 30),
         (55, 75)),
        # Right margin
        (int(cx + length * 0.25 * math.sin(math.radians(angle_deg + 90))),
         int(cy - length * 0.15),
         (35, 55)),
        # Left upper margin
        (int(cx - length * 0.28 * math.sin(math.radians(angle_deg + 90))),
         int(cy - length * 0.10),
         (30, 48)),
    ]
    for (nx, ny, (nax, nay)) in necrotic_regions:
        necr_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.ellipse(canvas, (nx, ny), (nax, nay), angle_deg + 20, 0, 360, necrosis_brown, -1)
        cv2.ellipse(necr_mask, (nx, ny), (nax, nay), angle_deg + 20, 0, 360, 255, -1)
        necr_mask = cv2.bitwise_and(necr_mask, mask)
        canvas[necr_mask > 0] = necrosis_brown

    # ── Desiccated vein system (pale tan) ──
    _draw_venation(canvas, cx, cy, length, 0.46, angle_deg, (14, 58, 112))

    # ── Petiole ──
    angle_rad = math.radians(angle_deg)
    s_tip = (int(cx + 0 * math.cos(angle_rad) - (length // 2 - 5) * math.sin(angle_rad)),
              int(cy + 0 * math.sin(angle_rad) + (length // 2 - 5) * math.cos(angle_rad)))
    s_base = (int(s_tip[0] - 12), int(s_tip[1] + 60))
    cv2.line(canvas, s_tip, s_base, (14, 52, 100), 5, cv2.LINE_AA)

    # ── Wilting texture: subtle noise to simulate desiccation wrinkle ──
    noise = rng.normal(0, 8, (height, width, 3)).astype(np.int16)
    canvas_noisy = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    canvas[mask > 0] = cv2.addWeighted(canvas[mask > 0], 0.75, canvas_noisy[mask > 0], 0.25, 0)

    cv2.imwrite(str(output_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
    size_kb = output_path.stat().st_size // 1024
    print(f"[OK] Generated: {output_path.name} ({size_kb} KB) - Root Water Stress leaf")


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 3 – Healthy Irrigated Control Leaf
# ─────────────────────────────────────────────────────────────────────────────

def create_healthy_leaf_image(output_path: Path):
    """
    Vibrant healthy irrigated leaf with full chlorophyll, crisp venation,
    rich glossy surface, and no stress indicators.
    """
    rng = np.random.default_rng(seed=99)
    width, height = 720, 720
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[:] = (18, 26, 14)   # Dark green botanical background

    cx, cy = 360, 365
    length = 495
    angle_deg = -8.0

    # ── Deep vibrant healthy leaf ──
    healthy_green = (22, 162, 48)  # BGR deep chlorophyll green
    mask = _draw_leaf_blade(canvas, cx, cy, length, 0.50, angle_deg, healthy_green)

    # ── Inner lighter mesophyll zone ──
    inner_pts: list = []
    for i in range(200):
        t = (i / 200) * 2 * math.pi
        r = length * 0.32
        xi = int(cx + r * 0.72 * math.cos(t))
        yi = int(cy + r * 0.45 * math.sin(t) - 10)
        inner_pts.append([xi, yi])
    inner_poly = np.array(inner_pts, dtype=np.int32)
    inner_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(canvas, [inner_poly], (28, 185, 55))
    cv2.fillPoly(inner_mask, [inner_poly], 255)

    # ── Rich cellular texture + specular gloss ──
    _add_cellular_texture(canvas, mask, h_center=0.48, v_offset=25, intensity=1.6)

    # ── Full healthy venation: dark green ──
    _draw_venation(canvas, cx, cy, length, 0.50, angle_deg, (12, 110, 28))

    # ── Petiole ──
    angle_rad = math.radians(angle_deg)
    s_tip = (int(cx + 0 * math.cos(angle_rad) - (length // 2 - 5) * math.sin(angle_rad)),
              int(cy + 0 * math.sin(angle_rad) + (length // 2 - 5) * math.cos(angle_rad)))
    s_base = (int(s_tip[0] - 8), int(s_tip[1] + 65))
    cv2.line(canvas, s_tip, s_base, (12, 95, 22), 6, cv2.LINE_AA)

    # ── Soft Gaussian polish ──
    blurred = cv2.GaussianBlur(canvas, (3, 3), 0.8)
    canvas[mask > 0] = cv2.addWeighted(canvas[mask > 0], 0.72, blurred[mask > 0], 0.28, 0)

    # ── Fine surface dewdrop / glossy noise ──
    dew_noise = rng.normal(0, 5, (height, width, 3)).astype(np.int16)
    canvas = np.clip(canvas.astype(np.int16) + dew_noise, 0, 255).astype(np.uint8)

    cv2.imwrite(str(output_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
    size_kb = output_path.stat().st_size // 1024
    print(f"[OK] Generated: {output_path.name} ({size_kb} KB) - Healthy Control leaf")


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 4 – Garden Turfgrass / Lawn Scorch
# ─────────────────────────────────────────────────────────────────────────────

def create_turfgrass_sample_image(output_path: Path):
    """
    Simulate a garden lawn / turfgrass sample with a blend of green grass
    and scorched yellow-brown patches typical of heat stress in Baghdad.
    """
    rng = np.random.default_rng(seed=101)
    width, height = 720, 720
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    # Base green turf
    canvas[:] = (25, 120, 45)

    # Add thousands of fine grass blades
    for _ in range(8000):
        gx = int(rng.integers(0, width))
        gy = int(rng.integers(0, height))
        blade_len = int(rng.integers(12, 35))
        angle = rng.uniform(-0.4, 0.4)
        ex = int(gx + blade_len * math.sin(angle))
        ey = int(gy - blade_len * math.cos(angle))
        color = (
            int(rng.integers(18, 35)),
            int(rng.integers(90, 165)),
            int(rng.integers(30, 65)),
        )
        cv2.line(canvas, (gx, gy), (ex, ey), color, 1, cv2.LINE_AA)

    # Add scorched brown/yellow drought patches
    for cx, cy, r1, r2, ang in [
        (260, 320, 140, 90, 25),
        (480, 420, 110, 80, -35),
        (380, 200, 80, 60, 10),
    ]:
        overlay = canvas.copy()
        cv2.ellipse(overlay, (cx, cy), (r1, r2), ang, 0, 360, (28, 95, 145), -1)
        cv2.GaussianBlur(overlay, (55, 55), 25, dst=overlay)
        canvas = cv2.addWeighted(canvas, 0.45, overlay, 0.55, 0)

    # Granular soil noise
    noise = rng.normal(0, 7, (height, width, 3)).astype(np.int16)
    canvas = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    cv2.imwrite(str(output_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    size_kb = output_path.stat().st_size // 1024
    print(f"[OK] Generated: {output_path.name} ({size_kb} KB) - Turfgrass Scorch sample")


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE 5 – Soil & Bare Ground Salinity (الشورة والسبخة)
# ─────────────────────────────────────────────────────────────────────────────

def create_soil_salinity_sample_image(output_path: Path):
    """
    Simulate compacted bare soil with white/pale salt crust efflorescence
    (الشورة والسبخة) and micro-cracks under arid Iraqi sun.
    """
    rng = np.random.default_rng(seed=202)
    width, height = 720, 720
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    # Earthy silt baseline (ochre-brown)
    canvas[:] = (65, 95, 125)

    # Add silt texture variations
    noise_silt = rng.normal(0, 15, (height, width, 3)).astype(np.int16)
    canvas = np.clip(canvas.astype(np.int16) + noise_silt, 0, 255).astype(np.uint8)

    # Draw salt efflorescence / white crystalline crust
    salt_mask = np.zeros((height, width), dtype=np.uint8)
    for _ in range(45):
        sx = int(rng.integers(60, width - 60))
        sy = int(rng.integers(60, height - 60))
        sr1 = int(rng.integers(25, 90))
        sr2 = int(rng.integers(15, 60))
        sang = rng.uniform(0, 180)
        cv2.ellipse(salt_mask, (sx, sy), (sr1, sr2), sang, 0, 360, 255, -1)

    salt_mask = cv2.GaussianBlur(salt_mask, (31, 31), 15)
    # White crystalline crust (high L, near gray-white)
    white_salt = np.full_like(canvas, 215)
    for c in range(3):
        alpha = (salt_mask.astype(np.float32) / 255.0) * 0.72
        canvas[:, :, c] = (canvas[:, :, c] * (1.0 - alpha) + white_salt[:, :, c] * alpha).astype(np.uint8)

    # Draw shrinkage micro-cracks
    for _ in range(25):
        pt1 = (int(rng.integers(30, width - 30)), int(rng.integers(30, height - 30)))
        curr = pt1
        for _ in range(rng.integers(4, 9)):
            nxt = (
                int(np.clip(curr[0] + rng.integers(-40, 40), 10, width - 10)),
                int(np.clip(curr[1] + rng.integers(-40, 40), 10, height - 10)),
            )
            cv2.line(canvas, curr, nxt, (30, 45, 60), 2, cv2.LINE_AA)
            curr = nxt

    cv2.imwrite(str(output_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    size_kb = output_path.stat().st_size // 1024
    print(f"[OK] Generated: {output_path.name} ({size_kb} KB) - Soil Salinity sample")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import sys
    import io
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    samples_dir = ensure_samples_dir()
    sep = "-" * 55
    print(sep)
    print("EcoSensing AI - Agro-Ecological Sample Generator")
    print("Generating high-resolution realistic multi-scene samples...")
    print(sep)

    create_dusty_leaf_image(samples_dir / "iraqi_dust_leaf.jpg")
    create_water_stressed_leaf_image(samples_dir / "water_stress_leaf.jpg")
    create_healthy_leaf_image(samples_dir / "healthy_control_leaf.jpg")
    create_turfgrass_sample_image(samples_dir / "turfgrass_sample.jpg")
    create_soil_salinity_sample_image(samples_dir / "soil_salinity_sample.jpg")

    print(sep)
    print("[OK] All 5 multi-scene samples generated successfully.")
    print(f"     Directory: {samples_dir}")
    print(sep)


if __name__ == "__main__":
    main()
