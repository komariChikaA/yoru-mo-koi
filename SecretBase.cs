using OpenTK;
using OpenTK.Graphics;
using StorybrewCommon.Animations;
using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using StorybrewCommon.Subtitles;
using System;
using System.Collections.Generic;
using System.IO;
using System.Globalization;

namespace StorybrewScripts
{
    // Remember first; archive second. The CG is always exactly one whole sprite.
    public class SecretBase : StoryboardObjectGenerator
    {
        const int Start = 14500;
        const int Duration = MemoryJourney.Hurt - Start; // Keep overscanned circles until they have fully left the viewport.
        const int BloomAt = 200; // 14.700s, before the same title-to-liquid continuation.
        const int LiquidFullAt = 2000;
        const int PictureAt = 2000;
        const int PrintCompleteAt = 4140;
        const int MoveAt = 4500;
        const int MoveEnd = 5400;
        const int ThreadAt = MoveAt + 360; // Begin after the camera visibly starts its pullback.
        const int PageTextAt = MoveAt + 700; // Wait until the left text group is inside the camera viewport.
        const float ThreadThickness = 3.4f;
        const float CordTextureHeight = ThreadThickness + 8.6f; // 96px texture = 12px including soft margins.
        const float ImageScale = 610f / 640f;
        const float PaperWidth = 626f;
        const float PaperHeight = 400f;
        const float Zoom = 0.54f; // The hero and following CGs share a narrow warm-white matte.
        const float ImageY = 950f;
        const float FinalX = 480f;
        const float FinalY = 234f;
        const float SectionCentreY = 422f;
        const string Pixel = "sb/px.png";
        const string PrintAssets = "sb/memory-print/";

        StoryboardLayer layer;
        StageCamera camera;
        RotaryPrintReveal.Settings print;
        readonly List<OsbSprite> scene = new List<OsbSprite>();
        int At(int time) => Start + time;

        public override void Generate()
        {
            layer = GetLayer("Memory");
            scene.Clear();
            print = new RotaryPrintReveal.Settings
            {
                Start = At(PictureAt), Centre = new Vector2(320, ImageY), Scale = ImageScale,
                CoarsePath = PrintAssets + "coarse.png", DetailPath = PrintAssets + "details.png",
                SweepDelay = 260, SweepDuration = 640, Pause = 80,
                SweepDurations = new[] { 800, 480, 440 }, SweepEasing = OsbEasing.InOutCubic,
                Paper = System.Drawing.Color.FromArgb(238, 221, 184), // #EEDDB8: same pale-cream seed below い.
                FinalPaper = System.Drawing.Color.FromArgb(255, 252, 246),
                PaperFadeStart = At(BloomAt), PaperFadeEnd = At(PrintCompleteAt),
                PaperGrainOpacity = 0,
            };
            CameraShots();
            Background();
            TitleHandoff();
            EditorialMaterials(); // Final-page surface, below the narrative rope and photograph.
            MemoryThread(); // One path below the photograph, with two actual gaps.
            PhotoPaper();
            Picture();
            PrintMemory();
            Liquid(); // Foreground wash clears; the same stock remains as the photograph paper.
            Words();
            foreach (var sprite in scene)
                sprite.Fade(At(Duration), 0);
            MemoryJourney.Generate(layer); // Continue the same canvas along the bell cords.
        }

        OsbSprite Sprite(string path, OsbOrigin origin = OsbOrigin.Centre)
        {
            var sprite = layer.CreateSprite(path, origin);
            scene.Add(sprite);
            sprite.Fade(At(-16), 0);
            return sprite;
        }

        void Tint(OsbSprite sprite, int time, int r, int g, int b)
            => sprite.Color(At(time), r / 255.0, g / 255.0, b / 255.0);

        void Appear(OsbSprite sprite, int from, int ms, double opacity = 1)
        {
            sprite.Fade(OsbEasing.OutCubic, At(from), At(from + ms), 0, opacity);
            sprite.Fade(At(Duration - 1), opacity);
        }

