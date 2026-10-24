using StorybrewCommon.Animations;
using StorybrewCommon.Storyboarding;
using System;
using System.Collections.Generic;

namespace StorybrewScripts
{
    // A 2D camera for later shots. Focus is the world point that sits at
    // screen center. Zoom 1 is the normal frame. Positive roll is clockwise.
    // Sprites join a shot through Place, PlaceVec, or PlaceKeys.
    public sealed class StageCamera
    {
        public const float ScreenX = 320f;
        public const float ScreenY = 240f;
        private const int SampleMs = 32;
        private const float MinZoom = 0.002f;

        private readonly List<Key> keys = new List<Key>();
        private readonly List<ShakeSpan> shakes = new List<ShakeSpan>();
        private int shakeSalt;

        public int ShotCount => keys.Count;
        public bool HasShots => keys.Count > 0 || shakes.Count > 0;

        public readonly struct Pose
        {
            public readonly int Time;
            public readonly float X;
            public readonly float Y;
            public readonly float ScaleX;
            public readonly float ScaleY;
            public readonly double Rotation;

            public Pose(int time, float x, float y, float scale = 1f, double rotation = 0)
            {
                Time = time;
                X = x;
                Y = y;
                ScaleX = scale;
                ScaleY = scale;
                Rotation = rotation;
            }

            public Pose(int time, float x, float y, float scaleX, float scaleY, double rotation)
            {
                Time = time;
                X = x;
                Y = y;
                ScaleX = scaleX;
                ScaleY = scaleY;
                Rotation = rotation;
            }
        }

        // Jump to this frame. The first shot is also a jump, from the normal frame.
        public void Cut(int time, float focusX, float focusY, float zoom = 1f, float rollDegrees = 0f)
        {
            Add(new Key(time, focusX, focusY, ClampZoom(zoom), rollDegrees * Math.PI / 180.0, true, OsbEasing.None));
        }

        // Move in from the previous shot. With no previous shot this is a cut.
        public void Ease(int time, float focusX, float focusY, float zoom = 1f, float rollDegrees = 0f, OsbEasing easing = OsbEasing.InOutSine)
        {
            if (keys.Count == 0)
            {
                Cut(time, focusX, focusY, zoom, rollDegrees);
                return;
            }
            Add(new Key(time, focusX, focusY, ClampZoom(zoom), rollDegrees * Math.PI / 180.0, false, easing));
        }

        // Screen-pixel shake. Strength eases in and out at the ends of the span.
        public void Shake(int from, int to, float pixels)
        {
            if (to < from) return;
            if (to - from < 16) to = from + 16;
            shakes.Add(new ShakeSpan(from, to, pixels, ++shakeSalt));
        }

        public (float x, float y) ToScreen(int time, float worldX, float worldY, float depth = 1f)
        {
            var sample = Project(time, worldX, worldY, 1f, 1f, 0, depth);
            return (sample.X, sample.Y);
        }

        // World rotation is radians, the same unit as sprite.Rotate.
        public void Place(OsbSprite sprite, int from, int to, float worldX, float worldY, float scale = 1f, double rotation = 0, float depth = 1f)
        {
            PlaceKeys(sprite, new[]
            {
                new Pose(from, worldX, worldY, scale, rotation),
                new Pose(to, worldX, worldY, scale, rotation),
            }, depth);
        }

        public void PlaceVec(OsbSprite sprite, int from, int to, float worldX, float worldY, float scaleX, float scaleY, double rotation = 0, float depth = 1f)
        {
            PlaceKeys(sprite, new[]
            {
                new Pose(from, worldX, worldY, scaleX, scaleY, rotation),
                new Pose(to, worldX, worldY, scaleX, scaleY, rotation),
            }, depth);
        }

        // Keys are the sprite's own motion in world space. The camera is folded into them.
        // Between keys the world pose moves linearly, so eased motion should already be sampled.
        public void PlaceKeys(OsbSprite sprite, IReadOnlyList<Pose> poses, float depth = 1f)
        {
            if (sprite == null || poses == null || poses.Count == 0) return;
            var ordered = new List<Pose>(poses);
            ordered.Sort((a, b) => a.Time.CompareTo(b.Time));

            var samples = new List<Sample>();
            if (ordered.Count == 1 || ordered[ordered.Count - 1].Time <= ordered[0].Time)
            {
                var pose = ordered[0];
                samples.Add(Project(pose.Time, pose.X, pose.Y, pose.ScaleX, pose.ScaleY, pose.Rotation, depth));
            }
            else
            {
                for (var i = 0; i < ordered.Count - 1; i++)
                {
                    var a = ordered[i];
                    var b = ordered[i + 1];
                    if (b.Time <= a.Time) continue;
                    foreach (var t in SampleTimes(a.Time, b.Time))
                    {
                        var u = (t - a.Time) / (double)(b.Time - a.Time);
                        if (u < 0) u = 0;
                        if (u > 1) u = 1;
                        samples.Add(Project(
                            t,
                            Lerp(a.X, b.X, u),
                            Lerp(a.Y, b.Y, u),
                            Lerp(a.ScaleX, b.ScaleX, u),
                            Lerp(a.ScaleY, b.ScaleY, u),
                            a.Rotation + (b.Rotation - a.Rotation) * u,
                            depth));
                    }
                }
            }
            Emit(sprite, Space(samples));
        }

