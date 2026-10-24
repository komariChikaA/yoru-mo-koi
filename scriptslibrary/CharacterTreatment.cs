using System;
using System.Drawing;
using OpenTK;
using StorybrewCommon.Storyboarding;

namespace StorybrewScripts
{
    public static class CharacterTreatment
    {
        public static (float x, float y) NamePosition(float x, float y)
            => (x, y); // Keep the original name group beneath the character.

        public static void Focus(StoryboardLayer layer, int start, int end)
        {
            var focus = layer.CreateSprite(CharacterPalette.Path("effects/focus.png"));
            focus.Move(start, 320, 240);
            focus.Fade(start, .07);
            focus.Fade(end, end + 16, .07, 0);
        }

        // Screen-space lamp sweep above the page, independent of its cel clock.
        public static void PageSweep(StoryboardLayer layer)
        {
            const int start = 9500;
            const int end = 13000;
            var source = new Vector2(320, -160);
            const double degree = Math.PI / 180;
            // The top aperture stays fixed. Rotation steers the entire shaft
            // left-to-right, slowing across the character before swinging out.
            var beam = LightingFx.SweepLight(layer, start, end, source, source,
                new Vector2(1.15f, 1), 50 * degree, Color.White,
                opacity: .24, fadeIn: 180, fadeOut: 400,
                texturePath: LightingFx.TubeBeam, origin: OsbOrigin.TopCentre);
            beam.Rotate(OsbEasing.OutCubic, start, 10320, 50 * degree, 5 * degree);
            beam.Rotate(OsbEasing.InOutSine, 10320, 11000, 5 * degree, -32 * degree);
            beam.Rotate(OsbEasing.InQuad, 11000, end, -32 * degree, -70 * degree);

            // A brief page-wide reflection while the beam crosses the subject.
            // Normal alpha preserves detail and restores the palette on release.
            LightingFx.HighlightPulse(layer, 10560, 400, new Vector2(320, 240),
                new Vector2(864, 480), Color.White, peakOpacity: .18,
                attackRatio: .25, texturePath: "sb/px.png");
        }
    }
}
