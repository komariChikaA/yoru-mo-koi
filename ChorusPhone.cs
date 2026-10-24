using StorybrewCommon.Scripting;
using System.Globalization;
using System.IO;

namespace StorybrewScripts
{
    // Godot's real 3D photo/room/phone sequence, installed by build-chorus-phone.py.
    public class ChorusPhone : StoryboardObjectGenerator
    {
        public override void Generate()
        {
            var layer = GetLayer("Chorus Photo Phone");
            foreach (var row in File.ReadAllLines(Path.Combine(MapsetPath, "sb/chorus-phone/frames.tsv")))
            {
                if (string.IsNullOrWhiteSpace(row)) continue;
                var fields = row.Split('\t');
                var start = double.Parse(fields[1], CultureInfo.InvariantCulture);
                var end = double.Parse(fields[2], CultureInfo.InvariantCulture);
                var sprite = layer.CreateSprite("sb/chorus-phone/" + fields[0]);
                sprite.Scale(start, 480.0 / 540);
                sprite.Fade(start, 1);
                sprite.Fade(end, 0);
            }
        }
    }
}
