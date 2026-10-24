using System;
using System.Collections.Generic;
using System.Drawing;
using OpenTK;
using StorybrewCommon.Animations;
using StorybrewCommon.Storyboarding;

namespace StorybrewScripts
{
    /// <summary>World-space cards baked to ordinary osu! sprites. +Z goes away from the camera.</summary>
    public static class Pseudo3D
    {
        public struct Pose
        {
            public Vector3 Position;
            public Vector2 Scale;
            // Radians, applied X (pitch), Y (yaw), Z (roll), in that order.
            public Vector3 Rotation;

            public Pose(float x, float y, float z, float scale = 1)
            {
                Position = new Vector3(x, y, z);
                Scale = new Vector2(scale, scale);
                Rotation = Vector3.Zero;
            }

            public Pose(Vector3 position, Vector2 scale, Vector3 rotation)
            {
                Position = position;
                Scale = scale;
                Rotation = rotation;
            }
        }

        public readonly struct Key
        {
            public readonly double Time;
            public readonly Pose Pose;
            public readonly OsbEasing Easing;
            public readonly bool Cut;

            public Key(double time, Pose pose, OsbEasing easing = OsbEasing.None, bool cut = false)
            {
                Time = time;
                Pose = pose;
                Easing = easing;
                Cut = cut;
            }
        }

        /// <summary>Each key's easing describes the move INTO that key; cut holds until its time.</summary>
        public sealed class Track
        {
            internal readonly List<Key> Keys = new List<Key>();

            public Track(params Key[] keys)
            {
                if (keys == null || keys.Length == 0) throw new ArgumentException("At least one pose is required.");
                Keys.AddRange(keys);
                Keys.Sort((a, b) => a.Time.CompareTo(b.Time));
                for (var i = 0; i < Keys.Count; i++)
                {
                    Finite(Keys[i].Time, nameof(keys));
                    CheckPose(Keys[i].Pose);
                    if (i > 0 && Keys[i].Time <= Keys[i - 1].Time)
                        throw new ArgumentException("Key times must be unique.", nameof(keys));
                }
            }

            public Pose At(double time)
            {
                if (time <= Keys[0].Time) return Keys[0].Pose;
                for (var i = 1; i < Keys.Count; i++)
                {
                    var b = Keys[i];
                    if (time >= b.Time) continue;
                    var a = Keys[i - 1];
                    if (b.Cut) return a.Pose;
                    var u = (float)b.Easing.Ease((time - a.Time) / (b.Time - a.Time));
                    return new Pose(a.Pose.Position + (b.Pose.Position - a.Pose.Position) * u,
                        a.Pose.Scale + (b.Pose.Scale - a.Pose.Scale) * u,
                        a.Pose.Rotation + (b.Pose.Rotation - a.Pose.Rotation) * u);
                }
                return Keys[Keys.Count - 1].Pose;
            }
        }

        public sealed class Camera
        {
            public Track Motion = new Track(new Key(0, new Pose(320, 240, -1000)));
            public float FocalLength = 1000;
            public float NearClip = 25;
            public float FarClip = 20000;
            public Vector2 ScreenCenter = new Vector2(320, 240);

            public Projection Project(double time, Pose pose, bool billboard = false)
            {
                Validate();
                CheckPose(pose);
                return ProjectAt(Motion.At(time), pose, billboard);
            }

