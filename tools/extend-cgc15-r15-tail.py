"""Continue the three cropped R15 locks below their original image boundary.

The original RGBA rectangle is copied byte for byte.  Only the off-canvas
continuation is synthesized from the trailing native colour cross sections.
No stage, rig, or central tracing document is changed by this helper.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d, map_coordinates


DEFAULT_STAGE = Path(
    "../../工作文件夹/output/CGC14-15_scene4/"
    "头发逐层重拆/CGC15/stage-15-R15-lower-long-tail-circled-native-v2"
)
PART = "15-R15-lower-long-tail"


def row_runs(alpha: np.ndarray) -> list[tuple[int, int]]:
    changes = np.diff(np.r_[False, alpha > 127, False].astype(np.int8))
    return list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))


def subpixel_edges(alpha: np.ndarray, left: int, right: int) -> tuple[float, float]:
    """Locate the 50% coverage boundary without quantizing it to whole pixels."""
    a = alpha.astype(np.float64) / 255.0
    l0 = max(0, left - 1)
    r0 = min(len(a) - 1, right)
    left_edge = l0 + (0.5 - a[l0]) / max(a[left] - a[l0], 1e-6)
    right_edge = right - 1 + (a[right - 1] - 0.5) / max(a[right - 1] - a[r0], 1e-6)
    return left_edge, right_edge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--height", type=int, default=1600)
    args = parser.parse_args()
    source_path = args.stage / f"{PART}-native.png"
    source = np.array(Image.open(source_path).convert("RGBA"))
    source_h, width = source.shape[:2]
    if args.height <= source_h:
        raise ValueError("The destination height must exceed the native image height.")

    # Each of the final native rows contains the same three disconnected locks.
    # Use their actual alpha boundaries, including the narrow left side branch.
    y0 = source_h - 70
    native_rows = np.arange(y0, source_h)
    run_rows = [row_runs(source[y, :, 3]) for y in native_rows]
    if any(len(runs) != 3 for runs in run_rows):
        raise ValueError("Expected three continuous hair cross sections in the final 70 rows.")

    result = np.zeros((args.height, width, 4), dtype=np.uint8)
    result[:source_h] = source
    profiles_u = np.linspace(0.0, 1.0, 512)
    strand_evidence = []

    for strand in range(3):
        edges = np.array([
            subpixel_edges(source[y, :, 3], *runs[strand])
            for y, runs in zip(native_rows, run_rows)
        ])
        centers = edges.mean(axis=1)
        widths = edges[:, 1] - edges[:, 0]
        # A local tangent follows the bend at the crop.  The downstream tangent
        # gradually turns downward, keeping the continuation inside the wider
        # safe canvas rather than introducing a second cut at the right edge.
        fit_rows = 12
        tangent = float(np.polyfit(np.arange(-fit_rows + 1, 1), centers[-fit_rows:], 1)[0])
        final_tangent = min(tangent, (0.55, 0.65, 0.72)[strand])
        curve_length = (190.0, 170.0, 150.0)[strand]
        target_width = widths[-1] * (0.86, 0.70, 0.82)[strand]

        # Register native colour profiles into each strand's own cross section.
        # A damped derivative continues the painted highlight and shadow bands;
        # a bounded colour change prevents flat repeats or unbounded RGB drift.
        profiles = []
        for y, (left, right) in zip(native_rows, edges):
            sample_x = left + profiles_u * (right - left)
            profiles.append(np.stack([
                map_coordinates(source[y, :, channel].astype(float), [sample_x], order=1, mode="nearest")
                for channel in range(3)
            ], axis=1))
        profiles = np.asarray(profiles)
        last_profile = profiles[-1]
        recent = gaussian_filter1d(profiles[-7:].mean(axis=0), 1.3, axis=0)
        preceding = gaussian_filter1d(profiles[-30:-20].mean(axis=0), 1.3, axis=0)
        colour_rate = (recent - preceding) / 22.0
        colour_change = np.clip(colour_rate * 54.0, -18.0, 18.0)
        # Preserve the fine native marks at the seam, then smoothly relax their
        # intensity within the extrapolated area.  There is no repeated tile.
        profile_base = gaussian_filter1d(last_profile, 0.65, axis=0)
        seam_detail = last_profile - profile_base

        for y in range(source_h, args.height):
            distance = float(y - source_h + 1)
            center = centers[-1] + final_tangent * distance + (
                tangent - final_tangent
            ) * curve_length * (1.0 - np.exp(-distance / curve_length))
            span = target_width + (widths[-1] - target_width) * np.exp(-distance / 210.0)
            left, right = center - span / 2, center + span / 2
            first = max(0, int(np.floor(left)) - 1)
            last = min(width - 1, int(np.ceil(right)) + 1)
            if first > last:
                continue
            xs = np.arange(first, last + 1)
            u = np.clip((xs - left) / span, 0.0, 1.0)
            # Pixel coverage produces a smooth alpha edge at fractional positions.
            alpha = np.minimum(np.clip(xs - left + 0.5, 0, 1), np.clip(right - xs + 0.5, 0, 1))
            profile = profile_base + seam_detail * np.exp(-distance / 110.0) + (
                colour_change * (1.0 - np.exp(-distance / 54.0))
            )
            rgb = np.stack([
                np.interp(u, profiles_u, profile[:, channel]) for channel in range(3)
            ], axis=1)
            out = result[y, first:last + 1]
            out[:, :3] = np.round(np.clip(rgb, 0, 255)).astype(np.uint8)
            out[:, 3] = np.round(alpha * 255).astype(np.uint8)

        strand_evidence.append({
            "strand_index_left_to_right": strand,
            "native_bottom_edges": edges[-1].tolist(),
            "initial_dx_dy": tangent,
            "downstream_dx_dy": final_tangent,
            "curve_relaxation_px": curve_length,
            "native_bottom_width": float(widths[-1]),
            "asymptotic_width": float(target_width),
        })

    image_path = args.stage / f"{PART}-native-extended.png"
    mask_path = args.stage / f"{PART}-extended-mask.png"
    Image.fromarray(result, "RGBA").save(image_path)
    Image.fromarray(result[:, :, 3], "L").save(mask_path)
    if not np.array_equal(np.array(Image.open(image_path))[:source_h], source):
        raise AssertionError("Native RGBA pixels changed.")

    # A neutral background exposes accidental holes, colour contamination, or
    # a false pointed end.  Both the native seam and the full extension are shown.
    gray = Image.new("RGBA", (width, args.height), (112, 112, 112, 255))
    gray.alpha_composite(Image.open(image_path))
    gray.convert("RGB").crop((840, 850, 1820, args.height)).save(
        args.stage / "R15-extension-gray-check.jpg", quality=96
    )
    gray.convert("RGB").crop((900, 1000, 1320, 1180)).resize((1260, 540)).save(
        args.stage / "R15-extension-seam-check.jpg", quality=96
    )
    main_strand = strand_evidence[2]
    suggested_chain = [[944, 888.5], [970, 940], [1006, 996], [1053, 1044], [1110, 1080]]
    for chain_y in (1160, 1260, 1420, args.height):
        distance = float(chain_y - source_h)
        tangent = main_strand["initial_dx_dy"]
        downstream = main_strand["downstream_dx_dy"]
        relaxation = main_strand["curve_relaxation_px"]
        chain_x = 1110 + downstream * distance + (tangent - downstream) * relaxation * (
            1.0 - np.exp(-distance / relaxation)
        )
        suggested_chain.append([round(chain_x, 2), chain_y])
    evidence = {
        "source": str(source_path),
        "image": str(image_path),
        "mask": str(mask_path),
        "size": [width, args.height],
        "unchanged_native_rgba_rectangle": [0, 0, width, source_h],
        "native_rgba_exact": True,
        "method": "three independent native cross-section continuations; damped curved flow and bounded colour derivative; no pointed artificial ends",
        "strands": strand_evidence,
        "suggested_chain": suggested_chain,
    }
    (args.stage / "R15-extension.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
