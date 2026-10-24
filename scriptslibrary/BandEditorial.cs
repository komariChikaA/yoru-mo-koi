using System.Drawing;
using StorybrewCommon.Storyboarding;

namespace StorybrewScripts
{
    // Materials and cross-axis spacing only; shot timing and motion stay in Background.
    public static class BandEditorial
    {
        public const string PaperPath = "sb/band-editorial/paper-band.png";
        public const double PaperOpacity = PaperMaterial.BackgroundOpacity;
        private static readonly Color[] Colors =
        {
            Color.FromArgb(0x83, 0xAA, 0xC0),
            Color.FromArgb(0xF8, 0xED, 0xD8),
            Color.FromArgb(0xE8, 0xC6, 0x6B),
            Color.FromArgb(0xBB, 0xD8, 0xDC),
            Color.FromArgb(0x83, 0xAA, 0xC0),
            Color.FromArgb(0xF8, 0xED, 0xD8),
            Color.FromArgb(0xE8, 0xC6, 0x6B),
            Color.FromArgb(0xBB, 0xD8, 0xDC),
        };
        // Sum is eight, preserving the original stack's overall cover span.
        private static readonly float[] Widths = { .72f, .76f, 1.12f, 1.40f, 1.40f, 1.12f, .76f, .72f };

        public static Color ColorAt(int index) => Colors[index];
        public static float WidthAt(int index) => Widths[index];

        public static float Offset(int index, float pitch)
        {
            var offset = -4f;
            for (var i = 0; i < index; i++) offset += Widths[i];
            return (offset + Widths[index] / 2f) * pitch;
        }

        // The caller applies the exact same scale/rotation/move commands as the solid band.
        public static OsbSprite Paper(StoryboardLayer layer)
            => layer.CreateSprite(PaperPath, OsbOrigin.Centre);
    }
}