        void Background()
        {
            var paper = layer.CreateSprite(Pixel, OsbOrigin.Centre);
            // One screen-sized ground spans both pages, behind all their decoration.
            Tint(paper, 0, 247, 244, 238);
            paper.Color(OsbEasing.InOutCubic, At(BloomAt + 320), At(BloomAt + 780),
                247 / 255.0, 244 / 255.0, 238 / 255.0, 245 / 255.0, 239 / 255.0, 228 / 255.0);
            paper.Color(OsbEasing.InOutCubic, At(MoveAt + 80), At(MoveEnd),
                245 / 255.0, 239 / 255.0, 228 / 255.0, 250 / 255.0, 249 / 255.0, 246 / 255.0);
            paper.Move(At(0), 320, 240);
            paper.ScaleVec(At(0), 862, 488); // Overscan the viewport edges during the whole pan.
            paper.Fade(At(0), 1);
            paper.Fade(MemoryJourney.End - 1, 1);
            paper.Fade(MemoryJourney.End, 0);
            // The title/printing entrance keeps its light stock. The unified
            // soft pastel surface appears during the 19s pullback below.
        }

        void EditorialMaterials()
        {
            var ground = Sprite(MemoryJourney.CanvasAssets + "page-ground.png");
            ground.Move(At(MoveAt), 320, 240);
            ground.Fade(OsbEasing.InOutSine, At(MoveAt), At(MoveEnd), 0, 1);
            MemoryJourney.PanPageSprite(ground, At(Duration), 320, 240, 1);
            MemoryJourney.GenerateBackground(layer);
            SectionStrip(MemoryJourney.CanvasAssets + "front-strip.png", 1);
            BlueThread(); // Visible over the label, still below the photograph created afterward.
        }

        void SectionStrip(string path, double opacity)
        {
            var strip = Sprite(path);
            var position = PageWorld(320, SectionCentreY); // 80px high, with an 18px bottom breathing margin.
            Appear(strip, MoveAt + 180, 600, opacity);
            camera.PlaceKeys(strip, new[]
            {
                new StageCamera.Pose(At(MoveAt + 180), position.X, position.Y, 0.5f / Zoom),
                new StageCamera.Pose(At(Duration), position.X, position.Y, 0.5f / Zoom),
            });
        }

        void TitleHandoff()
        {
            // Reuse the real title textures at their exact 14.5s pose. This overlays the
            // old shot, sharing its slower 1800ms group scale without a handoff jump.
            foreach (var line in File.ReadAllLines(Path.Combine(MapsetPath, "sb/title/layout.txt")))
            {
                var fields = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (fields.Length < 4 || (fields[0] != "glyph" && fields[0] != "dot" && fields[0] != "en")) continue;
                var path = "sb/title/" + fields[1];
                var raw = new Vector2(float.Parse(fields[2], CultureInfo.InvariantCulture), float.Parse(fields[3], CultureInfo.InvariantCulture));
                var sprite = Sprite(path);
                sprite.Fade(At(0), 1);
                if (fields[0] == "dot" && fields[1] == "d12.png")
                {
                    sprite.Fade(At(BloomAt), 0); // The liquid's first frame continues the seed here.
                    TitlePose(sprite, raw, 0, BloomAt, t => 1);
                    continue;
                }
                if (fields[0] != "dot")
                {
                    sprite.Fade(OsbEasing.OutCubic, At(BloomAt + 75), At(BloomAt + 270), 1, 0.30);
                    sprite.Fade(OsbEasing.InQuad, At(BloomAt + 390), At(BloomAt + 650), 0.30, 0);
                    TitlePose(sprite, raw, 0, BloomAt + 750, t => 1);
                    continue;
                }
                var image = GetMapsetBitmap(path);
                var color = image.GetPixel(image.Width / 2, image.Height / 2);
                var delay = BloomAt + (int)(Math.Abs(raw.X - 627.8) / 9);
                sprite.Fade(OsbEasing.OutCubic, At(delay + 90), At(delay + 360), 1, 0);
                TitlePose(sprite, raw, 0, delay + 360, t =>
                    1 + 1.9f * (float)OsbEasing.OutExpo.Ease(Math.Max(0, Math.Min(1, (t - delay) / 240.0))));

                // Solid cores swell; softer colored edges visibly bleed into the white page.
                var halo = Sprite("sb/memory-flow/halo.png");
                Tint(halo, delay, color.R, color.G, color.B);
                halo.Fade(OsbEasing.OutCubic, At(delay), At(delay + 80), 0, 0.48);
                halo.Fade(OsbEasing.InCubic, At(delay + 120), At(delay + 390), 0.48, 0);
                TitlePose(halo, raw, delay, delay + 390, t =>
                    0.02f + 1.65f * (float)OsbEasing.OutExpo.Ease(Math.Max(0, Math.Min(1, (t - delay) / 280.0))));
            }
            var brownHalo = Sprite("sb/memory-flow/halo.png");
            RotaryPrintReveal.ApplyPaperColor(brownHalo, print);
            brownHalo.Fade(OsbEasing.OutCubic, At(BloomAt), At(BloomAt + 100), 0, 0.25);
            brownHalo.Fade(OsbEasing.InCubic, At(BloomAt + 200), At(BloomAt + 400), 0.25, 0);
            TitlePose(brownHalo, new Vector2(627.8f, 295.4f), BloomAt, BloomAt + 440,
                t => 0.02f + 0.70f * (float)OsbEasing.OutCubic.Ease(Math.Min(1, (t - BloomAt) / 180.0)));
        }

