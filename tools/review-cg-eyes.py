"""Review actual GPU eyelid output; keep all CG imagery local."""
import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_preview" / "cg-puppet"
BOXES = {
    "CGC14_a": (950, 115, 1178, 275),
    "CGC15_c": (547, 160, 808, 437),
    "CGC16": (480, 83, 664, 230),
}


def still(shot, closure, suffix="-eyelids-fixed"):
    return Image.open(next(OUT.glob(f"{shot}{suffix}-b{closure:.2f}-t*.png"))).convert("RGB")


def panel(frame, box, shot, caption):
    tile = Image.new("RGB", (420, 360), "#20232a")
    face = frame.crop(box)
    scale = min(400/face.width,315/face.height)
    face = face.resize((round(face.width*scale),round(face.height*scale)),Image.Resampling.LANCZOS)
    tile.paste(face, ((420-face.width)//2, 35+(315-face.height)//2))
    ImageDraw.Draw(tile).text((12, 10), f"{shot}  {caption}", fill="white")
    return tile


def run(*args):
    subprocess.run(args, check=True)


def clip_tiles(shot, suffix, caption):
    cap = cv2.VideoCapture(str(OUT / (shot+suffix+".mp4")))
    if int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) != 360:
        raise RuntimeError(f"Incomplete clip: {shot}{suffix}")
    tiles = []
    for index in range(84,111):
        cap.set(cv2.CAP_PROP_POS_FRAMES,index)
        ok,frame = cap.read()
        if not ok:
            raise RuntimeError(f"Frame decode failed: {shot} {index}")
        tiles.append(panel(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)),BOXES[shot],shot,caption))
    cap.release()
    return tiles


