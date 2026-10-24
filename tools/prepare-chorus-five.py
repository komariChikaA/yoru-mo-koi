"""Prepare the CGC16 scene, native petals and independent hair assets.

All contours are in the unmodified 1920 x 1080 source coordinates.  This is a
base scene mask; the follow-up preparation steps remove native petals and
separate hair ribbons with repaired exposed regions. Re-run after contour edits.

White occlusion = either person, so rear 3D blossoms cannot pass across them.
White light-receiver = stronger warm lighting; black = no additional light.
"""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path("${GAME_ROOT}/解包/CG/CGC16.png")
OUT = ROOT / "godot/chorus-five/assets"
SIZE = (1920, 1080)

# The exterior silhouette is traced around the actual painted character, not
# around the pink blossoms.  The slim hair strands are separate filled shapes.
HEAD_AND_BODY = [
    (792,26),(814,14),(849,7),(887,6),(935,10),(974,23),(1009,43),
    (1024,49),(1045,50),(1072,63),(1091,82),(1107,107),(1121,135),
    (1144,166),(1172,192),(1212,221),(1255,250),(1302,279),
    (1340,303),(1360,323),(1367,348),(1376,366),(1417,369),
    (1478,376),(1533,394),(1571,420),(1589,448),(1595,480),
    (1596,493),(1589,464),(1577,436),(1557,416),(1523,402),
    (1482,394),(1440,395),(1408,402),(1372,416),(1351,436),
    (1377,440),(1425,454),(1470,475),(1506,505),(1532,542),
    (1548,580),(1553,610),(1551,624),(1548,600),(1535,570),
    (1514,542),(1486,520),(1457,505),(1480,539),(1501,578),
    (1515,615),(1517,641),(1511,617),(1497,588),(1475,561),
    (1442,538),(1426,530),(1450,568),(1465,608),(1469,644),
    (1466,681),(1460,709),(1455,725),(1458,690),(1451,658),
    (1441,630),(1425,600),(1414,586),(1431,628),(1443,671),
    (1443,699),(1436,722),(1437,693),(1428,666),(1414,638),
    (1388,602),(1368,581),(1358,576),(1368,611),(1371,637),
    (1367,663),(1356,687),(1338,707),(1329,714),(1336,691),
    (1339,665),(1335,638),(1323,608),(1308,583),(1293,572),
    (1281,568),(1284,605),(1293,649),(1306,686),(1332,730),
    (1373,779),(1393,806),(1465,809),(1499,822),(1516,851),
    (1551,884),(1549,917),(1521,964),(1541,1001),(1533,1033),
    (1491,1080),(921,1080),(882,1051),(860,1023),(852,1001),
    (857,987),(876,979),(900,975),(875,950),(861,924),(850,893),
    (846,868),(832,858),(801,838),(776,816),(753,791),(733,781),
    (716,790),(691,787),(683,778),(666,760),(652,742),(642,723),
    (638,705),(617,702),(585,703),(560,700),(542,695),(530,685),
    (518,672),(505,665),(498,657),(495,651),(490,645),(488,641),
    (491,636),(497,635),(494,632),(497,629),(505,630),(523,635),
    (543,641),(566,640),(585,633),(599,629),(584,617),(573,606),
    (566,598),(566,592),(571,591),(581,598),(597,609),(615,617),
    (641,625),(661,631),(679,631),(691,627),(682,619),(660,601),
    (646,582),(637,561),(632,540),(635,518),(644,496),(661,471),
    (681,447),(703,418),(723,389),(738,366),(725,352),(711,332),
    (699,308),(690,280),(684,250),(681,218),(683,183),(689,148),
    (698,112),(710,81),(725,59),(744,45),(762,40),(780,43),
]

AHOGE = [
    (789,42),(775,25),(752,14),(731,10),(708,12),(684,21),
    (660,37),(639,59),(621,86),(609,115),(601,146),(597,181),
    (597,219),(602,254),(610,275),(620,284),(633,285),(646,279),
    (656,266),(658,260),(649,271),(638,277),(627,277),(618,270),
    (612,255),(607,231),(605,205),(606,177),(612,144),(622,113),
    (637,85),(657,61),(681,42),(704,29),(725,25),(747,27),
    (768,35),(782,46),
]

LEFT_LOOP = [
    (748,357),(740,379),(721,407),(698,438),(676,468),(658,498),
    (649,525),(647,549),(652,574),(662,594),(681,612),(701,623),
    (722,628),(743,626),(753,616),(738,637),(720,647),(697,644),
    (678,637),(659,626),(643,611),(632,593),(626,573),(622,549),
    (623,525),(630,503),(642,480),(660,455),(680,432),(699,407),
    (718,381),(733,357),
]

