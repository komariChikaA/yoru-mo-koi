using OpenTK;
using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace StorybrewScripts
{
    // Individual native SB sprites: cinematic handoff, five portrait cards,
    // scene panel, footer slices and the four final title images.
    public class ChorusFiveEnding : StoryboardObjectGenerator
    {
        [Configurable] public double FengStart = 105400;
        [Configurable] public double FengFade = 250;
        [Configurable] public double CastHit = 106266.666;
        [Configurable] public double SilhouetteHit = 106483.333;
        [Configurable] public double FinalTitleHit = 106683.333;
        [Configurable] public double SongEnd = 111621.723;
        const string Assets = "sb/ending/";
        const double Unit = 480.0 / 1080;
        const double Beat = 60000.0 / 148;
        const double CaptureEnd = 91473.216216;
        const double TransferEnd = 93094.837838;
        const double MorphStart = 91635.378378;
        const double UnfoldEnd = 95932.675676;
        const double CgEnter = 93094.837838;
        const double CgLand = 93905.648649;
        const double Sector = Math.PI * 2 / 5;
        const int CardSamplesPerSecond = 120;
        const int CardAnglesPerTurn = 1440; // .25 degrees; at most .25px edge error.
        static readonly double[] Switches = { 97250.243243, 99682.675676, 102115.108108, 104547.540541 };

        public override void Generate()
        {
            Cinematic(GetLayer("Fifth CG"));
            var paper = GetLayer("Ending Paper");
            Hold(paper, "paper.png", CaptureEnd, CastHit, new Vector2(960, 540));
            Scenes(GetLayer("Ending Scenes"));
            Cards(GetLayer("Ending Cards"));
            Footer(GetLayer("Ending Footer"));
            Titles(GetLayer("Ending Title"));
        }

        void Cinematic(StoryboardLayer layer)
        {
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, Assets + "cinematic.tsv")))
            {
                var f = row.Split('\t');
                var sprite = layer.CreateSprite(Assets + f[0]);
                var start = Read(f[1]); var end = Read(f[2]);
                sprite.Scale(start, Unit);
                sprite.Fade(start, 1);
                sprite.Fade(end, 0);
            }
        }

        void Scenes(StoryboardLayer layer)
        {
            var centre = new Vector2(1295, 560);
            var border = layer.CreateSprite(Assets + "scene-border.png");
            border.Scale(92689.432432, Unit);
            border.Move(92689.432432, Position(centre));
            FadeCurve(border, 92689.432432, CgLand, 0, 1);
            border.Fade(CastHit, 0);
            for (int i = 0; i < 30; i++)
            {
                double a = CgEnter + (CgLand - CgEnter) * i / 30;
                double b = CgEnter + (CgLand - CgEnter) * (i + 1) / 30;
                var sprite = Hold(layer, "scene-enter-" + i.ToString("00") + ".png", a, b, centre);
                var p0 = Settle((a - CgEnter) / (CgLand - CgEnter));
                var p1 = Settle((b - CgEnter) / (CgLand - CgEnter));
                sprite.Move(a, b, Position(centre + new Vector2(24, 7) * (float)(1 - p0)),
                    Position(centre + new Vector2(24, 7) * (float)(1 - p1)));
            }
            double holdStart = CgLand;
            for (int n = 0; n < Switches.Length; n++)
            {
                Hold(layer, "scene-" + (n % 3) + ".png", holdStart, Switches[n], centre);
                for (int i = 0; i < 30; i++)
                {
                    double a = Switches[n] + 2 * Beat * i / 30;
                    double b = Switches[n] + 2 * Beat * (i + 1) / 30;
                    Hold(layer, "scene-swap-" + (n % 3) + "-" + i.ToString("00") + ".png", a, b, centre);
                }
                holdStart = Switches[n] + 2 * Beat;
            }
            Hold(layer, "scene-1.png", holdStart, CastHit, centre);
        }

        struct CardPose
        {
            public Vector2 Centre;
            public double Radius, Angle;
            public bool Visible;
        }

        CardPose[] Pose(double song)
        {
            double p = Clamp((song - CaptureEnd) / (TransferEnd - CaptureEnd));
            double transfer = Soft(p);
            double radius = Lerp(360, 285, transfer) * Lerp(1, .4, transfer);
            double rotation = Rotation(song);
            var hub = new Vector2(365, 280);
            var result = new CardPose[5];
            for (int i = 0; i < 5; i++)
            {
                double angle = -Math.PI / 2 + rotation + Sector * i;
                var target = hub + Turn(new Vector2(0, -152), angle);
                double revealStart = TransferEnd + (i - 1) * Beat * 1.5;
                double phase = Clamp((song - revealStart) / (Beat * 2.5));
                double reveal = Pull(phase);
                double growth = Lerp(.84, 1, Soft(phase));
                var centre = target;
                double r = 114 * growth;
                if (i == 0)
                {
                    centre = Transfer(new Vector2(1140.439024f, 329.268293f), target, p);
                    r = radius;
                }
                else
                {
                    var parent = result[i - 1].Centre;
                    var chord = target - parent;
                    var bow = Turn(chord, -Math.PI / 2) * (float)(.19 * Math.Sin(Math.PI * reveal));
                    centre = parent + chord * (float)reveal + bow;
                    angle = Lerp(result[i - 1].Angle, angle, reveal);
                    angle += 4 * Math.PI / 180 * Math.Sin(2 * Math.PI * phase) * Math.Pow(Math.Sin(Math.PI * phase), 2);
                }
                result[i] = new CardPose { Centre = centre, Radius = r, Angle = angle,
                    Visible = i == 0 || song > revealStart };
            }
            return result;
        }

        void Cards(StoryboardLayer layer)
        {
            var times = new SortedSet<double> { CaptureEnd, TransferEnd, CastHit, MorphStart, UnfoldEnd };
            for (int n = (int)Math.Ceiling(CaptureEnd * CardSamplesPerSecond / 1000);
                n * 1000.0 / CardSamplesPerSecond < CastHit; n++)
                times.Add(n * 1000.0 / CardSamplesPerSecond);
            // Sample the exact start/stop too, so interpolation cannot creep
            // across a hold or round off its landing.
            for (double start = UnfoldEnd; start < CastHit; start += 2 * Beat)
            {
                times.Add(start);
                if (start + 1.25 * Beat < CastHit) times.Add(start + 1.25 * Beat);
            }
            for (int i = 1; i < 5; i++)
            {
                times.Add(TransferEnd + (i - 1) * Beat * 1.5);
                times.Add(TransferEnd + (i - 1) * Beat * 1.5 + Beat * 2.5);
            }
            var samples = new List<double>(times);
            // Echo contours are behind every portrait; their texture shares the
            // actual morph. They carry no duplicated face or fixed rectangle.
            for (int j = 1; j <= 2; j++)
                Echo(layer, samples, j);
            // Back-to-front order matches the original layered card pull.
            for (int i = 4; i >= 0; i--)
            {
                OsbSprite sprite = null;
                string activePath = null;
                for (int n = 0; n + 1 < samples.Count; n++)
                {
                    double a = samples[n], b = samples[n + 1], mid = (a + b) * .5;
                    var first = Pose(a)[i]; var last = Pose(b)[i]; var middle = Pose(mid)[i];
                    if (!middle.Visible) continue;
                    string path;
                    if (i == 0 && mid < TransferEnd)
                        path = "morph-" + ((int)Math.Round(Clamp((mid - CaptureEnd) / (TransferEnd - CaptureEnd)) * 100)).ToString("000") + ".png";
                    else
                    {
                        // Match the mask to this interval's starting pose.
                        // Midpoint masks anticipated the orbit by half a frame,
                        // with coarse 2-degree jumps near the slow landings.
                        int index = ((int)Math.Round(first.Angle / (Math.PI * 2) * CardAnglesPerTurn)
                            % CardAnglesPerTurn + CardAnglesPerTurn) % CardAnglesPerTurn;
                        path = "card-fine-" + i + "-" + index.ToString("0000") + ".png";
                    }
                    if (path != activePath)
                    {
                        if (sprite != null) sprite.Fade(a, 0);
                        sprite = layer.CreateSprite(Assets + path);
                        sprite.Fade(a, 1);
                        activePath = path;
                    }
                    sprite.Move(a, b, Position(first.Centre), Position(last.Centre));
                    var textureFactor = path.StartsWith("morph-") ? 3.0 : 1.0;
                    sprite.Scale(a, b, first.Radius / 114 * Unit / textureFactor, last.Radius / 114 * Unit / textureFactor);
                    // Rotation stays zero: each texture clips an upright face
                    // with the corresponding frame angle. SB moves/scales it.
                }
                if (sprite != null) sprite.Fade(CastHit, 0);
            }
        }

        void Echo(StoryboardLayer layer, List<double> times, int index)
        {
            for (int n = 0; n + 1 < times.Count; n++)
            {
                double a = times[n], b = Math.Min(times[n + 1], TransferEnd), mid = (a + b) * .5;
                if (a >= TransferEnd) break;
                double phase = Clamp((mid - CaptureEnd) / (TransferEnd - CaptureEnd));
                double opacity = Soft((phase - .10) / .12) * (1 - Soft((phase - .82) / .18)) * (.17 - (index - 1) * .055);
                if (opacity < .002) continue;
                int mask = (int)Math.Round(phase * 100);
                var sprite = layer.CreateSprite(Assets + "echo-" + mask.ToString("000") + ".png");
                double pa = Clamp((a - CaptureEnd - 55 * index) / (TransferEnd - CaptureEnd));
                double pb = Clamp((b - CaptureEnd - 55 * index) / (TransferEnd - CaptureEnd));
                var destination = new Vector2(213, 280);
                sprite.Move(a, b, Position(Transfer(new Vector2(1140.439024f, 329.268293f), destination, pa)),
                    Position(Transfer(new Vector2(1140.439024f, 329.268293f), destination, pb)));
                sprite.Scale(a, b, Lerp(360, 285, Soft(pa)) * Lerp(1, .4, Soft(pa)) / 114 * Unit / 3,
                    Lerp(360, 285, Soft(pb)) * Lerp(1, .4, Soft(pb)) / 114 * Unit / 3);
                sprite.Fade(a, opacity);
                sprite.Fade(b, 0);
            }
        }

        void Footer(StoryboardLayer layer)
        {
            var rule = layer.CreateSprite(Assets + "pixel.png", OsbOrigin.CentreLeft, Position(new Vector2(135, 916)));
            rule.Move(CgEnter, Position(new Vector2(135, 916)));
            rule.Color(CgEnter, .88, .76, .78);
            rule.Fade(CgEnter, .30);
            rule.ScaleVec(OsbEasing.InOutSine, CgEnter, CgLand, 0, Unit, 1645 * Unit, Unit);
            rule.Fade(CastHit, 0);
            double[] columns = { 135, 655, 1310 };
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, Assets + "footer.tsv")))
            {
                var f = row.Split('\t'); int column = int.Parse(f[0]);
                double left = Read(f[1]), width = Read(f[2]), total = Read(f[3]);
                double onset = CgLand + column * Beat;
                double lo = 0, hi = 1;
                for (int i = 0; i < 24; i++) { double m = (lo + hi) / 2; if (Settle(m) < left / total) lo = m; else hi = m; }
                double reveal = onset + (lo + hi) / 2 * Beat;
                var sprite = layer.CreateSprite(Assets + f[4], OsbOrigin.TopLeft);
                sprite.Scale(onset, Unit);
                sprite.Move(OsbEasing.OutCubic, onset, onset + Beat,
                    Position(new Vector2((float)(columns[column] + left), 961)),
                    Position(new Vector2((float)(columns[column] + left), 945)));
                sprite.Fade(CaptureEnd, 0);
                sprite.Fade(reveal, 1);
                sprite.Fade(CastHit, 0);
            }
        }

        void Titles(StoryboardLayer layer)
        {
            var feng = layer.CreateSprite(Assets + "feng.png");
            feng.Scale(FengStart, Unit);
            FadeCurve(feng, FengStart, FengStart + FengFade, 0, 1);
            feng.Fade(CastHit, 0);
            Hold(layer, "title-cast.png", CastHit, SilhouetteHit, new Vector2(960, 540));
            Hold(layer, "title-silhouette.png", SilhouetteHit, FinalTitleHit, new Vector2(960, 540));
            Hold(layer, "title-final.png", FinalTitleHit, SongEnd, new Vector2(960, 540));
        }

        static OsbSprite Hold(StoryboardLayer layer, string path, double start, double end, Vector2 centre)
        {
            var sprite = layer.CreateSprite(Assets + path, OsbOrigin.Centre, Position(centre));
            sprite.Move(start, Position(centre));
            sprite.Scale(start, Unit);
            sprite.Fade(start, 1);
            sprite.Fade(end, 0);
            return sprite;
        }

        static void FadeCurve(OsbSprite sprite, double start, double end, double from, double to)
        {
            for (int i = 0; i < 16; i++)
                sprite.Fade(start + (end - start) * i / 16, start + (end - start) * (i + 1) / 16,
                    Lerp(from, to, Soft(i / 16.0)), Lerp(from, to, Soft((i + 1) / 16.0)));
        }

        double Rotation(double song)
        {
            double elapsed = Math.Max(0, Math.Min(song, CastHit) - UnfoldEnd);
            double turns = Math.Floor(elapsed / (2 * Beat));
            return Sector * (turns + Pull((elapsed - turns * 2 * Beat) / (1.25 * Beat)));
        }
        static Vector2 Transfer(Vector2 a, Vector2 b, double p)
        {
            double t = Soft((p - .06) / .94), q = 1 - t;
            var c1 = a + new Vector2(-190, -72); var c2 = b + new Vector2(220, 38);
            return a * (float)(q * q * q) + c1 * (float)(3 * q * q * t) + c2 * (float)(3 * q * t * t) + b * (float)(t * t * t)
                + new Vector2((float)(14 * Math.Sin(Math.PI * Clamp(p / .16))), 0);
        }
        static Vector2 Turn(Vector2 p, double a) => new Vector2((float)(p.X * Math.Cos(a) - p.Y * Math.Sin(a)), (float)(p.X * Math.Sin(a) + p.Y * Math.Cos(a)));
        static Vector2 Position(Vector2 p) => new Vector2((float)(320 + (p.X - 960) * Unit), (float)(240 + (p.Y - 540) * Unit));
        static double Read(string text) => double.Parse(text, CultureInfo.InvariantCulture);
        static double Clamp(double p) => Math.Max(0, Math.Min(1, p));
        static double Lerp(double a, double b, double p) => a + (b - a) * p;
        static double Soft(double p) { p = Clamp(p); return p * p * p * (p * (p * 6 - 15) + 10); }
        static double Pull(double p) { p = Clamp(p); return p * p * p * (20 - p * (45 - p * (36 - 10 * p))); }
        static double Settle(double p) { p = Clamp(p); return p * p * p * (35 - p * (105 - p * (126 - p * (70 - 15 * p)))); }
    }
}