            internal Projection ProjectAt(Pose view, Pose pose, bool billboard)
            {
                var center = InverseRotate(pose.Position - view.Position, view.Rotation);
                var visible = center.Z >= NearClip && center.Z <= FarClip;
                var depth = Math.Max(NearClip, center.Z);
                var factor = FocalLength / depth;
                var right = billboard ? new Vector3(1, 0, 0)
                    : InverseRotate(Rotate(new Vector3(1, 0, 0), pose.Rotation), view.Rotation);
                var down = billboard ? new Vector3(0, 1, 0)
                    : InverseRotate(Rotate(new Vector3(0, 1, 0), pose.Rotation), view.Rotation);
                if (billboard)
                {
                    right = Rotate(right, new Vector3(0, 0, pose.Rotation.Z));
                    down = Rotate(down, new Vector3(0, 0, pose.Rotation.Z));
                }
                // Perspective derivatives at the card center. osu! has no shear command:
                // retain the projected X axis and perpendicular Y component.
                var x = new Vector2(right.X - center.X * right.Z / depth, right.Y - center.Y * right.Z / depth);
                var y = new Vector2(down.X - center.X * down.Z / depth, down.Y - center.Y * down.Z / depth);
                var width = x.Length;
                var height = width > .00001f ? (x.X * y.Y - x.Y * y.X) / width : 0;
                return new Projection
                {
                    Position = ScreenCenter + new Vector2(center.X, center.Y) * factor,
                    Scale = new Vector2(Math.Max(.00001f, width * pose.Scale.X * factor),
                        Math.Max(.00001f, Math.Abs(height) * pose.Scale.Y * factor)),
                    Rotation = Math.Atan2(x.Y, x.X),
                    Depth = center.Z,
                    Visible = visible && width > .00001f && Math.Abs(height) > .00001f,
                };
            }

            internal void Validate()
            {
                if (Motion == null) throw new ArgumentNullException(nameof(Motion));
                Positive(FocalLength, nameof(FocalLength));
                Positive(NearClip, nameof(NearClip));
                Positive(FarClip, nameof(FarClip));
                if (FarClip <= NearClip) throw new ArgumentOutOfRangeException(nameof(FarClip));
                CheckVector(new Vector3(ScreenCenter.X, ScreenCenter.Y, 0));
            }
        }

        public struct Projection
        {
            public Vector2 Position;
            public Vector2 Scale;
            public double Rotation;
            public float Depth;
            public bool Visible;
        }

        public sealed class Light
        {
            public Track Motion = new Track(new Key(0, new Pose(320, 100, -400)));
            public Color Color = Color.White;
            public float Intensity = .8f;
            // Point: half the intensity at Range. Directional: direction points toward the source.
            public float Range = 600;
            public bool Directional;
            public Vector3 Direction = new Vector3(0, 0, -1);

            internal void Validate()
            {
                if (Motion == null) throw new ArgumentNullException(nameof(Motion));
                NonNegative(Intensity, nameof(Intensity));
                Positive(Range, nameof(Range));
                CheckVector(Direction);
                if (Directional && Direction.LengthSquared < .000001f)
                    throw new ArgumentException("Directional light needs a direction.");
            }
        }

        public sealed class Material
        {
            public Color Color = Color.White;
            public bool Unlit;
            public bool TwoSided = true;
            public bool ReceivesFog = true;
        }

        public sealed class Node
        {
            public string Texture;
            public Track Motion;
            // Optional procedural motion (e.g. orbit/rope/particle), evaluated in world coordinates.
            public Func<double, Pose> MotionAt;
            public Func<double, double> OpacityAt;
            public Material Material = new Material();
            public bool Billboard;
            public double Start;
            public double End;
            public double Opacity = 1;
            public double FadeIn;
            public double FadeOut;
            internal Func<double, bool> VisibleAt;
            internal Light AttachedLight;

            internal Pose At(double time) => MotionAt != null ? MotionAt(time) : Motion.At(time);

            internal double Alpha(double time)
            {
                var opacity = OpacityAt != null ? OpacityAt(time) : Opacity;
                Unit(opacity, nameof(Opacity));
                var fit = FadeIn + FadeOut > End - Start ? (End - Start) / (FadeIn + FadeOut) : 1;
                var attack = FadeIn * fit;
                var release = FadeOut * fit;
                if (attack > 0) opacity *= Clamp((time - Start) / attack);
                if (release > 0) opacity *= Clamp((End - time) / release);
                return opacity;
            }
        }

        public sealed class Scene
        {
            public readonly Camera Camera = new Camera();
            public readonly List<Light> Lights = new List<Light>();
            public readonly List<Node> Nodes = new List<Node>();
            public Color AmbientColor = Color.White;
            public float Ambient = .35f;
            public Color FogColor = Color.FromArgb(244, 239, 232);
            public float FogNear = 2000;
            public float FogFar = 6000;
            public bool Fog;
            public int SampleMs = 32;

