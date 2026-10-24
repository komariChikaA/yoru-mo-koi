using StorybrewCommon.Storyboarding;

namespace StorybrewScripts
{
    // Character-page material only. Geometry and motion remain in Background.
    public static class CharacterPalette
    {
        public static string Path(string original) => "sb/character-palette/" +
            (original.StartsWith("sb/") ? original.Substring(3) : original);

        public static void Paper(StoryboardLayer layer, int start, int end)
        {
            var paper = layer.CreateSprite(PaperMaterial.Path);
            paper.Move(start, 320, 240);
            paper.Scale(start, 1.2);
            paper.Fade(start, PaperMaterial.BackgroundOpacity);
            paper.Fade(end, end + 16, PaperMaterial.BackgroundOpacity, 0);
        }
    }
}
