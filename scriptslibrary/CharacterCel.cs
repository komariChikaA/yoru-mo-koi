using System;
using System.Collections.Generic;

namespace StorybrewScripts
{
    // One exposure clock for the page, independent of preview/render FPS.
    public static class CharacterCel
    {
        public const int HeavyStart = 9400;
        public const int End = 12500;
        public static bool Hold(int time) => time >= HeavyStart && time < End;

        public static IEnumerable<int> Times(int start, int end, int landing)
        {
            var times = new SortedSet<int> { start, end };
            void Add(int t) { if (t > start && t < end) times.Add(t); }
            for (var t = start; t < Math.Min(end, HeavyStart); t += 32) Add(t);
            Add(HeavyStart);
            Add(landing);
            Add(End);
            for (var i = 0; ; i++)
            {
                var t = HeavyStart + (int)Math.Round(i * 1000.0 / 12);
                if (t >= landing || t >= end) break;
                Add(t);
            }
            foreach (var t in LightTimes(Math.Max(start, landing), Math.Min(end, End), landing)) Add(t);
            for (var t = Math.Max(start, End); t < end; t += 80) Add(t);
            return times;
        }

        public static IEnumerable<int> LightTimes(int start, int end, int landing)
        {
            var first = Math.Max(0, (int)Math.Ceiling((start - landing) * 24.0 / 1000));
            for (var i = first; ; i++)
            {
                var t = landing + (int)Math.Round(i * 1000.0 / 24);
                if (t > end) yield break;
                if (t >= start) yield return t;
            }
        }
    }
}
