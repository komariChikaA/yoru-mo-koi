using OpenTK;
using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

namespace StorybrewScripts
{
    // Native sprite tracks, shared with the 1080p music review.
    // Final camera positions hold at 12fps; earlier rotations remain continuous.
    public class ChorusGate : StoryboardObjectGenerator
    {
        const string Assets = "sb/chorus-gate/";
        const double Unit = 480.0 / 1080;

        public override void Generate()
        {
            var layer = GetLayer("Chorus Gate");
            var sprites = new Dictionary<int, OsbSprite>();
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, Assets, "sprites.tsv")))
            {
                if (string.IsNullOrWhiteSpace(row)) continue;
                var fields = row.Split('\t');
                sprites.Add(int.Parse(fields[0]), layer.CreateSprite(Assets + fields[1]));
            }
            var ends = new Dictionary<int, double>();
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, Assets, "commands.tsv")))
            {
                if (string.IsNullOrWhiteSpace(row)) continue;
                var f = row.Split('\t');
                double Read(int index) => double.Parse(f[index], CultureInfo.InvariantCulture);
                var id = int.Parse(f[0]);
                var sprite = sprites[id];
                var from = Read(1);
                var to = Read(2);
                var p0 = Position(Read(3), Read(4));
                var p1 = Position(Read(5), Read(6));
                sprite.Move(from, to, p0, p1);
                sprite.ScaleVec(from, to, Read(7) * Unit, Read(8) * Unit,
                    Read(9) * Unit, Read(10) * Unit);
                // Unwrapped radians preserve the requested full clockwise turn.
                sprite.Rotate(from, to, Read(11), Read(12));
                // A constant-alpha interval needs only its starting command.
                // Ending a constant interval at the cut would compete with
                // the zero-alpha command at that same exact millisecond.
                if (Read(13) == Read(14)) sprite.Fade(from, Read(13));
                else sprite.Fade(from, to, Read(13), Read(14));
                ends[id] = Math.Max(ends.ContainsKey(id) ? ends[id] : 0, to);
            }
            foreach (var entry in ends) sprites[entry.Key].Fade(entry.Value, 0);
        }

        static Vector2 Position(double x, double y)
        {
            return new Vector2((float)(320 + (x - 960) * Unit),
                (float)(240 + (y - 540) * Unit));
        }
    }
}
