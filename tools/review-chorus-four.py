"""Review the current scene without rerendering independent puppet geometry."""
from pathlib import Path
import argparse
import json
import re
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'godot/chorus-four'
OUT = Path('../../工作文件夹/output/CGC14-15_scene4')
MAPSET = Path('E:/osu/Songs/beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ')
FFMPEG = 'D:/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe'
FFPROBE = FFMPEG.replace('ffmpeg.exe', 'ffprobe.exe')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def run(*args):
    subprocess.run([FFMPEG, '-hide_banner', '-v', 'error', '-y', *map(str, args)], check=True)


def frame(path, index):
    capture = cv2.VideoCapture(str(path))
    capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
    ok, data = capture.read()
    capture.release()
    require(ok, f'Cannot read frame {index}: {path}')
    return Image.fromarray(cv2.cvtColor(data, cv2.COLOR_BGR2RGB))


def probe_video(path, count, duration, audio_required=False):
    probe = json.loads(subprocess.check_output([FFPROBE, '-v', 'error', '-count_frames',
        '-show_streams', '-of', 'json', str(path)], encoding='utf-8'))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    require(int(video['nb_read_frames']) == count, f'{path}: frame count')
    require(video['avg_frame_rate'] == '60/1', f'{path}: expected 60fps')
    require(abs(float(video['duration'])-duration) < .001, f'{path}: video duration')
    require((video['width'], video['height']) == (1920, 1080), f'{path}: expected 1080p')
    result = dict(file=path.name, frames=count, seconds=float(video['duration']),
        width=video['width'], height=video['height'], fps=60)
    if audio_required:
        audio = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        require(audio is not None, f'{path}: missing music stream')
        require(abs(float(audio['duration'])-duration) < .05, f'{path}: audio duration')
        result['audio'] = dict(codec=audio['codec_name'], channels=audio['channels'],
            sample_rate=int(audio['sample_rate']), seconds=float(audio['duration']))
    run('-xerror', '-i', path, '-f', 'null', '-')
    result['decode'] = 'passed'
    return result


def review_storybrew(timeline):
    records = ROOT/'assets/chorus-four/frames.tsv'
    installed = MAPSET/'sb/chorus-four/frames.tsv'
    text = records.read_text(encoding='utf-8-sig')
    require(installed.read_text(encoding='utf-8-sig') == text,
            'Installed Storybrew frames.tsv differs from repository record')
    rows = [(p, float(a), float(b)) for p, a, b in
            (line.split('\t') for line in text.splitlines() if line.strip())]
    start, end = timeline['song_start']*1000, timeline['song_end']*1000
    hold_start = float(timeline.get('hold_start', 72.3))*1000
    require(abs(rows[0][1]-hold_start) < .00001 and abs(rows[0][2]-start) < .00001,
            'Storybrew must include the exact A-tail hold 72300→72500')
    require(abs(rows[1][1]-start) < .00001, 'Body must start at song_start after hold')
    require(abs(rows[-1][2]-end) < .00001, 'Storybrew must end exactly at song_end')
    require(all(a < b for _, a, b in rows), 'Storybrew contains empty/reversed intervals')
    require(all(abs(a[2]-b[1]) < .00001 for a, b in zip(rows, rows[1:])),
            'Storybrew frame intervals are not continuous')
    events = [timeline['song_start'], *timeline['cut_blend'], timeline['cut'],
              timeline['border_exit'], *timeline['exit_blur'], timeline['paint_start'],
              *timeline['camera_pullback'], *timeline['camera_enter']]
    for event in events:
        require(any(abs(a-event*1000) < .00001 for _, a, _ in rows),
                f'Storybrew misses exact event sample {event:.6f}s')
    for filename in set(row[0] for row in rows):
        image = installed.parent/filename
        require(image.is_file(), f'Missing installed Storybrew image: {filename}')
        with Image.open(image) as texture:
            require(texture.size == (1920, 1080),
                    f'Storybrew frame must retain native 1920x1080 detail: {filename}')
    hold = dict(start_ms=hold_start, end_ms=start, file=rows[0][0], image_exists=True)
    if timeline.get('hold_source'):
        source = Path(timeline['hold_source'])
        if not source.is_absolute():
            source = PROJECT/source
        expected = np.array(Image.open(source).convert('RGB').resize(
            (1920, 1080), Image.Resampling.LANCZOS))
        actual = np.array(Image.open(installed.parent/rows[0][0]).convert('RGB'))
        require(actual.shape == expected.shape, 'A-tail hold image must be 1920×1080 RGB')
        difference = np.abs(expected.astype(np.float32)-actual.astype(np.float32))
        mean_error = float(difference.mean())
        p95_error = float(np.percentile(difference, 95))
        require(mean_error < 2.5 and p95_error < 5,
                f'A-tail hold source error exceeds GPU/resize/JPEG tolerance: '
                f'mean={mean_error:.6f}, p95={p95_error:.6f}')
        hold.update(source=str(source), source_pixels='within GPU/resize/JPEG tolerance',
            source_comparison=dict(size=[1920, 1080], mean_absolute_rgb_error=mean_error,
                p95_absolute_rgb_error=p95_error, mean_limit=2.5, p95_limit=5))
    else:
        hold['source_pixels'] = 'source not specified; timing and installed image checked'
    return dict(frames=len(rows), body_frames=len(rows)-1, hold=hold,
        start_ms=start, end_ms=end, exact_event_samples_ms=[t*1000 for t in events],
        continuous=True, installed_tsv_matches=True, texture_size=[1920, 1080])


