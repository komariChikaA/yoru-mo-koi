using StorybrewCommon.Scripting;
using System.Globalization;
using System.IO;

namespace StorybrewScripts
{
    public class ChorusCgc06 : StoryboardObjectGenerator
    {
        public override void Generate()
        {
            var layer = GetLayer("Chorus CGC06");
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, "sb/chorus-cgc06/frames.tsv")))
            {
                if (string.IsNullOrWhiteSpace(row)) continue;
                var fields = row.Split('\t');
                var start = double.Parse(fields[1], CultureInfo.InvariantCulture);
                var end = double.Parse(fields[2], CultureInfo.InvariantCulture);
                var sprite = layer.CreateSprite("sb/chorus-cgc06/" + fields[0]);
                sprite.Scale(start, 480.0 / 1080);
                sprite.Fade(start, 1);
                sprite.Fade(end, 0);
            }
        }
    }
}