            public Node Add(string texture, double start, double end, Track motion,
                Color? color = null, bool billboard = false)
            {
                var node = new Node
                {
                    Texture = texture, Start = start, End = end, Motion = motion,
                    Billboard = billboard, Material = new Material { Color = color ?? Color.White },
                };
                ValidateNode(node);
                Nodes.Add(node);
                return node;
            }

            /// <summary>Project a centered silhouette from a point light onto a parallel Z receiver.</summary>
            public Node AddShadow(Node caster, Light light, float receiverZ, double opacity = .22)
            {
                if (caster == null || light == null) throw new ArgumentNullException("caster/light");
                if (light.Directional) throw new ArgumentException("Silhouette shadows require a point light.");
                Finite(receiverZ, nameof(receiverZ));
                Unit(opacity, nameof(opacity));
                var shadow = Add(caster.Texture, caster.Start, caster.End,
                    caster.Motion ?? new Track(new Key(caster.Start, caster.At(caster.Start))), Color.Black);
                shadow.Material.Unlit = true;
                shadow.Material.ReceivesFog = false;
                shadow.AttachedLight = light;
                shadow.MotionAt = time =>
                {
                    var pose = caster.At(time);
                    var source = light.Motion.At(time).Position;
                    var dz = pose.Position.Z - source.Z;
                    var ratio = Math.Abs(dz) > .00001f ? (receiverZ - source.Z) / dz : 1;
                    return new Pose(source + (pose.Position - source) * ratio,
                        pose.Scale * Math.Abs(ratio), pose.Rotation);
                };
                shadow.VisibleAt = time =>
                {
                    var z = caster.At(time).Position.Z;
                    return light.Motion.At(time).Position.Z < z && z < receiverZ
                        && (caster.VisibleAt == null || caster.VisibleAt(time));
                };
                shadow.OpacityAt = time => caster.Alpha(time) * opacity;
                return shadow;
            }

            /// <summary>Existing LightingFx texture on a world plane, following an animated point light.</summary>
            public Node AddLightSpot(Light light, double start, double end, float receiverZ,
                Vector2 scale, double opacity = .12, string texture = LightingFx.BigSpot)
            {
                if (light == null) throw new ArgumentNullException(nameof(light));
                if (light.Directional) throw new ArgumentException("Light spots require a point light.");
                var spot = Add(texture, start, end, new Track(new Key(start,
                    new Pose(new Vector3(320, 240, receiverZ), scale, Vector3.Zero))), light.Color);
                spot.Material.Unlit = true;
                spot.Material.ReceivesFog = false;
                spot.AttachedLight = light;
                spot.MotionAt = time =>
                {
                    var at = light.Motion.At(time).Position;
                    return new Pose(new Vector3(at.X, at.Y, receiverZ), scale, Vector3.Zero);
                };
                spot.Opacity = opacity;
                spot.FadeIn = 120;
                spot.FadeOut = 160;
                return spot;
            }

            public Vector3 Shade(double time, Pose pose, Material material, bool billboard = false)
            {
                if (material == null) throw new ArgumentNullException(nameof(material));
                var normal = Rotate(new Vector3(0, 0, -1), billboard ? Camera.Motion.At(time).Rotation : pose.Rotation);
                var illumination = Rgb(AmbientColor) * Ambient;
                if (material.Unlit) illumination = Vector3.One;
                else foreach (var light in Lights)
                {
                    var delta = light.Directional ? light.Direction : light.Motion.At(time).Position - pose.Position;
                    var length = delta.Length;
                    if (length < .00001f) continue;
                    var cosine = Vector3.Dot(normal, delta / length);
                    cosine = material.TwoSided ? Math.Abs(cosine) : Math.Max(0, cosine);
                    var attenuation = light.Directional ? 1 : 1 / (1 + length * length / (light.Range * light.Range));
                    illumination += Rgb(light.Color) * (light.Intensity * cosine * attenuation);
                }
                var baseColor = Rgb(material.Color);
                var color = new Vector3(baseColor.X * illumination.X, baseColor.Y * illumination.Y, baseColor.Z * illumination.Z);
                color = new Vector3((float)Clamp(color.X), (float)Clamp(color.Y), (float)Clamp(color.Z));
                if (Fog && material.ReceivesFog)
                {
                    var depth = Camera.ProjectAt(Camera.Motion.At(time), pose, billboard).Depth;
                    var amount = (float)Clamp((depth - FogNear) / (FogFar - FogNear));
                    color += (Rgb(FogColor) - color) * amount;
                }
                return color;
            }

