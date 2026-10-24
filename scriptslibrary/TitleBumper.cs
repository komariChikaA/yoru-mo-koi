using StorybrewCommon.Scripting;
using StorybrewCommon.Storyboarding;
using System;

namespace StorybrewScripts
{
    // Only 0–1680ms. Settled logo plates share six precomposed print bands;
    // grid timing stays a deterministic diagonal distance, never random debris.
    public static class TitleBumper
    {
        const string Assets = "sb/title-bumper/";
        const float X = 320, Y = 240, Scale = 0.5f, WordGap = 28;
        const int BellHeight = 74, Cell = 16, Columns = 54, Rows = 30;
        const float InkR = 61 / 255f, InkG = 48 / 255f, InkB = 42 / 255f;

        public static void Background(StoryboardLayer layer)
        {
            var paper = layer.CreateSprite(Assets + "paper.png");
            paper.Move(0, X, Y);
            paper.Scale(0, 1);
            paper.Fade(0, 1);
            paper.Fade(899, 1);
            paper.Fade(900, 0); // Same tiles take over; holes immediately reveal the blue layer.

            // One reusable white wash behind the logo gives the whole page
            // the print flash, rather than adding dozens of noise sprites.
            var flash = layer.CreateSprite("sb/px.png");
            flash.Move(480, X, Y);
            flash.ScaleVec(480, 864, 480);
            flash.Fade(OsbEasing.OutCubic, 480, 496, 0, 0.30);
            flash.Fade(OsbEasing.InQuad, 508, 600, 0.30, 0);
            flash.Fade(OsbEasing.OutCubic, 740, 752, 0, 0.18);
            flash.Fade(OsbEasing.InQuad, 768, 860, 0.18, 0);
        }

        public static void Logo(StoryboardObjectGenerator owner, StoryboardLayer layer)
        {
            var bell = owner.GetMapsetBitmap(Assets + "bell.png");
            var yume = owner.GetMapsetBitmap(Assets + "yume.png");
            var iro = owner.GetMapsetBitmap(Assets + "iro.png");
            var leftX = X - bell.Width * Scale / 2 - WordGap - yume.Width * Scale / 2;
            var rightX = X + bell.Width * Scale / 2 + WordGap + iro.Width * Scale / 2;
            // Printed layers sit behind the warm-black master, which remains dominant.
            InkPlates(layer, X + (iro.Width - yume.Width) * Scale / 2);

            var left = layer.CreateSprite(Assets + "yume.png");
            var right = layer.CreateSprite(Assets + "iro.png");
            Word(left, leftX);
            Word(right, rightX);
            Jolt(left, leftX);
            Jolt(right, rightX);
            var master = layer.CreateSprite(Assets + "bell.png");
            master.Color(20, InkR, InkG, InkB);
            master.Move(20, X, Y);
            master.Fade(20, 140, 0, 1);
            master.Scale(20, 150, Scale * 0.25f, Scale * 1.5f);
            master.Scale(166, 300, Scale * 1.5f, Scale);
            master.Rotate(20, 300, Math.PI / 6, 0);
            MasterPulse(master);
            Jolt(master, X);

            var sub = layer.CreateSprite(Assets + "subtitle.png");
            sub.Color(250, InkR, InkG, InkB);
            sub.Move(250, X, 307);
            sub.Scale(250, Scale);
            sub.Fade(OsbEasing.OutSine, 250, 430, 0, 0.72);
            sub.Fade(900, 1020, 0.72, 0);
        }

        static void Word(OsbSprite sprite, float restX)
        {
            sprite.Color(160, InkR, InkG, InkB);
            sprite.MoveY(160, Y);
            sprite.Scale(160, Scale);
            sprite.Fade(160, 400, 0, 1);
            sprite.MoveX(OsbEasing.Out, 160, 430, X, restX);
            MasterPulse(sprite);
        }

        static void MasterPulse(OsbSprite sprite)
        {
            sprite.Fade(480, 508, 1, 0.34);
            sprite.Fade(552, 600, 0.34, 1);
            sprite.Fade(740, 768, 1, 0.60);
            sprite.Fade(812, 860, 0.60, 1);
            sprite.Fade(900, 1080, 1, 0);
        }

        static void Jolt(OsbSprite sprite, float restX)
        {
            sprite.MoveX(OsbEasing.OutCubic, 480, 496, restX, restX - 7);
            sprite.MoveX(OsbEasing.InQuad, 576, 600, restX - 7, restX);
            sprite.MoveX(OsbEasing.OutCubic, 740, 752, restX, restX + 3);
            sprite.MoveX(OsbEasing.InQuad, 836, 860, restX + 3, restX);
        }

