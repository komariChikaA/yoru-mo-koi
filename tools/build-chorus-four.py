"""Prepare and install the current fourth shot; reviewed hair stages remain local."""
from pathlib import Path
import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'godot/chorus-four'
ASSETS = PROJECT / 'assets'
OUT = Path('../../工作文件夹/output/CGC14-15_scene4')
SOURCE = Path('${GAME_ROOT}/解包')
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
FFMPEG = 'D:/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe'


def timeline():
    return json.loads((PROJECT / 'timeline.json').read_text(encoding='utf-8'))


def helper(name):
    subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tools' / name)], check=True)


def entry_assets():
    """Continue the original CGC06 camera; never transform its flattened border."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    config = timeline()
    previous = ROOT / '工作文件夹/output/CGC06_scene3/scene3.avi'
    continuation = ASSETS / 'entry-continuation'
    continuation.mkdir(parents=True, exist_ok=True)
    first = round((config['song_start'] - 66.0) * 60)
    count = round((config['entry_sky'][1] - config['song_start']) * 60)
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', str(previous), '-vf',
        f'trim=start_frame={first}:end_frame={first+count},setpts=PTS-STARTPTS',
        '-fps_mode', 'vfr', '-frames:v', str(count), '-start_number', '0',
        '-q:v', '2', '-pix_fmt', 'yuvj444p', str(continuation / 'frame-%03d.jpg')], check=True)
    for n in range(count):
        with Image.open(continuation / f'frame-{n:03d}.jpg') as image:
            assert image.size == (1920, 1080)
    config.pop('previous_source_time', None)
    config['previous_continuation'] = dict(source='chorus-cgc06/scene3.avi', song_start=config['song_start'], fps=60, frames=count)
    config['hold_source'] = 'assets/entry-continuation/frame-000.jpg'
    (PROJECT / 'timeline.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    Image.open(SOURCE / '场景/空_夕.png').convert('RGB').resize((1920, 1080), Image.Resampling.LANCZOS).save(ASSETS / 'entry-sunset.png')
    shutil.copy2(ROOT / 'godot/chorus-cgc06/assets/frames/white-rectangle.png', ASSETS / 'white-frame.png')
    source_record = dict(previous_continuous_render=str(previous), previous_continuation=config['previous_continuation'], middle_scene=str(SOURCE / '场景/空_夕.png'),
        hold_source=config['hold_source'], cgc15_input=str(OUT / 'inputs/CGC15_c-user-20261018.png'),
        cgc15_input_size=[1672, 941], cgc15_canvas=[1920, 1080],
        hair_stages={
            '14': str(OUT / '头发逐层重拆/CGC14/stage-cliff-wind-v2'),
            '15': str(OUT / '头发逐层重拆/CGC15/stage-reference-wind-root-clean')},
        finish='assets/paint-finish/paint-finish.json', timeline='timeline.json',
        background_particles='../../assets/chorus-four/particles.json')
    (PROJECT / 'sources.json').write_text(json.dumps(source_record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for puppet in (14, 15):
        launcher = f'& "D:/software/Godot/4.7.2-stable/Godot_v4.7.2-stable_win64.exe" --path "{PROJECT}" -- --puppet{puppet}\n'
        (OUT / f'打开CGC{puppet}木偶.ps1').write_text(launcher, encoding='utf-8-sig')


def prepare(finish_only=False, cgc15_only=False):
    if cgc15_only:
        helper('prepare-cgc15-closed-smile.py')
        return
    entry_assets()
    helper('build-chorus-four-paint-finish.py')
    if not finish_only:
        helper('compose-cgc14-rebuilt-eye-clean.py')
        helper('prepare-cgc15-closed-smile.py')
        helper('prepare-chorus-four-particles.py')
    print('Prepared evening-sky entry, reviewed puppet facial plates, paint and 全收集.')


def install():
    config = timeline()
    duration = config['song_end'] - config['song_start']
    count = round(duration * 60)
    video = OUT / 'scene4.avi'
    target = MAPSET / 'sb/chorus-four'
    target.mkdir(parents=True, exist_ok=True)
    staged_frames = OUT / 'storybrew-frames'
    staged_frames.mkdir(parents=True, exist_ok=True)
    events = [config['cut'], config['paint_start'], config['paint_end'], config['border_exit']]
    for key in ('entry_sky', 'entry_cg', 'cut_blend', 'camera_pullback', 'camera_enter', 'smile_close', 'exit_blur', 'title_in'):
        events.extend(config[key])
    starts = sorted(set([n / 24 for n in range(math.ceil(duration * 24))]
        + [round(t - config['song_start'], 6) for t in events if config['song_start'] <= t < config['song_end']]))
    # The outgoing camera keeps the preceding shot's 30fps sampling phase.
    entry_duration = config['entry_sky'][1] - config['song_start']
    starts = sorted(set([n / 30 for n in range(math.ceil(entry_duration * 30))]
        + [t for t in starts if t >= entry_duration - 1e-6]))
    indices = [int(math.floor(t * 60 + 1e-6)) for t in starts]
    unique_indices = sorted(set(indices))
    selector = '+'.join(f'eq(n\\,{n})' for n in unique_indices)
    # Keep the native 1920x1080 render; multiple event rows may reuse one image.
    # q2 / 4:4:4 keeps fine hair, lettering and paint edges clear in Storybrew.
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', str(video), '-vf',
        f'select={selector}', '-fps_mode', 'vfr', '-q:v', '2', '-pix_fmt', 'yuvj444p',
        '-frames:v', str(len(unique_indices)), str(staged_frames / 'frame-%04d.jpg')], check=True)
    names = {index: f'frame-{n+1:04d}.jpg' for n, index in enumerate(unique_indices)}
    for name in names.values():
        staged_copy = target / (name + '.new')
        shutil.copyfile(staged_frames / name, staged_copy)
        for attempt in range(20):
            try:
                staged_copy.replace(target / name)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.15)
    previous_folder = MAPSET / 'sb/chorus-cgc06'
    last_previous = (previous_folder / 'frames.tsv').read_text().splitlines()[-1].split('\t')[0]
    rows = []
    if config['previous_end'] < config['song_start']:
        shutil.copy2(previous_folder / last_previous, target / 'entry-hold.jpg')
        rows.append(f'entry-hold.jpg\t{config["previous_end"]*1000:.6f}\t{config["song_start"]*1000:.6f}\n')
    for n, t in enumerate(starts):
        start = config['song_start'] * 1000 + t * 1000
        end = config['song_start'] * 1000 + starts[n+1] * 1000 if n+1 < len(starts) else config['song_end'] * 1000
        assert (target / names[indices[n]]).exists()
        rows.append(f'{names[indices[n]]}\t{start:.6f}\t{end:.6f}\n')
    (target / 'frames.tsv').write_text(''.join(rows), encoding='utf-8')
    records = ROOT / 'assets/chorus-four'
    records.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target / 'frames.tsv', records / 'frames.tsv')
    layer = '43113143113143113143113143113143'
    effect = ROOT / f'.sbrew/effect.{layer}.yaml'
    effect.write_text('FormatVersion: 7\nName: "Chorus Fourth 72.3–79.3s"\nScript: "ChorusFour"\nMultithreaded: No\nConfig:\nLayers:\n  ' + layer + ':\n    Name: "Chorus Fourth"\n    OsbLayer: Overlay\n    DiffSpecific: No\n    Visible: Yes\n', encoding='utf-8')
    index = ROOT / '.sbrew/index.yaml'
    text = index.read_text(encoding='utf-8')
    if layer not in text:
        index.write_text(text.rstrip() + '\n  - "' + layer + '"\n', encoding='utf-8')
    preview = OUT / '第四分镜-72.300-79.300-带音乐.mp4'
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', str(video), '-ss', str(config['song_start']),
        '-i', str(MAPSET / 'audio-balanced.mp3'), '-map', '0:v:0', '-map', '1:a:0',
        '-t', str(duration), '-frames:v', str(count), '-r', '60', '-c:v', 'libx264', '-crf', '16',
        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(preview)], check=True)
    # Show the preceding CG's real last 0.8s and the complete continuous new shot.
    previous = MAPSET / 'sb/chorus-cgc06'
    previous_rows = [row.split('\t') for row in (previous / 'frames.tsv').read_text().splitlines()]
    prefix = OUT / 'entry-context'
    prefix.mkdir(exist_ok=True)
    for n in range(round((config['song_start'] - 71.5) * 60)):
        song_ms = min(72299.99, 71500 + n * 1000 / 60)
        row = next(row for row in previous_rows if float(row[1]) <= song_ms < float(row[2]))
        shutil.copy2(previous / row[0], prefix / f'frame-{n:04d}.jpg')
    context = OUT / '第四分镜-含上一镜衔接-71.500-79.300.mp4'
    graph = '[0:v]scale=1920:1080:flags=lanczos,setsar=1[a];[1:v]setsar=1[b];[a][b]concat=n=2:v=1:a=0[v]'
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-framerate', '60', '-i', str(prefix / 'frame-%04d.jpg'),
        '-i', str(video), '-ss', '71.5', '-i', str(MAPSET / 'audio-balanced.mp3'), '-filter_complex', graph,
        '-map', '[v]', '-map', '2:a:0', '-frames:v', '468', '-t', '7.8', '-r', '60',
        '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
        '-movflags', '+faststart', str(context)], check=True)
    print(preview)
    print(context)
    image_count = len(unique_indices) + int(config['previous_end'] < config['song_start'])
    print(f'Installed {image_count} referenced images / {len(rows)} continuous Storybrew rows.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--finish-assets', action='store_true')
    parser.add_argument('--cgc15-only', action='store_true')
    args = parser.parse_args()
    install() if args.install else prepare(args.finish_assets, args.cgc15_only)