def review_paint():
    folder = PROJECT/'assets/paint-finish'
    config = read(folder/'paint-finish.json')
    state_records = {}
    for key in ('wall_states', 'dust_states'):
        names = config[key]
        require(len(names) == 6, f'{key}: expected six states')
        arrays = [np.array(Image.open(folder/name).convert('RGBA')) for name in names]
        require(all(im.shape == (1080, 1920, 4) for im in arrays), f'{key}: wrong canvas')
        require(all(np.any(arrays[i] != arrays[j]) for i in range(6) for j in range(i)),
                f'{key}: duplicate states')
        state_records[key] = names
    source = (PROJECT/'scene.gd').read_text(encoding='utf-8-sig')
    active = '\n'.join(line.split('#', 1)[0] for line in source.splitlines())
    require(re.search(r'bell|铃铛', active, re.IGNORECASE) is None,
            'Active sequence still contains a bell asset/function/reference')
    require('全種類のカラーベルを獲得しました！' == config['title'], 'Wrong original-image completion text')
    require((folder/config['title_texture']).is_file(), 'Missing all-collected title')
    title_states = config['title_states']
    require(len(title_states) == 6, 'Handwritten title needs six redraw states')
    title_images = [Image.open(folder/name).convert('RGBA') for name in title_states]
    require(all(im.size == (1400, 180) for im in title_images), 'Wrong title redraw canvas')
    title_bounds = [im.getbbox() for im in title_images]
    require(all(box and box[0] > 4 and box[1] > 4 and box[2] < 1396 and box[3] < 176
                for box in title_bounds), 'Handwritten title is empty or clips its canvas')
    require(all(np.any(np.array(title_images[i]) != np.array(title_images[j]))
                for i in range(6) for j in range(i)), 'Duplicate handwritten title redraws')
    arrival = np.array(Image.open(folder/config['arrival_texture']).convert('RGB'))/255
    require(float(arrival.min()) > .009 and float(arrival.max()) < .991,
            'Wipe arrival map cannot be empty at 0 and fully opaque at 1')
    yy, xx = np.mgrid[:1080:16, :1920:16]
    plane = np.column_stack((xx.ravel(), yy.ravel(), np.ones(xx.size)))
    coefficients = np.linalg.lstsq(plane, arrival[::16, ::16, 0].ravel(), rcond=None)[0]
    fitted_angle = float(np.degrees(np.arctan2(-coefficients[1], coefficients[0])))
    require(config['stroke_angle_degrees'] == 80 and abs(fitted_angle-80) < 4,
            f'Paint stroke direction differs from 80 degrees: {fitted_angle:.3f}')
    wet = np.array(Image.open(folder/config['paint_texture']).convert('RGB'), dtype=float)
    dry = np.array(Image.open(folder/config['wall_states'][0]).convert('RGB'), dtype=float)
    wet_difference = float(np.abs(wet-dry).mean())
    require(wet_difference > 3, 'Fresh paint must visibly differ from the settled wall')
    require((folder/config['bristle_texture']).is_file(), 'Missing two-dimensional brush detail')
    return dict(**state_records, state_rate_hz=config['state_rate_hz'],
        title=config['title'], font=config['font'], font_px=config['font_px'],
        title_states=title_states, title_bounds=title_bounds,
        title_state_rate_hz=config['title_state_rate_hz'],
        dust_particles=len(config['particles']),
        active_sequence_bells=False, arrival_range=[float(arrival.min()), float(arrival.max())],
        stroke_angle_degrees=config['stroke_angle_degrees'], fitted_arrival_axis_degrees=fitted_angle,
        wet_dry_mean_rgb_difference=wet_difference, bristle_texture=config['bristle_texture'])


