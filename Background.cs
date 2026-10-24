using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;

namespace StorybrewScripts
{
    public class Background : StoryboardObjectGenerator
    {
        private const float MarkX = 320f;
        private const float MarkY = 240f;
        private const int IntroLeave = 13000;
        private const int IntroExitMs = 1400;
        private const int IntroEnd = IntroLeave + IntroExitMs;
        private int characterLandingTime;
        // The wipe starts at 12.5s, while the intro is still in place, then opens the next picture.
        private const int BandCount = 8;
        private const int BandDrawMs = 208;
        private const int BandStaggerMs = 48;
        private const int BandHoldMs = 112;
        private const int BandShrinkMs = 192;
        private const int BandGapMs = 48;
        private const int BandStart = 12500;
        private const int BandCoverEnd = BandStart + BandDrawMs + (BandCount - 1) * BandStaggerMs;
        private const int BandShrinkStart = BandCoverEnd + BandHoldMs;
        private const int BandRevealEnd = BandShrinkStart + BandShrinkMs + (BandCount - 1) * BandGapMs;
        private const int BandLength = 969;
        private const int BandPitch = 128;
        private const float BandScaleX = 1.15f;
        private const float BandScaleY = 1.45f;
        // Same 45° as bg_0328.png: each stripe runs from the top-right toward the bottom-left.
        private const float BandTheta = 45f * (float)Math.PI / 180f;
        // Title card. Sprites are already at screen size. The group pivots on the logo center.
        private const float TitleX = 320f;
        private const float TitleY = 240f;
        private const int TitleJoinMs = 650;
        private const int TitleShowMs = 1000;
        private const int TitleHoldMs = 1600;
        private const int TitleDriftMs = 1800;
        private const float TitleSettleScale = 0.80f;

        private void CreateLogo(StoryboardLayer layer)
            => TitleBumper.Logo(this, layer);

        private void CreateDiagonalGrid(StoryboardLayer layer)
            => TitleBumper.Grid(layer);

        private void CreateSquareField(StoryboardLayer layer)
            => TitleBumper.DepartingSquares(layer);

        private int CreateCredits(StoryboardLayer layer)
        {
            // Music lasts 2.5s from the first letter to the last one gone.
            // Movie starts 0.8s after that. Its exit uses the same per-letter timing.
            const int stagger = 48;
            const int exitLen = 260;
            const int life = 2500;
            const int musicEnter = 2400;
            var musicCount = CountCreditGlyphs("music");
            var musicExit = musicEnter + life - Math.Max(0, musicCount - 1) * stagger - exitLen;
            PlaceCreditLine(layer, "music", musicEnter, musicExit, exitLen);
            var musicEnd = musicExit + Math.Max(0, musicCount - 1) * stagger + exitLen;
            var movieEnter = musicEnd + 800;
            var movieExit = movieEnter + (musicExit - musicEnter);
            PlaceCreditLine(layer, "movie", movieEnter, movieExit, exitLen);
            var movieCount = CountCreditGlyphs("movie");
            return movieExit + Math.Max(0, movieCount - 1) * stagger + exitLen;
        }

        private int CountCreditGlyphs(string name)
        {
            var layoutPath = Path.Combine(MapsetPath, "sb", "credit", name + ".txt");
            var count = 0;
            foreach (var line in File.ReadAllLines(layoutPath))
                if (!string.IsNullOrWhiteSpace(line)) count++;
            return count;
        }

        private void PlaceCreditLine(StoryboardLayer layer, string name, int enter, int exit, int exitLen)
        {
            var layoutPath = Path.Combine(MapsetPath, "sb", "credit", name + ".txt");
            var lines = File.ReadAllLines(layoutPath);
            const float baseY = 272f;
            const int drop = 420;
            const int stagger = 48;
            const int fadeOut = 100;
            const float creditScale = 0.5f;
            var index = 0;
            foreach (var line in lines)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                var parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                var glyph = GetMapsetBitmap(BooksEditorial.CreditPath(parts[0]));
                var visualW = glyph == null ? 0f : glyph.Width * creditScale;
                var rawX = 320f + float.Parse(parts[1], CultureInfo.InvariantCulture);
                var x = visualW > 0f ? (float)Math.Round(rawX - visualW / 2f) + visualW / 2f : rawX;
                var t = enter + index * stagger;
                var leave = exit + index * stagger;
                var sprite = layer.CreateSprite(BooksEditorial.CreditPath(parts[0]), OsbOrigin.BottomCentre);
                sprite.MoveX(t, x);
                sprite.MoveY(OsbEasing.OutBack, t, t + drop, baseY - 86f, baseY);
                sprite.Fade(t, t + 80, 0, 1);
                sprite.Scale(t, creditScale);
                sprite.Rotate(OsbEasing.In, leave, leave + exitLen, 0, 70.0 * Math.PI / 180.0);
                sprite.Scale(OsbEasing.In, leave, leave + exitLen, creditScale, 0);
                sprite.Fade(leave + exitLen - fadeOut, leave + exitLen, 1, 0);
                index++;
            }
        }

        private void CreateStarCut(StoryboardLayer layer, int movieEnd)
        {
            // Movie has already finished. Times below are offsets from that moment.
            var t0 = movieEnd;
            const float cx = 320f;
            const float cy = 240f;
            const float cover = 3.45f;
            const int burst = 250;
            const int yellowEnd = 500;
            const int starDur = 460;
            const int stagger = 180;
            const int reveal = yellowEnd + stagger + starDur - 50;
            const int revealDur = 600;

            var scene = t0 + reveal;
            // The scene is already underneath. The stars above it open onto the character and shelf.
            CreateIntroStage(layer, scene, t0 + yellowEnd);

            double[] rayDeg = { 45, 135, 225, 315 };
            foreach (var deg in rayDeg)
            {
                var a = deg * Math.PI / 180.0;
                var ray = layer.CreateSprite("sb/ray.png", OsbOrigin.Centre);
                ray.Color(t0, 227/255f, 201/255f, 126/255f);
                ray.Rotate(t0, a + Math.PI / 2.0);
                ray.Fade(t0, t0 + yellowEnd, 1, 1);
                ray.Move(
                    OsbEasing.OutCubic, t0, t0 + burst,
                    cx + (float)(46 * Math.Cos(a)), cy + (float)(46 * Math.Sin(a)),
                    cx + (float)(168 * Math.Cos(a)), cy + (float)(168 * Math.Sin(a)));
                ray.ScaleVec(OsbEasing.OutCubic, t0, t0 + 220, 0.2f, 0.03f, 0.42f, 0.34f);
            }

            var yellow = layer.CreateSprite("sb/star-concave.png", OsbOrigin.Centre);
            yellow.Move(t0, cx, cy);
            yellow.Color(t0, 227/255f, 201/255f, 126/255f);
            yellow.Fade(t0, t0 + yellowEnd + starDur, 1, 1);
            yellow.Scale(OsbEasing.OutCubic, t0, t0 + burst, 0.1f, 0.62f);
            yellow.Scale(OsbEasing.InCubic, t0 + burst, t0 + yellowEnd, 0.62f, cover);

            double[][] layerColor =
            {
                new[] { 73/255.0, 106/255.0, 120/255.0 },
                new[] { 247/255.0, 241/255.0, 232/255.0 }
            };
            for (var i = 0; i < layerColor.Length; i++)
            {
                var at = t0 + yellowEnd + i * stagger;
                var growEnd = at + starDur;
                var hold = i == layerColor.Length - 1
                    ? growEnd
                    : at + stagger + starDur;
                // End with the window, so the hole shows the scene instead of another solid star.
                if (growEnd > scene) growEnd = scene;
                if (hold > scene) hold = scene;
                var star = layer.CreateSprite("sb/star-concave.png", OsbOrigin.Centre);
                star.Move(at, cx, cy);
                star.Color(at, layerColor[i][0], layerColor[i][1], layerColor[i][2]);
                star.Fade(at, hold, 1, 1);
                star.Scale(OsbEasing.InOutCubic, at, growEnd, 0.06f, cover);
            }

            var open = layer.CreateSprite("sb/star-open.png", OsbOrigin.Centre);
            open.Move(scene, cx, cy);
            open.Color(scene, 247/255f, 241/255f, 232/255f);
            open.Fade(scene, 1);
            open.Scale(OsbEasing.InOutCubic, scene, scene + revealDur, 0.86f, 6.2f);
        }

