using StorybrewCommon.Scripting;
using System.Globalization;
using System.IO;

namespace StorybrewScripts
{
    public class ChorusFour : StoryboardObjectGenerator
    {
        public override void Generate()
        {
            var layer = GetLayer("Chorus Fourth");
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, "sb/chorus-four/frames.tsv")))
            {
                if (string.IsNullOrWhiteSpace(row)) continue;
                var fields = row.Split('\t');
                var start = double.Parse(fields[1], CultureInfo.InvariantCulture);
                var end = double.Parse(fields[2], CultureInfo.InvariantCulture);
                var sprite = layer.CreateSprite("sb/chorus-four/" + fields[0]);
                sprite.Scale(start, 480.0 / 1080);
                sprite.Fade(start, 1);
                sprite.Fade(end, 0);
            }
        }
    }
}
