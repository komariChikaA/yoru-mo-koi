using System;
using System.Collections.Generic;
using System.Drawing;
using OpenTK;
using StorybrewCommon.Storyboarding;

namespace StorybrewScripts
{
    /// <summary>Flat print sheen using normal-alpha sprites, without additive light or bloom.</summary>
    public static class LightingFx
    {
        public const string WideSweep = "sb/lighting-fx/light_sweep_wide.png";
        public const string NarrowSweep = "sb/lighting-fx/light_sweep_narrow.png";
        public const string RoundSpot = "sb/lighting-fx/soft_glow_round.png";
        public const string BigSpot = "sb/lighting-fx/soft_glow_big.png";
        public const string PaperBand = "sb/lighting-fx/paper_shine.png";
        public const string LineBand = "sb/lighting-fx/line_shine.png";
        public const string TubeBeam = "sb/lighting-fx/light_tube_beam.png";
        public static Color WarmIvory => Color.FromArgb(255, 244, 214);

        /// <summary>End of a native motion leg. Different axis easings produce a curved path.</summary>
        public readonly struct SweepPoint
        {
            public double Time { get; }
            public Vector2 Position { get; }
            public OsbEasing EasingX { get; }
            public OsbEasing EasingY { get; }

            public SweepPoint(double time, Vector2 position,
                OsbEasing easingX = OsbEasing.InOutSine, OsbEasing easingY = OsbEasing.InOutSine)
            {
                Time = time;
                Position = position;
                EasingX = easingX;
                EasingY = easingY;
            }
        }

        /// <summary>Soft moving band. Scale is relative to texture pixels; rotation is in radians.</summary>
        public static OsbSprite SweepLight(StoryboardLayer layer, double start, double end,
            Vector2 startPosition, Vector2 endPosition, Vector2 scale, double rotation,
            Color color, double opacity = .26, double fadeIn = 100, double fadeOut = 120,
            OsbEasing easing = OsbEasing.InOutSine, string texturePath = null,
            IReadOnlyList<SweepPoint> motion = null, OsbOrigin origin = OsbOrigin.Centre)
        {
            CheckPoint(endPosition, nameof(endPosition));
            if (motion != null) CheckMotion(motion, start, end, endPosition);
            var sprite = Create(layer, start, end, startPosition, scale, rotation, color,
                opacity, texturePath ?? WideSweep, origin);
            if (motion == null)
                sprite.Move(easing, start, end,
                    startPosition.X, startPosition.Y, endPosition.X, endPosition.Y);
            else
            {
                var at = start;
                var position = startPosition;
                foreach (var point in motion)
                {
                    sprite.MoveX(point.EasingX, at, point.Time, position.X, point.Position.X);
                    sprite.MoveY(point.EasingY, at, point.Time, position.Y, point.Position.Y);
                    at = point.Time;
                    position = point.Position;
                }
            }
            Envelope(sprite, start, end, opacity, fadeIn, fadeOut);
            return sprite;
        }

        /// <summary>Stationary broad focus, usually placed below the character or title layer.</summary>
        public static OsbSprite SoftSpotlight(StoryboardLayer layer, double start, double end,
            Vector2 position, Vector2 scale, Color color, double opacity = .07,
            double fadeIn = 120, double fadeOut = 160, double rotation = 0,
            string texturePath = null)
        {
            var sprite = Create(layer, start, end, position, scale, rotation, color,
                opacity, texturePath ?? BigSpot);
            Envelope(sprite, start, end, opacity, fadeIn, fadeOut);
            return sprite;
        }

        /// <summary>One soft attack and release. Duration is milliseconds; no persistent brightness change.</summary>
        public static OsbSprite HighlightPulse(StoryboardLayer layer, double start, double duration,
            Vector2 position, Vector2 scale, Color color, double peakOpacity = .18,
            double attackRatio = .25, double rotation = 0, string texturePath = null)
        {
            Positive(duration, nameof(duration));
            Finite(attackRatio, nameof(attackRatio));
            if (attackRatio <= 0 || attackRatio >= 1)
                throw new ArgumentOutOfRangeException(nameof(attackRatio), "Use a value between 0 and 1.");
            var end = start + duration;
            var sprite = Create(layer, start, end, position, scale, rotation, color,
                peakOpacity, texturePath ?? RoundSpot);
            Envelope(sprite, start, end, peakOpacity, duration * attackRatio, duration * (1 - attackRatio));
            return sprite;
        }

        /// <summary>Small sheen travelling along a line, rather than a glowing outline.
        /// Position is the line's starting endpoint, length/thickness are screen pixels.</summary>
        public static OsbSprite LineGlow(StoryboardLayer layer, double start, double end,
            Vector2 position, double length, double rotation, Color color,
            double opacity = .14, double thickness = 4, double highlightWidth = 48,
            double fadeIn = 50, double fadeOut = 70, OsbEasing easing = OsbEasing.InOutSine)
        {
            Positive(length, nameof(length));
            Positive(thickness, nameof(thickness));
            Positive(highlightWidth, nameof(highlightWidth));
            Finite(rotation, nameof(rotation));
            var width = Math.Min(length, highlightWidth);
            var direction = new Vector2((float)Math.Cos(rotation), (float)Math.Sin(rotation));
            return SweepLight(layer, start, end,
                position + direction * (float)(width / 2),
                position + direction * (float)(length - width / 2),
                new Vector2((float)(width / 256), (float)(thickness / 64)),
                rotation, color, opacity, fadeIn, fadeOut, easing, LineBand);
        }