        private void CreateIntroStage(StoryboardLayer layer, int cut, int ready)
        {
            // One circle center, below the screen. Shelf crest, orbits and the character share it.
            // ready is while the star still fills the frame. The spin itself still starts at stageStart.
            const float pivotX = 320f;
            const float pivotY = 900f;
            var ren = GetMapsetBitmap("sb/ren.png");
            var renScale = (ren == null || ren.Height == 0 ? 0.47f : 432f / ren.Height) * 1.5f;
            const float girlY = 428f;
            var stageStart = cut;
            var stage = BuildStageAngles(stageStart, out var arrived, out var leaveAt);
            // Start the turn with the star window: reveal and motion share the same clock.
            var posed = new List<ArcKey> { new ArcKey(ready, stage[0].Alpha) };
            posed.AddRange(stage);

            var backdrop = layer.CreateSprite(CharacterPalette.Path("sb/intro-bg.png"), OsbOrigin.Centre);
            backdrop.Move(ready, 320, 240);
            backdrop.ScaleVec(ready, 854f / 4f, 1f);
            backdrop.Fade(ready, 1);
            backdrop.Fade(BandCoverEnd, BandCoverEnd + 16, 1, 0);

            CharacterPalette.Paper(layer, ready, BandCoverEnd);

            PlaceOrbitField(layer, stageStart, arrived, pivotX, pivotY);
            PlaceFlipGrid(layer, stage, stageStart, arrived, pivotX, pivotY);
            CharacterTreatment.Focus(layer, ready, BandCoverEnd);

            var girl = layer.CreateSprite("sb/ren.png", OsbOrigin.Centre);
            var girlAnchor = CharacterLanding.OffsetAt80(320f, girlY, 854f * .04f, -480f * .03f);
            ApplyStageArc(girl, posed, pivotX, pivotY, girlAnchor.x, girlAnchor.y);
            girl.Scale(ready, renScale);
            girl.Fade(ready, 1);
            girl.Fade(BandCoverEnd, BandCoverEnd + 16, 1, 0);

            var shelf = layer.CreateSprite(CharacterPalette.Path("sb/arc-shelf.png"), OsbOrigin.Centre);
            // The thick inner body stays below the screen at 100°. Hold it there so the exit spin does not swing that body across the frame.
            var shelfKeys = new List<ArcKey>();
            foreach (var key in posed)
            {
                if (key.Time > leaveAt)
                    break;
                shelfKeys.Add(key);
            }
            var shelfAnchor = CharacterLanding.ShelfAnchor(
                GetMapsetBitmap(CharacterPalette.Path("sb/arc-shelf.png")), 320f, 1703.7f, 1f);
            ApplyStageArc(shelf, shelfKeys, pivotX, pivotY, shelfAnchor.x, shelfAnchor.y);
            shelf.Scale(ready, 1f * CharacterLanding.ShelfRatio);
            shelf.Fade(ready, 1);
            shelf.Fade(BandCoverEnd, BandCoverEnd + 16, 1, 0);

            PlaceShelfWood(layer, shelfKeys, pivotX, pivotY, ready, cut, arrived);
            CreateNameCard(layer, stageStart, arrived, leaveAt, stage, pivotX, pivotY);
        }

        private readonly struct ArcKey
        {
            public readonly int Time;
            public readonly double Alpha;

            public ArcKey(int time, double alpha)
            {
                Time = time;
                Alpha = alpha;
            }
        }

        // InOutCubic, matching the web preview and OsbEasing.InOutCubic.
        private static double EntranceEase(double t)
        {
            t = Math.Clamp(t, 0.0, 1.0);
            if (t < 0.5)
                return 4.0 * t * t * t;
            var u = 1.0 - t;
            return 1.0 - 4.0 * u * u * u;
        }

        // Math angles: counterclockwise from +X. 90° is upright above the pivot.
        // 30°→80° is a full InOutCubic. 80°→100° is a slow constant spin while the name is up.
        // 100° onward leaves the screen on another InOutCubic.
        private List<ArcKey> BuildStageAngles(int start, out int arrived, out int leaveAt)
        {
            const double startDeg = 30.0;
            const double aimDeg = 80.0;
            const double leaveDeg = 100.0;
            const double exitDeg = 270.0;
            const int fastMs = 640;
            const int exitMs = IntroExitMs;
            const int leaveTime = IntroLeave;
            var keys = new List<ArcKey>();

            void Add(int time, double angle)
            {
                if (keys.Count > 0 && time <= keys[keys.Count - 1].Time)
                    time = keys[keys.Count - 1].Time + 16;
                keys.Add(new ArcKey(time, angle));
            }

            foreach (var time in CharacterCel.Times(start, start + fastMs, start + fastMs))
            {
                var s = (time - start) / (double)fastMs;
                Add(time, startDeg + (aimDeg - startDeg) * EntranceEase(s));
            }

            arrived = keys[keys.Count - 1].Time;
            characterLandingTime = arrived;
            var holdMs = Math.Max(32, leaveTime - arrived);
            leaveAt = arrived + holdMs;
            foreach (var time in CharacterCel.Times(arrived, leaveAt, arrived))
                if (time > arrived)
                    Add(time, aimDeg + (leaveDeg - aimDeg) * (time - arrived) / holdMs);

            const int exitSteps = 20;
            for (var i = 1; i <= exitSteps; i++)
            {
                var s = i / (double)exitSteps;
                Add(leaveAt + (int)Math.Round(exitMs * s), leaveDeg + (exitDeg - leaveDeg) * EntranceEase(s));
            }

            return keys;
        }

        private static (float x, float y, double rot) PoseAt(float pivotX, float pivotY, float restX, float restY, double alphaDeg)
        {
            var delta = (alphaDeg - 90.0) * Math.PI / 180.0;
            var dx = restX - pivotX;
            var up = pivotY - restY;
            var cos = Math.Cos(delta);
            var sin = Math.Sin(delta);
            return (
                (float)(pivotX + dx * cos - up * sin),
                (float)(pivotY - (dx * sin + up * cos)),
                -delta);
        }

        // Invisible until the slow cruise. Then a quarter of the squares turn on an edge and stay open.
        private void PlaceFlipGrid(StoryboardLayer layer, IReadOnlyList<ArcKey> stage, int show, int arrived, float pivotX, float pivotY)
        {
            var layoutPath = Path.Combine(MapsetPath, "sb", "flip", "layout.txt");
            if (!File.Exists(layoutPath))
                return;
            const int dur = 224;
            const int gap = 56;
            var wave = arrived + 160;
            foreach (var raw in File.ReadAllLines(layoutPath))
            {
                if (string.IsNullOrWhiteSpace(raw) || raw.StartsWith("#"))
                    continue;
                var parts = raw.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                var hingeLeft = parts[0] == "left";
                var cx = float.Parse(parts[2], CultureInfo.InvariantCulture);
                var cy = float.Parse(parts[3], CultureInfo.InvariantCulture);
                var order = int.Parse(parts[4], CultureInfo.InvariantCulture);
                var at = wave + order * gap;
                PlaceFlipCell(layer, stage, show, at, dur, hingeLeft, parts[1], cx, cy, pivotX, pivotY);
            }
        }

        private void PlaceFlipCell(StoryboardLayer layer, IReadOnlyList<ArcKey> stage, int show, int at, int dur, bool hingeLeft, string backPath, float cx, float cy, float pivotX, float pivotY)
        {
            var mid = at + dur / 2;
            var end = at + dur;
            var front = layer.CreateSprite(CharacterPalette.Path("sb/flip/paper.png"), OsbOrigin.Centre);
            var back = layer.CreateSprite(CharacterPalette.Path(backPath), OsbOrigin.Centre);
            TrackFlip(front, stage, show, at, mid, end, hingeLeft, true, cx, cy, pivotX, pivotY);
            TrackFlip(back, stage, show, at, mid, end, hingeLeft, false, cx, cy, pivotX, pivotY);

            front.Fade(show, 0);
            front.Fade(at, 1);
            front.Fade(mid, 0);

            back.Fade(show, 0);
            back.Fade(mid, 1);
            back.Fade(BandCoverEnd, BandCoverEnd + 16, 1, 0);
        }

