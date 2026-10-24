namespace StorybrewScripts
{
    public static class CharacterAntialias
    {
        // Transparent padding is outside the authored 120px face.
        public const float CardScale = 1f / 3f;
        public const float ArcScale = .5f;
        public static string Stroke(float thick) => CharacterPalette.Path(
            "arc-stroke-" + System.Math.Round(thick * 10000) + ".png");
    }
}