# These are hair below the hand/sleeve.  The triangular sky gaps are kept open.
LOW_LEFT_HAIR = [
    [(679,739),(692,766),(668,798),(645,831),(621,869),(603,903),
     (596,918),(592,903),(592,885),(598,864),(610,838),(629,807),
     (648,781),(666,757)],
    [(696,776),(719,787),(706,818),(690,852),(676,885),(663,920),
     (649,959),(641,990),(633,977),(626,952),(624,927),(627,898),
     (635,867),(646,838),(662,807),(681,782)],
    [(733,786),(753,797),(741,827),(724,865),(711,901),(703,935),
     (701,956),(693,978),(688,962),(688,940),(692,908),(700,876),
     (711,841),(724,807)],
    [(841,852),(858,860),(858,891),(863,921),(874,951),(890,977),
     (910,994),(887,985),(866,967),(851,941),(842,914),(838,883)],
    [(930,677),(944,677),(948,719),(950,758),(952,800),(963,848),
     (979,884),(990,901),(970,886),(956,864),(944,831),(937,794),
     (934,751)],
]

RIGHT_PERSON = [
    (1302,0),(1750,0),(1771,39),(1794,96),(1810,159),(1824,220),
    (1844,281),(1874,334),(1908,379),(1920,382),(1920,1080),
    (1533,1080),(1470,1005),(1424,912),(1384,801),(1346,704),
    (1307,602),(1276,492),(1246,375),(1194,247),(1164,183),
    (1188,172),(1214,159),(1239,145),(1258,124),(1270,98),
    (1269,70),(1281,48),(1294,32),
]

# Holes visible between strands, blouse, and the right person's sleeve.
BACKGROUND_GAPS = [
    [(777,382),(790,382),(788,403),(780,426),(766,449),(747,474),
     (731,499),(720,526),(716,549),(717,576),(724,601),(732,618),
     (715,623),(696,615),(680,602),(671,586),(665,566),(665,543),
     (672,519),(684,494),(702,467),(725,439),(749,410),(765,391)],
    [(807,439),(812,432),(806,463),(797,495),(784,524),(769,550),
     (754,574),(741,599),(739,606),(734,592),(733,574),(736,551),
     (743,529),(754,507),(774,479),(792,456)],
    [(789,674),(802,691),(815,704),(807,722),(797,739),(782,757),
     (768,772),(760,755),(768,729),(778,704)],
    [(756,794),(769,804),(750,850),(738,887),(728,921),(720,953),
     (710,976),(703,969),(709,935),(719,899),(732,862),(746,824)],
    [(914,722),(925,716),(928,752),(928,790),(921,821),(912,842),
     (909,846),(914,808),(915,769)],
    [(965,737),(976,756),(984,788),(998,818),(1011,839),(1017,848),
     (999,858),(983,841),(974,815),(968,786)],
    [(1288,544),(1295,562),(1303,592),(1308,621),(1312,645),
     (1319,662),(1315,674),(1305,659),(1298,635),(1293,608)],
    [(1768,309),(1785,329),(1808,358),(1836,389),(1835,411),
     (1839,439),(1846,477),(1853,501),(1821,478),(1807,457),
     (1795,432),(1787,403),(1780,373),(1774,342)],
    [(1782,922),(1794,919),(1807,923),(1831,941),(1861,970),
     (1892,1005),(1920,1041),(1920,1080),(1837,1080),
     (1825,1046),(1814,1010),(1802,976),(1790,942)],
]


def polygon_image(polygons):
    result = Image.new("L", SIZE, 0)
    draw = ImageDraw.Draw(result)
    for points in polygons:
        draw.polygon(points, fill=255)
    return result


def soft_region(points, strength=255, blur=22):
    im = Image.new("L", SIZE, 0)
    ImageDraw.Draw(im).polygon(points, fill=strength)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(blur)), dtype=np.float32)