        // Scale collapses onto the hinge. The center moves with it so the scene rotation stays rigid.
        private void TrackFlip(OsbSprite sprite, IReadOnlyList<ArcKey> stage, int show, int at, int mid, int end, bool hingeLeft, bool closing, float cx, float cy, float pivotX, float pivotY)
        {
            var landing = stage.First(key => key.Alpha >= 80).Time;
            var times = new SortedSet<int>(stage.Select(key => key.Time)) { at, mid, end };
            foreach (var time in CharacterCel.LightTimes(at, end, landing)) times.Add(time);
            var kept = times.ToList();
            const float fit = CharacterAntialias.CardScale;
            var initial = closing ? 1f : 0f;
            sprite.ScaleVec(show, hingeLeft ? initial * fit : fit, hingeLeft ? fit : initial * fit);
            foreach (var time in kept)
            {
                if (time < at || time > end) continue;
                var width = FlipWidth(time, at, mid, end, closing);
                sprite.ScaleVec(time, hingeLeft ? width * fit : fit, hingeLeft ? fit : width * fit);
            }
            for (var i = 0; i < kept.Count - 1; i++)
            {
                var from = kept[i];
                var to = kept[i + 1];
                var prev = FlipPose(stage, from, at, mid, end, hingeLeft, closing, cx, cy, pivotX, pivotY);
                var next = FlipPose(stage, to, at, mid, end, hingeLeft, closing, cx, cy, pivotX, pivotY);
                if (CharacterCel.Hold(from))
                {
                    sprite.MoveX(from, prev.x);
                    sprite.MoveY(from, prev.y);
                    sprite.Rotate(from, prev.rot);
                }
                else
                {
                    sprite.MoveX(OsbEasing.None, from, to, prev.x, next.x);
                    sprite.MoveY(OsbEasing.None, from, to, prev.y, next.y);
                    sprite.Rotate(OsbEasing.None, from, to, prev.rot, next.rot);
                }
            }
        }

        private static (float x, float y, double rot) FlipPose(IReadOnlyList<ArcKey> stage, int time, int at, int mid, int end, bool hingeLeft, bool closing, float cx, float cy, float pivotX, float pivotY)
        {
            var width = FlipWidth(time, at, mid, end, closing);
            var shift = 60f * (1f - width);
            var restX = hingeLeft ? cx - shift : cx;
            var restY = hingeLeft ? cy : cy - shift;
            return PoseAt(pivotX, pivotY, restX, restY, AngleAt(stage, time));
        }

        private static float FlipWidth(int time, int at, int mid, int end, bool closing)
        {
            if (closing)
            {
                if (time <= at) return 1f;
                if (time >= mid) return 0f;
                return (float)(1.0 - EntranceEase((time - at) / (double)(mid - at)));
            }
            if (time <= mid) return 0f;
            if (time >= end) return 1f;
            return (float)EntranceEase((time - mid) / (double)(end - mid));
        }

        private static double AngleAt(IReadOnlyList<ArcKey> keys, int time)
        {
            if (time <= keys[0].Time)
                return keys[0].Alpha;
            for (var i = 1; i < keys.Count; i++)
            {
                if (time > keys[i].Time)
                    continue;
                var span = keys[i].Time - keys[i - 1].Time;
                if (time < keys[i].Time && CharacterCel.Hold(keys[i - 1].Time))
                    return keys[i - 1].Alpha;
                var t = span <= 0 ? 1.0 : (time - keys[i - 1].Time) / (double)span;
                return keys[i - 1].Alpha + (keys[i].Alpha - keys[i - 1].Alpha) * t;
            }
            return keys[keys.Count - 1].Alpha;
        }

        private static void ApplyStageArc(OsbSprite sprite, IReadOnlyList<ArcKey> keys, float pivotX, float pivotY, float restX, float restY, double localRot = 0)
        {
            if (keys.Count < 2) return;
            var prev = PoseAt(pivotX, pivotY, restX, restY, keys[0].Alpha);
            for (var i = 1; i < keys.Count; i++)
            {
                var next = PoseAt(pivotX, pivotY, restX, restY, keys[i].Alpha);
                var at = keys[i - 1].Time;
                var to = keys[i].Time;
                if (to <= at) to = at + 16;
                if (CharacterCel.Hold(at))
                {
                    sprite.MoveX(at, prev.x);
                    sprite.MoveY(at, prev.y);
                    sprite.Rotate(at, prev.rot + localRot);
                }
                else
                {
                    sprite.MoveX(OsbEasing.None, at, to, prev.x, next.x);
                    sprite.MoveY(OsbEasing.None, at, to, prev.y, next.y);
                    sprite.Rotate(OsbEasing.None, at, to, prev.rot + localRot, next.rot + localRot);
                }
                prev = next;
            }
        }

        // Quiet marks on the tan body under the books. Authored for the diagonal pass
        // (shelf near 47°) and parented to the shelf pivot, so they stay on the wood
        // and leave with it. Drawn above the shelf and below the name card.
        private void PlaceShelfWood(StoryboardLayer layer, IReadOnlyList<ArcKey> keys, float pivotX, float pivotY, int born, int enter, int arrived)
        {
            const double design = (47.11 - 90.0) * Math.PI / 180.0;
            var cos = Math.Cos(design);
            var sin = Math.Sin(design);
            var fadeAt = arrived + 120;
            const int fadeMs = 340;
            const float blueR = 73f / 255f;
            const float blueG = 106f / 255f;
            const float blueB = 120f / 255f;

            (float x, float y) Rest(float screenX, float screenY)
            {
                var px = screenX - pivotX;
                var py = pivotY - screenY;
                var dx = px * cos + py * sin;
                var up = -px * sin + py * cos;
                return ((float)(pivotX + dx), (float)(pivotY - up));
            }

            void Ride(OsbSprite sprite, float restX, float restY, double localRot)
            {
                ApplyStageArc(sprite, keys, pivotX, pivotY, restX, restY, localRot);
            }

            void Plane(float screenX, float screenY, float width, float height, float alpha, float cr, float cg, float cb)
            {
                var rest = Rest(screenX, screenY);
                var sprite = layer.CreateSprite("sb/px.png", OsbOrigin.Centre);
                Ride(sprite, rest.x, rest.y, 0);
                sprite.ScaleVec(born, width, height);
                sprite.Color(born, cr, cg, cb);
                sprite.Fade(born, 0);
                sprite.Fade(OsbEasing.Out, enter, enter + 420, 0, alpha);
                sprite.Fade(fadeAt, fadeAt + fadeMs, alpha, 0);
            }

            // Two parallel slabs, tilted with the shelf. Cream first, then a smaller blue-gray.
            Plane(90f, 420f, 480f, 220f, 0.18f, 247/255f, 241/255f, 232/255f);
            Plane(190f, 415f, 360f, 140f, 0.12f, 171/255f, 196/255f, 196/255f);

            void Dot(float screenX, float screenY, int delay, float size, float alpha, float cr, float cg, float cb)
            {
                var rest = Rest(screenX, screenY);
                var sprite = layer.CreateSprite("sb/px.png", OsbOrigin.Centre);
                Ride(sprite, rest.x, rest.y, 0);
                var appear = enter + delay;
                sprite.Scale(born, size);
                sprite.Color(born, cr, cg, cb);
                sprite.Fade(born, 0);
                sprite.Fade(appear, appear + 170, 0, alpha);
                sprite.Fade(fadeAt, fadeAt + fadeMs, alpha, 0);
            }

            // Sparse 3×3 in the lower-left 15%–35% of the frame. Rows fade in as batches.
            float[] dotX = { 32f, 96f, 160f };
            float[] dotY = { 348f, 404f, 456f };
            for (var row = 0; row < dotY.Length; row++)
                for (var col = 0; col < dotX.Length; col++)
                    Dot(dotX[col], dotY[row], row * 80, 3.2f, 0.38f, blueR, blueG, blueB);

            void Spark(string path, float screenX, float screenY, int delay, float size, double localRot, float alpha, float cr, float cg, float cb)
            {
                var rest = Rest(screenX, screenY);
                var sprite = layer.CreateSprite(path, OsbOrigin.Centre);
                Ride(sprite, rest.x, rest.y, localRot);
                var appear = enter + delay;
                sprite.Color(born, cr, cg, cb);
                sprite.Fade(born, 0);
                sprite.Scale(born, 0.01f);
                sprite.Fade(appear, appear + 180, 0, alpha);
                sprite.Scale(OsbEasing.OutCubic, appear, appear + 250, 0.01f, size * 1.08f);
                sprite.Scale(OsbEasing.InOutSine, appear + 250, appear + 400, size * 1.08f, size);
                sprite.Fade(fadeAt, fadeAt + fadeMs, alpha, 0);
            }

            Spark("sb/star4.png", 168f, 392f, 40, 0.058f, 0, 0.72f, 227/255f, 201/255f, 126/255f);
            Spark("sb/px.png", 338f, 424f, 110, 6.5f, Math.PI / 4.0, 0.55f, 183/255f, 206/255f, 208/255f);

            void Arc(float radius, double theta0, double theta1, int at, int drawMs, float thick, float alpha, float cr, float cg, float cb)
            {
                var span = theta1 - theta0;
                var count = Math.Max(6, (int)Math.Round(Math.Abs(span) * radius / 22.0));
                var step = span / count;
                for (var i = 0; i < count; i++)
                {
                    var theta = theta0 + step * (i + 0.5);
                    var restX = (float)(pivotX + radius * Math.Cos(theta));
                    var restY = (float)(pivotY + radius * Math.Sin(theta));
                    var localRot = Math.Atan2(-Math.Cos(theta), Math.Sin(theta));
                    var sprite = layer.CreateSprite("sb/px.png", OsbOrigin.Centre);
                    Ride(sprite, restX, restY, localRot);
                    var appear = at + drawMs * i / count;
                    sprite.Color(born, cr, cg, cb);
                    sprite.Fade(born, 0);
                    sprite.Fade(appear, appear + 90, 0, alpha);
                    sprite.ScaleVec(appear, (float)(Math.Abs(step) * radius * 1.15), thick);
                    sprite.Fade(fadeAt, fadeAt + fadeMs, alpha, 0);
                }
            }

            var main0 = -172.0 * Math.PI / 180.0;
            var main1 = -138.0 * Math.PI / 180.0;
            Arc(620f, main0, main1, enter, 420, 1.8f, 0.30f, blueR, blueG, blueB);
            // About 40% of the main arc, set inward so the two lines stay apart.
            Arc(545f, -161.0 * Math.PI / 180.0, -147.0 * Math.PI / 180.0, enter + 70, 300, 1.6f, 0.34f, 227/255f, 201/255f, 126/255f);

            for (var i = 0; i < 3; i++)
            {
                var theta = (-168.0 + i * 14.0) * Math.PI / 180.0;
                var restX = (float)(pivotX + 578.0 * Math.Cos(theta));
                var restY = (float)(pivotY + 578.0 * Math.Sin(theta));
                var sprite = layer.CreateSprite("sb/px.png", OsbOrigin.Centre);
                Ride(sprite, restX, restY, 0);
                var appear = enter + 30 + i * 40;
                sprite.Scale(born, 2.4f);
                sprite.Color(born, 247/255f, 241/255f, 232/255f);
                sprite.Fade(born, 0);
                sprite.Fade(appear, appear + 140, 0, 0.42f);
                sprite.Fade(fadeAt, fadeAt + fadeMs, 0.42f, 0);
            }
        }

