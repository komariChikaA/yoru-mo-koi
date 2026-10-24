using OpenTK;
using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System.Globalization;
using System.IO;

namespace StorybrewScripts
{
    public class Kobe3D : StoryboardObjectGenerator
    {
        [Configurable] public string TimelinePath = "sb/kobe3d-simple/timeline.tsv";

        public override void Generate()
        {
            var layer = GetLayer("Kobe3D");
            var folder = Path.GetDirectoryName(TimelinePath).Replace('\\', '/');
            var timelineFile = Path.Combine(MapsetPath, TimelinePath);
            AddDependency(timelineFile);
            var lines = File.ReadAllLines(timelineFile);
            foreach (var line in lines)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                var fields = line.Split('\t');
                var from = int.Parse(fields[0], CultureInfo.InvariantCulture);
                var to = int.Parse(fields[1], CultureInfo.InvariantCulture);
                var height = int.Parse(fields[3], CultureInfo.InvariantCulture);
                var frame = layer.CreateSprite(folder + "/" + fields[2], OsbOrigin.Centre, new Vector2(320, 240));
                frame.Scale(from, 480.0 / height);
                // Round each absolute 24fps boundary once; no accumulated 42ms drift.
                frame.Fade(from, 1);
                frame.Fade(to, 0);
            }
        }
    }
}
