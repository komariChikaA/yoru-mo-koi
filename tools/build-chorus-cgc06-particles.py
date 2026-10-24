"""Prepare the existing unpacked snow sprite; no generated texture."""
import json
import shutil
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw, ImageChops

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('${GAME_ROOT}/解包/其他图片/粒子/雪球大.png')
RECORDS = ROOT / 'assets/chorus-cgc06/particles'


def prepare():
    RECORDS.mkdir(parents=True, exist_ok=True)
    original = RECORDS / 'unpacked-snowball-large.png'
    if not original.exists():
        shutil.copy2(SOURCE, original)
    native = Image.open(original).convert('RGBA')
    canvas = Image.new('RGBA', (64, 64))
    canvas.paste(native, (16, 16))
    mask_source = RECORDS / 'heroine-focus-mask.png'
    if not mask_source.exists():
        shutil.copy2(Path('../../工作文件夹/output/CGC06_scene3/heroine-focus-mask.png'), mask_source)
    exclusion = Image.open(mask_source).convert('L')
    male = Image.new('L', exclusion.size)
    ImageDraw.Draw(male).polygon([(1376,100),(1290,106),(1215,163),(1165,241),
        (1155,316),(1170,367),(1104,411),(1055,463),(1023,517),(965,575),
        (850,650),(805,752),(1376,752)], fill=255)
    exclusion = ImageChops.lighter(exclusion, male).filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.GaussianBlur(8))
    # Preserve source falloff, soften the body and derive a restrained halo.
    for project in ['chorus-cgc06', 'chorus-phone']:
        target = ROOT / 'godot' / project / 'assets/particles'
        target.mkdir(parents=True, exist_ok=True)
        canvas.filter(ImageFilter.GaussianBlur(1.1)).save(target / 'snow-soft.png')
        canvas.filter(ImageFilter.GaussianBlur(3.0)).save(target / 'snow-glow.png')
        exclusion.save(target / 'character-exclusion.png')
    config = {
        'source': str(SOURCE), 'source_copy': str(original.relative_to(ROOT)),
        'source_size': list(native.size), 'body_gaussian_sigma_source_px': 1.1,
        'halo_gaussian_sigma_source_px': 3.0, 'world_pool_count': 104,
        'closeup_fill': {'extra_count': 5, 'source_points': [[300,680],[425,555],[615,475],[800,350],[940,505]], 'foreground_gain': 0.8, 'scope': 'Closeup and incoming preroll only; sparse foreground across background, hand and clothing without character exclusion; same soft textures and motion; fade with outgoing closeup'},
        'camera_balance': {'closeup_background_keep_every': 3, 'closeup_background_active_pool_count': 35, 'closeup_foreground_count': 5, 'overview_size_multiplier': 1.3, 'overview_opacity_multiplier': 1.35, 'overview_pool_count': 104},
        'native_diameter_source_px': [4.5, 20], 'fall_source_px_per_second': [10, 18],
        'size_distribution': {'small': {'share': 0.30, 'source_px': [4.5, 7]}, 'medium': {'share': 0.50, 'source_px': [8, 12]}, 'large': {'share': 0.20, 'source_px': [15, 20]}},
        'closeup_foreground_diameter_source_px': [7, 11], 'closeup_foreground_fall_source_px_per_second': 5,
        'camera_scaled_diameter_screen_px': {'closeup': [14.175,70], 'overview': [9.6525,42.9], 'closeup_foreground': [22.05,38.5]},
        'world_bounds': [-128,-192,1504,944],
        'character_exclusion': 'Existing full heroine matte plus loose male silhouette, 10px expansion / sigma8 feather;98 percent particle attenuation over characters',
        'horizontal_drift_source_px': [9, 3.5], 'opacity': 0.65, 'halo_opacity_multiplier': 0.22,
        'seed': 60617, 'motion': 'CG source-space particles shared by both camera worlds; analytic continuous time, visibly drifting background at10–18 source px/s with three size bands; no flicker',
        'entry_song_seconds': [65.670, 65.910],
        'border': 'White Rectangle, Eagle LIELI0JVC8GGY, existing 42px frame',
        'visual_acceptance': 'pending',
    }
    (RECORDS / 'source.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    for metadata in [ROOT/'godot/chorus-cgc06/scene.json', Path('../../工作文件夹/output/CGC06_scene3/scene.json')]:
        data = json.loads(metadata.read_text(encoding='utf-8'))
        data['atmosphere'] = config
        metadata.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    prepare()
