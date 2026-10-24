"""Render amplitude-only comparisons without installing a production strength."""
from pathlib import Path
import argparse
import json
import subprocess
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('../../工作文件夹/output/CGC14-15_scene4')
DEST = OUT / '头发幅度标定'
FF = 'D:/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe'
PROBE = FF.replace('ffmpeg.exe', 'ffprobe.exe')
LEVELS = {15: [1, 2, 4, 8], 14: [1, 2, 4, 8]}
COUNTS = {15: 552, 14: 336}


def source(puppet, strength):
    suffix = '' if strength == 1 else f'-strength-{strength:g}'
    return OUT / f'puppet{puppet}{suffix}.avi'


def run(*args):
    subprocess.run([FF, '-hide_banner', '-v', 'error', '-y', *map(str, args)], check=True)


def frame(path, index):
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, pixels = cap.read()
    cap.release()
    assert ok, (path, index)
    return Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--reuse', action='store_true', help='Reuse completed calibration AVI renders')
    parser.add_argument('--puppet', type=int, choices=[14, 15], help='Refresh only this puppet')
    args = parser.parse_args()
    DEST.mkdir(exist_ok=True)
    selected = {k: v for k, v in LEVELS.items() if args.puppet is None or k == args.puppet}
    if args.render:
        for puppet, levels in selected.items():
            for strength in levels[1:]:
                movie = source(puppet, strength)
                if args.reuse and movie.exists():
                    cap = cv2.VideoCapture(str(movie))
                    valid = cap.get(cv2.CAP_PROP_FRAME_COUNT) >= COUNTS[puppet]
                    cap.release()
                    if valid:
                        continue
                print(f'RENDER CGC{puppet} x{strength}', flush=True)
                subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ROOT / 'tools/render-godot-chorus-four.ps1'), '-SkipPrepare',
                    '-Puppet', str(puppet), '-Strength', str(strength), '-NoInstall'], check=True)
    checks = []
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 33)
    for puppet, levels in selected.items():
        clips = []
        for n, strength in enumerate(levels):
            label = Image.new('RGB', (1920, 72), '#242a34')
            draw = ImageDraw.Draw(label)
            text = f'{chr(65+n)}  |  CGC{puppet}  |  当前幅度 ×{strength:g}  |  原速 · 仅放大幅度 · 待选定100%'
            draw.text((24, 13), text, fill='#ffffff', font=font)
            png = DEST / f'CGC{puppet}-{chr(65+n)}-label.png'
            label.save(png)
            target = DEST / f'CGC{puppet}-{chr(65+n)}-x{strength:g}.mp4'
            run('-i', source(puppet, strength), '-i', png,
                '-filter_complex', '[0:v]pad=1920:1152:0:72[base];[base][1:v]overlay=0:0',
                '-frames:v', COUNTS[puppet], '-an', '-c:v', 'libx264', '-preset', 'fast',
                '-crf', 17, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', target)
            clips.append(target)
            checks.append((target, COUNTS[puppet]))
        inputs = [arg for path in clips for arg in ('-i', path)]
        grid = DEST / f'CGC{puppet}-四档同步对比.mp4'
        graph = ';'.join(f'[{i}:v]scale=960:576[v{i}]' for i in range(4))
        graph += ';[v0][v1][v2][v3]xstack=inputs=4:layout=0_0|960_0|0_576|960_576[out]'
        run(*inputs, '-filter_complex', graph, '-map', '[out]', '-frames:v', COUNTS[puppet],
            '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', 17,
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', grid)
        checks.append((grid, COUNTS[puppet]))
        progression = DEST / f'CGC{puppet}-逐档增强.mp4'
        graph = ''.join(f'[{i}:v]' for i in range(4)) + 'concat=n=4:v=1:a=0[out]'
        run(*inputs, '-filter_complex', graph, '-map', '[out]', '-an', '-c:v', 'libx264',
            '-preset', 'fast', '-crf', 17, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', progression)
        checks.append((progression, COUNTS[puppet]*4))
        sheet = Image.new('RGB', (1920, 1152))
        # Same instant in each cell: comparisons isolate amplitude, not phase/speed.
        sample = 414 if puppet == 15 else 293
        for n, clip in enumerate(clips):
            sheet.paste(frame(clip, sample).resize((960, 576)), ((n % 2)*960, (n//2)*576))
        sheet.save(DEST / f'CGC{puppet}-同相位检查.jpg', quality=95)
    previous = DEST / 'validation.json'
    results = [] if not previous.exists() else [record for record in
        json.loads(previous.read_text(encoding='utf-8'))['videos']
        if not any(record['file'].startswith(f'CGC{k}-') for k in selected)]
    for path, count in checks:
        probe = json.loads(subprocess.check_output([PROBE, '-v', 'error', '-count_frames',
            '-select_streams', 'v:0', '-show_streams', '-of', 'json', str(path)], encoding='utf-8'))['streams'][0]
        assert int(probe['nb_read_frames']) == count, path
        assert probe['avg_frame_rate'] == '60/1', path
        assert abs(float(probe['duration']) - count/60) < .001, path
        run('-xerror', '-i', path, '-f', 'null', '-')
        results.append(dict(file=path.name, frames=count, seconds=count/60, decode='passed'))
    (DEST / 'validation.json').write_text(json.dumps(dict(
        purpose='Amplitude calibration only; user has not selected perceived 100%',
        levels=LEVELS, production_installed=False, speed=1,
        visual_notes='CGC14 high levels expose stretched overlaps and joins; evaluate amplitude only, repair after selection',
        videos=results), ensure_ascii=False, indent=2), encoding='utf-8')
    (DEST / '查看说明.txt').write_text(
        '头发幅度标定：倍率均相对本轮之前的当前版本，尚未定义用户感觉的100%。\n'
        '两组各自：A=1倍，B=2倍，C=4倍，D=8倍。倍率相对于各CG当前版本。\n'
        '先看逐档增强（每档播放完整一个周期），再看四档同步对比；单档保留原始全幅便于放大检查。\n'
        '所有样片60fps原速，只放大发束幅度，眼睛、细节、风速与取景一致。强档用于标定，不能当作最终成片质量验收。\n'
        'CGC14强档可见交叠处拉伸与接缝；选定强度后再针对该幅度修整。\n'
        'CGC14保留区域相对比例，增幅可超过此前45度模型上限，仅用于校准。正式镜头及已安装素材未修改。\n'
        '请分别选择CGC14/CGC15的档位，或指出两档之间，作为你感觉的100%。\n', encoding='utf-8-sig')
    print(DEST, flush=True)


if __name__ == '__main__':
    main()