        void TitlePose(OsbSprite sprite, Vector2 raw, int from, int to, Func<int, float> localScale)
        {
            var poses = new List<StageCamera.Pose>();
            for (var time = from; time <= to; time += 20)
            {
                var u = Math.Max(0, Math.Min(1, (Start + time - 13156) / 1800.0));
                var scale = (float)(1 - 0.2 * Math.Sin(u * Math.PI / 2));
                poses.Add(new StageCamera.Pose(At(time), 320 + (raw.X - 320) * scale,
                    240 + (raw.Y - 240) * scale, scale * localScale(time)));
            }
            // Camera zoom stays 1 throughout the title handoff. Emit its translation
            // separately so the camera optimizer cannot flatten the small scale settle.
            var groupOnly = poses.TrueForAll(p => Math.Abs(localScale(p.Time - Start) - 1) < .000001);
            for (var i = 1; i < poses.Count; i++)
            {
                var a = poses[i - 1]; var b = poses[i];
                var pa = camera.ToScreen(a.Time, a.X, a.Y);
                var pb = camera.ToScreen(b.Time, b.X, b.Y);
                sprite.Move(OsbEasing.None, a.Time, b.Time, pa.x, pa.y, pb.x, pb.y);
                if (!groupOnly) sprite.Scale(OsbEasing.None, a.Time, b.Time, a.ScaleX, b.ScaleX);
            }
            if (groupOnly)
                sprite.Scale(OsbEasing.OutSine, 13156, 14956, 1, .8);
        }

        void Liquid()
        {
            // The ball below い becomes a connected neck, pinches, accelerates,
            // lands and spreads as a damped height-field on the receiving photograph plane.
            foreach (var line in File.ReadAllLines(Path.Combine(MapsetPath, "sb/memory-flow/layout.txt")))
            {
                var fields = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                var time = BloomAt + int.Parse(fields[1], CultureInfo.InvariantCulture);
                var x = float.Parse(fields[2], CultureInfo.InvariantCulture);
                var y = float.Parse(fields[3], CultureInfo.InvariantCulture);
                var fluid = Sprite("sb/paper-material/flow/" + fields[0]);
                RotaryPrintReveal.ApplyPaperColor(fluid, print);
                fluid.Fade(At(time), 1);
                fluid.Fade(At(time + 20), 0);
                Carry(fluid, time, x, y, 1, 1, time + 20);
            }
            var filled = Sprite(Pixel);
            RotaryPrintReveal.ApplyPaperColor(filled, print);
            filled.Fade(At(LiquidFullAt), 1);
            filled.Fade(OsbEasing.InOutSine, At(PictureAt), At(PictureAt + 140), 1, 0);
            // Temporary foreground coverage clears on the original schedule. The
            // persistent stock below remains as the narrow photograph border.
            Carry(filled, LiquidFullAt, 320, ImageY, 854, 538, PictureAt + 140);
        }