        private void CreateNameCard(StoryboardLayer layer, int cut, int arrived, int leaveAt, IReadOnlyList<ArcKey> stage, float pivotX, float pivotY)
        {
            var layoutPath = Path.Combine(MapsetPath, "sb", "ren-name", "layout.txt");
            if (!File.Exists(layoutPath)) return;
            var main = new List<(string path, float x, float y)>();
            var sub = new List<(string path, float x, float y)>();
            var rules = new List<(bool left, float x, float y, float width)>();
            var sparks = new List<(float x, float y)>();
            foreach (var raw in File.ReadAllLines(layoutPath))
            {
                if (string.IsNullOrWhiteSpace(raw)) continue;
                var parts = raw.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (parts[0] == "slice")
                {
                    var position = CharacterTreatment.NamePosition(float.Parse(parts[3], CultureInfo.InvariantCulture), float.Parse(parts[4], CultureInfo.InvariantCulture));
                    var item = (parts[2], position.x, position.y);
                    if (parts[1] == "m") main.Add(item);
                    else sub.Add(item);
                }
                else if (parts[0] == "rule")
                {
                    rules.Add((
                        parts[1] == "left",
                        float.Parse(parts[2], CultureInfo.InvariantCulture),
                        float.Parse(parts[3], CultureInfo.InvariantCulture),
                        float.Parse(parts[4], CultureInfo.InvariantCulture)));
                }
                else if (parts[0] == "spark")
                {
                    sparks.Add((
                        float.Parse(parts[1], CultureInfo.InvariantCulture),
                        float.Parse(parts[2], CultureInfo.InvariantCulture)));
                }
            }

            const float nameScale = 0.5f;
            const float fit = 1f;
            const float ruleThick = 2f;
            // The name starts as soon as the spin reaches 80° and the slow cruise begins.
            var mainAt = arrived;
            const int mainDur = 280;
            var subAt = mainAt + 120;
            const int subDur = 190;
            const int exitDur = 420;
            var mainOut = leaveAt;
            var subOut = leaveAt + 70;
            WipeSlices(layer, main, cut, mainAt, mainDur, mainOut, exitDur, nameScale, stage, pivotX, pivotY);
            WipeSlices(layer, sub, cut, subAt, subDur, subOut, exitDur, nameScale, stage, pivotX, pivotY);

            foreach (var rule in rules)
            {
                var bar = layer.CreateSprite("sb/px.png", rule.left ? OsbOrigin.CentreRight : OsbOrigin.CentreLeft);
                var position = CharacterTreatment.NamePosition(rule.x, rule.y);
                ApplyStageArc(bar, stage, pivotX, pivotY, position.x, position.y);
                bar.Color(subAt, 73/255f, 106/255f, 120/255f);
                bar.Fade(cut, 0);
                bar.Fade(subAt, 1);
                bar.Fade(subOut, subOut + 180, 1, 0);
                bar.ScaleVec(OsbEasing.OutCubic, subAt, subAt + subDur, 0f, ruleThick, rule.width * fit, ruleThick);
                bar.ScaleVec(OsbEasing.In, subOut, subOut + 180, rule.width * fit, ruleThick, 0f, 0.4f);
            }

            foreach (var spark in sparks)
            {
                var star = layer.CreateSprite("sb/star4.png", OsbOrigin.Centre);
                var position = CharacterTreatment.NamePosition(spark.x, spark.y);
                ApplyStageArc(star, stage, pivotX, pivotY, position.x, position.y);
                star.Color(subAt, 227/255f, 201/255f, 126/255f);
                star.Fade(cut, 0);
                star.Fade(subAt, 1);
                star.Fade(subOut, subOut + 160, 1, 0);
                star.Scale(OsbEasing.OutCubic, subAt, subAt + subDur, 0.01f, 0.05f);
                star.Scale(OsbEasing.In, subOut, subOut + 160, 0.05f, 0.01f);
            }
            CharacterTreatment.PageSweep(layer);
        }

        private void WipeSlices(StoryboardLayer layer, List<(string path, float x, float y)> slices, int cut, int start, int duration, int exitStart, int exitDur, float scale, IReadOnlyList<ArcKey> stage, float pivotX, float pivotY)
        {
            if (slices.Count == 0) return;
            slices.Sort((a, b) => a.x.CompareTo(b.x));
            var left = slices[0].x;
            var right = slices[slices.Count - 1].x;
            var span = Math.Max(0.001f, right - left);
            foreach (var slice in slices)
            {
                var p = (slice.x - left) / span;
                var u = 1.0 - Math.Pow(1.0 - p, 1.0 / 3.0);
                var at = start + (int)Math.Round(duration * u);
                if (at < start) at = start;
                var q = (right - slice.x) / span;
                var v = 1.0 - Math.Pow(1.0 - q, 1.0 / 3.0);
                var outAt = exitStart + (int)Math.Round(exitDur * v);
                if (outAt < at + 16) outAt = at + 16;
                var sprite = layer.CreateSprite(CharacterPalette.Path(slice.path), OsbOrigin.Centre);
                ApplyStageArc(sprite, stage, pivotX, pivotY, slice.x, slice.y);
                sprite.Scale(cut, scale);
                sprite.Fade(cut, 0);
                if (at > cut)
                    sprite.Fade(at, 1);
                sprite.Fade(outAt, outAt + 90, 1, 0);
                sprite.Scale(OsbEasing.In, outAt, outAt + 90, scale, scale * 0.35f);
            }
        }

        // Pages are already open. After the character reaches 80°, regions turn one after another.
        // Top row flips sideways, the left column flips sideways, the right column flips vertically.
        private void PlacePageGrid(StoryboardLayer layer, int show, int arrived)
        {
            var layoutPath = Path.Combine(MapsetPath, "sb", "pages", "layout.txt");
            if (!File.Exists(layoutPath))
                return;

            var flips = new List<(int wave, bool vertical, string front, string back, float x, float y)>();
            foreach (var raw in File.ReadAllLines(layoutPath))
            {
                if (string.IsNullOrWhiteSpace(raw) || raw.StartsWith("#"))
                    continue;
                var parts = raw.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (parts[0] == "flip")
                {
                    flips.Add((
                        int.Parse(parts[1], CultureInfo.InvariantCulture),
                        parts[2] == "v",
                        parts[3],
                        parts[4],
                        float.Parse(parts[5], CultureInfo.InvariantCulture),
                        float.Parse(parts[6], CultureInfo.InvariantCulture)));
                    continue;
                }

                var page = layer.CreateSprite(parts[1], OsbOrigin.Centre);
                page.Move(show, float.Parse(parts[2], CultureInfo.InvariantCulture), float.Parse(parts[3], CultureInfo.InvariantCulture));
                page.ScaleVec(show, 0.5f, 0.5f);
                page.Fade(show, 1);
                page.Fade(IntroEnd - 400, IntroEnd, 1, 0);
            }

            // Start offset, neighbor delay, flip length. Delays stay inside 35–70ms, flips inside 180–260ms.
            (int start, int gap, int dur)[] waves =
            {
                (60, 48, 200),
                (520, 56, 220),
                (980, 52, 240),
            };
            for (var wave = 0; wave < waves.Length; wave++)
            {
                var group = flips.Where(item => item.wave == wave)
                    .OrderBy(item => item.y)
                    .ThenBy(item => item.x)
                    .ToList();
                var (start, gap, dur) = waves[wave];
                for (var i = 0; i < group.Count; i++)
                    PlayPageFlip(layer, group[i].front, group[i].back, group[i].x, group[i].y, show, arrived + start + i * gap, dur, group[i].vertical);
            }
        }

