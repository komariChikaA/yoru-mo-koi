# Quaternius Simple Buildings — optional B trial

Author: Quaternius. Pack: Simple Buildings Pack (August 2017).

- Official source and license: https://quaternius.com/packs/simplebuildings.html
- License: CC0 1.0, https://creativecommons.org/publicdomain/zero/1.0/
- Official download folder: https://drive.google.com/drive/folders/1r-FcNFxC6ziN0oI3GqZJdEkdzglFQHQH
- Public mirror used after the official Drive download returned quota exceeded:
  https://github.com/omaima112/Myth-Busters/tree/a022c3cff9050683d20eb8d5ee490eb3d9c6ffd8/Buildings%20pack%20-%20Aug%202017

Only `OBJ/Flat.obj`, `Flat.mtl`, `House2.obj`, `House2.mtl` and
`Textures/HouseTexture1.png` were copied from this directory. No repository code
or unrelated assets were copied. The pack's official CC0 license applies to
these Quaternius assets.

Original files are retained unchanged. `tools/simplify-kobe-buildings.py`
generates the two `*-simple.obj` derivatives by removing the orange extruded
window-frame faces; cream wall faces, glass, door and roof remain. Flat decreases
from 946 to 109 faces and House2 from 911 to 127 faces, including nine flat
wall-colour caps per model behind retained window/door faces. These seal the
openings left by the removed frames, preventing the rear wall from showing
through beside the windows. Original OBJ vertices, UVs and normals are preserved;
the caps add their own vertices, flat normals and a constant wall-colour UV.
`simple-palette.png` replaces the original saturated
palette with wall-relative white, muted blue windows and grey roof/door patches.

The runtime trial fits the existing city parcels, places the base at ground
level, rotates the entrance facade towards the nearest street, and uses the
existing printed-building shader with texture boiling. It requires the explicit
`--buildings=simple` argument for direct scene viewing. The formal Storybrew
sequence now uses the simplified models in `sb/kobe3d-simple/`; the sequence
exporter selects them by default. `-Buildings original` exports and selects the
original geometric buildings in `sb/kobe3d/`.