        public static void Verify()
        {
            var camera = new StageCamera();
            var home = camera.ToScreen(0, 100f, 200f);
            if (Math.Abs(home.x - 100f) > 0.02f || Math.Abs(home.y - 200f) > 0.02f)
                throw new InvalidOperationException("camera identity");

            camera.Cut(0, 420f, 240f, 2f, 0f);
            var center = camera.ToScreen(0, 420f, 240f);
            var beside = camera.ToScreen(0, 320f, 240f);
            if (Math.Abs(center.x - 320f) > 0.02f || Math.Abs(center.y - 240f) > 0.02f)
                throw new InvalidOperationException("camera focus");
            if (Math.Abs(beside.x - 120f) > 0.02f || Math.Abs(beside.y - 240f) > 0.02f)
                throw new InvalidOperationException("camera zoom");

            var turned = new StageCamera();
            turned.Cut(0, 420f, 240f, 1f, 90f);
            var spun = turned.ToScreen(0, 420f, 140f);
            if (Math.Abs(spun.x - 420f) > 0.02f || Math.Abs(spun.y - 240f) > 0.02f)
                throw new InvalidOperationException("camera roll");

            var cuts = new StageCamera();
            cuts.Cut(0, 320f, 240f);
            cuts.Cut(1000, 420f, 240f);
            var held = cuts.ToScreen(500, 420f, 240f);
            var jumped = cuts.ToScreen(1000, 420f, 240f);
            if (Math.Abs(held.x - 420f) > 0.02f || Math.Abs(jumped.x - 320f) > 0.02f)
                throw new InvalidOperationException("camera cut");

            var glide = new StageCamera();
            glide.Cut(0, 320f, 240f);
            glide.Ease(1000, 420f, 240f, 1f, 0f, OsbEasing.InOutSine);
            var mid = glide.ToScreen(500, 370f, 240f);
            if (Math.Abs(mid.x - 320f) > 0.05f)
                throw new InvalidOperationException("camera ease");

            var far = new StageCamera();
            far.Cut(0, 320f, 240f);
            var lagged = far.ToScreen(0, 420f, 240f, 0.5f);
            if (Math.Abs(lagged.x - 370f) > 0.02f)
                throw new InvalidOperationException("camera depth");
        }

        private void Add(Key key)
        {
            for (var i = keys.Count - 1; i >= 0; i--)
            {
                if (Math.Abs(keys[i].Time - key.Time) < 16)
                    keys.RemoveAt(i);
            }
            keys.Add(key);
            keys.Sort((a, b) => a.Time.CompareTo(b.Time));
            for (var i = 1; i < keys.Count; i++)
            {
                if (keys[i].Time >= keys[i - 1].Time + 16) continue;
                var shifted = keys[i];
                shifted.Time = keys[i - 1].Time + 16;
                keys[i] = shifted;
            }
        }

        private View ViewAt(double time)
        {
            var view = new View { FocusX = ScreenX, FocusY = ScreenY, Zoom = 1f };
            if (keys.Count > 0 && time >= keys[0].Time)
            {
                if (time >= keys[keys.Count - 1].Time)
                {
                    view = ViewFrom(keys[keys.Count - 1]);
                }
                else
                {
                    var i = 0;
                    while (i + 1 < keys.Count && keys[i + 1].Time <= time) i++;
                    var a = keys[i];
                    var b = keys[i + 1];
                    if (b.Cut || b.Time <= a.Time)
                    {
                        view = ViewFrom(a);
                    }
                    else
                    {
                        var u = (time - a.Time) / (double)(b.Time - a.Time);
                        var e = b.Easing.Ease(u);
                        view.FocusX = (float)(a.X + (b.X - a.X) * e);
                        view.FocusY = (float)(a.Y + (b.Y - a.Y) * e);
                        view.Zoom = (float)(a.Zoom + (b.Zoom - a.Zoom) * e);
                        view.Roll = a.Roll + (b.Roll - a.Roll) * e;
                    }
                }
            }
            view.ShakeX = ShakeAt(time, 1);
            view.ShakeY = ShakeAt(time, 2);
            return view;
        }