            /// <summary>Owns transform, color and opacity commands. Keep all mutually occluding nodes on ONE layer.</summary>
            public IReadOnlyList<OsbSprite> Bake(StoryboardLayer layer, double start, double end)
            {
                if (layer == null) throw new ArgumentNullException(nameof(layer));
                Finite(start, nameof(start));
                Finite(end, nameof(end));
                if (end <= start) throw new ArgumentOutOfRangeException(nameof(end));
                Camera.Validate();
                NonNegative(Ambient, nameof(Ambient));
                if (SampleMs < 1) throw new ArgumentOutOfRangeException(nameof(SampleMs));
                if (Fog)
                {
                    Finite(FogNear, nameof(FogNear));
                    Finite(FogFar, nameof(FogFar));
                    if (FogFar <= FogNear) throw new ArgumentOutOfRangeException(nameof(FogFar));
                }
                foreach (var light in Lights) light.Validate();
                foreach (var node in Nodes)
                {
                    ValidateNode(node);
                    if (node.AttachedLight != null) node.AttachedLight.Validate();
                }
                var times = new SortedSet<double> { start, end };
                for (var time = start + SampleMs; time < end; time += SampleMs) times.Add(time);
                AddTimes(times, Camera.Motion, start, end);
                foreach (var light in Lights) AddTimes(times, light.Motion, start, end);
                foreach (var node in Nodes)
                {
                    AddTime(times, node.Start, start, end);
                    AddTime(times, node.End, start, end);
                    var fit = node.FadeIn + node.FadeOut > node.End - node.Start
                        ? (node.End - node.Start) / (node.FadeIn + node.FadeOut) : 1;
                    AddTime(times, node.Start + node.FadeIn * fit, start, end);
                    AddTime(times, node.End - node.FadeOut * fit, start, end);
                    AddTimes(times, node.Motion, start, end);
                    if (node.AttachedLight != null) AddTimes(times, node.AttachedLight.Motion, start, end);
                }
                var orderedTimes = new List<double>(times);
                var baked = new List<OsbSprite>();
                List<int> previous = null;
                var run = new List<double>();
                for (var i = 0; i < orderedTimes.Count - 1; i++)
                {
                    var time = orderedTimes[i];
                    var order = OrderAt(time);
                    // A cut must not be interpolated across, even if depth order stays the same.
                    if (previous != null && (!SameOrder(previous, order) || IsCut(time)))
                    {
                        run.Add(time);
                        EmitRun(layer, baked, previous, run, IsCut(time));
                        run.Clear();
                    }
                    previous = order;
                    run.Add(time);
                }
                if (previous != null)
                {
                    run.Add(end);
                    EmitRun(layer, baked, previous, run, IsCut(end));
                }
                return baked;
            }

            private List<int> OrderAt(double time)
            {
                var order = new List<int>();
                var depths = new Dictionary<int, float>();
                var view = Camera.Motion.At(time);
                for (var i = 0; i < Nodes.Count; i++)
                {
                    var node = Nodes[i];
                    if (time < node.Start || time >= node.End || (node.VisibleAt != null && !node.VisibleAt(time))) continue;
                    var pose = node.At(time);
                    CheckPose(pose);
                    var projection = Camera.ProjectAt(view, pose, node.Billboard);
                    if (!projection.Visible) continue;
                    order.Add(i);
                    depths[i] = projection.Depth;
                }
                order.Sort((a, b) =>
                {
                    var compare = depths[b].CompareTo(depths[a]);
                    return compare != 0 ? compare : a.CompareTo(b);
                });
                return order;
            }

