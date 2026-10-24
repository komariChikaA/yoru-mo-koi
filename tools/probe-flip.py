# Measure whether revealed flip cells share an edge in the preview frame.
import math
import os

from PIL import Image

FRAME = r"../..\_preview\flip-live\t010800.png"
OUT = r"../..\_preview\flip-live"

SIDE = 120
OX = 320 - 8 * SIDE // 2
OY = 240 - 5 * SIDE // 2
CELLS = [
    (1, 1, "dots"),
    (1, 2, "height"),
    (1, 3, "eyes"),
    (2, 1, "starL"),
    (5, 1, "hair"),
    (6, 1, "starR"),
    (5, 2, "slash"),
    (6, 2, "cv"),
    (6, 3, "dotsR"),
    (7, 2, "dotsFar"),
]


def pose(rest_x, rest_y, alpha):
    delta = math.radians(alpha - 90.0)
    dx = rest_x - 320.0
    up = 900.0 - rest_y
    cos = math.cos(delta)
    sin = math.sin(delta)
    x = 320.0 + dx * cos - up * sin
    y = 900.0 - (dx * sin + up * cos)
    return x + 107.0, y


def main():
    arrived = 9958
    hold = 13000 - arrived
    alpha = 80.0 + 20.0 * (10800 - arrived) / hold
    print("alpha", round(alpha, 3))
    centers = {}
    for col, row, name in CELLS:
        cx = OX + col * SIDE + SIDE / 2
        cy = OY + row * SIDE + SIDE / 2
        px, py = pose(cx, cy, alpha)
        centers[name] = (px, py, cx, cy)
        print(name, "rest", cx, cy, "preview", round(px, 2), round(py, 2))

    im = Image.open(FRAME).convert("RGB")
    # Shared edge between height and eyes: midpoint of the two centers.
    pairs = [("dots", "height"), ("height", "eyes"), ("dots", "starL"),
             ("hair", "starR"), ("hair", "slash"), ("starR", "cv"), ("cv", "dotsR"), ("cv", "dotsFar")]
    for a, b in pairs:
        ax, ay = centers[a][0], centers[a][1]
        bx, by = centers[b][0], centers[b][1]
        dist = math.hypot(bx - ax, by - ay)
        # Sample across the join, perpendicular to the center line, at the midpoint.
        mx, my = (ax + bx) / 2, (ay + by) / 2
        # Walk from a toward b and count background-like pixels near the join.
        steps = 40
        run = 0
        worst = 0
        for i in range(steps + 1):
            t = i / steps
            x = int(round(ax + (bx - ax) * t))
            y = int(round(ay + (by - ay) * t))
            if not (0 <= x < im.width and 0 <= y < im.height):
                continue
            r, g, bch = im.getpixel((x, y))
            # Gradient backdrop is pale and g close to b. Cell fills are white, yellow, or blue with ink.
            pale = r > 210 and g > 220 and bch > 220 and abs(g - bch) < 18 and abs(r - g) < 30
            if pale:
                run += 1
                worst = max(worst, run)
            else:
                run = 0
        print(f"join {a}-{b} center-dist {dist:.2f} pale-run {worst}")

    # Crops of the two clusters in preview space.
    def crop(names, tag, pad=16):
        xs = [centers[n][0] for n in names]
        ys = [centers[n][1] for n in names]
        box = (
            max(0, int(min(xs) - SIDE / 2 - pad)),
            max(0, int(min(ys) - SIDE / 2 - pad)),
            min(im.width, int(max(xs) + SIDE / 2 + pad)),
            min(im.height, int(max(ys) + SIDE / 2 + pad)),
        )
        im.crop(box).save(os.path.join(OUT, tag + ".png"))
        print("crop", tag, box)

    crop(["dots", "height", "eyes", "starL"], "left-10800")
    crop(["hair", "starR", "slash", "cv", "dotsR", "dotsFar"], "right-10800")

    early = Image.open(os.path.join(OUT, "t010160.png")).convert("RGB")
    mid = Image.open(os.path.join(OUT, "t010320.png")).convert("RGB")
    # Order-0 cells start at wave 10118. At 10160 they are partly closed.
    # Use the same rest centers; alpha differs.
    def alpha_at(t):
        return 80.0 + 20.0 * (t - arrived) / hold

    for t, src, names, tag in (
        (10160, early, ["dots", "hair"], "early"),
        (10320, mid, ["height", "eyes", "hair", "slash"], "mid"),
    ):
        a = alpha_at(t)
        pts = []
        for col, row, name in CELLS:
            if name not in names:
                continue
            cx = OX + col * SIDE + SIDE / 2
            cy = OY + row * SIDE + SIDE / 2
            pts.append(pose(cx, cy, a))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        box = (
            max(0, int(min(xs) - 90)),
            max(0, int(min(ys) - 90)),
            min(src.width, int(max(xs) + 90)),
            min(src.height, int(max(ys) + 90)),
        )
        src.crop(box).save(os.path.join(OUT, tag + ".png"))
        print("crop", tag, "alpha", round(a, 2), box)


if __name__ == "__main__":
    main()
