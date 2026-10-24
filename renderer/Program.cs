using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using FullExport;
using OpenTK;
using OpenTK.Graphics;
using OpenTK.Graphics.OpenGL;
using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using StorybrewEditor.Mapset;
using PixelFormat = System.Drawing.Imaging.PixelFormat;

CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
string Arg(string key, string fallback = null) {
    var i = Array.IndexOf(args, key);
    return i < 0 ? fallback : i + 1 < args.Length ? args[i + 1] : throw new ArgumentException(key);
}
var project = Path.GetFullPath(Arg("--project", Environment.CurrentDirectory));
var output = Path.GetFullPath(Arg("--out", Path.Combine(project, "output")));
var fps = int.Parse(Arg("--fps", "24"));
var start = double.Parse(Arg("--start", "0"));
var end = double.Parse(Arg("--end", "111621.723"));
var width = int.Parse(Arg("--width", "1920"));
var height = int.Parse(Arg("--height", "1080"));
var crf = Arg("--crf", "10");
var bitrate = Arg("--bitrate", null);
var encoderThreads = int.Parse(Arg("--threads", "1"));
if (fps <= 0 || end <= start || width <= 0 || height <= 0 || encoderThreads <= 0) throw new ArgumentException("Invalid video range, size, or encoder thread count");
Directory.CreateDirectory(output);
var user = File.ReadAllText(Path.Combine(project, ".sbrew/user.yaml"));
var mapset = Regex.Match(user, "(?m)^MapsetPath: \"([^\"]+)\"").Groups[1].Value;
var beatmapPath = Directory.GetFiles(mapset, "*.osu").Single();
var beatmap = EditorBeatmap.Load(beatmapPath);
var audio = Path.Combine(mapset, beatmap.AudioFilename);
var durationProbe = new ProcessStartInfo("ffprobe") { RedirectStandardOutput = true, UseShellExecute = false, CreateNoWindow = true };
foreach (var a in new[] { "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", audio }) durationProbe.ArgumentList.Add(a);
using var probe = Process.Start(durationProbe);
var audioDuration = double.Parse(probe.StandardOutput.ReadToEnd()) * 1000;
probe.WaitForExit();
if (probe.ExitCode != 0) throw new Exception("Audio duration probe failed");
var texts = Directory.GetFiles(Path.Combine(project, ".sbrew"), "effect.*.yaml").ToDictionary(p => ".sbrew/" + Path.GetFileName(p), File.ReadAllText);
var configs = ProjectConfig.Read(texts);
var order = Regex.Matches(File.ReadAllText(Path.Combine(project, ".sbrew/index.yaml")), "(?m)^  - \"([^\"]+)\"").Select(m => m.Groups[1].Value).ToList();
var assembly = Assembly.LoadFrom(Path.GetFullPath(Arg("--dll", Path.Combine(project, "bin/Debug/net8.0-windows/storyboard.dll"))));
using var context = new HostContext(project, mapset) { SelectedBeatmap = beatmap, Duration = audioDuration };
foreach (var config in configs.Where(c => c.Layers.Any(l => l.Visible))) {
    var type = assembly.GetTypes().Single(t => t.Name == config.Script && typeof(StoryboardObjectGenerator).IsAssignableFrom(t));
    var effect = (StoryboardObjectGenerator)Activator.CreateInstance(type);
    config.Apply(effect);
    context.ActiveEffect = config.File;
    context.ActiveLayers = config.Layers;
    effect.Generate(context);
    Console.WriteLine($"Generated {config.Name}");
}
var layers = context.Layers.Cast<HostLayer>().Where(l => l.Visible).OrderBy(l => l.ExportLayer).ThenBy(l => {
    var i = order.IndexOf(l.ConfigId);
    if (i < 0) throw new Exception("Generated layer missing from index: " + l.Identifier);
    return i;
}).ToList();
var sprites = layers.SelectMany(l => l.Sprites).ToList();
var beatmapStem = Path.GetFileNameWithoutExtension(beatmapPath);
var osbName = Regex.Replace(beatmapStem, @"\s+\[[^\]]*\]$", "") + ".osb";
var osb = Path.Combine(output, osbName);
using (var writer = new StreamWriter(osb, false, new UTF8Encoding(false))) {
    writer.WriteLine("[Events]");
    var transform = new StoryboardTransform(null, Vector2.Zero, Vector2.Zero, 0, 1);
    var settings = new ExportSettings { UseFloatForTime = user.Contains("ExportTimeAsFloatingPoint: Yes") };
    foreach (var layer in layers) {
        writer.WriteLine("// " + layer.Identifier);
        foreach (var sprite in layer.Sprites) sprite.WriteOsb(writer, settings, layer.ExportLayer, transform, CancellationToken.None);
    }
}
var references = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
foreach (var line in File.ReadLines(osb)) {
    if (!line.StartsWith("Sprite,") && !line.StartsWith("Animation,")) continue;
    var path = Regex.Match(line, "\"([^\"]+)\"").Groups[1].Value.Replace('\\', '/');
    if (line.StartsWith("Animation,")) throw new NotSupportedException("Animation packaging requires frame expansion");
    references.Add(path);
}
foreach (var path in references) if (!File.Exists(Path.Combine(mapset, path))) throw new FileNotFoundException("Missing texture", path);
File.WriteAllText(Path.Combine(output, "export.json"), JsonSerializer.Serialize(new {
    project, mapset, beatmap = beatmapPath, audio, audioDuration, osb, fps, width, height, start, end,
    bitrate = bitrate ?? $"CRF {crf}", encoderThreads,
    sprites = sprites.Count, textures = references.Count,
    layers = layers.Select(l => new { l.Identifier, l.ConfigId, layer = l.ExportLayer.ToString(), sprites = l.Sprites.Count }),
    references = references.OrderBy(p => p).ToArray(), warnings = context.Warnings
}, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"OSB ready: {sprites.Count} sprites / {references.Count} textures / {layers.Count} layers");
if (args.Contains("--export-only")) return;

// OpenTK uses the host GPU with osu!'s standard alpha/additive sprite blending.
using var window = new GameWindow(width, height, GraphicsMode.Default, "Storybrew full export", GameWindowFlags.Default, DisplayDevice.Default, 2, 1, GraphicsContextFlags.Default);
window.Visible = false;
window.MakeCurrent();
window.VSync = VSyncMode.Off;
GL.Viewport(0, 0, width, height);
GL.MatrixMode(MatrixMode.Projection);
GL.LoadIdentity();
var margin = (width * 480.0 / height - 640) / 2;
GL.Ortho(-margin, 640 + margin, 480, 0, -1, 1);
GL.MatrixMode(MatrixMode.Modelview);
GL.LoadIdentity();
GL.Disable(EnableCap.DepthTest);
GL.Enable(EnableCap.Texture2D);
GL.Enable(EnableCap.Blend);
GL.ClearColor(0, 0, 0, 1);
GL.PixelStore(PixelStoreParameter.PackAlignment, 1);
Console.WriteLine("GPU: " + GL.GetString(StringName.Renderer));
var movie = Path.Combine(output, $"夜もすがら君想ふ_全片_{height}p{fps}.mp4");
var encode = new ProcessStartInfo("ffmpeg") { RedirectStandardInput = true, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true };
var frameCount = (int)Math.Ceiling((end - start) * fps / 1000);
var ffmpegArgs = new List<string> {
    "-hide_banner", "-loglevel", "warning", "-y", "-f", "rawvideo", "-pixel_format", "bgra",
    "-video_size", $"{width}x{height}", "-framerate", fps.ToString(), "-i", "pipe:0",
    "-ss", (start / 1000).ToString("R"), "-i", audio, "-map", "0:v:0", "-map", "1:a:0",
    "-vf", "vflip", "-c:v", "libx264", "-preset", "medium", "-threads", encoderThreads.ToString()
};
if (!string.IsNullOrEmpty(bitrate)) {
    ffmpegArgs.AddRange(new[] { "-b:v", bitrate, "-maxrate", bitrate, "-bufsize", "40M" });
} else {
    ffmpegArgs.AddRange(new[] { "-crf", crf });
}
ffmpegArgs.AddRange(new[] {
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k",
    "-t", ((end - start) / 1000).ToString("R"), "-movflags", "+faststart", movie
});
foreach (var a in ffmpegArgs) encode.ArgumentList.Add(a);
using var encoder = Process.Start(encode);
var encoderLog = encoder.StandardError.ReadToEndAsync();
var pixels = new byte[width * height * 4];
var textures = new Dictionary<string, (int Id, int Width, int Height)>(StringComparer.OrdinalIgnoreCase);
var timer = Stopwatch.StartNew();
try {
    for (var n = 0; n < frameCount; n++) {
        var time = start + n * 1000.0 / fps;
        GL.Clear(ClearBufferMask.ColorBufferBit);
        foreach (var sprite in sprites) {
            if (time + .000001 < sprite.StartTime || time - .000001 > sprite.EndTime) continue;
            var alpha = (float)(double)sprite.OpacityAt(time);
            if (alpha <= 0) continue;
            var scale = (Vector2)sprite.ScaleAt(time);
            if (scale.X == 0 || scale.Y == 0) continue;
            var path = sprite.GetTexturePathAt(time);
            if (!textures.TryGetValue(path, out var texture)) {
                using var image = new Bitmap(Path.Combine(mapset, path));
                var bits = image.LockBits(new Rectangle(0, 0, image.Width, image.Height), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
                var id = GL.GenTexture();
                GL.BindTexture(TextureTarget.Texture2D, id);
                GL.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureMinFilter, (int)TextureMinFilter.Linear);
                GL.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureMagFilter, (int)TextureMagFilter.Linear);
                GL.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureWrapS, (int)TextureWrapMode.ClampToEdge);
                GL.TexParameter(TextureTarget.Texture2D, TextureParameterName.TextureWrapT, (int)TextureWrapMode.ClampToEdge);
                GL.TexImage2D(TextureTarget.Texture2D, 0, PixelInternalFormat.Rgba, image.Width, image.Height, 0, OpenTK.Graphics.OpenGL.PixelFormat.Bgra, PixelType.UnsignedByte, bits.Scan0);
                image.UnlockBits(bits);
                texture = (id, image.Width, image.Height);
                textures.Add(path, texture);
            }
            GL.BindTexture(TextureTarget.Texture2D, texture.Id);
            GL.BlendFunc(BlendingFactorSrc.SrcAlpha, sprite.AdditiveAt(time) ? BlendingFactorDest.One : BlendingFactorDest.OneMinusSrcAlpha);
            var pos = (Vector2)sprite.PositionAt(time);
            var color = sprite.ColorAt(time);
            var origin = OsbSprite.GetOriginVector(sprite.Origin, texture.Width, texture.Height);
            GL.PushMatrix();
            GL.Translate(pos.X, pos.Y, 0);
            GL.Rotate((double)sprite.RotationAt(time) * 180 / Math.PI, 0, 0, 1);
            GL.Scale(scale.X * (sprite.FlipHAt(time) ? -1 : 1), scale.Y * (sprite.FlipVAt(time) ? -1 : 1), 1);
            GL.Translate(-origin.X, -origin.Y, 0);
            GL.Color4(color.R / 255f, color.G / 255f, color.B / 255f, alpha);
            GL.Begin(PrimitiveType.Quads);
            GL.TexCoord2(0, 0); GL.Vertex2(0, 0);
            GL.TexCoord2(1, 0); GL.Vertex2(texture.Width, 0);
            GL.TexCoord2(1, 1); GL.Vertex2(texture.Width, texture.Height);
            GL.TexCoord2(0, 1); GL.Vertex2(0, texture.Height);
            GL.End();
            GL.PopMatrix();
        }
        GL.ReadPixels(0, 0, width, height, OpenTK.Graphics.OpenGL.PixelFormat.Bgra, PixelType.UnsignedByte, pixels);
        encoder.StandardInput.BaseStream.Write(pixels);
        if (n % fps == 0) Console.WriteLine($"frame={n}/{frameCount} song={time/1000:F3}s elapsed={timer.Elapsed.TotalSeconds:F1}s");
        // Avoid keeping cinematic sequences and fine-angle portrait masks in VRAM.
        while (textures.Count > 24) {
            var oldest = textures.First(); GL.DeleteTexture(oldest.Value.Id); textures.Remove(oldest.Key);
        }
    }
} finally {
    encoder.StandardInput.Close();
    foreach (var texture in textures.Values) GL.DeleteTexture(texture.Id);
}
encoder.WaitForExit();
File.WriteAllText(Path.Combine(output, "ffmpeg.log"), encoderLog.GetAwaiter().GetResult());
if (encoder.ExitCode != 0) throw new Exception("FFmpeg failed, see ffmpeg.log");
Console.WriteLine($"Video ready: {movie}; {frameCount} frames; elapsed={timer.Elapsed}");
