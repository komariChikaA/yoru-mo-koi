using OpenTK;
using StorybrewCommon.Animations;
using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;

namespace StorybrewScripts
{
    // Three continuous passes of a corner-pivoted printing bar. The caller keeps
    // one complete photograph underneath these stationary whole-image occluders.
    public static class RotaryPrintReveal
    {
        public sealed class Settings
        {
            public string CoarsePath, DetailPath;
            public string PaperGrainPath; // Optional material on masks only; never on the underlying CG.
            public double PaperGrainOpacity;
            public string CacheRoot = "sb/memory-print/cache";
            public int Start, SweepDelay = 260, SweepDuration = 640, Pause = 80, Step = 20;
            public int[] SweepDurations; // Optional three-pass clock; uniform duration remains supported.
            public OsbEasing SweepEasing = OsbEasing.InOutSine;
            public Vector2 Centre;
            public float Scale = 1;
            public Color Paper = Color.FromArgb(241, 233, 215);
            public Color? FinalPaper;
            public int PaperFadeStart, PaperFadeEnd;
            public float PivotInset = -4; // Negative places the axle just outside the photo.
            public int DurationOf(int pass) => SweepDurations == null ? SweepDuration : SweepDurations[pass];
            public int End => Start + SweepDelay + DurationOf(0) + DurationOf(1) + DurationOf(2) + 2 * Pause;
        }

        struct State { public int Pass; public double Progress, Angle; }

        // Flow masks, persistent stock and unprinted areas share one color clock.
        public static void ApplyPaperColor(OsbSprite sprite, Settings s)
        {
            if (s.FinalPaper.HasValue && s.PaperFadeEnd > s.PaperFadeStart)
            {
                var end = s.FinalPaper.Value;
                sprite.Color(OsbEasing.InOutSine, s.PaperFadeStart, s.PaperFadeEnd,
                    s.Paper.R / 255.0, s.Paper.G / 255.0, s.Paper.B / 255.0,
                    end.R / 255.0, end.G / 255.0, end.B / 255.0);
            }
            else sprite.Color(s.Start, s.Paper.R / 255.0, s.Paper.G / 255.0, s.Paper.B / 255.0);
        }

        static Color PaperAt(int time, Settings s)
        {
            if (!s.FinalPaper.HasValue || s.PaperFadeEnd <= s.PaperFadeStart) return s.Paper;
            var progress = OsbEasing.InOutSine.Ease(Math.Max(0, Math.Min(1,
                (time - s.PaperFadeStart) / (double)(s.PaperFadeEnd - s.PaperFadeStart))));
            var end = s.FinalPaper.Value;
            return Color.FromArgb(
                (int)Math.Round(s.Paper.R + (end.R - s.Paper.R) * progress),
                (int)Math.Round(s.Paper.G + (end.G - s.Paper.G) * progress),
                (int)Math.Round(s.Paper.B + (end.B - s.Paper.B) * progress));
        }

