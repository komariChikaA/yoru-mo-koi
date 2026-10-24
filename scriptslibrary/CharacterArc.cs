using System;
using System.Globalization;
using System.IO;

namespace StorybrewScripts
{
    public static class CharacterArc
    {
        public static (string path, float x, float y) Find(string mapset, float radius,
            double start, double end, float thickness, bool taper)
        {
            var key = string.Join("_", Math.Round(radius), Math.Round(start * 10000),
                Math.Round(end * 10000), Math.Round(thickness * 10000), taper ? 1 : 0);
            foreach (var line in File.ReadAllLines(Path.Combine(mapset, "sb", "character-palette", "arcs", "layout.txt")))
            {
                var fields = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (fields[0] == key)
                    return ("sb/character-palette/arcs/" + key + ".png",
                        float.Parse(fields[1], CultureInfo.InvariantCulture),
                        float.Parse(fields[2], CultureInfo.InvariantCulture));
            }
            throw new InvalidOperationException("Missing character arc: " + key);
        }
    }
}
