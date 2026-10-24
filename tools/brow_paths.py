"""Hand-drawn cubic Bezier lash contours; historical 'brows' JSON key retained."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = (1376, 752)


def validate(data):
    if data.get('version') != 1 or data.get('image_size') != list(SIZE):
        raise ValueError('描边文件版本或原图尺寸不匹配')
    if len(data.get('brows', [])) != 2:
        raise ValueError('需要两条上睫毛的路径记录')
    for brow in data['brows']:
        if not 0 <= float(brow.get('feather', .25)) <= 2:
            raise ValueError('羽化范围为 0–2 原图像素')
        nodes = brow.get('nodes', [])
        if len(nodes) > 256:
            raise ValueError('每条路径最多 256 个节点')
        if brow.get('closed') and len(nodes) < 3:
            raise ValueError('闭合路径至少需要三个节点')
        for node in nodes:
            for key in ['p', 'in', 'out']:
                point = np.asarray(node[key], dtype=float)
                if point.shape != (2,) or not np.isfinite(point).all():
                    raise ValueError('节点坐标无效')
                if not (-SIZE[0] <= point[0] <= SIZE[0]*2 and -SIZE[1] <= point[1] <= SIZE[1]*2):
                    raise ValueError('节点超出画布范围')
    return data


def load(path):
    return validate(json.loads(Path(path).read_text(encoding='utf-8')))


def rasterize(brow):
    if not brow.get('closed') or len(brow.get('nodes', [])) < 3:
        raise ValueError('请先闭合上睫毛轮廓')
    points = []
    nodes = brow['nodes']
    for index, a in enumerate(nodes):
        b = nodes[(index+1) % len(nodes)]
        p = np.array([a['p'], a['out'], b['in'], b['p']], dtype=float)
        steps = max(12, min(2048, int(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()*8)))
        t = np.linspace(0, 1, steps, endpoint=False)[:, None]
        points.extend((1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t**2*p[2]+t**3*p[3])
    image = Image.new('L', (SIZE[0]*4, SIZE[1]*4))
    ImageDraw.Draw(image).polygon([(float(p[0]*4), float(p[1]*4)) for p in points], fill=255)
    feather = float(brow.get('feather', .25))
    if feather:
        image = image.filter(ImageFilter.GaussianBlur(feather*4))
    mask = np.array(image.resize(SIZE, Image.Resampling.LANCZOS))
    if (mask > 127).sum() < 2:
        raise ValueError('轮廓面积过小，请沿上睫毛外沿描出闭合区域')
    return mask


def extract(photo, brow, origin, axis):
    """Keep every selected native RGB pixel; selection comes only from the pen."""
    alpha = rasterize(brow)
    support = cv2.dilate(np.uint8(alpha > 0), np.ones((3, 3), np.uint8))*255
    under = cv2.inpaint(photo, support, 4, cv2.INPAINT_TELEA)
    underlay = photo.copy()
    underlay[support > 0] = under[support > 0]
    y, x = np.where(alpha > 8)
    normal = np.array([-axis[1], axis[0]])
    world = np.c_[x, y] - origin
    local_x = world @ axis
    local_y = world @ normal
    weights = alpha[y, x].astype(float)
    stations = np.linspace(local_x.min(), local_x.max(), 64)
    width = max((stations[-1]-stations[0])/48, 1)
    center = []
    for station in stations:
        w = weights*np.exp(-.5*((local_x-station)/width)**2)
        center.append(float(np.sum(w*local_y)/np.sum(w)))
    curve = np.c_[stations, center]
    half_width = max(7, float(np.max(np.abs(local_y-np.interp(local_x, stations, center))))+3)
    return np.dstack([photo, alpha]), underlay, curve, half_width
