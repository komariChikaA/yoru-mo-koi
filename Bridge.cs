using OpenTK;
using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System.IO;
using System.Globalization;
using System;
using System.Collections.Generic;

namespace StorybrewScripts
{
    // Timings are shared with the Godot map-to-bridge preview.
    public class Bridge : StoryboardObjectGenerator
    {
        [Configurable] public bool ShowLyrics = true;
        // Milliseconds: retime only the four drum cuts while preserving
        // the saved source tracks.
        [Configurable] public int DrumCut1Ms = 50116;
        [Configurable] public int DrumCut2Ms = 50637;
        [Configurable] public int DrumCut3Ms = 51158;
        [Configurable] public int DrumFallCutMs = 51679;
        const string Assets = "sb/bridge/";
        const int Start = 40000, End = 53260;
        double[] drumSource = { 50530, 50939, 51348, 51762, 52200 };

        public override void Generate()
        {
            if (!(48200 < DrumCut1Ms && DrumCut1Ms < DrumCut2Ms &&
                DrumCut2Ms < DrumCut3Ms && DrumCut3Ms < DrumFallCutMs && DrumFallCutMs < 52200))
                throw new InvalidOperationException("鼓点切点必须递增：48200 < Cut1 < Cut2 < Cut3 < Fall < 52200（毫秒）。");
            // The builder records the cut times already baked into the TSV.
            // Retiming from that baseline avoids applying saved edits twice.
            var cutFile = Path.Combine(MapsetPath, "sb/bridge-montage/cut-times.tsv");
            if (File.Exists(cutFile))
            {
                var cuts = File.ReadAllText(cutFile).Trim().Split('\t');
                for (var i = 0; i < 4; i++) drumSource[i] = double.Parse(cuts[i], CultureInfo.InvariantCulture);
            }
            var layer = GetLayer("Bridge");
            var black = layer.CreateSprite(Assets + "black.png");
            black.ScaleVec(Start, 854, 480);
            black.Fade(Start, 1);
            black.Fade(End, 0);
            Timeline(layer, "timeline.tsv");
            Letterbox(layer);
            SpriteTracks(layer, "sb/bridge-montage/");
            if (ShowLyrics) Timeline(layer, "lyrics-motion.tsv");
        }

        double DrumTime(double time)
        {
            var source = drumSource;
            var target = new double[] { DrumCut1Ms, DrumCut2Ms, DrumCut3Ms, DrumFallCutMs, 52200 };
            if (time < source[0] || time >= source[4]) return time;
            for (var i = 0; i < 4; i++)
                if (time < source[i + 1])
                    return target[i] + (time - source[i]) * (target[i + 1] - target[i]) / (source[i + 1] - source[i]);
            return time;
        }

