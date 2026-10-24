"""Draw a flat, north-up Kobe storyboard map and shared building footprints.

Street axes and neighborhoods are composed for the shot. The retained OSM
source is a geographic reference; no warped real-world coastline is drawn.
"""
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "godot/kobe-map/assets"
WIDTH, HEIGHT = 4096, 3072
# One world unit is one metre. Only map symbols are deliberately enlarged.
BOUNDS = (-1100.0, -800.0, 1100.0, 800.0)
BLUE = [[-650,210],[-550,210],[-550,145],[-260,145],[-260,-80],[520,-80]]
PINK = [[-650,-330],[-280,-330],[-280,-170],[520,-170]]
ANCHORS = {"jr":[-590,150],"ai":[-620,210],"ren":[-620,-330],
           "kumo":[210,-370],"shrine":[210,-400],"kamome":[-140,280],
           "shiori":[-130,-370],"shiori_home":[-130,-410],
           "hiiro":[740,-210],"hiiro_home":[740,-240],"port":[110,265]}
PARKS = [[210,-400,80,70],[-750,-390,90,70],[-130,-410,85,70],[760,-530,110,80]]
RESERVES = [[-590,150,85,30],[-130,-400,85,100],[210,-390,90,110],
            [740,-230,75,95],[520,-125,100,160],[110,265,55,65],
            [-140,280,130,65],[-620,-330,40,50]]


def pixel(point):
    x, z = point
    return ((x - BOUNDS[0]) / 2200 * WIDTH, (z - BOUNDS[1]) / 1600 * HEIGHT)


def rectangle(center):
    x, z, w, d = center
    return (x - w/2, z - d/2, x + w/2, z + d/2)


def overlaps(a, b, gap=0.0):
    return a[0] < b[2]+gap and a[2] > b[0]-gap and a[1] < b[3]+gap and a[3] > b[1]-gap


def road_plan():
    roads = []
    def road(a, b, width, major=False):
        roads.append({"a": a, "b": b, "width": width, "major": major})
    for z,start,end,major in [(-660,-1100,1100,False),(-490,-950,1000,False),
                            (-330,-1100,1100,True),(-170,-1000,1100,False),
                            (-80,-1100,1100,False),(80,-1100,980,False),
                            (210,-1100,1100,False),(310,-1100,1100,True)]:
        road([start,z],[end,z],14 if major else 10,major)
    for x,top,end,major in [(-940,-800,310,False),(-780,-660,210,False),
                           (-650,-800,310,True),(-480,-800,310,False),
                           (-260,-660,310,False),(-90,-800,210,False),
                           (100,-660,210,False),(300,-800,310,False),
                           (520,-800,310,True),(710,-660,310,False),
                           (910,-800,310,False)]:
        road([x,top],[x,end],14 if major else 10,major)
    # Local streets add several intersections between the widely spaced nodes.
    for a,b in [([-850,-490],[-850,-170]),([-940,-240],[-650,-240]),
                ([-570,-170],[-570,80]),([-480,-410],[-260,-410]),
                ([-370,-330],[-370,-170]),([-260,-570],[100,-570]),
                ([10,-330],[10,-170]),([100,-240],[300,-240]),
                ([410,-490],[410,-170]),([520,145],[710,145]),
                ([-940,140],[-780,140]),([-90,-410],[100,-410]),
                ([820,-170],[820,80])]:
        road(a,b,8)
    for a,b in zip(BLUE,BLUE[1:]):
        road(a,b,14)
    return roads


def road_rectangle(road):
    a,b = road["a"], road["b"]
    half = road["width"]/2
    return (min(a[0],b[0])-half, min(a[1],b[1])-half,
            max(a[0],b[0])+half, max(a[1],b[1])+half)


def building_plan(roads):
    rng = random.Random(27140)
    blocks = []
    occupied = []
    protected = [rectangle(p) for p in RESERVES + PARKS]
    streets = [road_rectangle(r) for r in roads]
    def place(x,z,w,d):
        candidate = rectangle([x,z,w,d])
        if candidate[0] < -1000 or candidate[2] > 1000 or candidate[1] < -720 or candidate[3] > 303:
            return
        if any(overlaps(candidate,r,1.0) for r in streets+protected):
            return
        if any(overlaps(candidate,r,2.0) for r in occupied):
            return
        height = rng.uniform(12.0,40.0)
        if rng.random() < 0.18:
            height = rng.uniform(7.0,12.0)
        blocks.append({"x":round(x,3), "z":round(z,3), "width":round(w,3), "depth":round(d,3),
                       "height":round(height,3), "color":rng.randrange(5)})
        occupied.append(candidate)
    # Prioritize tight but varied frontage on the driving street.
    background = roads[:-len(BLUE)+1].copy()
    rng.shuffle(background)
    ordered = roads[-len(BLUE)+1:] + background
    for road in ordered:
        a,b = road["a"], road["b"]
        horizontal = a[1] == b[1]
        start,end = sorted([a[0],b[0]] if horizontal else [a[1],b[1]])
        for side in [-1,1]:
            cursor = start + rng.uniform(2.0,9.0)
            while cursor < end:
                frontage, depth = rng.uniform(9.0,25.0), rng.uniform(10.0,28.0)
                middle = cursor + frontage/2
                setback = rng.uniform(1.2,4.0)
                cross = (a[1] if horizontal else a[0]) + side*(road["width"]/2 + depth/2 + setback)
                if rng.random() > 0.13:
                    if horizontal:
                        place(middle,cross,frontage,depth)
                    else:
                        place(cross,middle,depth,frontage)
                cursor += frontage + rng.uniform(2.5,7.5)
    # Some grouped interiors, with courtyards left open instead of a full array.
    for _ in range(3000):
        place(rng.uniform(-990,990),rng.uniform(-710,298),rng.uniform(12,30),rng.uniform(12,32))
    return blocks


