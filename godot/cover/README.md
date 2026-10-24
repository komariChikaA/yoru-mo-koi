# Cover refinement

Open this local Godot project and run with F5, or run `cover_refined.tscn`
with F6. Existing local `cover.tscn` and `cover_intertwined.tscn` remain unchanged
for comparison. The former main scene was `cover.tscn`.

The title has been manually redrawn in `assets/title-redrawn.svg`, following
the original geometric lettering and the author's thin-line reference. Regular
straight strokes, circular arcs and angular counters replace the blurred raster
and its thick shadows. Small yellow diamonds and four-diamond accents remain.
The SVG imports at 2x display resolution and remains editable vector source.
夜 and 恋 use slightly wider rose-coloured strokes as the two visual anchors;
the other characters retain the lighter neutral linework.

`original_title_ink.gdshader` gives the thin lines dark plum ink on pale paper /
white clothing and light ink over dark fabric. It reads the rendered background
to change only the line colour; no white halo or local background patch remains.

`cover_wash.gdshader` blends the original CG into warm paper using
`assets/portrait-contour-smooth.svg`. This editable Bezier mask follows the
author's red hand-drawn contour: the outer silhouette and eight marked inner
gaps retain their route, with small wobbles replaced by smooth curves. The mask
uses the original 1920 × 1080 coordinates and imports at 2x resolution for AA.
The CG itself supplies every visible pixel; original raster files are unchanged.

`cover_frame.gd` draws a fine warm-grey frame with restrained corner crosses and
gold endpoints. Gaps at the upper hair and lower skirt keep the character free
to extend beyond the frame. There is no horizontal rule through the title.

Local assets, excluded from Git:

- `assets/cgc16.png`: existing 1920 × 1080 original CG.
- `assets/cgc16_ren_cutout.png`: earlier portrait mask, preserved but no longer used.
- `assets/title.png`: original lettering reference, unchanged; no longer rendered.

The hand-redrawn title and smoothed portrait SVGs are tracked with the scene
code. The original CG and raster title assets remain local and unchanged.

Export with the existing local exporter:

```powershell
godot --path godot/cover --script res://export_cover.gd -- --scene=res://cover_refined.tscn --out=cover-refined.png
```

Add `--contour-guide` after `--` to export the smoothed outline over the original
full CG, without the title or frame, for checking the author's route directly.

Validation: Godot 4.7.2 import and 1920 × 1080 rendered PNG export succeeded on
RTX 2060 using the project's default Vulkan Forward+ renderer. Visual acceptance
remains with the author. Latest previews in the local `mad/封面/` output folder:
`42_沿手绘路线_平滑轮廓对照.png` (contour) and
`43_平滑角色轮廓_封面应用.png` (cover). Typography and frame remain as in preview 41.
Previews 37 and 38 show earlier raster approaches;
39 was the intermediate contour trace and is superseded by the manual redraw.