def reuse_hair_metrics(timeline):
    previews = timeline.get('hair_previews', {})
    stages = read(PROJECT/'sources.json')['hair_stages']
    policy = read(PROJECT/'hair-redo/user-grouping.json')
    results = {}
    for cg, title in [(14, 'CGC14-九簇悬崖强风'), (15, 'CGC15-八簇悬崖强风')]:
        path = Path(previews.get(str(cg), OUT/'头发逐层重拆/悬崖强风'/f'{title}-记录.json'))
        record = read(path)
        stage = Path(stages[str(cg)])
        expected_parts = [p['id'] for p in read(stage/'stage.json')['parts']]
        require(record['parts'] == expected_parts, f'{path}: current rebuilt clusters differ')
        require(Path(record['stages'][-1]).resolve() == stage.resolve(),
                f'{path}: metrics belong to a different hair stage')
        require(record.get('motion_profile') == policy.get('motion_profile'),
                f'{path}: metrics belong to a different motion profile')
        require(record.get('gradient_solver_by_id') == policy.get('gradient_solver_by_id'),
                f'{path}: gradient solvers differ from the production rig')
        require(record.get('pinned_return_tips') == policy.get('pinned_return_tips'),
                f'{path}: concealed return-tip constraints differ')
        for part in record['resolved_motion']:
            if policy.get('motion_profile') == 'reference-wind-arc-length':
                reference = policy['reference_by_id'][part['id']]
                require(part['reference_amplitude_deg'] == reference['amplitude_deg']
                        and part['reference_lag'] == reference['lag'],
                        f'{path}: reference wind parameters differ for {part["id"]}')
            else:
                require(part['motion_gain'] == policy['motion_gain_by_id'][part['id']],
                        f'{path}: motion gain differs for {part["id"]}')
        proof = record['proof']
        require(proof is not None, f'{path}: missing existing geometry metrics')
        require(proof['fixed_max_displacement_px'] < .0001, f'{path}: fixed support moved')
        require(proof['support_max_displacement_px'] < .0001, f'{path}: anchor moved')
        require(proof['visible_folded_triangles_max'] == 0, f'{path}: visible folded triangles')
        require(proof['visible_min_area_ratio'] > 0, f'{path}: nonpositive visible area')
        if policy.get('motion_profile') == 'reference-wind-arc-length':
            require(proof['visible_min_edge_ratio'] >= .72
                    and proof['visible_max_edge_ratio'] <= 1.32,
                    f'{path}: visible edge compression or stretch exceeds calibration bounds')
        results[str(cg)] = dict(source=str(path), parts=record['parts'], proof=proof,
            scope='Current rebuilt-preview metrics; full-scene review does not rerun puppet geometry')
    return results