        void LiquidStock()
        {
            var stock = Sprite(Pixel);
            RotaryPrintReveal.ApplyPaperColor(stock, print);
            stock.Fade(At(LiquidFullAt), 1);
            stock.Fade(At(Duration - 1), 1);
            Carry(stock, LiquidFullAt, 320, ImageY, PaperWidth, PaperHeight);
        }

        void PhotoPaper()
        {
            LiquidStock(); // The print stock becomes the same warm-white matte used later.
        }

        void Picture()
        {
            var photo = Sprite("sb/secret-base.png");
            photo.Fade(At(PictureAt), 1); // Fully hidden by stationary print masks.
            photo.Fade(At(Duration - 1), 1);
            Carry(photo, PictureAt, 320, ImageY, ImageScale, ImageScale);
        }

        void PrintMemory()
        {
            RotaryPrintReveal.Draw(this, camera, (path, origin) => Sprite(path, origin), print);
        }

        // CG, liquid, title, photograph margins, words and rope share this one world camera.
        // No independent CG Move/Scale tween: the photograph stays fixed at world y=950.
        void CameraShots()
        {
            camera = new StageCamera();
            camera.Cut(At(0), 320, 240);
            camera.Cut(At(BloomAt + 310), 320, 240);
            camera.Ease(At(BloomAt + 650), 320, 620, 1, 0, OsbEasing.InQuad);
            camera.Ease(At(BloomAt + 840), 320, ImageY, 1, 0, OsbEasing.OutCubic);
            // Keep the large central photograph fixed until printing and its hold finish.
            camera.Cut(At(MoveAt), 320, ImageY, 1);
            camera.Ease(At(MoveEnd), FinalFocusX, FinalFocusY, Zoom, 0, OsbEasing.InOutCubic);
            MemoryJourney.ApplyPan(camera, FinalFocusX, FinalFocusY, Zoom);
        }

        float FinalFocusX => 320 - (FinalX - 320) / Zoom;
        float FinalFocusY => ImageY - (FinalY - 240) / Zoom;

        void Carry(OsbSprite sprite, int from, float x, float y, float sx, float sy, int to = Duration)
            => camera.PlaceVec(sprite, At(from), At(to), x, y, sx, sy);

        Vector2 PageWorld(float x, float y)
            => new Vector2(FinalFocusX + (x - 320) / Zoom, FinalFocusY + (y - 240) / Zoom);

        void BlueThread()
        {
            var points = new List<Vector2>();
            Curve(points, new Vector2(-145, 58), new Vector2(92, 61), new Vector2(330, 57), new Vector2(542, 58), 58);
            // A gently tensioned bell cord: broad, unequal bends instead of pipe elbows.
            Curve(points, new Vector2(542, 58), new Vector2(590, 57), new Vector2(605, 74), new Vector2(603, 108), 14);
            Curve(points, new Vector2(603, 108), new Vector2(597, 204), new Vector2(594, 315), new Vector2(598, 392), 36);
            Curve(points, new Vector2(598, 392), new Vector2(599, 423), new Vector2(616, 432), new Vector2(642, 432), 12);
            // Follow the annotated rightward exit across the label's otherwise empty end.
            Curve(points, new Vector2(642, 432), new Vector2(686, 432), new Vector2(731, 432), new Vector2(780, 432), 20);
            DrawCord(points, "sb/memory-editorial/blue-cord.png", 12f, ThreadAt + 80,
                MemoryJourney.PenHandoff - At(ThreadAt + 80));
        }