def draw_base(roads, buildings, overview=False):
    image = Image.new("RGB", (WIDTH,HEIGHT), "#e8eef0" if overview else "#f1f3f4")
    draw = ImageDraw.Draw(image)
    draw.rectangle([pixel((-1100,320)),pixel((1100,800))], fill="#b5d9e9")
    for park in PARKS:
        rect = rectangle(park)
        draw.rectangle([pixel(rect[:2]),pixel(rect[2:])],fill="#d5e7c8",outline="#c9dcbf",width=2)
    for block in buildings:
        rect = rectangle([block["x"],block["z"],block["width"],block["depth"]])
        draw.rectangle([pixel(rect[:2]),pixel(rect[2:])],fill="#edf1f2" if overview else "#e1e4e6",outline="#dfe7ea" if overview else "#d5dadf",width=2)
    for road in sorted(roads,key=lambda r:r["width"]):
        points = [pixel(road["a"]),pixel(road["b"])]
        width = round(road["width"]*WIDTH/2200)
        draw.line(points,fill="#aebfc9" if overview else "#d9dfe4",width=width+5 if overview else width+4)
        draw.line(points,fill="#ffe5a5" if road["major"] else "#ffffff",width=width)
    # A straight JR corridor communicates its east-west direction without shear.
    for z in [-26,-22]:
        draw.line([pixel((-1100,z)),pixel((1100,z))],fill="#b9c1c8",width=3)
    return image


def draw_labels(image, background):
    draw = ImageDraw.Draw(image)
    font_path = ASSETS / "fonts/fz-shaoer-map.ttf"
    district = ImageFont.truetype(str(font_path),48)
    small = ImageFont.truetype(str(font_path),32)
    for words,point in [("山手",(-690,-440)),("花隈",(-240,-390)),("元町",(80,120)),
                        ("三宫",(570,-250)),("北野",(300,-580)),("灘",(820,-390)),
                        ("兵库",(-890,150)),("神户港",(300,470))]:
        draw.text(pixel(point),words,font=district,fill="#7d8992",anchor="mm",stroke_width=2,stroke_fill=background)
    for words,point,color in [("公园",(-750,-390),"#70a465"),("商店街",(-220,-190),"#a978b1"),
                              ("南京町",(150,225),"#c48757"),("umie",(-610,280),"#a978b1")]:
        px,py = pixel(point)
        draw.ellipse((px-7,py-7,px+7,py+7),fill=color,outline="white",width=2)
        draw.text((px+12,py),words,font=small,fill=color,anchor="lm",stroke_width=1,stroke_fill="white")


def draw_surface():
    roads = road_plan()
    buildings = building_plan(roads)
    image = draw_base(roads, buildings)
    overview = draw_base(roads, buildings, True)
    draw_labels(image, "#f1f3f4")
    draw_labels(overview, "#e8eef0")
    ASSETS.mkdir(parents=True,exist_ok=True)
    image.save(ASSETS/"map-surface.png",optimize=True)
    overview.save(ASSETS/"map-overview.png",optimize=True)
    layout = {"bounds":BOUNDS,"land":[[-1100,-800],[1100,-800],[1100,320],[-1100,320]],
              "roads":roads,"buildings":buildings,"blue":BLUE,"pink":PINK,
              "anchors":ANCHORS,"metres_per_unit":1.0,"drive_start":0.04,"drive_end":0.125,
              "attribution":"© OpenStreetMap contributors | Composed storyboard map",
              "license":"https://www.openstreetmap.org/copyright"}
    (ASSETS/"world-map.json").write_text(json.dumps(layout,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("Flat composed map:",WIDTH,"x",HEIGHT,"buildings=",len(buildings))


if __name__ == "__main__":
    draw_surface()