def contact_sheet(movie, timeline, count):
    start, end = timeline['song_start'], timeline['song_end']
    blend_start, blend_end = timeline['cut_blend']
    times = [start, start+.25, start+.5, timeline['entry_cg'][1],
        timeline['camera_pullback'][0]+.15, timeline['camera_pullback'][0]+.3, timeline['camera_pullback'][1],
        timeline['camera_enter'][0], timeline['camera_enter'][0]+.15, timeline['camera_enter'][0]+.3, timeline['camera_enter'][1],
        start+1.32, start+1.44, start+1.64, blend_start,
        timeline['cut'], blend_end, timeline['border_exit'], timeline['smile_close'][0],
        sum(timeline['smile_close'])/2, timeline['smile_close'][1]+1/60,
        timeline['exit_blur'][0], timeline['paint_start']-1/60, timeline['paint_start'],
        timeline['paint_start']+.2, timeline['paint_start']+.45,
        timeline['exit_blur'][1],
        timeline['title_in'][0], timeline['paint_end'],
        timeline['title_in'][1], end-.45, end-.2, end-1/60]
    sheet = Image.new('RGB', (1920, ((len(times)+3)//4)*330), '#34312c')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
    samples = []
    for n, time in enumerate(times):
        index = min(count-1, max(0, round((time-start)*60)))
        actual_time = start+index/60
        x, y = n%4*480, n//4*330
        sheet.paste(frame(movie, index).resize((480, 270), Image.Resampling.LANCZOS), (x, y+35))
        draw.text((x+8, y+8), f'{actual_time:.3f}s / frame {index}', font=font, fill='white')
        samples.append(dict(requested_song_time=time, frame=index, actual_song_time=actual_time))
    sheet.save(OUT/'分镜检查.jpg', quality=95)
    return samples


def review_scene():
    timeline = read(PROJECT/'timeline.json')
    required = ['song_start', 'cut', 'paint_start', 'song_end', 'cut_blend', 'border_exit']
    require(all(key in timeline for key in required), 'Shared timeline is missing required scene events')
    start, end = timeline['song_start'], timeline['song_end']
    duration = end-start
    count = round(duration*60)
    require(count == 408 and abs(duration-6.8) < .00001, 'Expected the 72.500–79.300 scene duration')
    movie = OUT/'第四分镜-72.500-79.300-带音乐.mp4'
    video = probe_video(movie, count, duration, audio_required=True)
    context_movie = OUT/'第四分镜-含上一镜衔接-71.500-79.300.mp4'
    context_video = probe_video(context_movie, 468, 7.8, audio_required=True)
    storybrew = review_storybrew(timeline)
    paint = review_paint()
    hair = reuse_hair_metrics(timeline)
    for name in ['import-errors.log', 'scene4-errors.log']:
        path = OUT/name
        require(path.is_file(), f'Missing current scene log {path}')
        errors = path.read_text(encoding='utf-8', errors='replace')
        require(not any(s in errors for s in ['SCRIPT ERROR:', 'SHADER ERROR:', 'ERROR:']), str(path))
    samples = contact_sheet(movie, timeline, count)
    record = dict(timeline=timeline, videos=[video, context_video], storybrew=storybrew,
        paint_finish=paint, rebuilt_hair_metrics=hair,
        contact_sheet='分镜检查.jpg', contact_samples=samples,
        status='Scene technical checks passed; contact sheet generated for visual review; user acceptance pending')
    previous_path = OUT/'validation.json'
    if previous_path.exists():
        previous = read(previous_path)
        # Older standalone puppets and eye/wind proofs are historical evidence.
        record['historical'] = previous.get('historical', {
            key: previous[key] for key in ['videos', 'cgc14_eye', 'cgc14_wind', 'cgc15_source'] if key in previous})
    previous_path.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-only', action='store_true', help='Validate current scene; this is the default')
    args = parser.parse_args()
    review_scene()
