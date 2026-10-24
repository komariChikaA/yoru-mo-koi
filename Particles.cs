using OpenTK;
using OpenTK.Graphics;
using StorybrewCommon.Mapset;
using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System;
using System.Drawing;
using System.IO;
using System.Linq;

namespace StorybrewScripts
{
    public class Particles : StoryboardObjectGenerator
    {
        [Group("Timing")]
        [Configurable] public int StartTime;
        [Configurable] public int EndTime;

        [Group("Sprite")]
        [Configurable] public string Path = "particle.png";
        [Configurable] public OsbOrigin Origin = OsbOrigin.Centre;
        [Configurable] public Vector2 Scale = new Vector2(0.1f, 0.1f);
        [Description("Rotation of the sprite; does not influences particle motion direction.")]
        [Configurable] public float Rotation = 2;
        [Configurable] public Color4 Color = Color4.White;
        [Description("Varies the saturation and brightness of the selected Color for each particle.")]
        [Configurable] public float ColorVariance = 0.6f;
        [Configurable] public bool Additive = false;

        [Group("Spawn")]
        [Configurable] public int ParticleCount = 32;
        [Configurable] public float Lifetime = 3000;
        [Description("The point around which particles will be created.")]
        [Configurable] public Vector2 SpawnOrigin = new Vector2(320, 400);
        [Description("The distance around the Spawn Origin point where particles will be created.")]
        [Configurable] public float SpawnSpread = 140;

        [Group("Motion")]
        [Description("The angle in degrees at which particles will be moving.\n0 is to the right, positive values rotate counterclockwise.")]
        [Configurable] public float Angle = -90;
        [Description("The spread in degrees around Angle.")]
        [Configurable] public float AngleSpread = 80;
        [Description("The speed at which particles move, in osupixels.")]
        [Configurable] public float Speed = 220;
        [Description("Eases the motion of particles.")]
        [Configurable] public OsbEasing Easing = OsbEasing.Out;

        public override void Generate()
        {
            if (EndTime <= StartTime)
                EndTime = (int)AudioDuration;
            if (StartTime <= 0)
                StartTime = 1100;
            EndTime = Math.Min(EndTime, (int)AudioDuration);
            if (EndTime - StartTime < 800) return;

            const string starPath = "sb/star-w.png";
            try
            {
                GetMapsetBitmap(starPath);
            }
            catch (FileNotFoundException)
            {
                return;
            }

            var count = Math.Max(18, ParticleCount);
            var layer = GetLayer("ParticlesBack");
            const float bottom = 508f;
            const float top = -28f;
            var travel = bottom - top;
            OsbEasing[] riseCurves =
            {
                OsbEasing.OutSine,
                OsbEasing.InOutSine,
                OsbEasing.OutQuad,
                OsbEasing.InOutQuad,
                OsbEasing.OutCubic,
                OsbEasing.InSine,
                OsbEasing.InOutCubic,
            };
            OsbEasing[] outCurves = { OsbEasing.OutSine, OsbEasing.OutQuad, OsbEasing.OutCubic };
            OsbEasing[] inCurves = { OsbEasing.InSine, OsbEasing.InQuad, OsbEasing.InCubic };

            for (var i = 0; i < count; i++)
            {
                var x = (float)Random(-60, 700);
                var bow = (float)Random(-120, 120);
                if (Math.Abs(bow) < 36)
                    bow = bow < 0 ? -36 : 36;
                var endX = x + (float)Random(-56, 56);
                var speed = Random(64.0, 168.0);
                var fullMs = Math.Max(2800, (int)(travel / speed * 1000.0));
                var phase = (int)Random(0, fullMs);
                var rise = riseCurves[(int)Random(0, riseCurves.Length)];
                var outEase = outCurves[(int)Random(0, outCurves.Length)];
                var inEase = inCurves[(int)Random(0, inCurves.Length)];
                var spinEase = Random(0.0, 1.0) < 0.5 ? OsbEasing.InOutSine : OsbEasing.OutSine;
                var roll = Random(0.0, 1.0);
                double scale;
                double alpha;
                if (roll < 0.12)
                {
                    scale = Random(0.22, 0.38);
                    alpha = Random(0.72, 0.96);
                }
                else if (roll < 0.4)
                {
                    scale = Random(0.08, 0.15);
                    alpha = Random(0.42, 0.78);
                }
                else
                {
                    scale = Random(0.028, 0.068);
                    alpha = Random(0.28, 0.7);
                }
                var rot0 = MathHelper.DegreesToRadians((float)Random(0.0, 360.0));
                var spin = MathHelper.DegreesToRadians((float)((Random(0.0, 1.0) < 0.5 ? -1 : 1) * Random(22.0, 96.0)));

                var cycle = StartTime - phase;
                while (cycle < EndTime)
                {
                    var born = cycle;
                    var die = cycle + fullMs;
                    var visStart = Math.Max(born, StartTime);
                    var visEnd = Math.Min(die, EndTime);
                    cycle += fullMs;
                    if (visEnd - visStart < 320)
                        continue;

                    var mid = born + fullMs / 2;
                    var star = layer.CreateSprite(starPath, OsbOrigin.Centre);
                    star.Scale(visStart, scale);
                    star.MoveY(rise, born, die, bottom, top);
                    star.MoveX(outEase, born, mid, x, x + bow);
                    star.MoveX(inEase, mid, die, x + bow, endX);
                    star.Rotate(spinEase, born, die, rot0, rot0 + spin);

                    var fadeIn = visStart == born ? 200 : 16;
                    var fadeOut = visEnd == die ? 200 : 16;
                    if (visEnd - visStart < fadeIn + fadeOut + 16)
                    {
                        fadeIn = 16;
                        fadeOut = 16;
                    }
                    star.Fade(visStart, visStart + fadeIn, 0, alpha);
                    star.Fade(visEnd - fadeOut, visEnd, alpha, 0);
                }
            }
        }

    }
}
