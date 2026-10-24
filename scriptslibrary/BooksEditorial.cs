using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System;
using System.Globalization;
using System.IO;
using System.Linq;

namespace StorybrewScripts
{
    public static class BooksEditorial
    {
        const string Assets = "sb/books-editorial/";
        const float Left = -107, Right = 747, Period = 396, StripWidth = 1584, Scale = .5f;
        const int GrowMs = 220;

        public static string CreditPath(string file) => Assets + "credit/" + file;

        public static void Background(StoryboardLayer layer, int start, int end)
        {
            var blue = layer.CreateSprite("sb/px.png");
            blue.Move(start, 320, 240);
            blue.ScaleVec(start, 864, 480);
            blue.Color(start, 170/255f, 208/255f, 222/255f); // #AAD0DE
            blue.Fade(start, start + 140, 0, 1);
            blue.Fade(end, end + 16, 1, 0);
        }

        public static void Paper(StoryboardLayer layer, int start, int end)
        {
            var paper = layer.CreateSprite(PaperMaterial.Path);
            paper.Move(start, 320, 240);
            paper.Scale(start, 1.2);
            paper.Fade(OsbEasing.OutSine, start, start + 380, 0, PaperMaterial.BackgroundOpacity);
            paper.Fade(end, end + 16, PaperMaterial.BackgroundOpacity, 0);
        }

        // Restore the character-page underlay while the star fills the screen.
        // Its palette is separate from this books page; scrolling is unchanged.
        public static void FollowingShotUnderlay(StoryboardLayer blueLayer, StoryboardLayer booksLayer,
            int originalStart, int restore, int moveEnd, int hide)
        {
            var blue = blueLayer.CreateSprite(CharacterPalette.Path("bluebg.png"));
            blue.Scale(restore, 480f / 768);
            blue.Fade(restore, 1);
            blue.Fade(hide, hide + 16, 1, 0);
            const float distance = StripWidth * 3, margin = 48;
            var coverLeft = Left - distance - margin;
            var count = (int)Math.Ceiling((Right + distance + margin - coverLeft) / StripWidth);
            for (var i = 0; i < count; i++)
                for (var row = 0; row < 2; row++)
                {
                    var top = row == 1;
                    var x = coverLeft + i * StripWidth;
                    var strip = booksLayer.CreateSprite(CharacterPalette.Path(top ? "sb/books-down.png" : "sb/books-up.png"),
                        top ? OsbOrigin.TopLeft : OsbOrigin.BottomLeft);
                    strip.Scale(restore, 1);
                    strip.MoveY(restore, top ? 0 : 480);
                    strip.MoveX(originalStart, moveEnd, x, x + (top ? distance : -distance));
                    strip.Fade(originalStart, 0);
                    strip.Fade(restore, 1);
                    strip.Fade(hide, hide + 16, 1, 0);
                }
        }

        public static void Rows(StoryboardObjectGenerator owner, StoryboardLayer layer, int start, int moveEnd, int hide)
        {
            var books = File.ReadAllLines(Path.Combine(owner.MapsetPath, Assets, "layout.txt"))
                .Where(l => !string.IsNullOrWhiteSpace(l))
                .Select(l => l.Split(' ').Select(v => int.Parse(v, CultureInfo.InvariantCulture)).ToArray()).ToArray();
            const float distance = StripWidth * 3, margin = 48;
            var coverLeft = Left - distance - margin;
            var coverRight = Right + distance + margin;
            // Only visible books need separate grow sprites. Distant repeats are
            // already part of the strips once the row starts scrolling.
            var positions = Enumerable.Range(0, (int)Math.Ceiling((coverRight-coverLeft)/Period))
                .SelectMany(i => books.Select(b => (x: coverLeft + i*Period + b[1], book: b)))
                .Where(p => p.x + p.book[2] > Left-margin && p.x < Right+margin).ToArray();
            var growStart = start + 160;
            var lastDelay = Delay(positions.Length - 1) + 24;
            var moveStart = growStart + lastDelay + GrowMs + 40;
            for (var row = 0; row < 2; row++)
            {
                var top = row == 1;
                var rail = layer.CreateSprite("sb/px.png");
                rail.Move(start, 320, top ? 2 : 478);
                rail.ScaleVec(start, 864, 4);
                rail.Color(start, 48/255f, 70/255f, 93/255f);
                rail.Fade(start, start + 140, 0, 1);
                rail.Fade(moveStart, 0);
                for (var i = 0; i < positions.Length; i++)
                {
                    var p = positions[i];
                    var delay = Delay(top ? i : positions.Length-1-i) + (top ? 0 : 24);
                    GrowBook(layer, p.book[0], p.x, top, growStart + delay, moveStart);
                }
                for (var i = 0; i < (int)Math.Ceiling((coverRight-coverLeft)/StripWidth); i++)
                {
                    var x = coverLeft + i * StripWidth;
                    var strip = layer.CreateSprite(Assets + (top ? "row-top.png" : "row-bottom.png"),
                        top ? OsbOrigin.TopLeft : OsbOrigin.BottomLeft);
                    strip.Scale(moveStart, Scale);
                    strip.MoveY(moveStart, top ? 0 : 480);
                    strip.MoveX(moveStart, moveEnd, x, x + (top ? distance : -distance));
                    strip.Fade(moveStart, 1);
                    strip.Fade(hide, hide + 16, 1, 0);
                }
            }
        }

        static int Delay(int index) => index / 4 * 72 + index % 4 * 16;

        static void GrowBook(StoryboardLayer layer, int index, float x, bool top, int start, int swap)
        {
            var book = layer.CreateSprite(Assets + "book-" + index.ToString("D2") + (top ? "-top.png" : "-bottom.png"),
                top ? OsbOrigin.TopLeft : OsbOrigin.BottomLeft);
            book.Move(start, x, top ? 4 : 476);
            book.Fade(start, 1);
            book.ScaleVec(OsbEasing.OutCubic, start, start + GrowMs, Scale, 0, Scale, Scale);
            book.Fade(swap, 0);
        }
    }
}