        private void PlayPageFlip(StoryboardLayer layer, string frontPath, string backPath, float x, float y, int show, int at, int dur, bool vertical)
        {
            var mid = at + dur / 2;
            var end = at + dur;
            if (mid < at + 16)
                mid = at + 16;
            if (end < mid + 16)
                end = mid + 16;

            var front = layer.CreateSprite(frontPath, OsbOrigin.Centre);
            front.Move(show, x, y);
            front.ScaleVec(show, 0.5f, 0.5f);
            front.Fade(show, 1);
            front.Fade(mid, 0);

            var back = layer.CreateSprite(backPath, OsbOrigin.Centre);
            back.Move(show, x, y);
            back.Fade(show, 0);
            back.Fade(mid, 1);
            back.Fade(IntroEnd - 400, IntroEnd, 1, 0);

            if (vertical)
            {
                front.ScaleVec(OsbEasing.InOutCubic, at, mid, 0.5f, 0.5f, 0.5f, 0f);
                back.ScaleVec(show, 0.5f, 0f);
                back.ScaleVec(OsbEasing.InOutCubic, mid, end, 0.5f, 0f, 0.5f, 0.5f);
            }
            else
            {
                front.ScaleVec(OsbEasing.InOutCubic, at, mid, 0.5f, 0.5f, 0f, 0.5f);
                back.ScaleVec(show, 0f, 0.5f);
                back.ScaleVec(OsbEasing.InOutCubic, mid, end, 0f, 0.5f, 0.5f, 0.5f);
            }
        }

        private void PlaceOrbitField(StoryboardLayer layer, int stageStart, int arrived, float pivotX, float pivotY)
        {
            const float main = 0.48f;
            const float mid = 0.28f;
            const float slim = 0.18f;
            const double bw = 73/255.0, bg = 106/255.0, bb = 120/255.0; // #496A78
            const double yw = 227/255.0, yg = 201/255.0, yb = 126/255.0; // #E3C97E

            DrawConcentricArc(layer, stageStart, pivotX, pivotY, 900f, -0.62, -2.52, main, 0.70, bw, bg, bb, 160, 4200, 0, 0, false);
            DrawConcentricArc(layer, stageStart + 220, pivotX, pivotY, 830f, -1.20, -1.94, main, 0.74, 247/255.0, 241/255.0, 232/255.0, 180, 4000, 0, 0, false);

            DrawConcentricArc(layer, stageStart + 520, pivotX, pivotY, 860f, -2.15, -1.78, mid, 0.58, 247/255.0, 241/255.0, 232/255.0, 400, 1500, 220, 0, false);
            DrawConcentricArc(layer, stageStart + 980, pivotX, pivotY, 760f, -1.22, -0.86, mid, 0.58, bw, bg, bb, 400, 1500, 220, 0, false);
            DrawConcentricArc(layer, stageStart + 1440, pivotX, pivotY, 690f, -2.35, -1.90, mid, 0.54, 247/255.0, 241/255.0, 232/255.0, 420, 1400, 220, 0, false);
            DrawConcentricArc(layer, stageStart + 1900, pivotX, pivotY, 650f, -1.18, -0.80, mid, 0.54, bw, bg, bb, 420, 1400, 220, 0, false);
            DrawConcentricArc(layer, stageStart + 2360, pivotX, pivotY, 720f, -2.05, -1.68, mid, 0.50, yw, yg, yb, 440, 1300, 220, 0, false);

            DrawConcentricArc(layer, arrived + 80, pivotX, pivotY, 880f, -2.05, -1.88, slim, 0.82, 247/255.0, 241/255.0, 232/255.0, 280, 380, 160, -0.02, true);
            DrawConcentricArc(layer, arrived + 420, pivotX, pivotY, 840f, -2.18, -1.98, slim, 0.78, bw, bg, bb, 300, 360, 160, -0.02, false);
            DrawConcentricArc(layer, arrived + 760, pivotX, pivotY, 870f, -1.15, -0.98, slim, 0.82, 247/255.0, 241/255.0, 232/255.0, 280, 380, 160, -0.02, true);
            DrawConcentricArc(layer, arrived + 1100, pivotX, pivotY, 800f, -1.22, -1.02, slim, 0.76, 247/255.0, 241/255.0, 232/255.0, 300, 360, 160, -0.02, false);
            DrawConcentricArc(layer, arrived + 1440, pivotX, pivotY, 660f, -2.20, -2.02, slim, 0.8, 247/255.0, 241/255.0, 232/255.0, 280, 340, 150, -0.02, true);
            DrawConcentricArc(layer, arrived + 1780, pivotX, pivotY, 620f, -1.12, -0.96, slim, 0.76, bw, bg, bb, 280, 340, 150, -0.02, true);
            DrawConcentricArc(layer, arrived + 2120, pivotX, pivotY, 600f, -1.95, -1.78, slim, 0.72, 247/255.0, 241/255.0, 232/255.0, 300, 320, 150, -0.015, false);
            DrawConcentricArc(layer, arrived + 2460, pivotX, pivotY, 580f, -1.28, -1.12, slim, 0.7, yw, yg, yb, 300, 320, 150, -0.015, false);

            DrawArcTicks(layer, stageStart + 860, pivotX, pivotY, 870f, -1.68, -1.46, 9, 0.009f, 0, 0.7, 247/255.0, 241/255.0, 232/255.0, true);
            DrawArcTicks(layer, stageStart + 1280, pivotX, pivotY, 800f, -2.18, -1.90, 7, 0.14f, 0.22f, 0.62, bw, bg, bb, false);
            DrawArcTicks(layer, stageStart + 1720, pivotX, pivotY, 740f, -1.15, -0.90, 7, 0.14f, 0.22f, 0.62, 247/255.0, 241/255.0, 232/255.0, false);
            DrawArcTicks(layer, arrived + 360, pivotX, pivotY, 580f, -1.28, -1.12, 6, 0.008f, 0, 0.6, yw, yg, yb, true);

            PlaceGeoMark(layer, "sb/star4.png", stageStart + 1100, pivotX, pivotY, 760f, -2.08, 0.042f, yw, yg, yb, 0);
            PlaceGeoMark(layer, "sb/star4.png", stageStart + 2100, pivotX, pivotY, 700f, -0.98, 0.038f, yw, yg, yb, 0);
            PlaceGeoMark(layer, "sb/star-line.png", arrived + 240, pivotX, pivotY, 860f, -2.28, 0.09f, 247/255.0, 241/255.0, 232/255.0, 0);
            PlaceGeoMark(layer, "sb/px.png", stageStart + 1500, pivotX, pivotY, 850f, -1.95, 4.5f, bw, bg, bb, Math.PI / 4);
            PlaceGeoMark(layer, "sb/px.png", arrived + 520, pivotX, pivotY, 700f, -1.08, 4f, bw, bg, bb, Math.PI / 4);
            PlaceGeoMark(layer, "sb/burst.png", stageStart + 1900, pivotX, pivotY, 780f, -2.32, 0.018f, 247/255.0, 241/255.0, 232/255.0, 0);
            PlaceGeoMark(layer, "sb/burst.png", arrived + 160, pivotX, pivotY, 740f, -0.92, 0.016f, 247/255.0, 241/255.0, 232/255.0, 0);
        }