        void DrawCord(List<Vector2> points, string texture, float textureHeight,
            int from, int duration, Func<Vector2, bool> isGap = null)
        {
            float total = 0;
            for (var i = 1; i < points.Count; i++) total += (points[i] - points[i - 1]).Length;
            float traveled = 0;
            for (var i = 1; i < points.Count; i++)
            {
                var delta = points[i] - points[i - 1];
                var length = delta.Length;
                var mid = points[i - 1] + delta * 0.5f;
                if (isGap != null && isGap(mid))
                {
                    traveled += length; // Narrative gaps remain part of the same drawing clock.
                    continue;
                }
                var a = PageWorld(points[i - 1].X, points[i - 1].Y);
                var start = from + (int)(duration * traveled / total);
                var stop = from + (int)(duration * (traveled + length) / total);
                var end = Math.Max(start + 16, stop);
                var strand = Sprite(texture, OsbOrigin.CentreLeft);
                // Full joined segments reveal through alpha, avoiding several
                // partly scaled stubs at the fast drawing head during pullback.
                strand.Fade(OsbEasing.None, At(start), At(end), 0, 1);
                strand.Fade(At(Duration - 1), 1);
                camera.PlaceKeys(strand, new[]
                {
                    new StageCamera.Pose(At(start), a.X, a.Y, (length + 1.8f) / 16f / Zoom, textureHeight / 96f / Zoom, Math.Atan2(delta.Y, delta.X)),
                    new StageCamera.Pose(At(Duration), a.X, a.Y, (length + 1.8f) / 16f / Zoom, textureHeight / 96f / Zoom, Math.Atan2(delta.Y, delta.X)),
                });
                traveled += length;
            }
        }

        void MemoryThread()
        {
            var points = new List<Vector2>();
            // Leave a short straight run after the gap; the corner itself stays continuous.
            Curve(points, new Vector2(-138, 104), new Vector2(110, 107), new Vector2(358, 102), new Vector2(606, 104), 66);
            Curve(points, new Vector2(606, 104), new Vector2(610, 104), new Vector2(614, 104), new Vector2(618, 104), 3);
            Curve(points, new Vector2(618, 104), new Vector2(636, 103), new Vector2(640, 124), new Vector2(635, 145), 16);
            // This vertical stem and the following bend are hidden beneath the photo.
            Curve(points, new Vector2(635, 145), new Vector2(625, 192), new Vector2(620, 238), new Vector2(622, 292), 22);
            Curve(points, new Vector2(622, 292), new Vector2(624, 319), new Vector2(620, 337), new Vector2(625, 350), 12);
            Curve(points, new Vector2(625, 350), new Vector2(629, 365), new Vector2(636, 370), new Vector2(650, 370), 12);
            Curve(points, new Vector2(650, 370), new Vector2(663, 372), new Vector2(677, 369), new Vector2(690, 370), 10);
            Curve(points, new Vector2(690, 370), new Vector2(709, 371), new Vector2(716, 383), new Vector2(714, 400), 12);
            Curve(points, new Vector2(714, 400), new Vector2(712, 419), new Vector2(714, 437), new Vector2(714, 455), 24);
            // A compact corner joins a level exit, matching the annotated bottom rule.
            Curve(points, new Vector2(714, 455), new Vector2(713, 466), new Vector2(728, 469), new Vector2(744, 469), 12);
            Curve(points, new Vector2(744, 469), new Vector2(756, 469), new Vector2(768, 469), new Vector2(779, 469), 6);
            DrawCord(points, "sb/memory-editorial/memory-cord.png", CordTextureHeight, ThreadAt,
                MemoryJourney.PenHandoff - At(ThreadAt),
                mid => (mid.X > 116 && mid.X < 138)
                    || (mid.X > 588 && mid.X < 618 && Math.Abs(mid.Y - 104) < 5) // Clear both sides of the blue cord; keep the bend continuous.
                    || (mid.Y > 422 && mid.Y < 444 && mid.X > 704)); // Clear the blue horizontal run at y432.
        }

