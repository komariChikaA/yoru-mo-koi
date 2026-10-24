"""Recolor/composite Eagle material pixels and export shot border alternatives."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageOps, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'assets/chorus-cgc06/borders'
FRAMES = ROOT / 'godot/chorus-cgc06/assets/frames'
OUT = Path('../../工作文件夹/output/CGC06_scene3')
FFMPEG = Path('D:/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe')
FFPROBE = FFMPEG.with_name('ffprobe.exe')
AUDIO = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ/audio-balanced.mp3')


def build():
    FRAMES.mkdir(parents=True, exist_ok=True)
    pigment = ImageOps.grayscale(Image.open(SOURCES / 'imagewatercolor_00388.jpg'))
    alpha = np.asarray(pigment).astype(float) / 255
    pixels = np.zeros((*alpha.shape, 4), np.uint8)
    pixels[:, :, :3] = [247, 247, 247]
    pixels[:, :, 3] = np.uint8(alpha * .88 * 255)
    blob = Image.fromarray(pixels)
    wash = Image.new('RGBA', (1920, 1080))
    # Overlap enlarged native pigment shapes so every edge has a visible border.
    top = blob.resize((2700, 480), Image.Resampling.LANCZOS)
    wash.alpha_composite(top, (-390, -315))
    wash.alpha_composite(ImageOps.mirror(top), (-270, -325))
    wash.alpha_composite(ImageOps.flip(top), (-310, 915))
    wash.alpha_composite(ImageOps.flip(ImageOps.mirror(top)), (-430, 925))
    side = blob.transpose(Image.Transpose.ROTATE_90).resize((400, 1600), Image.Resampling.LANCZOS)
    wash.alpha_composite(side, (-260, -220))
    wash.alpha_composite(ImageOps.flip(side), (-280, -300))
    wash.alpha_composite(ImageOps.mirror(side), (1780, -280))
    wash.alpha_composite(ImageOps.flip(ImageOps.mirror(side)), (1800, -200))
    # Both silhouette and small dry-brush holes come from actual Eagle pixels.
    grain = np.asarray(ImageOps.grayscale(ImageOps.fit(
        Image.open(SOURCES / 'imagewatercolor_00383.jpg'), wash.size,
        method=Image.Resampling.LANCZOS))).astype(float) / 255
    pixels = np.array(wash)
    # Retain the original pigment body below its dry-brush texture, rather than
    # cutting long transparent gaps into the outside perimeter.
    pixels[:, :, 3] = np.uint8(pixels[:, :, 3].astype(float) * (.35 + .65 * grain) * .90)
    Image.fromarray(pixels).save(FRAMES / 'wash.png')

    native_paper = np.asarray(ImageOps.fit(Image.open(SOURCES / 'imagepaper_00184.jpg').convert('RGB'),
        (1920, 1080), method=Image.Resampling.LANCZOS)).astype(float)
    paper = np.clip(native_paper / native_paper.mean((0, 1)) * [87, 60, 46], 0, 255).astype(np.uint8)
    rectangle = np.dstack((paper, np.full((1080, 1920), 255, np.uint8)))
    rectangle[42:-42, 42:-42, 3] = 0
    Image.fromarray(rectangle).filter(ImageFilter.GaussianBlur(.65)).save(FRAMES / 'cocoa-rectangle.png')

    # Recolor the same Eagle paper to white while retaining its native fibers.
    gray = native_paper.mean(2)
    white = np.clip(247 + (gray / gray.mean() - 1) * 38, 0, 255).astype(np.uint8)
    rectangle[:, :, :3] = white[:, :, None]
    Image.fromarray(rectangle).filter(ImageFilter.GaussianBlur(.65)).save(FRAMES / 'white-rectangle.png')


def run(args):
    subprocess.run([str(FFMPEG), '-hide_banner', '-v', 'error', '-y', *map(str, args)], check=True)


def export(selected='all'):
    OUT.mkdir(parents=True, exist_ok=True)
    # Final production scene3 now includes the selected frame and particles.
    # Alternate-border previews must use the preserved clean GPU baselines.
    baseline = OUT / 'scene3-no-border-no-particles.avi'
    previous = ROOT / '_preview/chorus-photo-phone/final-before-cgc06-particles.avi'
    assert baseline.exists() and previous.exists(), 'Preserve clean GPU baselines before exporting border alternatives'
    results = []
    for style, label in [('wash', 'Wash'), ('cocoa-rectangle', 'Cocoa-Rectangle'), ('white-rectangle', 'White-Rectangle')]:
        if selected != 'all' and style != selected:
            continue
        overlay = FRAMES / (style + '.png')
        third = OUT / f'Chorus-CGC06-Border-{label}-66.000-72.300-song.mp4'
        linked = OUT / f'Chorus-Linked-End-Border-{label}-64.800-72.300-song.mp4'
        encoding = ['-r', '60', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart']
        run(['-i', baseline, '-framerate', '60', '-loop', '1', '-i', overlay, '-ss', '66', '-i', AUDIO,
             '-filter_complex', '[0:v][1:v]overlay=0:0:format=auto[v]',
             '-map', '[v]', '-map', '2:a:0', '-frames:v', '378', '-t', '6.3', *encoding, third])
        # Reuse the previous native GPU shot; no additional encoding of its source.
        # The incoming CG first appears at 65.670, before the 66.000 shot join.
        # Match its smoothstep reveal; never add the border as a later hard cut.
        border_graph = ("[2:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                        "a='alpha(X,Y)*(3*pow(clip((T-0.87)/0.24,0,1),2)-2*pow(clip((T-0.87)/0.24,0,1),3))'[border];"
                        '[joined][border]overlay=0:0:format=auto[v]')
        graph = ('[0:v]fps=60,scale=1920:1080:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[a];'
                 '[1:v]trim=end_frame=378,setpts=PTS-STARTPTS,setsar=1[b];'
                 '[a][b]concat=n=2:v=1:a=0[joined];'
                 + border_graph)
        run(['-ss', '5.6', '-t', '1.2', '-i', previous,
             '-i', baseline, '-framerate', '60', '-loop', '1', '-i', overlay, '-ss', '64.8', '-i', AUDIO,
             '-filter_complex', graph, '-map', '[v]', '-map', '3:a:0', '-frames:v', '450',
             '-t', '7.5', *encoding, linked])
        for movie, frames, duration in [(third, 378, 6.3), (linked, 450, 7.5)]:
            run(['-i', movie, '-f', 'null', '-'])
            probe = json.loads(subprocess.check_output([str(FFPROBE), '-v', 'error', '-count_frames',
                '-show_streams', '-show_format', '-of', 'json', str(movie)]))
            video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            assert (video['width'], video['height'], video['r_frame_rate'], int(video['nb_read_frames'])) == (1920, 1080, '60/1', frames)
            assert abs(float(probe['format']['duration']) - duration) < .03
            results.append({'file': str(movie), 'frames': frames, 'seconds': duration, 'full_decode': 'passed'})
        for name, time in [('closeup', 1.5), ('transition', 3.175), ('closed', 4.375), ('open', 5.5)]:
            run(['-ss', str(time), '-i', third, '-frames:v', '1', OUT / f'border-{style}-{name}.jpg'])
    # Rows = closeup/transition/closed/open; columns = wash/cocoa/white.
    available = [style for style in ['wash', 'cocoa-rectangle', 'white-rectangle']
                 if all((OUT / f'border-{style}-{name}.jpg').exists()
                        for name in ['closeup', 'transition', 'closed', 'open'])]
    sheet = Image.new('RGB', (960 * len(available), 2160))
    for row, name in enumerate(['closeup', 'transition', 'closed', 'open']):
        for col, style in enumerate(available):
            sheet.paste(Image.open(OUT / f'border-{style}-{name}.jpg').resize((960, 540)), (960 * col, 540 * row))
    sheet.save(OUT / 'border-comparison.jpg', quality=93)
    validation = OUT / 'border-versions-validation.json'
    previous = json.loads(validation.read_text(encoding='utf-8')) if validation.exists() else {}
    updated_paths = {r['file'] for r in results}
    combined = [r for r in previous.get('outputs', []) if r['file'] not in updated_paths] + results
    validation.write_text(json.dumps({
        **previous,
        'status': 'qualified_pending_visual_review', 'sources': str(SOURCES / 'eagle-sources.json'),
        'baseline': '11f5812; close/open 0.8s; unchanged native puppet and camera',
        'materials': 'Eagle originals only; crop, scale, recolor, subtle Gaussian blur and alpha composite',
        'cocoa_rectangle': {**previous.get('cocoa_rectangle', {}),
                            'blur_sigma_px': .65, 'linked_reveal_song_seconds': [65.67, 65.91],
                            'reveal_curve': 'smoothstep; same incoming CG timing'},
        'wash': {**previous.get('wash', {}),
                 'color_rgb': [247, 247, 247],
                 'linked_reveal_song_seconds': [65.67, 65.91], 'reveal_curve': 'smoothstep; same incoming CG timing',
                 'native_pigment_instances': 8, 'maximum_inward_px': {'horizontal': 165, 'vertical': 140},
                 'pigment_body_opacity': .35, 'dry_brush_weight': .65},
        'white_rectangle': {**previous.get('white_rectangle', {}),
                            'source_id': 'LIELI0JVC8GGY', 'source': 'imagepaper_00184.jpg',
                            'neutral_white_target': 247, 'border_width_px': 42, 'blur_sigma_px': .65,
                            'linked_reveal_song_seconds': [65.67, 65.91]},
        'outputs': combined}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', action='store_true', help='Export alternatives without replacing production files')
    parser.add_argument('--style', choices=['all', 'wash', 'cocoa-rectangle', 'white-rectangle'], default='all')
    args = parser.parse_args()
    build()
    if args.export:
        export(args.style)
