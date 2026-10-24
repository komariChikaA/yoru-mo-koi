"""Render the ordered hair-redo stages with a real Godot renderer.

Repeat --layer for preceding foreground stages, in front-to-back order. The
--stage plate is the newest repaired background. Native cutouts stay external.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GODOT = Path('D:/software/Godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--layer', type=Path, action='append', default=[])
    parser.add_argument('--out', type=Path, required=True, help='Output stem without extension')
    parser.add_argument('--cg', type=int, choices=[14, 15], required=True)
    parser.add_argument('--crop', default='')
    parser.add_argument('--strength', type=float, default=1)
    parser.add_argument('--seconds', type=float, help='CGC14 defaults to 5.6s; CGC15 uses the slower 9.2s cycle')
    parser.add_argument('--samples', default='', help='Snapshot times; omits continuous video')
    args = parser.parse_args()
    if args.seconds is None:
        args.seconds = 5.6 if args.cg == 14 else 9.2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    work = args.out.parent / (args.out.name+'-render')
    work.mkdir(exist_ok=True)
    parts, overlays, seen = [], [], set()
    policy = json.loads((ROOT/'godot/chorus-four/hair-redo/user-grouping.json').read_text(encoding='utf-8-sig'))
    for stage in args.layer+[args.stage]:
        stage = stage.resolve()
        record = json.loads((stage/'stage.json').read_text(encoding='utf-8-sig'))
        for original in record['parts']:
            part = dict(original)
            if part['id'] in seen:
                continue
            seen.add(part['id'])
            texture = Path(part.get('native_texture', part['id']+'-native.png'))
            part['native_texture'] = str(texture if texture.is_absolute() else stage/texture)
            part['motion_gain'] = policy.get('motion_gain_by_id', {}).get(part['id'], part.get('motion_gain', 1))
            part.setdefault('deformation_model', policy.get('deformation_by_id', {}).get(part['id'], 'skeleton'))
            part.setdefault('sway_percent', 15 if args.cg == 14 else 10)
            reference = policy.get('reference_by_id', {}).get(part['id'], {})
            part['reference_amplitude_deg'] = reference.get('amplitude_deg', 0.45*part['sway_percent'])
            part['reference_lag'] = reference.get('lag', 0.28)
            parts.append(part)
        for original in record.get('static_overlays', []):
            if isinstance(original, str):
                path = Path(original)
                overlay = str(path if path.is_absolute() else stage/path)
            else:
                overlay = dict(original)
                key = 'path' if 'path' in overlay else 'texture'
                path = Path(overlay[key])
                overlay[key] = str(path if path.is_absolute() else stage/path)
            if overlay not in overlays:
                overlays.append(overlay)
    record.update(parts=parts, static_overlays=overlays)
    (work/'stage.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copyfile(args.stage/'repaired-plate.png', work/'repaired-plate.png')
    frames = work/'frames'
    command = [str(GODOT), '--path', str(ROOT/'godot/chorus-four'), '--audio-driver', 'Dummy', '--disable-render-loop',
        '--script', 'res://hair-redo/preview.gd', '--', '--stage', str(work),
        '--cg', str(args.cg), '--frames', str(frames), '--seconds', str(args.seconds),
        '--strength', str(args.strength)]
    if args.crop:
        command += ['--crop', args.crop]
    if args.samples:
        command += ['--samples', args.samples]
    with (work/'stdout.log').open('w', encoding='utf-8') as stdout, (work/'stderr.log').open('w', encoding='utf-8') as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW)
    errors = (work/'stderr.log').read_text(encoding='utf-8')
    if result.returncode or any(x in errors for x in ['SCRIPT ERROR:', 'SHADER ERROR:', 'ERROR:']):
        raise RuntimeError(f'Godot render failed; see {work}/stderr.log: {errors[:1500]}')
    samples = [float(x) for x in args.samples.split(',')] if args.samples else []
    count = len(samples) if samples else round(args.seconds*60)
    frame_files = [frames/f'frame-{i:04d}.png' for i in range(count)]
    if not all(path.exists() for path in frame_files):
        raise RuntimeError(f'Incomplete capture in {frames}')
    if not samples:
        video = args.out.with_suffix('.mp4')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '60',
            '-i', str(frames/'frame-%04d.png'), '-frames:v', str(count), '-c:v', 'libx264',
            '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
        indices = [round(i*(count-1)/7) for i in range(8)]
    else:
        indices = list(range(count))
    width, height = 640, 360
    rows = (len(indices)+3)//4
    montage = Image.new('RGB', (4*width, rows*(height+26)), '#202020')
    draw = ImageDraw.Draw(montage)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 17)
    for cell, index in enumerate(indices):
        x, y = (cell%4)*width, (cell//4)*(height+26)
        source = Image.open(frame_files[index]).convert('RGB')
        source.thumbnail((width, height), Image.Resampling.LANCZOS)
        montage.paste(source, (x+(width-source.width)//2, y+26+(height-source.height)//2))
        time = samples[index] if samples else index/60
        draw.text((x+8, y+2), f'{time:.2f}s | 参考重做 ×{args.strength:g}', font=font, fill='white')
    montage.save(args.out.parent/(args.out.name+'-检查.jpg'), quality=95)
    proof = None
    for line in (work/'stdout.log').read_text(encoding='utf-8').splitlines():
        if line.startswith('SHORT_PREVIEW_PROOF '):
            proof = json.loads(line.removeprefix('SHORT_PREVIEW_PROOF '))
    summary = dict(cg=args.cg, stages=[str(p) for p in args.layer+[args.stage]],
        parts=[p['id'] for p in parts], strength=args.strength, seconds=args.seconds,
        wind_time_offset=policy.get('time_offset_by_cg', {}).get(str(args.cg), 0),
        motion_profile=policy.get('motion_profile', ''),
        release_fraction_by_id=policy.get('release_fraction_by_id', {}),
        gradient_solver_by_id=policy.get('gradient_solver_by_id', {}),
        pinned_return_tips=policy.get('pinned_return_tips', []),
        resolved_motion=[{key: p[key] for key in ['id', 'sway_percent', 'motion_gain',
            'deformation_model', 'bend_length_px', 'reference_amplitude_deg', 'reference_lag'] if key in p} for p in parts],
        sample_times=samples, frames=count, fps=60, proof=proof,
        scope='Local hair preview; not final perceptual 100% or production shot acceptance')
    (args.out.parent/(args.out.name+'-记录.json')).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