        static void Curve(List<Vector2> path, Vector2 a, Vector2 b, Vector2 c, Vector2 d, int steps)
        {
            for (var i = path.Count == 0 ? 0 : 1; i <= steps; i++)
            {
                var t = i / (float)steps;
                var v = 1 - t;
                path.Add(a * (v * v * v) + b * (3 * v * v * t) + c * (3 * v * t * t) + d * (t * t * t));
            }
        }

        void Words()
        {
            var fonts = Environment.GetFolderPath(Environment.SpecialFolder.Fonts);
            var rounded = Path.Combine(ProjectPath, "assets", "fonts", "ZenMaruGothic-Medium.ttf");
            var serif = Path.Combine(fonts, "GARA.TTF");
            var mincho = Path.Combine(fonts, "yuminl.ttf");
            var title = LoadFont(PrintAssets + "memory-garamond-title", Face(serif, 122, 117, 89, 75));
            var label = LoadFont(PrintAssets + "memory-garamond-label", Face(serif, 40, 159, 128, 110));
            var prose = LoadFont(PrintAssets + "memory-mincho-light-prose", Face(mincho, 56, 142, 116, 100));
            // One left-aligned title/prose column, sharing the hero's vertical
            // centre. Small label, display serif, then two close lines.
            Line(label, "A CHILDHOOD HIDEAWAY", PageTextAt, -46, 158, 0.22f, 1);
            Line(title, "Secret Base", PageTextAt + 70, -48, 186, 0.40f, 1);
            Line(prose, "放課後、夢を持ち寄った。", PageTextAt + 220, -46, 270, 0.205f, 1);
            Line(prose, "僕らだけの、小さな隠れ家。", PageTextAt + 280, -46, 289, 0.205f, 1);
            var stripText = LoadFont(PrintAssets + "rounded-japanese", Face(rounded, 48, 110, 75, 58));
            const float stripScale = 0.34f;
            const float stripCentreY = 433f; // Same reading height as the following page.
            const string detail = "いつまでも覚えていられますように。";
            // FontTexture has the exact PNG size; reading our output as an input
            // adds a file dependency that retriggers this effect on every save.
            var leadImage = stripText.GetTexture("この想い出を、");
            var detailImage = stripText.GetTexture(detail);
            var leadWidth = leadImage.Width * stripScale;
            // A single typographic voice, with the original two entrance times.
            Line(stripText, "この想い出を、", MoveAt + 840, -48,
                stripCentreY + leadImage.Height * stripScale / 2, stripScale, 1, OsbOrigin.BottomLeft);
            Line(stripText, detail, MoveAt + 920, -48 + leadWidth + 4,
                stripCentreY + detailImage.Height * stripScale / 2, stripScale, 1, OsbOrigin.BottomLeft);
        }

        static FontDescription Face(string file, int size, int r, int g, int b)
            => new FontDescription { FontPath = file, FontSize = size,
                Color = new Color4((byte)r, (byte)g, (byte)b, (byte)255),
                Padding = new Vector2(3, 3), TrimTransparency = true };

        void Line(FontGenerator font, string text, int start, float x, float y, float scale, double alpha,
            OsbOrigin origin = OsbOrigin.CentreLeft)
        {
            var texture = font.GetTexture(text);
            var worldScale = scale / Zoom;
            var position = PageWorld(x, y);
            if (origin != OsbOrigin.BottomLeft) position += texture.OffsetFor(origin) * worldScale;
            var sprite = Sprite(texture.Path, origin);
            Appear(sprite, start, 200, alpha);
            var poses = new List<StageCamera.Pose>();
            for (var t = start; t <= start + 200; t += 20)
            {
                var progress = OsbEasing.OutCubic.Ease((t - start) / 200.0);
                poses.Add(new StageCamera.Pose(At(t), position.X, position.Y + (float)((1 - progress) * 7 / Zoom), worldScale));
            }
            poses.Add(new StageCamera.Pose(At(Duration), position.X, position.Y, worldScale));
            camera.PlaceKeys(sprite, poses);
        }
    }
}
