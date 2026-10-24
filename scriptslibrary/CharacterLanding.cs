using System;
using System.Drawing;

namespace StorybrewScripts
{
    // Layout values authored at the existing 80-degree landing pose.
    // Converting them to rest coordinates keeps the original rotation clock.
    public static class CharacterLanding
    {
        public const float ShelfRatio = .82f;

        public static (float x, float y) OffsetAt80(float x, float y, float dx, float dy)
        {
            var angle = 10 * Math.PI / 180;
            return ((float)(x + dx * Math.Cos(angle) + dy * Math.Sin(angle)),
                    (float)(y - dx * Math.Sin(angle) + dy * Math.Cos(angle)));
        }

        public static (float x, float y) ShelfAnchor(Bitmap texture, float x, float y, float originalScale)
        {
            var crest = 0;
            while (crest < texture.Height && texture.GetPixel(texture.Width / 2, crest).A < 128)
                crest++;
            var offset = crest + .5f - texture.Height / 2f;
            // Counter the shrink about the texture center, then lower its crest.
            y += (1 - ShelfRatio) * offset * originalScale;
            return OffsetAt80(x, y, 0, 15);
        }
    }
}