        /// <summary>Quiet paper reflection. Callers choose its size/path to fit their page or card.</summary>
        public static OsbSprite PaperShine(StoryboardLayer layer, double start, double end,
            Vector2 startPosition, Vector2 endPosition, Vector2 scale, double rotation,
            Color color, double opacity = .12, double fadeIn = 80, double fadeOut = 120,
            OsbEasing easing = OsbEasing.InOutSine, string texturePath = null)
            => SweepLight(layer, start, end, startPosition, endPosition, scale, rotation,
                color, opacity, fadeIn, fadeOut, easing, texturePath ?? PaperBand);

        private static OsbSprite Create(StoryboardLayer layer, double start, double end,
            Vector2 position, Vector2 scale, double rotation, Color color, double opacity, string texturePath,
            OsbOrigin origin = OsbOrigin.Centre)
        {
            if (layer == null) throw new ArgumentNullException(nameof(layer));
            Finite(start, nameof(start));
            Finite(end, nameof(end));
            if (end <= start) throw new ArgumentOutOfRangeException(nameof(end), "End must be after start.");
            CheckPoint(position, nameof(position));
            Positive(scale.X, nameof(scale));
            Positive(scale.Y, nameof(scale));
            Finite(rotation, nameof(rotation));
            Finite(opacity, nameof(opacity));
            if (opacity < 0 || opacity > 1) throw new ArgumentOutOfRangeException(nameof(opacity));
            if (color.IsEmpty) throw new ArgumentException("Choose an RGB tint.", nameof(color));
            if (string.IsNullOrWhiteSpace(texturePath)) throw new ArgumentException("Texture path is required.", nameof(texturePath));
            // Initial position belongs in the sprite header. A combined Move command
            // would compete with the independent X/Y tracks used by curved paths.
            var sprite = layer.CreateSprite(texturePath, origin, position);
            sprite.ScaleVec(start, scale.X, scale.Y);
            sprite.Rotate(start, rotation);
            sprite.Color(start, color.R / 255.0, color.G / 255.0, color.B / 255.0);
            return sprite;
        }

        private static void Envelope(OsbSprite sprite, double start, double end,
            double peak, double fadeIn, double fadeOut)
        {
            Finite(fadeIn, nameof(fadeIn));
            Finite(fadeOut, nameof(fadeOut));
            if (fadeIn < 0 || fadeOut < 0) throw new ArgumentOutOfRangeException("fade", "Fade durations must be non-negative.");
            // Short pulses keep the requested attack/release ratio without overlapping commands.
            var total = fadeIn + fadeOut;
            if (total > end - start)
            {
                var fit = (end - start) / total;
                fadeIn *= fit;
                fadeOut *= fit;
            }
            // Instant clears following a curve are ambiguous in native command
            // lookup. Use an imperceptible (at most 1ms) release ending at zero.
            if (fadeOut == 0)
            {
                fadeOut = Math.Min(1, (end - start) / 2);
                fadeIn = Math.Min(fadeIn, end - start - fadeOut);
            }
            if (fadeIn > 0) sprite.Fade(OsbEasing.OutSine, start, start + fadeIn, 0, peak);
            else sprite.Fade(start, peak);
            // Storyboard retains the preceding endpoint during the hold.
            if (fadeOut > 0) sprite.Fade(OsbEasing.InSine, end - fadeOut, end, peak, 0);
            else sprite.Fade(end, 0);
        }

        private static void CheckMotion(IReadOnlyList<SweepPoint> motion,
            double start, double end, Vector2 endPosition)
        {
            if (motion.Count == 0) throw new ArgumentException("Motion needs at least one endpoint.", nameof(motion));
            var at = start;
            foreach (var point in motion)
            {
                Finite(point.Time, nameof(motion));
                CheckPoint(point.Position, nameof(motion));
                if (point.Time <= at || point.Time > end)
                    throw new ArgumentException("Motion times must increase within the effect interval.", nameof(motion));
                at = point.Time;
            }
            var last = motion[motion.Count - 1];
            if (last.Time != end || last.Position != endPosition)
                throw new ArgumentException("The final motion point must match end time and position.", nameof(motion));
        }

        private static void CheckPoint(Vector2 point, string name)
        {
            Finite(point.X, name);
            Finite(point.Y, name);
        }

        private static void Positive(double value, string name)
        {
            Finite(value, name);
            if (value <= 0) throw new ArgumentOutOfRangeException(name, "Use a positive value.");
        }

        private static void Finite(double value, string name)
        {
            if (double.IsNaN(value) || double.IsInfinity(value)) throw new ArgumentOutOfRangeException(name);
        }
    }
}
