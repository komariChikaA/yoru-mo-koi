# Cover refinement

Open this local Godot project and run with F5, or run `cover_refined.tscn`
with F6. Existing local `cover.tscn` and `cover_intertwined.tscn` remain unchanged
for comparison. The former main scene was `cover.tscn`.

The refined scene keeps the original full-width title artwork, including its
letterforms, colours, texture, shadows and spacing. The original `title.png`
is drawn as one texture: the old per-character crops cut across neighbouring
letters. Ink coverage is strengthened for readability over the CG, without
changing the glyphs. The horizontal rule and rectangular frame are omitted.

`cover_wash.gdshader` blends the original CG into warm paper while preserving
the existing portrait mask. The CG itself supplies the hair detail and scenery
between strands; the original texture files are unchanged.

Local assets, excluded from Git:

- `assets/cgc16.png`: existing 1920 × 1080 original CG.
- `assets/cgc16_ren_cutout.png`: existing aligned portrait mask.
- `assets/title.png`: existing original title artwork, unchanged.

Export with the existing local exporter:

```powershell
godot --path godot/cover --script res://export_cover.gd -- --scene=res://cover_refined.tscn --out=cover-refined.png
```

Validation: Godot 4.7.2 import and 1920 × 1080 rendered PNG export succeeded on
RTX 2060 using both OpenGL Compatibility and the project's default Vulkan
Forward+ renderer. Visual acceptance remains with the author.