        private void DrawConcentricArc(StoryboardLayer layer, int at, float pivotX, float pivotY, float radius, double thetaStart, double thetaEnd, float thick, double alpha, double cr, double cg, double cb, int drawMs, int holdMs, int fadeMs, double drift, bool taper)
        {
            var span = thetaEnd - thetaStart;
            var arcLen = Math.Abs(span) * radius;
            var count = Math.Max(2, Math.Min(140, (int)Math.Round(arcLen / 16.0)));
            var step = span / count;
            var life = drawMs + holdMs;
            for (var i = 0; i < count; i++)
            {
                var theta = thetaStart + step * (i + 0.5);
                var x = (float)(pivotX + radius * Math.Cos(theta));
                var y = (float)(pivotY + radius * Math.Sin(theta));
                if (y < -60f || y > 520f || x < -180f || x > 900f) continue;
                if (x > 250f && x < 480f && y > 95f && y < 230f) continue;
                if (x > 230f && x < 480f && y > 300f && y < 420f) continue;
                var rot = Math.Atan2(-Math.Cos(theta), Math.Sin(theta));
                var len = (float)(2 * radius * Math.Sin(Math.Abs(step) / 2) / 64f);
                var appear = at + drawMs * i / count;
                if (appear < at) appear = at;
                var segAlpha = alpha;
                if (taper)
                    segAlpha *= 0.35 + 0.65 * (i / (double)Math.Max(1, count - 1));
                var sprite = layer.CreateSprite(CharacterAntialias.Stroke(thick), OsbOrigin.Centre);
                var moveEnd = at + life;
                if (moveEnd < appear + 32) moveEnd = appear + 32;
                OrbitSpan(sprite, at, moveEnd, OsbEasing.None, 0, drift, pivotX, pivotY, x, y, rot);
                sprite.Color(appear, cr, cg, cb);
                if (appear >= at + 16)
                    sprite.Fade(at, 0);
                sprite.Fade(appear, appear + 24, 0, (float)segAlpha);
                sprite.ScaleVec(appear, len * CharacterAntialias.ArcScale, thick * CharacterAntialias.ArcScale);
                // A single continuous curve takes over once all pieces are drawn.
                sprite.Fade(at + drawMs + 24, 0);
            }
            var mask = CharacterArc.Find(MapsetPath, radius, thetaStart, thetaEnd, thick, taper);
            var continuous = layer.CreateSprite(mask.path, OsbOrigin.Centre);
            continuous.Scale(at, CharacterAntialias.ArcScale);
            OrbitSpan(continuous, at, at + life, OsbEasing.None, 0, drift, pivotX, pivotY, mask.x, mask.y, 0);
            continuous.Color(at, cr, cg, cb);
            continuous.Fade(at, 0);
            continuous.Fade(at + drawMs + 24, alpha);
            if (fadeMs <= 0)
                continuous.Fade(BandCoverEnd, BandCoverEnd + 16, alpha, 0);
            else
                continuous.Fade(at + life, at + life + fadeMs, alpha, 0);
        }

        private void DrawArcTicks(StoryboardLayer layer, int at, float pivotX, float pivotY, float radius, double thetaStart, double thetaEnd, int ticks, float thick, float dashLen, double alpha, double cr, double cg, double cb, bool round)
        {
            for (var i = 0; i < ticks; i++)
            {
                var theta = thetaStart + (thetaEnd - thetaStart) * (i + 0.5) / ticks;
                var x = (float)(pivotX + radius * Math.Cos(theta));
                var y = (float)(pivotY + radius * Math.Sin(theta));
                if (y < -40f || y > 500f || x < -140f || x > 860f) continue;
                if (x > 250f && x < 480f && y > 95f && y < 230f) continue;
                if (x > 230f && x < 480f && y > 300f && y < 420f) continue;
                var appear = at + i * 32;
                var sprite = layer.CreateSprite(round ? "sb/burst.png" : "sb/orbit-dash.png", OsbOrigin.Centre);
                var rot = Math.Atan2(-Math.Cos(theta), Math.Sin(theta));
                OrbitSpan(sprite, at, appear + 780, OsbEasing.None, 0, 0, pivotX, pivotY, x, y, round ? 0 : rot);
                sprite.Color(appear, cr, cg, cb);
                if (appear >= at + 16)
                    sprite.Fade(at, 0);
                sprite.Fade(appear, appear + 24, 0, (float)alpha);
                if (round)
                    sprite.Scale(appear, thick);
                else
                    sprite.ScaleVec(appear, dashLen, thick);
                sprite.Fade(appear + 640, appear + 800, (float)alpha, 0);
            }
        }

        private void PlaceGeoMark(StoryboardLayer layer, string path, int at, float pivotX, float pivotY, float radius, double theta, float size, double cr, double cg, double cb, double baseRot)
        {
            var x = (float)(pivotX + radius * Math.Cos(theta));
            var y = (float)(pivotY + radius * Math.Sin(theta));
            var sprite = layer.CreateSprite(path, OsbOrigin.Centre);
            OrbitSpan(sprite, at, at + 640, OsbEasing.None, 0, -0.04, pivotX, pivotY, x, y, baseRot);
            sprite.Color(at, cr, cg, cb);
            sprite.Fade(at, at + 50, 0, 0.95f);
            sprite.Fade(at + 620, at + 760, 0.95f, 0);
            if (path.EndsWith("px.png") && size > 2f)
                sprite.ScaleVec(OsbEasing.Out, at, at + 120, size * 0.15f, size > 10f ? 1.6f : size, size, size > 10f ? 1.6f : size);
            else
                sprite.Scale(OsbEasing.Out, at, at + 120, size * 0.2f, size);
        }

        private void PlaceArc(StoryboardLayer layer, int cut, int moveEnd, OsbEasing ease, double travel, float pivotX, float pivotY, float radius, double theta0, double theta1, int delay, int stagger, float thick, double alpha, double cr, double cg, double cb, int fadeHold)
        {
            const float dashW = 96f;
            var span = theta1 - theta0;
            var arcLen = Math.Abs(span) * radius;
            var count = Math.Max(4, (int)Math.Round(arcLen / 46f));
            var step = span / count;
            for (var i = 0; i < count; i++)
            {
                var theta = theta0 + step * (i + 0.5);
                var x = (float)(pivotX + radius * Math.Cos(theta));
                var y = (float)(pivotY + radius * Math.Sin(theta));
                var end = OrbitOf(pivotX, pivotY, x, y, travel);
                if (!NearScreen(x, y) && !NearScreen(end.x, end.y)) continue;
                var rot = Math.Atan2(-radius * Math.Cos(theta), radius * Math.Sin(theta));
                var len = (float)(Math.Abs(step) * radius / dashW * 1.18);
                var appear = cut + delay + i * stagger;
                if (appear > moveEnd - 80) appear = moveEnd - 80;
                var sprite = layer.CreateSprite("sb/orbit-dash.png", OsbOrigin.Centre);
                OrbitSpan(sprite, cut, moveEnd, ease, 0, travel, pivotX, pivotY, x, y, rot);
                sprite.Color(cut, cr, cg, cb);
                if (appear >= cut + 16)
                    sprite.Fade(cut, 0);
                sprite.Fade(appear, appear + 40, 0, (float)alpha);
                sprite.ScaleVec(OsbEasing.Out, appear, appear + 90, len * 0.05f, thick, len, thick);
                if (fadeHold > 0)
                    sprite.Fade(appear + fadeHold, appear + fadeHold + 140, (float)alpha, 0);
                else
                    sprite.Fade(EndTime, EndTime + 400, (float)alpha, 0);
            }
        }

        private void PlaceArcMark(StoryboardLayer layer, string path, int cut, int moveEnd, double travel, float pivotX, float pivotY, float radius, double theta, float size, int delay, double baseRot, double cr, double cg, double cb, bool pulse)
        {
            var x = (float)(pivotX + radius * Math.Cos(theta));
            var y = (float)(pivotY + radius * Math.Sin(theta));
            var start = cut + delay;
            var sprite = layer.CreateSprite(path, OsbOrigin.Centre);
            OrbitSpan(sprite, cut, moveEnd, OsbEasing.None, 0, travel, pivotX, pivotY, x, y, baseRot);
            sprite.Color(cut, cr, cg, cb);
            if (start >= cut + 16)
                sprite.Fade(cut, 0);
            sprite.Fade(start, start + 50, 0, 0.95f);
            sprite.Fade(EndTime, EndTime + 400, 0.95f, 0);
            if (pulse)
            {
                sprite.Scale(OsbEasing.OutBack, start, start + 160, size * 0.15f, size * 1.12f);
                sprite.Scale(OsbEasing.InOutSine, start + 160, start + 340, size * 1.12f, size);
            }
            else
            {
                sprite.Scale(OsbEasing.Out, start, start + 140, size * 0.15f, size);
            }
        }

        private static (float x, float y) OrbitOf(float pivotX, float pivotY, float x, float y, double angle)
        {
            var dx = x - pivotX;
            var dy = y - pivotY;
            var cos = Math.Cos(angle);
            var sin = Math.Sin(angle);
            return ((float)(pivotX + dx * cos - dy * sin), (float)(pivotY + dx * sin + dy * cos));
        }

        private static bool NearScreen(float x, float y)
        {
            return x > -220f && x < 860f && y > -90f && y < 540f;
        }

