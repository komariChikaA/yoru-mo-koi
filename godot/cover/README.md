# Cover refinement

Open this local Godot project and run with F5, or run `cover_refined.tscn`
with F6. Existing local `cover.tscn` and `cover_intertwined.tscn` remain unchanged
for comparison. The former main scene was `cover.tscn`.

The refined scene keeps the original full-width title artwork, including its
letterforms, colours, texture and spacing. The original `title.png`
is drawn as one texture: the old per-character crops cut across neighbouring
letters. The raster already contains soft edges at near-display resolution;
`original_title_ink.gdshader` sharpens alpha coverage and suppresses the broad
blur while retaining faint textured shadows. No replacement glyphs are used.
The horizontal rule and rectangular frame are omitted.

`cover_wash.gdshader` blends the original CG into warm paper while preserving
the existing portrait mask. The CG itself supplies the hair detail and scenery
between strands; the original texture files are unchanged.

Where the title overlaps the hand, clothing or hair, a narrow soft paper-coloured
underlay follows the original ink strokes. It reduces local interference without
washing out a rectangular band of the CG. `title_underlay_strength` on the root
node controls this treatment (default 0.74; 0 disables it). Title layout is shared
with the background shader so the underlay remains aligned with the lettering.

Local assets, excluded from Git:

- `assets/cgc16.png`: existing 1920 × 1080 original CG.
- `assets/cgc16_ren_cutout.png`: existing aligned portrait mask.
- `assets/title.png`: existing original title artwork, unchanged.

Export with the existing local exporter:

```powershell
godot --path godot/cover --script res://export_cover.gd -- --scene=res://cover_refined.tscn --out=cover-refined.png
```

Validation: Godot 4.7.2 import and 1920 × 1080 rendered PNG export succeeded on
RTX 2060 using the project's default Vulkan Forward+ renderer. Visual acceptance
remains with the author. Latest preview: `38_原字形锐化_局部背景让位.png` in the
local `mad/封面/` output folder; `37_Godot修正版_保留原字.png` is the earlier comparison.
