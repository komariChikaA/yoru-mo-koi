# Cover refinement

Open this local Godot project and run with F5, or run `cover_refined.tscn`
with F6. Existing local `cover.tscn` and `cover_intertwined.tscn` remain unchanged
for comparison. The former main scene was `cover.tscn`.

The title has been manually redrawn in `assets/title-redrawn.svg`, following
the original geometric lettering and the author's thin-line reference. Regular
straight strokes, circular arcs and angular counters replace the blurred raster
and its thick shadows. Small yellow diamonds and four-diamond accents remain.
The SVG imports at 2x display resolution and remains editable vector source.

`original_title_ink.gdshader` gives the thin lines dark plum ink on pale paper /
white clothing and light ink over dark fabric. It reads the rendered background
to change only the line colour; no white halo or local background patch remains.

`cover_wash.gdshader` blends the original CG into warm paper while preserving
the existing portrait mask. The CG itself supplies the hair detail and scenery
between strands; the original texture files are unchanged.

`cover_frame.gd` draws a fine warm-grey frame with restrained corner crosses and
gold endpoints. Gaps at the upper hair and lower skirt keep the character free
to extend beyond the frame. There is no horizontal rule through the title.

Local assets, excluded from Git:

- `assets/cgc16.png`: existing 1920 × 1080 original CG.
- `assets/cgc16_ren_cutout.png`: existing aligned portrait mask.
- `assets/title.png`: original lettering reference, unchanged; no longer rendered.

The hand-redrawn title SVG is tracked with the scene code. The original CG and
raster title assets remain local and unchanged.

Export with the existing local exporter:

```powershell
godot --path godot/cover --script res://export_cover.gd -- --scene=res://cover_refined.tscn --out=cover-refined.png
```

Validation: Godot 4.7.2 import and 1920 × 1080 rendered PNG export succeeded on
RTX 2060 using the project's default Vulkan Forward+ renderer. Visual acceptance
remains with the author. Latest preview: `40_几何细线重绘_装饰断框.png` in the
local `mad/封面/` output folder. Previews 37 and 38 show earlier raster approaches;
39 was the intermediate contour trace and is superseded by the manual redraw.
