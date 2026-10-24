"""Package the exported Storybrew commands and their referenced mapset assets."""
import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path
from compress_osb import optimize_osb

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
parser.add_argument("--install", action="store_true")
args = parser.parse_args()
output = args.output.resolve()
data = json.loads((output / "export.json").read_text(encoding="utf-8"))
mapset = Path(data["mapset"])
osb = Path(data["osb"])
raw_texture_references = set(data["references"])
raw_osb = output / (osb.name + ".uncompressed")
if not raw_osb.is_file():
    shutil.copy2(osb, raw_osb)
compressed_osb = output / (osb.name + ".compressed.tmp")
compression_stats = optimize_osb(raw_osb, compressed_osb)
if compressed_osb.stat().st_size >= raw_osb.stat().st_size:
    compressed_osb.unlink()
    raise ValueError("OSB optimizer did not reduce file size")
osb.write_bytes(compressed_osb.read_bytes())
compressed_osb.unlink()
texture_references = set()
for line in osb.read_text(encoding="utf-8-sig").splitlines():
    if not line.startswith(("Sprite,", "Animation,")):
        continue
    match = re.search(r'"([^"]+)"', line)
    if match:
        texture_references.add(match.group(1).replace("\\", "/"))
if not texture_references:
    raise ValueError("Compressed OSB has no texture references")
(output / "compression-check.json").write_text(json.dumps({
    "original_osb": str(raw_osb),
    "original_bytes": raw_osb.stat().st_size,
    "compressed_bytes": osb.stat().st_size,
    **compression_stats,
    "texture_references_before": len(raw_texture_references),
    "texture_references_after": len(texture_references),
    "unused_textures_removed": len(raw_texture_references - texture_references),
}, ensure_ascii=False, indent=2), encoding="utf-8")
entries = {path: mapset / path for path in texture_references}
beatmap = Path(data["beatmap"])
entries[beatmap.name] = beatmap
audio = Path(data["audio"])
entries[audio.name] = audio
# Include the beatmap's background and optional sound samples as well.
text = beatmap.read_text(encoding="utf-8-sig")
for match in re.finditer(r'(?m)^(?:0,0|Sample,[^,]+,[^,]+),"([^"]+)"', text):
    path = match.group(1).replace("\\", "/")
    entries[path] = mapset / path
entries[osb.name] = osb

# Ensure standard osu! / osu!lazer naming is also present in the package
m_artist = re.search(r"^Artist:(.*)$", text, re.M)
m_title = re.search(r"^Title:(.*)$", text, re.M)
m_creator = re.search(r"^Creator:(.*)$", text, re.M)
meta_artist = m_artist.group(1).strip() if m_artist else ""
meta_title = m_title.group(1).strip() if m_title else ""
meta_creator = m_creator.group(1).strip() if m_creator else ""
# Storybrew binds its OSB to the selected chart basename before [difficulty].
std_base = re.sub(r"\s+\[[^\]]*\]$", "", beatmap.stem) + ".osb"
entries.pop(osb.name, None)
entries[std_base] = osb
for name, path in entries.items():
    if not path.is_file():
        raise FileNotFoundError(path)
    if name.startswith("/") or ".." in Path(name).parts:
        raise ValueError(f"Invalid archive path: {name}")

archive = output / "夜もすがら君想ふ_全片.osz"
temporary = archive.with_suffix(".osz.tmp")
with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
    for name, path in sorted(entries.items()):
        z.write(path, name)
with zipfile.ZipFile(temporary) as z:
    bad = z.testzip()
    if bad:
        raise ValueError(f"ZIP CRC failed: {bad}")
    if set(z.namelist()) != set(entries):
        raise ValueError("Archive entries do not match export references")
    if z.read(osb.name) != osb.read_bytes():
        raise ValueError("Archive OSB differs from export")
temporary.replace(archive)

if args.install:
    installed = mapset / std_base
    if installed.exists() and installed.read_bytes() != osb.read_bytes():
        shutil.copy2(installed, output / (osb.name + ".previous"))
    shutil.copy2(osb, installed)
result = {"archive": str(archive), "entries": len(entries), "bytes": archive.stat().st_size,
          "crc": "passed", "texture_references": len(texture_references),
          "installed_osb": str(mapset / std_base) if args.install else None,
          "osb_uncompressed_in_archive": False}
(output / "package-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