        private static View ViewFrom(Key key)
        {
            return new View
            {
                FocusX = key.X,
                FocusY = key.Y,
                Zoom = key.Zoom,
                Roll = key.Roll,
            };
        }

        private float ShakeAt(double time, int axis)
        {
            var sum = 0.0;
            foreach (var shake in shakes)
            {
                if (time < shake.From || time > shake.To || shake.To <= shake.From) continue;
                var edge = Math.Min((time - shake.From) / 48.0, (shake.To - time) / 48.0);
                if (edge <= 0) continue;
                if (edge > 1) edge = 1;
                var bucket = (int)(time / SampleMs);
                sum += edge * shake.Pixels * Hash(bucket, axis + shake.Salt);
            }
            return (float)sum;
        }

        private Sample Project(int time, float worldX, float worldY, float scaleX, float scaleY, double rotation, float depth)
        {
            var view = ViewAt(time);
            var dx = worldX - view.FocusX;
            var dy = worldY - view.FocusY;
            var cos = Math.Cos(view.Roll);
            var sin = Math.Sin(view.Roll);
            var rx = dx * cos - dy * sin;
            var ry = dx * sin + dy * cos;
            var z = view.Zoom * depth;
            return new Sample
            {
                Time = time,
                X = (float)(ScreenX + rx * z + view.ShakeX),
                Y = (float)(ScreenY + ry * z + view.ShakeY),
                ScaleX = scaleX * view.Zoom,
                ScaleY = scaleY * view.Zoom,
                Rotation = rotation + view.Roll,
            };
        }

        private List<int> SampleTimes(int from, int to)
        {
            var times = new List<int> { from, to };
            for (var i = 0; i < keys.Count; i++)
            {
                var key = keys[i];
                if (key.Cut && key.Time > from && key.Time <= to)
                {
                    var pre = key.Time - 16;
                    if (pre > from) times.Add(pre);
                    times.Add(key.Time);
                }
                if (i == 0 || key.Cut) continue;
                var segStart = keys[i - 1].Time;
                var segEnd = key.Time;
                if (segEnd <= from || segStart >= to) continue;
                var start = Math.Max(from, segStart);
                var end = Math.Min(to, segEnd);
                for (var t = start; t < end; t += SampleMs)
                    times.Add(t);
                times.Add(end);
            }
            foreach (var shake in shakes)
            {
                if (shake.To <= from || shake.From >= to) continue;
                var start = Math.Max(from, shake.From);
                var end = Math.Min(to, shake.To);
                for (var t = start; t < end; t += SampleMs)
                    times.Add(t);
                times.Add(end);
            }
            return Sanitize(times);
        }

        private static List<int> Sanitize(List<int> times)
        {
            times.Sort();
            var kept = new List<int>();
            foreach (var t in times)
            {
                if (kept.Count == 0 || t != kept[kept.Count - 1])
                    kept.Add(t);
            }
            for (var i = 1; i < kept.Count; i++)
            {
                if (kept[i] < kept[i - 1] + 16)
                    kept[i] = kept[i - 1] + 16;
            }
            var unique = new List<int>();
            foreach (var t in kept)
            {
                if (unique.Count == 0 || t != unique[unique.Count - 1])
                    unique.Add(t);
            }
            return unique;
        }

        // Storybrew treats a command as overlapped when the next one starts
        // before the previous one ends. Samples from neighbouring keys can land
        // inside that gap after short segments are padded, so keep one sample
        // and leave at least 16ms before the next.
        private static List<Sample> Space(List<Sample> samples)
        {
            samples.Sort((a, b) => a.Time.CompareTo(b.Time));
            var spaced = new List<Sample>();
            foreach (var sample in samples)
            {
                if (spaced.Count == 0)
                {
                    spaced.Add(sample);
                    continue;
                }
                if (sample.Time >= spaced[spaced.Count - 1].Time + 16)
                    spaced.Add(sample);
            }
            return spaced;
        }

        private static void Emit(OsbSprite sprite, List<Sample> samples)
        {
            if (samples.Count == 0) return;
            var vec = false;
            foreach (var sample in samples)
            {
                if (Math.Abs(sample.ScaleX - sample.ScaleY) > 0.0001f)
                {
                    vec = true;
                    break;
                }
            }

            EmitMove(sprite, samples);
            if (vec) EmitScaleVec(sprite, samples);
            else EmitScale(sprite, samples);
            EmitRotate(sprite, samples);
        }