        static void InkPlates(StoryboardLayer layer, float restX)
        {
            float[] nudge = { -40f, 24f, -30f, 36f, -20f, 28f };
            for (var i = 0; i < 6; i++)
            {
                var top = BellHeight * 2 * i / 6;
                var bottom = BellHeight * 2 * (i + 1) / 6;
                var y = Y + (top + bottom - BellHeight * 2) * 0.25f;
                for (var ink = 0; ink < 2; ink++)
                {
                    var sprite = layer.CreateSprite(Assets + "ink-" + i + ".png");
                    sprite.Scale(480, Scale);
                    sprite.MoveY(480, y);
                    sprite.Color(480, ink == 0 ? 233 / 255f : 112 / 255f,
                        ink == 0 ? 132 / 255f : 185 / 255f, ink == 0 ? 165 / 255f : 212 / 255f);
                    var sign = ink == 0 ? -1 : 1;
                    PrintPass(sprite, restX, restX + sign * 36 + nudge[i], 480, 600, 0.98);
                    PrintPass(sprite, restX, restX + sign * 18 + nudge[i] * 0.55f, 740, 860, 0.78);
                }
            }
        }

        static void PrintPass(OsbSprite sprite, float restX, float offsetX, int start, int end, double alpha)
        {
            sprite.Fade(start, start + 28, 0, alpha);
            sprite.Fade(end - 24, end, alpha, 0);
            sprite.MoveX(OsbEasing.OutCubic, start, start + 28, restX, offsetX);
            sprite.MoveX(OsbEasing.InQuad, end - 24, end, offsetX, restX);
        }

        public static void Grid(StoryboardLayer layer)
        {
            for (var row = 0; row < Rows; row++)
                for (var col = 0; col < Columns; col++)
                {
                    var distance = Math.Abs((col - row) - 12);
                    var start = 900 + distance * 16;
                    var square = layer.CreateSprite(Assets + "tile.png");
                    square.Move(900, -104 + col * Cell, 8 + row * Cell);
                    square.Scale(start, start + 90, 1, 0);
                }
            // Faint ink patches reach only the first three diagonal waves near the
            // logo. Full tile shapes avoid a technical-looking field of thin ticks.
            // They are gone at 940ms, before the ordinary grid continues.
            for (var row = 12; row <= 17; row++)
                for (var d = -2; d <= 2; d++)
                {
                    var col = row + 12 + d;
                    var start = 900 + Math.Abs(d) * 16;
                    var ink = (row + d) & 1;
                    var patch = layer.CreateSprite("sb/px.png");
                    var x = -104 + col * Cell + (ink == 0 ? -2 : 2);
                    patch.Move(860, x, 8 + row * Cell);
                    patch.Color(860, ink == 0 ? 233 / 255f : 112 / 255f,
                        ink == 0 ? 132 / 255f : 185 / 255f, ink == 0 ? 165 / 255f : 212 / 255f);
                    patch.ScaleVec(860, 16, 16);
                    patch.ScaleVec(start, start + 90, 16, 16, 0, 0);
                    patch.Fade(OsbEasing.OutSine, 860, 884, 0, 0.16);
                    patch.Fade(OsbEasing.InQuad, 900, 940, 0.16, 0);
                }
        }

        public static void DepartingSquares(StoryboardLayer layer)
        {
            float[] x = { -40, 40, 700, 760, -80, 300, 640, 80 };
            float[] y = { 70, 40, 60, 400, 420, 450, 30, 430 };
            float[] toX = { -120, -20, 780, 820, -140, 250, 760, -40 };
            float[] toY = { 16, 8, 18, 468, 470, 476, 6, 468 };
            for (var i = 0; i < x.Length; i++)
            {
                var time = 1180 + (i % 4) * 16;
                var square = layer.CreateSprite("sb/px.png");
                square.Color(time, 247 / 255f, 228 / 255f, 161 / 255f);
                square.Fade(time, time + 40, 0, 0.95);
                square.Fade(time + 160, 1680, 0.95, 0);
                square.ScaleVec(time, 8 + (i % 3) * 2, 8 + (i % 3) * 2);
                square.Move(time, 1680, x[i], y[i], toX[i], toY[i]);
            }
        }
    }
}