        private void OrbitSpan(OsbSprite sprite, int start, int end, OsbEasing ease, double from, double to, float pivotX, float pivotY, float x, float y, double rot)
        {
            var a = OrbitOf(pivotX, pivotY, x, y, from);
            var b = OrbitOf(pivotX, pivotY, x, y, to);
            if (ease == OsbEasing.None && from != to && start < CharacterCel.End && end > CharacterCel.HeavyStart)
            {
                var times = new SortedSet<int> { start, end };
                foreach (var t in CharacterCel.LightTimes(Math.Max(start, CharacterCel.HeavyStart),
                    Math.Min(end, CharacterCel.End), characterLandingTime)) times.Add(t);
                if (CharacterCel.End > start && CharacterCel.End < end) times.Add(CharacterCel.End);
                var keys = times.ToList();
                for (var i = 0; i < keys.Count - 1; i++)
                {
                    var at = keys[i];
                    var next = keys[i + 1];
                    var p = (at - start) / (double)(end - start);
                    var q = (next - start) / (double)(end - start);
                    var px = a.x + (b.x - a.x) * p;
                    var py = a.y + (b.y - a.y) * p;
                    if (CharacterCel.Hold(at))
                    {
                        sprite.MoveX(at, px);
                        sprite.MoveY(at, py);
                        sprite.Rotate(at, rot + from + (to - from) * p);
                    }
                    else
                    {
                        sprite.MoveX(ease, at, next, px, a.x + (b.x - a.x) * q);
                        sprite.MoveY(ease, at, next, py, a.y + (b.y - a.y) * q);
                        sprite.Rotate(ease, at, next, rot + from + (to - from) * p, rot + from + (to - from) * q);
                    }
                }
                sprite.MoveX(end, b.x);
                sprite.MoveY(end, b.y);
                sprite.Rotate(end, rot + to);
                return;
            }
            sprite.MoveX(ease, start, end, a.x, b.x);
            sprite.MoveY(ease, start, end, a.y, b.y);
            sprite.Rotate(ease, start, end, rot + from, rot + to);
        }

        // The title is already under the bands when they start to shrink, and the whole card starts scaling down immediately.
        private void PlaceTitle(StoryboardLayer layer)
        {
            var page = layer.CreateSprite("sb/px.png", OsbOrigin.Centre);
            page.Color(BandCoverEnd, 247 / 255.0, 244 / 255.0, 238 / 255.0);
            page.ScaleVec(BandCoverEnd, 854, 480);
            page.Move(BandCoverEnd, 320, 240);
            page.Fade(0, 0);
            page.Fade(BandCoverEnd, BandShrinkStart + TitleShowMs + TitleHoldMs + TitleDriftMs, 1, 1);
            SequenceMaterial.Paper(layer, BandCoverEnd,
                BandShrinkStart + TitleShowMs + TitleHoldMs + TitleDriftMs, SequenceMaterial.TitlePaperOpacity);

            var layoutPath = Path.Combine(MapsetPath, "sb", "title", "layout.txt");
            var glyphs = new List<(string name, float x, float y, float h)>();
            var dots = new List<(string name, float x, float y)>();
            var enName = "en.png";
            var enX = TitleX;
            var enY = TitleY;
            var ourLeft = 0f;
            var ourRight = 0f;
            foreach (var raw in File.ReadAllLines(layoutPath))
            {
                var text = raw.Trim();
                if (text.Length == 0)
                    continue;
                var parts = text.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (parts[0] == "glyph")
                    glyphs.Add((parts[1], float.Parse(parts[2], CultureInfo.InvariantCulture), float.Parse(parts[3], CultureInfo.InvariantCulture), float.Parse(parts[4], CultureInfo.InvariantCulture)));
                else if (parts[0] == "en")
                {
                    enName = parts[1];
                    enX = float.Parse(parts[2], CultureInfo.InvariantCulture);
                    enY = float.Parse(parts[3], CultureInfo.InvariantCulture);
                }
                else if (parts[0] == "our")
                {
                    ourLeft = float.Parse(parts[1], CultureInfo.InvariantCulture);
                    ourRight = float.Parse(parts[2], CultureInfo.InvariantCulture);
                }
                else if (parts[0] == "dot")
                    dots.Add((parts[1], float.Parse(parts[2], CultureInfo.InvariantCulture), float.Parse(parts[3], CultureInfo.InvariantCulture)));
            }

            var t0 = BandShrinkStart;
            var joinEnd = t0 + TitleJoinMs;
            var scaleEnd = t0 + TitleDriftMs;

            for (var i = 0; i < glyphs.Count; i++)
            {
                var glyph = glyphs[i];
                var sprite = layer.CreateSprite("sb/title/" + glyph.name, OsbOrigin.Centre);
                var offset = glyph.h * 0.28f;
                var fromY = i % 2 == 0 ? glyph.y - offset : glyph.y + offset;
                var startPose = TitlePose(t0, scaleEnd, t0, glyph.x, fromY, 1.02f);
                sprite.MoveX(BandCoverEnd, startPose.x);
                sprite.MoveY(BandCoverEnd, startPose.y);
                sprite.Scale(BandCoverEnd, startPose.scale);
                sprite.Fade(0, 0);
                sprite.Fade(OsbEasing.InOutSine, t0, joinEnd, 0, 1);
                TrackTitle(sprite, t0, scaleEnd, time =>
                {
                    var localY = glyph.y;
                    if (time < joinEnd)
                        localY = Lerp(fromY, glyph.y, InOutSine((time - t0) / (double)TitleJoinMs));
                    var localScale = time >= joinEnd ? 1f : Lerp(1.02f, 1f, InOutSine((time - t0) / (double)TitleJoinMs));
                    return TitlePose(t0, scaleEnd, time, glyph.x, localY, localScale);
                });
            }

            var englishSprite = layer.CreateSprite("sb/title/" + enName, OsbOrigin.Centre);
            var englishStart = TitlePose(t0, scaleEnd, t0, enX, enY + 4f, 1f);
            englishSprite.MoveX(BandCoverEnd, englishStart.x);
            englishSprite.MoveY(BandCoverEnd, englishStart.y);
            englishSprite.Scale(BandCoverEnd, englishStart.scale);
            englishSprite.Fade(0, 0);
            englishSprite.Fade(OsbEasing.OutCubic, t0 + 150, t0 + 540, 0, 1);
            TrackTitle(englishSprite, t0, scaleEnd, time =>
            {
                var localY = enY;
                if (time < t0 + 150)
                    localY = enY + 4f;
                else if (time < t0 + 540)
                    localY = Lerp(enY + 4f, enY, OutCubic((time - (t0 + 150)) / 390.0));
                return TitlePose(t0, scaleEnd, time, enX, localY, 1f);
            });

            dots.Sort((a, b) =>
            {
                var da = (a.x - TitleX) * (a.x - TitleX) + (a.y - TitleY) * (a.y - TitleY);
                var db = (b.x - TitleX) * (b.x - TitleX) + (b.y - TitleY) * (b.y - TitleY);
                return da.CompareTo(db);
            });
            for (var i = 0; i < dots.Count; i++)
            {
                var dot = dots[i];
                var sprite = layer.CreateSprite("sb/title/" + dot.name, OsbOrigin.Centre);
                var born = t0 + i * 22;
                var grown = born + 180;
                var dotStart = TitlePose(t0, scaleEnd, t0, dot.x, dot.y, 0.02f);
                sprite.MoveX(BandCoverEnd, dotStart.x);
                sprite.MoveY(BandCoverEnd, dotStart.y);
                sprite.Scale(BandCoverEnd, dotStart.scale);
                sprite.Fade(0, 0);
                sprite.Fade(OsbEasing.OutCubic, born, grown, 0, 1);
                var dotX = dot.x;
                var dotY = dot.y;
                TrackTitle(sprite, t0, scaleEnd, time =>
                {
                    var localScale = 1f;
                    if (time <= born)
                        localScale = 0.02f;
                    else if (time < grown)
                        localScale = 0.02f + 0.98f * (float)OutBack((time - born) / 180.0);
                    return TitlePose(t0, scaleEnd, time, dotX, dotY, localScale);
                });
            }

            var english = GetMapsetBitmap("sb/title/" + enName);
            if (english != null && ourRight > ourLeft)
            {
                var barW = (ourRight - ourLeft) * 0.42f;
                var barH = english.Height * 0.70f;
                var sweep0 = t0 + 450;
                var sweep1 = t0 + 850;
                var bar = layer.CreateSprite("sb/px.png", OsbOrigin.Centre);
                bar.Color(sweep0, 1, 244 / 255.0, 214 / 255.0); // Warm ivory #FFF4D6; original shine motion retained.
                bar.Fade(0, 0);
                bar.Fade(OsbEasing.OutCubic, sweep0, sweep0 + 80, 0, 0.52f);
                bar.Fade(OsbEasing.OutCubic, sweep1 - 90, sweep1, 0.52f, 0);
                // Normal alpha preserves the ivory tint on the warm paper without clipping it to white.
                var steps = (sweep1 - sweep0) / 16;
                for (var step = 0; step < steps; step++)
                {
                    var from = sweep0 + step * 16;
                    var to = from + 16;
                    var a = HighlightPose(t0, scaleEnd, from, sweep0, sweep1, enY, ourLeft, ourRight, barW, barH);
                    var b = HighlightPose(t0, scaleEnd, to, sweep0, sweep1, enY, ourLeft, ourRight, barW, barH);
                    bar.MoveX(OsbEasing.None, from, to, a.x, b.x);
                    bar.MoveY(OsbEasing.None, from, to, a.y, b.y);
                    bar.ScaleVec(OsbEasing.None, from, to, a.w, a.h, b.w, b.h);
                }
            }
        }