        private static void EmitMove(OsbSprite sprite, List<Sample> samples)
        {
            if (Flat(samples, s => s.X) && Flat(samples, s => s.Y))
            {
                sprite.Move(samples[0].Time, samples[0].X, samples[0].Y);
                return;
            }
            for (var i = 1; i < samples.Count; i++)
            {
                var a = samples[i - 1];
                var b = samples[i];
                if (b.Time < a.Time + 16) continue;
                sprite.Move(OsbEasing.None, a.Time, b.Time, a.X, a.Y, b.X, b.Y);
            }
        }

        private static void EmitScale(OsbSprite sprite, List<Sample> samples)
        {
            if (Flat(samples, s => s.ScaleX))
            {
                sprite.Scale(samples[0].Time, SafeScale(samples[0].ScaleX));
                return;
            }
            for (var i = 1; i < samples.Count; i++)
            {
                var a = samples[i - 1];
                var b = samples[i];
                if (b.Time < a.Time + 16) continue;
                sprite.Scale(OsbEasing.None, a.Time, b.Time, SafeScale(a.ScaleX), SafeScale(b.ScaleX));
            }
        }

        private static void EmitScaleVec(OsbSprite sprite, List<Sample> samples)
        {
            if (Flat(samples, s => s.ScaleX) && Flat(samples, s => s.ScaleY))
            {
                sprite.ScaleVec(samples[0].Time, SafeScale(samples[0].ScaleX), SafeScale(samples[0].ScaleY));
                return;
            }
            for (var i = 1; i < samples.Count; i++)
            {
                var a = samples[i - 1];
                var b = samples[i];
                if (b.Time < a.Time + 16) continue;
                sprite.ScaleVec(
                    OsbEasing.None, a.Time, b.Time,
                    SafeScale(a.ScaleX), SafeScale(a.ScaleY),
                    SafeScale(b.ScaleX), SafeScale(b.ScaleY));
            }
        }

        private static void EmitRotate(OsbSprite sprite, List<Sample> samples)
        {
            var changing = false;
            foreach (var sample in samples)
            {
                if (Math.Abs(sample.Rotation - samples[0].Rotation) > 0.0005)
                {
                    changing = true;
                    break;
                }
            }
            if (!changing)
            {
                if (Math.Abs(samples[0].Rotation) > 0.0005)
                    sprite.Rotate(samples[0].Time, samples[0].Rotation);
                return;
            }
            for (var i = 1; i < samples.Count; i++)
            {
                var a = samples[i - 1];
                var b = samples[i];
                if (b.Time < a.Time + 16) continue;
                sprite.Rotate(OsbEasing.None, a.Time, b.Time, a.Rotation, b.Rotation);
            }
        }

        private static bool Flat(List<Sample> samples, Func<Sample, float> pick)
        {
            var first = pick(samples[0]);
            for (var i = 1; i < samples.Count; i++)
            {
                if (Math.Abs(pick(samples[i]) - first) > 0.05f) return false;
            }
            return true;
        }

        private static float Lerp(float a, float b, double u) => (float)(a + (b - a) * u);

        private static double SafeScale(double scale)
        {
            if (double.IsNaN(scale) || double.IsInfinity(scale)) return 0.0001;
            if (Math.Abs(scale) < 0.0001) return scale < 0 ? -0.0001 : 0.0001;
            return scale;
        }

        private static float ClampZoom(float zoom)
        {
            if (float.IsNaN(zoom) || zoom < MinZoom) return MinZoom;
            return zoom;
        }

        private static float Hash(int bucket, int salt)
        {
            unchecked
            {
                var n = bucket * 374761393 + salt * 668265263;
                n = (n ^ (n >> 13)) * 1274126177;
                n ^= n >> 16;
                return (n & 65535) / 32767.5f - 1f;
            }
        }

        private struct Key
        {
            public int Time;
            public float X;
            public float Y;
            public float Zoom;
            public double Roll;
            public bool Cut;
            public OsbEasing Easing;

            public Key(int time, float x, float y, float zoom, double roll, bool cut, OsbEasing easing)
            {
                Time = time;
                X = x;
                Y = y;
                Zoom = zoom;
                Roll = roll;
                Cut = cut;
                Easing = easing;
            }
        }

        private readonly struct ShakeSpan
        {
            public readonly int From;
            public readonly int To;
            public readonly float Pixels;
            public readonly int Salt;

            public ShakeSpan(int from, int to, float pixels, int salt)
            {
                From = from;
                To = to;
                Pixels = pixels;
                Salt = salt;
            }
        }

        private struct View
        {
            public float FocusX;
            public float FocusY;
            public float Zoom;
            public double Roll;
            public float ShakeX;
            public float ShakeY;
        }

        private struct Sample
        {
            public int Time;
            public float X;
            public float Y;
            public float ScaleX;
            public float ScaleY;
            public double Rotation;
        }
    }
}
