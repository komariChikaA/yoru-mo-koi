"""Make review videos, actual-frame contact sheets, and measured pilot results."""
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WORKSPACE = Path(__file__).resolve().parents[1]
OUTPUT = WORKSPACE / "_preview" / "cg-puppet"
ASSETS = WORKSPACE / "godot" / "cg-puppet" / "assets"
SHOTS = ["CGC14_a", "CGC14_b", "CGC14_c", "CGC15_c", "CGC16"]


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def frame(path, seconds):
    capture = cv2.VideoCapture(str(path))
    capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    okay, pixels = capture.read()
    capture.release()
    if not okay:
        raise RuntimeError(f"Could not read {path} at {seconds}s")
    return pixels


def review():
    measurements = []
    concat = OUTPUT / "playlist.txt"
    concat.write_text("".join(f"file '{shot}.mp4'\n" for shot in SHOTS), encoding="utf-8")
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
        "-i", concat, "-c", "copy", "-movflags", "+faststart", OUTPUT / "CG-Puppet-Pilot-All.mp4")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
    for shot in SHOTS:
        video = OUTPUT / f"{shot}.mp4"
        probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames:format=duration",
            "-of", "json", str(video)], text=True))
        stream = probe["streams"][0]
        if int(stream["nb_read_frames"]) != 360 or stream["r_frame_rate"] != "60/1":
            raise AssertionError(f"Unexpected movie frame count/rate: {shot} {stream}")
        first = frame(video, 0)
        moved = frame(video, 1.0)
        last = frame(video, 359 / 60)
        flow = cv2.calcOpticalFlowFarneback(cv2.cvtColor(first, cv2.COLOR_BGR2GRAY),
                                          cv2.cvtColor(moved, cv2.COLOR_BGR2GRAY),
                                          None, .5, 3, 25, 4, 7, 1.5, 0)
        magnitude = np.linalg.norm(flow, axis=2)
        family = "CGC14" if shot.startswith("CGC14") else shot
        controls = json.loads((ASSETS.parent / "rigs.json").read_text(encoding="utf-8"))[family]["pins"]
        size = (stream["width"], stream["height"])
        union = np.zeros((1080,1920), np.uint8)
        weights = []
        for atlas in range(4):
            data = np.array(Image.open(ASSETS / family / f"weights{atlas}.png"))
            weights.extend([data[:, :, index] for index in range(3)])
            union = np.maximum(union, np.max(data, axis=2))
        static = cv2.resize(union, size, interpolation=cv2.INTER_NEAREST) == 0
        static = cv2.erode(np.uint8(static), np.ones((15,15),np.uint8)) > 0
        bg_motion = float(np.median(magnitude[static]))
        part_motion = {}
        for control, weight in zip(controls, weights):
            active = cv2.resize(weight, size, interpolation=cv2.INTER_NEAREST) > 128
            if np.any(active):
                part_motion[control["name"]] = round(float(np.median(magnitude[active])), 3)
        if bg_motion > .08:
            raise AssertionError(f"Unintended global/background movement: {shot}, {bg_motion}")
        if max(part_motion[name] for name in part_motion if "hair" in name) < .25:
            raise AssertionError(f"No measurable hair movement: {shot}")
        if max(part_motion[name] for name in part_motion if "hand" in name) < .2:
            raise AssertionError(f"No measurable hand movement: {shot}")
        # Boundary check on the decoded clip, not just the mathematical waveform.
        loop_error = float(np.mean(np.abs(first.astype(np.float32) - last.astype(np.float32))))
        measurements.append(dict(shot=shot, resolution=list(size), duration=probe["format"]["duration"],
                                 frames=360, fps=60, static_background_flow_pixels=round(bg_motion,5),
                                 part_flow_pixels=part_motion, first_last_mean_rgb_difference=round(loop_error,3)))
        sheet = Image.new("RGB", (1280, 776), (24,24,24))
        draw = ImageDraw.Draw(sheet)
        for index, at in enumerate([0.0, 1.0, 1.57, 4.55]):
            rgb = cv2.cvtColor(frame(video, at), cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb).resize((640,360), Image.Resampling.LANCZOS)
            x, y = (index % 2)*640, (index // 2)*388
            sheet.paste(image,(x,y+28))
            draw.text((x+8,y+1), f"{shot}  {at:.2f}s", fill=(255,255,255),font=font)
        sheet.save(OUTPUT / f"{shot}-frames.jpg", quality=94)
        comparison = OUTPUT / f"{shot}-compare.mp4"
        # Labels are English to avoid adding a font/runtime dependency to reproduction.
        filters = ("[0:v]scale=960:540,setsar=1,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='ORIGINAL':x=12:y=12:"
                   "fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=6[left];"
                   "[1:v]scale=960:540,setsar=1,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='" + shot + " PUPPET PILOT':x=12:y=12:"
                   "fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=6[right];"
                   "[left][right]hstack=inputs=2[v]")
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "60",
            "-i", ASSETS / f"{shot}.png", "-i", video, "-filter_complex", filters,
            "-map", "[v]", "-t", "6", "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", comparison)
        print(f"REVIEW {shot}: background flow={bg_motion:.4f}, loop RGB diff={loop_error:.3f}", flush=True)
    compare_list = OUTPUT / "compare-playlist.txt"
    compare_list.write_text("".join(f"file '{shot}-compare.mp4'\n" for shot in SHOTS), encoding="utf-8")
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
        "-i", compare_list, "-c", "copy", "-movflags", "+faststart", OUTPUT / "CG-Puppet-Original-Compare.mp4")
    for path in [OUTPUT / "CG-Puppet-Pilot-All.mp4", OUTPUT / "CG-Puppet-Original-Compare.mp4"]:
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-f", "null", "-")
    (OUTPUT / "review.json").write_text(json.dumps(measurements,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


if __name__ == "__main__":
    review()