def review(suffix="-eyelids-fixed", only_shot=None, before_suffix="-eyelids"):
    boxes = {only_shot: BOXES[only_shot]} if only_shot else BOXES
    tag = suffix.removeprefix("-eyelids")
    sheet = Image.new("RGB", (1260, 360*len(boxes)), "#20232a")
    report = {}
    for row, (shot, box) in enumerate(boxes.items()):
        frames = [still(shot,b,suffix) for b in [0,.5,1]]
        for col, (frame, label) in enumerate(zip(frames, ["Open", "50% closed", "Closed"])):
            sheet.paste(panel(frame, box, shot, label), (col*420, row*360))
        family = "CGC14" if shot.startswith("CGC14") else shot
        mask = Image.open(ROOT / "godot" / "cg-puppet" / "assets" / family / "eye-region.png")
        mask = np.array(mask.resize(frames[0].size)) > 0
        mask = cv2.dilate(np.uint8(mask), np.ones((9, 9), np.uint8)) > 0
        difference = np.max(np.abs(np.array(frames[0]).astype(int)-np.array(frames[-1]).astype(int)), axis=2)
        outside = int(np.count_nonzero(difference[~mask]))
        if outside:
            raise RuntimeError(f"{shot}: {outside} changed pixels outside eyelid region")
        report[shot] = dict(outside_eye_changed_pixels=outside,
                            changed_pixels=int(np.count_nonzero(difference)),
                            clip_frames=360, clip_fps=60)
        if shot == "CGC16":
            foreground = Image.open(ROOT / "godot/cg-puppet/assets/CGC16/eye-foreground.png")
            protected = np.array(foreground.resize(frames[0].size)) >= 254
            protected &= np.array(Image.open(ROOT / "godot/cg-puppet/assets/CGC16/eye-region.png").resize(frames[0].size)) >= 254
            protected = cv2.erode(np.uint8(protected),np.ones((3,3),np.uint8)) > 0
            if not np.any(protected):
                raise RuntimeError("CGC16 foreground protection check has no interior pixels")
            for frame in frames[1:]:
                delta = np.max(np.abs(np.array(frames[0]).astype(int)-np.array(frame).astype(int)),axis=2)
                if np.any(delta[protected]):
                    raise RuntimeError("CGC16 foreground hair pixels changed")
            report[shot].update(protected_hair_pixels=int(np.count_nonzero(protected)),protected_hair_changed_pixels=0)
    if only_shot is None:
        # Closed-expression CG stays exactly unchanged even with forced blink=1.
        closed_difference = np.abs(np.array(still("CGC14_c",0,suffix)).astype(int)-np.array(still("CGC14_c",1,suffix)).astype(int))
        if np.any(closed_difference):
            raise RuntimeError("CGC14_c closed expression changed")
        report["CGC14_c"] = dict(forced_blink_changed_pixels=0)
        # a/b have slightly different source pixels. Validate b independently rather
        # than demanding equal deltas from two different original paintings.
        b0,b1 = np.array(still("CGC14_b",0,suffix)).astype(int),np.array(still("CGC14_b",1,suffix)).astype(int)
        mask = np.array(Image.open(ROOT / "godot/cg-puppet/assets/CGC14/eye-region.png").resize((1280,720))) > 0
        mask = cv2.dilate(np.uint8(mask),np.ones((9,9),np.uint8)) > 0
        outside = int(np.count_nonzero(np.max(np.abs(b1-b0),axis=2)[~mask]))
        if outside:
            raise RuntimeError(f"CGC14_b: {outside} changed pixels outside eyes")
        report["CGC14_b"] = dict(outside_eye_changed_pixels=outside,own_original_iris=True)
    sheet.save(OUT / "eyes" / ("Eyelids-Open-Half-Closed"+tag+".jpg"),quality=95)
    # Enlarge a real blink from each rendered six-second clip, then slow 4x.
    slow_tiles = []
    for shot in boxes:
        slow_tiles.append(clip_tiles(shot,suffix,"4x slow / fixed iris"))
    frames_dir = OUT / "eyes" / ("slow-frames"+tag)
    frames_dir.mkdir(exist_ok=True)
    for index in range(27):
        frame = Image.new("RGB", (420*len(boxes), 360), "#20232a")
        for col, tiles in enumerate(slow_tiles):
            frame.paste(tiles[index], (col*420, 0))
        frame.save(frames_dir / f"{index:03d}.png")
    path = str(OUT / ("Eyelids-Closeup-4x"+tag+".mp4"))
    run("ffmpeg", "-v", "error", "-y", "-framerate", "15", "-i", str(frames_dir / "%03d.png"),
        "-frames:v", "27", "-an", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path)
    run("ffmpeg", "-v", "error", "-i", path, "-f", "null", "-")
    # An inline looping image makes this short movement directly reviewable.
    frames = [Image.open(frames_dir / f"{i:03d}.png") for i in range(27)]
    frames[0].save(OUT / "eyes" / ("Eyelids-Closeup-4x"+tag+".gif"),save_all=True,append_images=frames[1:],
                   duration=67, loop=0)
    if tag and "CGC16" in boxes:
        before = clip_tiles("CGC16",before_suffix,"Before / 4x slow")
        after = clip_tiles("CGC16",suffix,"After / 4x slow")
        comparison = []
        for old,new in zip(before,after):
            frame = Image.new("RGB",(840,360))
            frame.paste(old,(0,0)); frame.paste(new,(420,0))
            comparison.append(frame)
        comparison[0].save(OUT / "eyes" / ("CGC16-Before-After"+tag+".gif"),save_all=True,
                           append_images=comparison[1:],duration=67,loop=0)
        compare_dir = OUT / "eyes" / ("comparison-frames"+tag)
        compare_dir.mkdir(exist_ok=True)
        for index,frame in enumerate(comparison):
            frame.save(compare_dir / f"{index:03d}.png")
        compare_path = str(OUT / ("CGC16-Before-After"+tag+".mp4"))
        run("ffmpeg","-v","error","-y","-framerate","15","-i",str(compare_dir / "%03d.png"),
            "-frames:v","27","-an","-c:v","libx264","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart",compare_path)
        run("ffmpeg","-v","error","-i",compare_path,"-f","null","-")
    (OUT / "eyes" / ("review"+tag+".json")).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--suffix",default="-eyelids-fixed")
    parser.add_argument("--shot",choices=list(BOXES))
    parser.add_argument("--before-suffix",default="-eyelids")
    args = parser.parse_args()
    review(args.suffix,args.shot,args.before_suffix)
