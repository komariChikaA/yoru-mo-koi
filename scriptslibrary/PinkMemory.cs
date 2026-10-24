using System;

namespace StorybrewScripts
{
    // The heroine's thread, and the bell string drawn as a broken line.
    // This shot leaves the tip outside the frame. The next shot continues from TipAtEnd().
    public static class PinkMemory
    {
        public const double Red = 215.0 / 255.0;
        public const double Green = 160.0 / 255.0;
        public const double Blue = 173.0 / 255.0;
        public const float Width = 2.5f;

        // Slow drift of the whole thread across this shot, in screen pixels.
        public const float DriftX = 8f;
        public const float DriftY = -6f;

        public readonly struct Segment
        {
            public readonly float X0, Y0, X1, Y1;
            public readonly int StartMs;
            public readonly int DrawMs;
            public readonly bool Under;
            public readonly bool GrowsAway;

            public Segment(float x0, float y0, float x1, float y1, int startMs, int drawMs, bool under = false, bool growsAway = false)
            {
                X0 = x0;
                Y0 = y0;
                X1 = x1;
                Y1 = y1;
                StartMs = startMs;
                DrawMs = drawMs;
                Under = under;
                GrowsAway = growsAway;
            }
        }

        // One rope. It enters from the upper left, bends once, breaks for 22px
        // just before the settled frame, runs behind that frame, comes out
        // along the bottom, breaks again, and keeps going.
        public static readonly Segment[] SecretBase =
        {
            new Segment(-130f, 20f, 28f, 74f, 880, 880),
            new Segment(28f, 74f, 195f, 173f, 1780, 1080, true),
            new Segment(214f, 185f, 547f, 382f, 3000, 1760, true),
            new Segment(547f, 382f, 608f, 418f, 4780, 360, true),
            new Segment(627f, 429f, 770f, 514f, 5220, 380),
        };

        public static (float x, float y) TipAtEnd()
        {
            var last = SecretBase[SecretBase.Length - 1];
            return (last.X1 + DriftX, last.Y1 + DriftY);
        }
    }
}