            private void EmitRun(StoryboardLayer layer, List<OsbSprite> baked, List<int> order,
                List<double> times, bool cutAtEnd)
            {
                var start = times[0];
                var end = times[times.Count - 1];
                foreach (var index in order)
                {
                    var node = Nodes[index];
                    var sprite = layer.CreateSprite(node.Texture, OsbOrigin.Centre);
                    baked.Add(sprite);
                    var a = Sample(node, start);
                    sprite.Move(start, a.Projection.Position.X, a.Projection.Position.Y);
                    sprite.ScaleVec(start, a.Projection.Scale.X, a.Projection.Scale.Y);
                    sprite.Rotate(start, a.Projection.Rotation);
                    sprite.Color(start, a.Color.X, a.Color.Y, a.Color.Z);
                    var releaseStart = Math.Max(start, end - Math.Min(1, (end - start) / 2));
                    var alphaTimes = new SortedSet<double> { start, releaseStart };
                    foreach (var time in times) if (time > start && time < releaseStart) alphaTimes.Add(time);
                    var at = start;
                    var alpha = node.Alpha(start);
                    sprite.Fade(start, alpha);
                    foreach (var time in alphaTimes)
                    {
                        if (time <= start) continue;
                        var next = node.Alpha(time);
                        sprite.Fade(OsbEasing.None, at, time, alpha, next);
                        at = time;
                        alpha = next;
                    }
                    sprite.Fade(OsbEasing.None, releaseStart, end, alpha, 0);
                    for (var i = 1; i < times.Count; i++)
                    {
                        var time = times[i];
                        // End sample of a cut uses the old pose, then the new sprite starts at the cut.
                        var b = Sample(node, cutAtEnd && i == times.Count - 1 ? time - .000001 : time);
                        var from = times[i - 1];
                        sprite.Move(OsbEasing.None, from, time, a.Projection.Position.X, a.Projection.Position.Y,
                            b.Projection.Position.X, b.Projection.Position.Y);
                        sprite.ScaleVec(OsbEasing.None, from, time, a.Projection.Scale.X, a.Projection.Scale.Y,
                            b.Projection.Scale.X, b.Projection.Scale.Y);
                        var angle = b.Projection.Rotation;
                        while (angle - a.Projection.Rotation > Math.PI) angle -= Math.PI * 2;
                        while (angle - a.Projection.Rotation < -Math.PI) angle += Math.PI * 2;
                        b.Projection.Rotation = angle;
                        sprite.Rotate(OsbEasing.None, from, time, a.Projection.Rotation, angle);
                        sprite.Color(OsbEasing.None, from, time, a.Color.X, a.Color.Y, a.Color.Z, b.Color.X, b.Color.Y, b.Color.Z);
                        a = b;
                    }
                }
            }

            private Frame Sample(Node node, double time)
            {
                var pose = node.At(time);
                CheckPose(pose);
                return new Frame
                {
                    Projection = Camera.ProjectAt(Camera.Motion.At(time), pose, node.Billboard),
                    Color = Shade(time, pose, node.Material, node.Billboard),
                };
            }

            private bool IsCut(double time)
            {
                if (HasCut(Camera.Motion, time)) return true;
                foreach (var light in Lights) if (HasCut(light.Motion, time)) return true;
                foreach (var node in Nodes)
                    if (HasCut(node.Motion, time) || (node.AttachedLight != null && HasCut(node.AttachedLight.Motion, time))) return true;
                return false;
            }

            private struct Frame { public Projection Projection; public Vector3 Color; }
        }

        private static bool SameOrder(List<int> a, List<int> b)
        {
            if (a.Count != b.Count) return false;
            for (var i = 0; i < a.Count; i++) if (a[i] != b[i]) return false;
            return true;
        }