        // The whole title starts shrinking as soon as it appears. No extra rotation or pan.
        private static void TrackTitle(OsbSprite sprite, int start, int end, Func<int, (float x, float y, float scale)> pose)
        {
            var steps = (end - start) / 16;
            for (var step = 0; step < steps; step++)
            {
                var from = start + step * 16;
                var to = from + 16;
                var a = pose(from);
                var b = pose(to);
                sprite.MoveX(OsbEasing.None, from, to, a.x, b.x);
                sprite.MoveY(OsbEasing.None, from, to, a.y, b.y);
                sprite.Scale(OsbEasing.None, from, to, a.scale, b.scale);
            }
        }

        private static (float x, float y, float scale) TitlePose(int start, int end, int time, float rawX, float rawY, float localScale)
        {
            var u = (time - start) / (double)(end - start);
            if (u < 0) u = 0;
            if (u > 1) u = 1;
            var group = 1.0 + (TitleSettleScale - 1.0) * Math.Sin(u * Math.PI / 2.0);
            return (
                (float)(TitleX + (rawX - TitleX) * group),
                (float)(TitleY + (rawY - TitleY) * group),
                (float)(localScale * group));
        }

        private static (float x, float y, float w, float h) HighlightPose(int start, int end, int time, int sweep0, int sweep1, float enY, float ourLeft, float ourRight, float barW, float barH)
        {
            var sweep = (time - sweep0) / (double)(sweep1 - sweep0);
            if (sweep < 0) sweep = 0;
            if (sweep > 1) sweep = 1;
            var rawX = (float)((ourLeft - barW / 2f) + ((ourRight + barW / 2f) - (ourLeft - barW / 2f)) * sweep);
            var pose = TitlePose(start, end, time, rawX, enY, 1f);
            var u = (time - start) / (double)(end - start);
            if (u < 0) u = 0;
            if (u > 1) u = 1;
            var group = 1.0 + (TitleSettleScale - 1.0) * Math.Sin(u * Math.PI / 2.0);
            return (pose.x, pose.y, (float)(barW * group), (float)(barH * group));
        }

        private static float Lerp(float from, float to, double t)
        {
            return (float)(from + (to - from) * t);
        }

        private static double InOutSine(double t)
        {
            if (t <= 0) return 0;
            if (t >= 1) return 1;
            return (1 - Math.Cos(t * Math.PI)) / 2.0;
        }

        private static double OutBack(double t)
        {
            if (t <= 0) return 0;
            if (t >= 1) return 1;
            const double c1 = 1.70158;
            const double c3 = c1 + 1;
            var p = t - 1;
            return 1 + c3 * p * p * p + c1 * p * p;
        }

        // Parallel bands. The rightmost one leads, shooting from the top-right toward the bottom-left. The shrink closes both long edges onto the center line.
        private void PlaceBandWipe(StoryboardLayer layer)
        {
            PlaceTitle(layer);

            for (var i = 0; i < BandCount; i++)
            {
                var drawAt = BandStart + (BandCount - 1 - i) * BandStaggerMs;
                var drawEnd = drawAt + BandDrawMs;
                var closeAt = BandShrinkStart + i * BandGapMs;
                var closeEnd = closeAt + BandShrinkMs;
                var color = BandEditorial.ColorAt(i);
                var width = BandScaleY * BandEditorial.WidthAt(i);

                var band = layer.CreateSprite("sb/band.png", OsbOrigin.Centre);
                band.Color(drawAt, color.R / 255.0, color.G / 255.0, color.B / 255.0);
                var paper = BandEditorial.Paper(layer);
                foreach (var sprite in new[] { band, paper })
                {
                    var opacity = sprite == band ? 1 : BandEditorial.PaperOpacity;
                    sprite.Rotate(drawAt, -BandTheta);
                    sprite.Fade(0, 0);
                    sprite.Fade(drawAt, opacity);
                    sprite.Fade(closeEnd - 48, closeEnd, opacity, 0);
                    sprite.ScaleVec(OsbEasing.OutCubic, drawAt, drawEnd, 0f, width, BandScaleX, width);
                    sprite.ScaleVec(OsbEasing.InCubic, closeAt, closeEnd, BandScaleX, width, BandScaleX, 0f);

                    var steps = BandDrawMs / 16;
                    for (var step = 0; step < steps; step++)
                    {
                        var from = drawAt + step * 16;
                        var to = from + 16;
                        var a = BandPoint(i, OutCubic((from - drawAt) / (double)BandDrawMs));
                        var b = BandPoint(i, OutCubic((to - drawAt) / (double)BandDrawMs));
                        sprite.MoveX(OsbEasing.None, from, to, a.x, b.x);
                        sprite.MoveY(OsbEasing.None, from, to, a.y, b.y);
                    }
                }
            }
        }

        private static (float x, float y) BandPoint(int index, double progress)
        {
            var along = BandEditorial.Offset(index, BandPitch);
            var restX = 320f + (float)(along * Math.Sin(BandTheta));
            var restY = 240f + (float)(along * Math.Cos(BandTheta));
            var shift = BandLength * BandScaleX / 2f * (1.0 - progress);
            return (
                restX + (float)(shift * Math.Cos(BandTheta)),
                restY - (float)(shift * Math.Sin(BandTheta)));
        }

        private static double OutCubic(double t)
        {
            if (t <= 0) return 0;
            if (t >= 1) return 1;
            return 1 - Math.Pow(1 - t, 3);
        }

        private void CreateScrollingBooks(StoryboardLayer booksLayer, int startTime, int endTime, int hide)
            => BooksEditorial.Rows(this, booksLayer, startTime, endTime, hide);

        [Group("Timing")]
        [Configurable] public int StartTime = 0;
        [Configurable] public int EndTime = 0;

        [Group("Sprite")]
        [Description("Leave empty to automatically use the map's background.")]
        [Configurable] public string SpritePath = "";
        [Configurable] public double Opacity = 0.2;

        public override void Generate()
        {
            StageCamera.Verify();
            if (SpritePath == "") SpritePath = Beatmap.BackgroundPath ?? string.Empty;
            if (StartTime == EndTime) EndTime = (int)(Beatmap.HitObjects.LastOrDefault()?.EndTime ?? AudioDuration);

            var bitmap = GetMapsetBitmap(SpritePath);
            var bgLayer = GetLayer("");
            var blueLayer = GetLayer("Blue");
            var booksLayer = GetLayer("BooksLayer");
            var mainLayer = GetLayer("Main");
            int bgInTime = StartTime + 1800;
            int yellowInTime = StartTime;
            int blueInTime = StartTime + 820;
            int booksInTime = StartTime + 820;

            TitleBumper.Background(mainLayer);

            BooksEditorial.Paper(mainLayer, blueInTime, 8200 +
                (Math.Max(0, CountCreditGlyphs("movie") - 1) - Math.Max(0, CountCreditGlyphs("music") - 1)) * 48); // Under logo, credits and star reveal.
            CreateLogo(mainLayer);
            CreateSquareField(mainLayer);
            CreateDiagonalGrid(mainLayer);

            var movieEnd = CreateCredits(mainLayer);
            var pageHandoff = movieEnd + 500; // Original star reaches full cover.
            BooksEditorial.Background(blueLayer, blueInTime, pageHandoff);
            CreateScrollingBooks(booksLayer, booksInTime, IntroEnd - 500, pageHandoff);
            BooksEditorial.FollowingShotUnderlay(blueLayer, booksLayer, booksInTime, pageHandoff, IntroEnd - 500, BandCoverEnd);
            CreateStarCut(mainLayer, movieEnd);

            // =====================
            // 原背景图
            // =====================
            var bg = bgLayer.CreateSprite(SpritePath, OsbOrigin.Centre);
            bg.Scale(bgInTime, 480.0f / bitmap.Height);
            bg.Fade(bgInTime, bgInTime + 500, 0, Opacity);
            bg.Fade(BandCoverEnd, BandCoverEnd + 16, Opacity, 0);

            PlaceBandWipe(GetLayer("Wipe"));


        }
    }
}