def build(source):
    OUT.mkdir(parents=True, exist_ok=True)
    original = Image.open(source).convert("RGB")
    if original.size != SIZE:
        raise ValueError(f"Expected unmodified 1920 x 1080 CGC16, got {original.size}")
    shutil.copyfile(source, OUT / "source.png")
    main = polygon_image([HEAD_AND_BODY, AHOGE, LEFT_LOOP] + LOW_LEFT_HAIR)
    union = np.maximum(np.asarray(main), np.asarray(polygon_image([RIGHT_PERSON])))
    holes = np.asarray(polygon_image(BACKGROUND_GAPS))
    union[holes > 0] = 0
    # Two pixels of overlap prevent a light-coloured line or a flower entering a
    # face at the photographed silhouette.  Only the edge is lightly softened.
    occlusion = cv2.dilate(union, np.ones((5, 5), np.uint8))
    occlusion = cv2.GaussianBlur(occlusion, (0, 0), 0.65)
    Image.fromarray(occlusion, "L").save(OUT / "occlusion.png")

    # A restrained receiver: strongest on hair tops and hand, weaker through
    # cheek/blouse.  It is not a repaint or global exposure lift.
    receiver = np.zeros((SIZE[1], SIZE[0]), dtype=np.float32)
    areas = [
        ([(708,90),(767,38),(857,17),(938,35),(998,69),(1047,142),
          (1030,212),(975,195),(928,164),(878,136),(832,141),(789,191),
          (762,256),(748,321),(717,296),(699,225)], 176, 27),
        ([(756,192),(803,171),(864,177),(940,217),(977,266),(971,321),
          (924,366),(872,371),(819,342),(781,305)], 104, 34),
        ([(1052,76),(1081,100),(1115,160),(1157,208),(1203,242),
          (1290,291),(1335,323),(1343,344),(1306,326),(1218,285),
          (1136,239),(1083,193),(1053,138)], 125, 18),
        ([(1028,302),(1083,343),(1141,367),(1210,389),(1301,396),
          (1376,388),(1433,382),(1487,389),(1523,407),(1442,405),
          (1367,426),(1279,433),(1187,415),(1086,381)], 96, 18),
        ([(748,393),(747,432),(714,484),(689,531),(684,572),(700,604),
          (727,617),(743,637),(714,639),(676,621),(653,585),(648,543),
          (660,493),(699,439)], 94, 16),
        ([(497,634),(543,644),(582,636),(594,619),(573,595),(608,617),
          (655,634),(674,654),(670,686),(640,699),(578,695),(544,685),
          (519,664)], 196, 17),
        ([(840,488),(867,481),(892,506),(933,573),(1009,599),(1077,591),
          (1118,622),(1080,664),(1009,679),(935,670),(886,635),(847,591)], 77, 30),
        ([(1175,412),(1208,431),(1244,467),(1269,516),(1267,556),
          (1235,566),(1208,536),(1195,492)], 67, 26),
        ([(765,755),(800,782),(852,816),(884,832),(886,856),(851,859),
          (800,830),(766,802)], 58, 20),
    ]
    for points, strength, blur in areas:
        receiver = np.maximum(receiver, soft_region(points, strength, blur))
    # Retain eye and mouth linework under warm illumination.  These areas keep a
    # small amount of receiver rather than cutting visible hard black holes.
    facial_detail = np.zeros_like(receiver)
    for points in [
        [(766,253),(796,241),(824,253),(845,291),(833,319),(806,323),(784,303)],
        [(880,190),(919,183),(949,197),(965,220),(950,252),(918,266),(889,245)],
        [(870,312),(897,307),(927,317),(924,342),(911,358),(889,349)],
    ]:
        facial_detail = np.maximum(facial_detail, soft_region(points, 255, 7))
    receiver *= 1.0 - facial_detail / 255.0 * 0.80
    # The light stays inside the person even along the left silhouette.
    clip = np.asarray(main, dtype=np.float32) / 255.0
    clip[holes > 0] = 0
    clip = cv2.GaussianBlur(clip, (0, 0), 0.8)
    receiver = np.clip(receiver * clip, 0, 255).astype(np.uint8)
    Image.fromarray(receiver, "L").save(OUT / "light-receiver.png")

    rgb = np.asarray(original, dtype=np.float32)
    blue = np.array([45, 143, 234], dtype=np.float32)
    amber = np.array([255, 186, 92], dtype=np.float32)
    occ_alpha = (occlusion.astype(np.float32) / 255.0 * 0.53)[..., None]
    light_alpha = (receiver.astype(np.float32) / 255.0 * 0.80)[..., None]
    overlay = Image.fromarray(np.clip(rgb * (1-occ_alpha) + blue * occ_alpha, 0, 255).astype(np.uint8))
    light_review = Image.fromarray(np.clip(rgb * (1-light_alpha) + amber * light_alpha, 0, 255).astype(np.uint8))
    board = Image.new("RGB", (1920, 1080), (20, 21, 24))
    panels = [original, overlay, Image.fromarray(occlusion).convert("RGB"), light_review]
    labels = ["CGC16 original / unchanged", "Blue = rear-petal occlusion", "White = both people / black = background", "Amber = warm-light receiver; facial details reduced"]
    for i, (panel, label) in enumerate(zip(panels, labels)):
        x, y = (i % 2) * 960, (i // 2) * 540
        board.paste(panel.resize((960, 540), Image.Resampling.LANCZOS), (x, y))
        draw = ImageDraw.Draw(board)
        draw.rectangle((x+8, y+8, x+8+len(label)*6+14, y+32), fill=(20, 21, 24))
        draw.text((x+15, y+15), label, fill="white")
    board.save(OUT / "review-mask.jpg", quality=95, subsampling=0)
    print(f"Prepared source plate and two {SIZE[0]}x{SIZE[1]} masks in {OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    build(args.source)
    subprocess.run([sys.executable, str(ROOT / "tools/prepare-chorus-five-native-petals.py"),
                    "--source", str(args.source)], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/prepare-chorus-five-hair.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/prepare-chorus-five-hand.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/prepare-chorus-five-entry.py")], check=True)
