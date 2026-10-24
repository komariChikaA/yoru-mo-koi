using StorybrewCommon.Storyboarding;

namespace StorybrewScripts
{
    // Materials only: preserve original inks on the title and the photograph.
    public static class SequenceMaterial
    {
        public const string PaperPath = PaperMaterial.Path;
        public const string PhotoGrainPath = "sb/sequence-editorial/photo-paper-grain.png";
        public const double TitlePaperOpacity = PaperMaterial.SparseOpacity;
        public const double MemoryPaperOpacity = PaperMaterial.MemoryOpacity;
        public const double PhotoPaperOpacity = PaperMaterial.MemoryOpacity;
        // No global alpha wash: normal-alpha tint would yellow the CG and flatten title inks.
        public const double GlobalWarmOpacity = 0;

        public static OsbSprite Paper(StoryboardLayer layer, int start, int end, double opacity)
        {
            var paper = layer.CreateSprite(PaperPath);
            paper.Move(start, 320, 240);
            paper.Scale(start, 1.2);
            paper.Fade(0, 0);
            paper.Fade(start, opacity);
            paper.Fade(end - 1, opacity);
            paper.Fade(end, 0);
            return paper;
        }
    }
}