        private static bool HasCut(Track track, double time)
        {
            if (track != null) foreach (var key in track.Keys) if (key.Time == time && key.Cut) return true;
            return false;
        }

        private static void AddTimes(SortedSet<double> times, Track track, double start, double end)
        {
            if (track == null) return;
            foreach (var key in track.Keys)
            {
                AddTime(times, key.Time, start, end);
                if (key.Cut) AddTime(times, key.Time - .001, start, end);
            }
        }

        private static void AddTime(SortedSet<double> times, double time, double start, double end)
        {
            if (time > start && time < end) times.Add(time);
        }

        private static void ValidateNode(Node node)
        {
            if (string.IsNullOrWhiteSpace(node.Texture)) throw new ArgumentException("Texture path is required.");
            if (node.Motion == null && node.MotionAt == null) throw new ArgumentException("World motion is required.");
            if (node.Material == null) throw new ArgumentNullException(nameof(node.Material));
            Finite(node.Start, nameof(node.Start));
            Finite(node.End, nameof(node.End));
            if (node.End <= node.Start) throw new ArgumentException("End must be after start.");
            Unit(node.Opacity, nameof(node.Opacity));
            NonNegative(node.FadeIn, nameof(node.FadeIn));
            NonNegative(node.FadeOut, nameof(node.FadeOut));
        }

        private static Vector3 Rotate(Vector3 p, Vector3 r)
        {
            var cx = (float)Math.Cos(r.X); var sx = (float)Math.Sin(r.X);
            var cy = (float)Math.Cos(r.Y); var sy = (float)Math.Sin(r.Y);
            var cz = (float)Math.Cos(r.Z); var sz = (float)Math.Sin(r.Z);
            p = new Vector3(p.X, p.Y * cx - p.Z * sx, p.Y * sx + p.Z * cx);
            p = new Vector3(p.X * cy + p.Z * sy, p.Y, -p.X * sy + p.Z * cy);
            return new Vector3(p.X * cz - p.Y * sz, p.X * sz + p.Y * cz, p.Z);
        }

        private static Vector3 InverseRotate(Vector3 p, Vector3 r)
        {
            var cx = (float)Math.Cos(r.X); var sx = (float)Math.Sin(r.X);
            var cy = (float)Math.Cos(r.Y); var sy = (float)Math.Sin(r.Y);
            var cz = (float)Math.Cos(r.Z); var sz = (float)Math.Sin(r.Z);
            p = new Vector3(p.X * cz + p.Y * sz, -p.X * sz + p.Y * cz, p.Z);
            p = new Vector3(p.X * cy - p.Z * sy, p.Y, p.X * sy + p.Z * cy);
            return new Vector3(p.X, p.Y * cx + p.Z * sx, -p.Y * sx + p.Z * cx);
        }

        private static Vector3 Rgb(Color color) => new Vector3(color.R / 255f, color.G / 255f, color.B / 255f);
        private static double Clamp(double value) => Math.Max(0, Math.Min(1, value));
        private static void CheckPose(Pose pose)
        {
            CheckVector(pose.Position); CheckVector(pose.Rotation);
            Positive(pose.Scale.X, nameof(pose.Scale)); Positive(pose.Scale.Y, nameof(pose.Scale));
        }
        private static void CheckVector(Vector3 vector)
        {
            Finite(vector.X, nameof(vector)); Finite(vector.Y, nameof(vector)); Finite(vector.Z, nameof(vector));
        }
        private static void Unit(double value, string name)
        {
            Finite(value, name);
            if (value < 0 || value > 1) throw new ArgumentOutOfRangeException(name);
        }
        private static void Positive(double value, string name)
        {
            Finite(value, name);
            if (value <= 0) throw new ArgumentOutOfRangeException(name);
        }
        private static void NonNegative(double value, string name)
        {
            Finite(value, name);
            if (value < 0) throw new ArgumentOutOfRangeException(name);
        }
        private static void Finite(double value, string name)
        {
            if (double.IsNaN(value) || double.IsInfinity(value)) throw new ArgumentOutOfRangeException(name);
        }
    }
}