        public static void Draw(StoryboardObjectGenerator owner, StageCamera camera,
            Func<string, OsbOrigin, OsbSprite> create, Settings settings)
        {
            if (settings.SweepDurations != null && settings.SweepDurations.Length != 3)
                throw new ArgumentException("Specify exactly three printing pass durations.");
            if (settings.Step < 16 || settings.DurationOf(0) < settings.Step ||
                settings.DurationOf(1) < settings.Step || settings.DurationOf(2) < settings.Step)
                throw new ArgumentException("Printing samples must be at least 16ms apart.");
            if (settings.Scale <= 0 || settings.PivotInset > 0 || settings.Pause < 0 || settings.SweepDelay < 100)
                throw new ArgumentException("Use a positive scale, an outside corner pivot, and non-negative pauses.");
            using var coarseImage = new Bitmap(owner.GetMapsetBitmap(settings.CoarsePath));
            using var detailImage = new Bitmap(owner.GetMapsetBitmap(settings.DetailPath));
            int width = coarseImage.Width, height = coarseImage.Height;
            if (detailImage.Width != width || detailImage.Height != height)
                throw new ArgumentException("Printing stages must have identical dimensions.");
            var coarse = Pixels(coarseImage);
            var detail = Pixels(detailImage);
            byte[] grain = null;
            if (!string.IsNullOrEmpty(settings.PaperGrainPath))
            {
                using var grainImage = new Bitmap(owner.GetMapsetBitmap(settings.PaperGrainPath));
                if (grainImage.Width != width || grainImage.Height != height)
                    throw new ArgumentException("Paper grain must match the printing mask dimensions.");
                grain = Pixels(grainImage);
            }
            var px = width - settings.PivotInset;
            var py = height - settings.PivotInset;
            var key = CacheKey(coarse, detail, settings, width, height, grain);
            var relative = settings.CacheRoot.TrimEnd('/') + "/" + key + "/";
            var directory = Path.Combine(owner.MapsetPath, relative.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(directory);
            var times = new List<int>();
            for (var t = settings.Start; t < settings.End; t += settings.Step) times.Add(t);
            times.Add(settings.End);
            var angles = new double[width * height];
            var radii = new double[width * height];
            for (var y = 0; y < height; y++) for (var x = 0; x < width; x++)
            {
                var dx = x - px; var dy = y - py; var i = y * width + x;
                angles[i] = Math.Atan2(dy, dx);
                radii[i] = Math.Sqrt(dx * dx + dy * dy);
            }
            for (var frame = 0; frame < times.Count - 1; frame++)
            {
                var name = "state-" + frame.ToString("000") + ".png";
                var path = Path.Combine(directory, name);
                if (!File.Exists(path))
                {
                    var state = At(times[frame], settings);
                    var paper = PaperAt(times[frame], settings);
                    var output = new byte[coarse.Length];
                    for (var pixel = 0; pixel < angles.Length; pixel++)
                    {
                        double coverage;
                        if (state.Progress <= 0) coverage = 0;
                        else if (state.Progress >= 1) coverage = 1;
                        else
                        {
                            var signed = Math.Sin(state.Angle - angles[pixel]) * radii[pixel];
                            if (state.Pass == 1) signed = -signed;
                            coverage = Math.Max(0, Math.Min(1, 0.5 + signed / 1.5));
                        }
                        var i = pixel * 4;
                        if (state.Pass == 2)
                        {
                            for (var c = 0; c < 3; c++) output[i + c] = detail[i + c];
                            output[i + 3] = (byte)Math.Round(255 * (1 - coverage));
                        }
                        else
                        {
                            for (var c = 0; c < 3; c++)
                            {
                                var before = state.Pass == 0 ? PaperChannel(paper, c) : coarse[i + c];
                                var after = state.Pass == 0 ? coarse[i + c] : detail[i + c];
                                output[i + c] = (byte)Math.Round(before + (after - before) * coverage);
                            }
                            output[i + 3] = 255;
                        }
                        // Grain belongs to the printing surface. Existing mask alpha
                        // reveals the untouched original photograph beneath it.
                        if (grain != null)
                            for (var c = 0; c < 3; c++)
                                output[i + c] = (byte)Math.Round(output[i + c] +
                                    (grain[i + c] - output[i + c]) * settings.PaperGrainOpacity);
                    }
                    SavePixels(path, output, width, height);
                }
                var veil = create(relative + name, OsbOrigin.Centre);
                veil.Fade(times[frame], 1);
                veil.Fade(times[frame + 1], 0);
                camera.Place(veil, times[frame], times[frame + 1],
                    settings.Centre.X, settings.Centre.Y, settings.Scale);
            }
            Tool(owner, camera, create, settings, relative, directory, coarse, detail, width, height, px, py);
        }

        static State At(int time, Settings s)
        {
            var local = time - s.Start - s.SweepDelay;
            var pass = 0;
            while (pass < 2 && local >= s.DurationOf(pass) + s.Pause)
            {
                local -= s.DurationOf(pass) + s.Pause;
                pass++;
            }
            var raw = Math.Max(0, Math.Min(1, local / (double)s.DurationOf(pass)));
            var progress = s.SweepEasing.Ease(raw);
            return new State { Pass = pass, Progress = progress,
                Angle = -Math.PI + (pass == 1 ? 1 - progress : progress) * Math.PI / 2 };
        }

        static void Tool(StoryboardObjectGenerator owner, StageCamera camera,
            Func<string, OsbOrigin, OsbSprite> create, Settings s, string relative, string directory,
            byte[] coarse, byte[] detail, int width, int height, float px, float py)
        {
            // The capsule is a small geometric object, with a finite soft offset shadow.
            const int textureWidth = 800, textureHeight = 18;
            var bodyPath = Path.Combine(directory, "bar.png");
            var facePath = Path.Combine(directory, "bar-face.png");
            var shadowPath = Path.Combine(directory, "bar-shadow.png");
            if (!File.Exists(bodyPath))
            {
                using var barTexture = new Bitmap(textureWidth, textureHeight, PixelFormat.Format32bppArgb);
                using var graphics = Graphics.FromImage(barTexture);
                graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
                graphics.FillRectangle(Brushes.White, 8, 2, textureWidth - 16, 14);
                graphics.FillEllipse(Brushes.White, 1, 2, 14, 14);
                graphics.FillEllipse(Brushes.White, textureWidth - 15, 2, 14, 14);
                barTexture.Save(bodyPath, ImageFormat.Png);
            }
            if (!File.Exists(facePath))
            {
                // Put the bevel inside the same pivoted texture coordinates. It rotates
                // with the body natively, without sampled orbiting Move commands.
                using var faceTexture = new Bitmap(textureWidth, textureHeight, PixelFormat.Format32bppArgb);
                using var graphics = Graphics.FromImage(faceTexture);
                graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
                graphics.FillRectangle(Brushes.White, 8, 4, textureWidth - 16, 3);
                graphics.FillEllipse(Brushes.White, 6.5f, 4, 3, 3);
                graphics.FillEllipse(Brushes.White, textureWidth - 9.5f, 4, 3, 3);
                faceTexture.Save(facePath, ImageFormat.Png);
            }
            if (!File.Exists(shadowPath))
            {
                var pixels = new byte[textureWidth * 32 * 4];
                for (var y = 0; y < 32; y++) for (var x = 0; x < textureWidth; x++)
                {
                    var edge = Math.Min(1, Math.Min(x / 10.0, (textureWidth - 1 - x) / 10.0));
                    pixels[(y * textureWidth + x) * 4 + 3] = (byte)(95 * Math.Exp(-Math.Pow((y - 15.5) / 8, 2)) * edge);
                }
                SavePixels(shadowPath, pixels, textureWidth, 32);
            }
            var shadow = create(relative + "bar-shadow.png", OsbOrigin.CentreLeft);
            var bar = create(relative + "bar.png", OsbOrigin.CentreLeft);
            var edgeFace = create(relative + "bar-face.png", OsbOrigin.CentreLeft);
            var from = s.Start + s.SweepDelay - 100;
            var end = s.End + 120;
            var pivot = s.Centre + new Vector2((px - width / 2f) * s.Scale, (py - height / 2f) * s.Scale);
            var length = (float)Math.Sqrt(width * width + height * height) + 16;
            for (var time = from; time <= end; time += s.Step)
            {
                var state = At(time, s);
                var reach = Math.Min(px / Math.Max(0.001, -Math.Cos(state.Angle)),
                    py / Math.Max(0.001, -Math.Sin(state.Angle)));
                var sx = Math.Max(0, Math.Min(width - 1, (int)(px + Math.Cos(state.Angle) * reach * 0.52)));
                var sy = Math.Max(0, Math.Min(height - 1, (int)(py + Math.Sin(state.Angle) * reach * 0.52)));
                var source = state.Pass == 0 ? coarse : detail;
                var index = (sy * width + sx) * 4;
                var r = source[index + 2] / 255.0; var g = source[index + 1] / 255.0; var b = source[index] / 255.0;
                // Sample the region under the bar; the bevel stays a little lighter.
                bar.Color(time, r, g, b);
                edgeFace.Color(time, Math.Min(1, r + .19), Math.Min(1, g + .19), Math.Min(1, b + .19));
            }
            // Printing happens before camera motion. Emit one native eased rotation
            // per complete arc, rather than a series of 20ms linear rotation samples.
            var screenPivot = camera.ToScreen(from, pivot.X, pivot.Y);
            var screenAxis = camera.ToScreen(from, pivot.X + 1, pivot.Y);
            var axis = new Vector2(screenAxis.x - screenPivot.x, screenAxis.y - screenPivot.y);
            var zoom = axis.Length;
            var roll = Math.Atan2(axis.Y, axis.X);
            foreach (var sprite in new[] { shadow, bar, edgeFace })
            {
                var offset = sprite == shadow ? new Vector2(4, 6) * s.Scale : Vector2.Zero;
                var position = camera.ToScreen(from, pivot.X + offset.X, pivot.Y + offset.Y);
                var exitPosition = camera.ToScreen(end, pivot.X + offset.X + 24, pivot.Y + offset.Y + 8);
                sprite.Move(from, position.x, position.y);
                sprite.Move(OsbEasing.OutCubic, s.End, end, position.x, position.y, exitPosition.x, exitPosition.y);
                sprite.ScaleVec(from, length / textureWidth * s.Scale * zoom, s.Scale * zoom);
                sprite.Rotate(from, -Math.PI + roll);
                var sweepStart = s.Start + s.SweepDelay;
                for (var pass = 0; pass < 3; pass++)
                {
                    var a = pass == 1 ? -Math.PI / 2 : -Math.PI;
                    var b = pass == 1 ? -Math.PI : -Math.PI / 2;
                    sprite.Rotate(s.SweepEasing, sweepStart, sweepStart + s.DurationOf(pass), a + roll, b + roll);
                    sweepStart += s.DurationOf(pass) + s.Pause;
                }
                sprite.Fade(OsbEasing.OutCubic, from, from + 100, 0, 1);
                sprite.Fade(OsbEasing.InCubic, s.End, end, 1, 0);
            }
        }

        static byte PaperChannel(Color paper, int channel) => channel == 0 ? paper.B : channel == 1 ? paper.G : paper.R;

        static byte[] Pixels(Bitmap source)
        {
            using var bitmap = new Bitmap(source.Width, source.Height, PixelFormat.Format32bppArgb);
            using (var graphics = Graphics.FromImage(bitmap)) graphics.DrawImageUnscaled(source, 0, 0);
            var bytes = new byte[bitmap.Width * bitmap.Height * 4];
            var data = bitmap.LockBits(new Rectangle(0, 0, bitmap.Width, bitmap.Height), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            try { for (var y = 0; y < bitmap.Height; y++) Marshal.Copy(data.Scan0 + y * data.Stride, bytes, y * bitmap.Width * 4, bitmap.Width * 4); }
            finally { bitmap.UnlockBits(data); }
            return bytes;
        }

        static void SavePixels(string path, byte[] bytes, int width, int height)
        {
            using var bitmap = new Bitmap(width, height, PixelFormat.Format32bppArgb);
            var data = bitmap.LockBits(new Rectangle(0, 0, width, height), ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
            try { for (var y = 0; y < height; y++) Marshal.Copy(bytes, y * width * 4, data.Scan0 + y * data.Stride, width * 4); }
            finally { bitmap.UnlockBits(data); }
            bitmap.Save(path, ImageFormat.Png);
        }

        static string CacheKey(byte[] coarse, byte[] detail, Settings s, int width, int height, byte[] grain)
        {
            using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
            hash.AppendData(coarse); hash.AppendData(detail);
            if (grain != null) hash.AppendData(grain);
            var model = string.Join("|", "rotary-print-v3", width, height, s.SweepDelay,
                s.DurationOf(0), s.DurationOf(1), s.DurationOf(2), s.SweepEasing,
                s.Pause, s.Step, s.PivotInset.ToString("R", CultureInfo.InvariantCulture), s.Paper.ToArgb(),
                s.FinalPaper?.ToArgb(), s.PaperFadeStart - s.Start, s.PaperFadeEnd - s.Start,
                s.PaperGrainOpacity.ToString("R", CultureInfo.InvariantCulture));
            hash.AppendData(Encoding.UTF8.GetBytes(model));
            return BitConverter.ToString(hash.GetHashAndReset()).Replace("-", "").Substring(0, 16).ToLowerInvariant();
        }
    }
}
