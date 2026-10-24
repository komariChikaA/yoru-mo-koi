# Soft capsule used by every orbit. Ends fade so neighboring pieces join into one stroke.
import math
import os

from PIL import Image

MAPSET = r"E:\osu\Songs\beatmap-639117755766042807-西沢さんP,GUMI - 夜もすがら君想ふ"
OUT = os.path.join(MAPSET, "sb", "orbit-dash.png")

W, H = 64, 16
core = 5.2
feather = 2.2
cap = 3.0
im = Image.new("RGBA", (W, H))
px = im.load()
cy = (H - 1) / 2.0
for y in range(H):
    dy = abs(y - cy)
    if dy <= core:
        vertical = 1.0
    else:
        t = min(1.0, (dy - core) / feather)
        vertical = (1.0 - t) * (1.0 - t)
    for x in range(W):
        edge = min(x + 0.5, W - x - 0.5)
        if edge >= cap:
            horizontal = 1.0
        else:
            t = max(0.0, edge / cap)
            horizontal = t * t * (3.0 - 2.0 * t)
        alpha = int(round(255 * vertical * horizontal))
        px[x, y] = (255, 255, 255, alpha)

im.save(OUT)
print("dash", im.size, OUT)
