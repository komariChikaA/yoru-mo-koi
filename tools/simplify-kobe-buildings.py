"""Reduce Quaternius Simple Buildings to walls, roof and solid door/window patches."""
from pathlib import Path
from collections import defaultdict
import json
import math
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'godot/kobe-map/assets/buildings/quaternius-simple'
atlas = Image.open(ASSETS / 'Textures/HouseTexture1.png').convert('RGB')
FRAME = (161, 84, 47)
palette = {
    (236, 231, 217): (255, 255, 255),
    (239, 239, 239): (255, 255, 255),
    (169, 169, 169): (228, 228, 228),
    (73, 71, 71): (211, 216, 220),
    (63, 63, 63): (211, 216, 220),
    (120, 69, 43): (199, 208, 214),
    (204, 247, 248): (202, 221, 229),
    FRAME: (255, 255, 255),
}
soft = Image.new('RGB', atlas.size)
soft.putdata([palette[p] for p in atlas.getdata()])
soft.save(ASSETS / 'Textures/simple-palette.png')
stats = {}

def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def unit(a):
    length = math.sqrt(dot(a, a))
    return tuple(x / length for x in a)

wall_pixel = next((x, y) for y in range(atlas.height) for x in range(atlas.width)
                  if atlas.getpixel((x, y)) == (236, 231, 217))
wall_uv = ((wall_pixel[0] + 0.5) / atlas.width, 1 - (wall_pixel[1] + 0.5) / atlas.height)
for name in ('Flat', 'House2'):
    vertices = []
    normals = []
    uv = []
    retained = []
    frame_faces = []
    features = []
    original_faces = kept_faces = 0
    for line in (ASSETS / 'OBJ' / f'{name}.obj').read_text().splitlines():
        parts = line.split()
        if parts and parts[0] == 'v':
            vertices.append(tuple(map(float, parts[1:4])))
        if parts and parts[0] == 'vn':
            normals.append(tuple(map(float, parts[1:4])))
        if parts and parts[0] == 'vt':
            uv.append(tuple(map(float, parts[1:3])))
        if parts and parts[0] == 'f':
            original_faces += 1
            coords = [uv[int(p.split('/')[1]) - 1] for p in parts[1:]]
            u = sum(p[0] for p in coords) / len(coords)
            v = sum(p[1] for p in coords) / len(coords)
            pixel = atlas.getpixel((min(31, max(0, int(u * 32))), min(31, max(0, int((1 - v) * 32)))))
            indices = [int(p.split('/')[0]) - 1 for p in parts[1:]]
            # The wall has openings around the frames. Seal each opening with a
            # flat wall-colour quad behind its retained window/door.
            if pixel == FRAME:
                frame_faces.append(indices)
                continue
            if pixel in ((204, 247, 248), (120, 69, 43)):
                points = [vertices[i] for i in indices]
                centre = tuple(sum(p[j] for p in points) / len(points) for j in range(3))
                normal = unit(normals[int(parts[1].split('/')[2]) - 1])
                features.append((centre, normal, unit(sub(points[1], points[0]))))
            kept_faces += 1
        retained.append(line)
    parent = {}
    def find(i):
        parent.setdefault(i, i)
        if parent[i] != i:
            parent[i] = find(parent[i])
        return parent[i]
    for face in frame_faces:
        for i in face:
            parent[find(i)] = find(face[0])
    openings = defaultdict(set)
    for face in frame_faces:
        openings[find(face[0])].update(face)
    for opening in openings.values():
        centre = tuple(sum(vertices[i][j] for i in opening) / len(opening) for j in range(3))
        origin, normal, u_axis = min(features, key=lambda f: dot(sub(f[0], centre), sub(f[0], centre)))
        v_axis = unit(cross(normal, u_axis))
        bounds_u = [dot(sub(vertices[i], origin), u_axis) for i in opening]
        bounds_v = [dot(sub(vertices[i], origin), v_axis) for i in opening]
        start = len(vertices) + 1
        # Small inset avoids coplanar glass while covering the complete frame opening.
        for u, v in ((min(bounds_u), min(bounds_v)), (max(bounds_u), min(bounds_v)),
                     (max(bounds_u), max(bounds_v)), (min(bounds_u), max(bounds_v))):
            point = tuple(origin[j] + u_axis[j]*u + v_axis[j]*v - normal[j]*0.001 for j in range(3))
            vertices.append(point)
            retained.append('v ' + ' '.join(f'{x:.6f}' for x in point))
        uv.append(wall_uv)
        normals.append(normal)
        retained.append('vt ' + ' '.join(f'{x:.6f}' for x in wall_uv))
        retained.append('vn ' + ' '.join(f'{x:.6f}' for x in normal))
        retained.append('f ' + ' '.join(f'{i}/{len(uv)}/{len(normals)}' for i in range(start, start + 4)))
        kept_faces += 1
    (ASSETS / 'OBJ' / f'{name}-simple.obj').write_text('\n'.join(retained) + '\n')
    stats[name] = {'source_faces': original_faces, 'simple_faces': kept_faces, 'sealed_openings': len(openings)}
print(json.dumps(stats))