        // Same continuous native sprite format as the chorus. Hands, fingers,
        // character and scenery remain independently animated sprite layers.
        protected void SpriteTracks(StoryboardLayer layer, string assets)
        {
            var sprites = new Dictionary<int, OsbSprite>();
            var ends = new Dictionary<int, double>();
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, assets, "sprites.tsv")))
            {
                if (string.IsNullOrWhiteSpace(row)) continue;
                var f = row.Split('\t');
                sprites.Add(int.Parse(f[0]), layer.CreateSprite(assets + f[1]));
            }
            const double unit = 480.0 / 1080;
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, assets, "commands.tsv")))
            {
                if (string.IsNullOrWhiteSpace(row)) continue;
                var f = row.Split('\t');
                double Read(int i) => double.Parse(f[i], CultureInfo.InvariantCulture);
                var id = int.Parse(f[0]);
                var sprite = sprites[id];
                var from = Read(1); var to = Read(2);
                if (assets == "sb/bridge-montage/")
                {
                    from = DrumTime(from); to = DrumTime(to);
                }
                Vector2 Position(int i) => new Vector2((float)(320 + (Read(i) - 960) * unit),
                    (float)(240 + (Read(i + 1) - 540) * unit));
                sprite.Move(from, to, Position(3), Position(5));
                sprite.ScaleVec(from, to, Read(7) * unit, Read(8) * unit, Read(9) * unit, Read(10) * unit);
                sprite.Rotate(from, to, Read(11), Read(12));
                if (Read(13) == Read(14)) sprite.Fade(from, Read(13));
                else sprite.Fade(from, to, Read(13), Read(14));
                ends[id] = Math.Max(ends.ContainsKey(id) ? ends[id] : 0, to);
            }
            foreach (var entry in ends) sprites[entry.Key].Fade(entry.Value, 0);
        }

        void Letterbox(StoryboardLayer layer)
        {
            var fields = File.ReadAllText(Path.Combine(MapsetPath, Assets, "letterbox.tsv")).Trim().Split('\t');
            var from = int.Parse(fields[0]);
            var settle = int.Parse(fields[1]);
            var end = int.Parse(fields[2]);
            if (end == drumSource[0]) end = DrumCut1Ms;
            var height = double.Parse(fields[3], CultureInfo.InvariantCulture) * 480 / 1080;
            var top = layer.CreateSprite(Assets + "black.png", OsbOrigin.TopLeft);
            top.ScaleVec(from, 854, height);
            top.Move(OsbEasing.OutCubic, from, settle, new Vector2(-107, (float)-height), new Vector2(-107, 0));
            top.Fade(from, 1);
            top.Fade(end, 0);
            var bottom = layer.CreateSprite(Assets + "black.png", OsbOrigin.BottomLeft);
            bottom.ScaleVec(from, 854, height);
            bottom.Move(OsbEasing.OutCubic, from, settle, new Vector2(-107, (float)(480 + height)), new Vector2(-107, 480));
            bottom.Fade(from, 1);
            bottom.Fade(end, 0);
        }

        void Timeline(StoryboardLayer layer, string file)
        {
            foreach (var line in File.ReadAllLines(Path.Combine(MapsetPath, Assets, file)))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                var fields = line.Split('\t');
                var from = int.Parse(fields[0]);
                var to = int.Parse(fields[1]);
                if (to == drumSource[0]) to = DrumCut1Ms;
                var fadeIn = int.Parse(fields[3]);
                var fadeOut = int.Parse(fields[4]);
                var path = Assets + fields[2];
                var bitmap = GetMapsetBitmap(path);
                var sprite = layer.CreateSprite(path, OsbOrigin.Centre, new Vector2(320, 240));
                var lyric = fields.Length >= 15 && fields[5] == "lyric";
                if (lyric)
                {
                    double Read(int index) => double.Parse(fields[index], CultureInfo.InvariantCulture);
                    const double unit = 480.0 / 1080;
                    var position = new Vector2((float)(320 + (Read(6) - 960) * unit),
                        (float)(240 + (Read(7) - 540) * unit));
                    var enter = Read(8);
                    var leave = Read(9);
                    if (enter > 0)
                    {
                        sprite.Move(OsbEasing.OutCubic, from, from + enter,
                            position + new Vector2(0, (float)(Read(10) * unit)), position);
                        sprite.Scale(OsbEasing.OutCubic, from, from + enter, unit * Read(12), unit);
                    }
                    else
                    {
                        sprite.Move(from, position);
                        sprite.Scale(from, unit);
                    }
                    if (leave > 0)
                    {
                        sprite.Move(OsbEasing.InCubic, to - leave, to, position,
                            position + new Vector2(0, (float)(Read(11) * unit)));
                        sprite.Scale(OsbEasing.InCubic, to - leave, to, unit, unit * Read(13));
                    }
                }
                else if (fields.Length >= 9)
                {
                    var zoom = double.Parse(fields[5], CultureInfo.InvariantCulture);
                    var cx = double.Parse(fields[6], CultureInfo.InvariantCulture);
                    var y0 = double.Parse(fields[7], CultureInfo.InvariantCulture);
                    var y1 = double.Parse(fields[8], CultureInfo.InvariantCulture);
                    var full = fields.Length >= 10 && fields[9] == "full";
                    var viewHeight = full ? 480.0 : 432.0;
                    var viewWidth = viewHeight * bitmap.Width / bitmap.Height;
                    sprite.Scale(from, viewHeight / bitmap.Height * zoom);
                    sprite.Move(from, to,
                        new Vector2((float)(320 + (.5 - cx) * viewWidth * zoom), (float)(240 + (.5 - y0) * viewHeight * zoom)),
                        new Vector2((float)(320 + (.5 - cx) * viewWidth * zoom), (float)(240 + (.5 - y1) * viewHeight * zoom)));
                }
                else sprite.Scale(from, 480.0 / bitmap.Height);
                var initialAlpha = lyric ? double.Parse(fields[14], CultureInfo.InvariantCulture) : 0;
                if (fadeIn > 0) sprite.Fade(from, from + fadeIn, initialAlpha, 1);
                else sprite.Fade(from, 1);
                if (fadeOut > 0) sprite.Fade(to - fadeOut, to, 1, 0);
                else sprite.Fade(to, 0);
            }
        }
    }
}
