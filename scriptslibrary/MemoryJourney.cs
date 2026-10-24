using OpenTK;
using StorybrewCommon.Animations;
using StorybrewCommon.Storyboarding;
using System;
using System.Collections.Generic;

namespace StorybrewScripts
{
    // Relationship changes are drawn farther along a fixed canvas, never
    // animated by reshaping an already painted cord. Page two begins at x854.
    public static class MemoryJourney
    {
        public const int Start = 21000, Arrive = 21900, Hurt = 22200;
        public const int PenHandoff = 21200;
        public const int Apart = 23000, Love = 23940, Cross = 24340, Heart = 25540;
        public const int Route = 26140, End = 27140;
        public const int Handoff = 26600; // Kobe3D takes over this canvas here.
        public const float PageX = 854, ExitFocus = 1540;
        public const float CruiseSpeed = (ExitFocus - 320) / (End - Arrive); // px/ms
        const string Assets = "sb/cord-memories/";
        const string Disc = "sb/memory-editorial/background-disc.png";
        public const string CanvasAssets = "sb/memory-popprint/";

        public static void Generate(StoryboardLayer layer)
        {
            var camera = Camera();
            Cords(layer, camera);
            // One picture leads each passage. A shared 24px top edge keeps the
            // smaller heart-context image in the same composition as the CGs.
            Picture(layer, camera, "after-school", 180, 350, 21520, 22880);
            Picture(layer, camera, "home", 675, 240, 22640, 24200);
            Picture(layer, camera, "hand-in-hand", 1140, 208, 24080, 25560);
            Picture(layer, camera, "together", 1530, 340, 25440, End);
            // Top lyrics stay disabled; the footer carries the dialogue.
            for (var i = 0; i < 3; i++)
            {
                Station(layer, camera, 1690 + i * 100, 252, 26760 + i * 90);
                Station(layer, camera, 1710 + i * 100, 302, 26800 + i * 80);
            }
            Decorations(layer, camera);
            Dialogues(layer, camera);
            EndingCharacter(layer);
        }

        static void Dialogues(StoryboardLayer layer, StageCamera camera)
        {
            // Rounded dark type, centred in the band instead of on its bottom rail.
            DialogueReveal(layer, camera, "dialogue-memory", 21480, 265, .34f);
            DialogueReveal(layer, camera, "dialogue-thanks", 22380, 825, .34f);
            DialogueReveal(layer, camera, "dialogue-love", 24600, 1370, .34f);
        }

        static void DialogueReveal(StoryboardLayer layer, StageCamera camera,
            string name, int from, float x, float scale)
        {
            // Native sprites instead of OsbAnimation: same canvas and camera
            // projection at each handoff, with no changes to pan speed.
            for (var frame = 1; frame <= 18; frame++)
            {
                var begin = from + frame * 32;
                var finish = frame == 18 ? End : begin + 32;
                var suffix = frame == 18 ? ".png" : "-reveal-" + frame + ".png";
                var text = Sprite(layer, Assets + name + suffix);
                text.Fade(begin, 1);
                text.Fade(finish, 0);
                camera.Place(text, begin, finish, PageX + x, 433, scale);
            }
        }

        static void Decorations(StoryboardLayer layer, StageCamera camera)
        {
            // Build five-petal flowers from the original transparent petal cells.
            var groups = new[]
            {
                new Vector2(429, 72), new Vector2(457, 95), new Vector2(401, 103),
                new Vector2(910, 55), new Vector2(940, 78), new Vector2(883, 85),
                new Vector2(1718, 64), new Vector2(1746, 88), new Vector2(1719, 109),
            };
            // Three clusters, each with one leading bloom and two smaller ones.
            // Keep the cord field and dialogue band free of loose ornaments.
            var flowerStarts = new[] { 22040, 22120, 22200, 23740, 23820, 23900,
                26180, 26260, 26340 };
            var flowerEnds = new[] { 23320, 23320, 23320, 25160, 25160, 25160,
                End, End, End };
            for (var i = 0; i < groups.Length; i++)
            {
                var from = flowerStarts[i];
                var duration = Math.Min(480, Handoff - from - 40);
                for (var j = 0; j < 5; j++)
                {
                    var petal = Sprite(layer, Assets + "petal-0.png");
                    var scale = i % 3 == 0 ? .46f : i % 3 == 1 ? .32f : .25f;
                    var radiusFinal = i % 3 == 0 ? 8f : i % 3 == 1 ? 6f : 4.8f;
                    var poses = new List<StageCamera.Pose>();
                    var finalAngle = i * .71 + j * Math.PI * 2 / 5;
                    for (var t = from; t < from + duration; t += 32)
                    {
                        var grow = (float)OsbEasing.OutCubic.Ease((t - from) / (double)duration);
                        var turn = finalAngle - 1.8 * (1 - OsbEasing.OutSine.Ease((t - from) / (double)duration));
                        var radius = radiusFinal * grow;
                        poses.Add(new StageCamera.Pose(t, PageX + groups[i].X + (float)Math.Cos(turn) * radius,
                            groups[i].Y + (float)Math.Sin(turn) * radius, scale * grow, turn - Math.PI / 2));
                    }
                    var finalX = PageX + groups[i].X + (float)Math.Cos(finalAngle) * radiusFinal;
                    var finalY = groups[i].Y + (float)Math.Sin(finalAngle) * radiusFinal;
                    poses.Add(new StageCamera.Pose(from + duration, finalX, finalY, scale, finalAngle - Math.PI / 2));
                    poses.Add(new StageCamera.Pose(flowerEnds[i], finalX, finalY, scale, finalAngle - Math.PI / 2));
                    petal.Fade(from, .92);
                    if (flowerEnds[i] < End)
                        petal.Fade(OsbEasing.InSine, flowerEnds[i] - 140, flowerEnds[i], .92, 0);
                    camera.PlaceKeys(petal, poses);
                }
                var centre = Sprite(layer, Disc);
                centre.Color(from, 236 / 255.0, 196 / 255.0, 80 / 255.0);
                centre.Fade(from, 1);
                centre.Scale(OsbEasing.OutCubic, from, from + duration, 0, (i % 3 == 0 ? 4.5 : 3) / 512.0);
                if (flowerEnds[i] < End)
                    centre.Fade(OsbEasing.InSine, flowerEnds[i] - 140, flowerEnds[i], 1, 0);
                FollowPoint(centre, camera, from, PageX + groups[i].X, groups[i].Y);
            }
            var notes = new[] { new Vector2(475, 59), new Vector2(958, 45), new Vector2(1748, 145) };
            var noteStarts = new[] { 22200, 23900, 26260 };
            var noteEnds = new[] { 23320, 25160, End };
            for (var i = 0; i < notes.Length; i++)
            {
                var from = noteStarts[i];
                var note = Sprite(layer, Assets + "music-" + i % 3 + ".png");
                note.Fade(from, 1);
                if (noteEnds[i] < End)
                    note.Fade(OsbEasing.InSine, noteEnds[i] - 140, noteEnds[i], 1, 0);
                var poses = new List<StageCamera.Pose>();
                for (var t = from; t < noteEnds[i]; t += 32)
                    poses.Add(NotePose(t, from, notes[i]));
                poses.Add(NotePose(noteEnds[i], from, notes[i]));
                camera.PlaceKeys(note, poses);
            }
        }

        static StageCamera.Pose NotePose(int time, int from, Vector2 point)
        {
            var age = time - from;
            var grow = (float)OsbEasing.OutCubic.Ease(Math.Min(1, age / 240.0));
            var turn = OsbEasing.OutSine.Ease(Math.Min(1, age / 300.0));
            var sway = Math.Sin(Math.Max(0, age - 300) / 420.0);
            return new StageCamera.Pose(time, PageX + point.X, point.Y + (float)sway * 3,
                .23f * grow, -.35 + .41 * turn + sway * .07);
        }

        static void EndingCharacter(StoryboardLayer layer)
        {
            const int from = 25920, settle = 26200;
            var character = Sprite(layer, Assets + "sd-blonde.png", OsbOrigin.BottomCentre);
            character.Fade(from, 1);
            character.Move(OsbEasing.OutCubic, from, settle, 632, 486, 632, 464);
            character.Scale(OsbEasing.OutCubic, from, settle, .19, .225);
            var joy = Sprite(layer, Assets + "joy.png");
            joy.Move(settle, 710, 291);
            joy.Scale(settle, .40);
            // Hard on/off beats: no opacity tween between these intervals.
            foreach (var time in new[] { 26200, 26340, 26480 })
            {
                joy.Fade(time, 1);
                joy.Fade(time + 90, 0);
            }
            joy.Fade(26590, 1);
        }

        // Emit before the old-page cords too, so the extended footer cannot
        // hide their final 20px overhang at the page seam.
        public static void GenerateBackground(StoryboardLayer layer) => Background(layer, Camera());

        static StageCamera Camera()
        {
            var camera = new StageCamera();
            ApplyPan(camera, 320, 240);
            return camera;
        }

        public static float TravelX(int time)
        {
            var elapsed = Math.Max(0, Math.Min(End - Start, time - Start));
            const double acceleration = 200;
            const double deceleration = Arrive - Start - acceleration;
            var peak = (2 * PageX - CruiseSpeed * deceleration) / (Arrive - Start);
            if (elapsed <= acceleration)
                return (float)(peak * .5 * (elapsed - acceleration / Math.PI * Math.Sin(Math.PI * elapsed / acceleration)));
            if (time < Arrive)
            {
                var t = elapsed - acceleration;
                return (float)(peak * acceleration * .5 + (peak + CruiseSpeed) * t * .5
                    + (peak - CruiseSpeed) * deceleration / (2 * Math.PI) * Math.Sin(Math.PI * t / deceleration));
            }
            return PageX + CruiseSpeed * (elapsed - (Arrive - Start));
        }

        // Only the first pan accelerates and settles. The rest is one linear
        // camera segment, including the heart and route handoff.
        public static void ApplyPan(StageCamera camera, float x, float y, float zoom = 1)
        {
            camera.Cut(Start, x, y, zoom);
            for (var time = Start + 16; time < Arrive - 15; time += 16)
                camera.Ease(time, x + TravelX(time) / zoom, y, zoom, 0, OsbEasing.None);
            camera.Ease(Arrive, x + PageX / zoom, y, zoom, 0, OsbEasing.None);
            camera.Ease(End, x + TravelX(End) / zoom, y, zoom, 0, OsbEasing.None);
        }

        public static void PanPageSprite(OsbSprite sprite, int to, float x, float y, float scale)
            => Camera().Place(sprite, Start, to, x, y, scale);

        static OsbSprite Sprite(StoryboardLayer layer, string path, OsbOrigin origin = OsbOrigin.Centre)
        {
            var sprite = layer.CreateSprite(path, origin);
            sprite.Fade(Start - 1, 0);
            sprite.Fade(End, 0);
            return sprite;
        }

        static void Background(StoryboardLayer layer, StageCamera camera)
        {
            // Both pages share the same world-space pastel wash and yellow band.
            var ground = Sprite(layer, CanvasAssets + "ground.png");
            ground.Fade(Start, 1);
            camera.Place(ground, Start, End, 1940, 240);
            var ribbon = Sprite(layer, CanvasAssets + "ribbon.png");
            ribbon.Fade(Start, 1);
            camera.Place(ribbon, Start, End, 1840, 422);
        }

        // Opaque white first, then a widening transparent centre. The exterior
        // grows in 180ms; the border becomes a fine line and clears by 360ms.
        public static void BubbleRim(StoryboardLayer layer, int from, float x, float y,
            float diameter, StageCamera camera = null)
        {
            for (var frame = 0; frame < 18; frame++)
            {
                var begin = from + frame * 20;
                var finish = begin + 20;
                var rim = layer.CreateSprite(Assets + "bubble-rim-" + frame + ".png");
                rim.Fade(begin - 1, 0);
                rim.Fade(begin, 1);
                rim.Fade(finish, 0);
                var a = (float)(diameter / 512 * OsbEasing.OutCubic.Ease(Math.Min(1, (begin-from)/180.0)));
                var b = (float)(diameter / 512 * OsbEasing.OutCubic.Ease(Math.Min(1, (finish-from)/180.0)));
                if (camera == null)
                {
                    rim.Move(begin, x, y);
                    rim.Scale(begin, finish, a, b);
                }
                else camera.PlaceKeys(rim, new[] {
                    new StageCamera.Pose(begin, x, y, a),
                    new StageCamera.Pose(finish, x, y, b),
                });
            }
        }

        static void Cords(StoryboardLayer layer, StageCamera camera)
        {
            // The drawing clock follows the lyrics through successive spatial sections.
            // Every cubic is fixed. Its painted portion remains in the world afterwards.
            // Join the actual old-page endpoints (world x780/x779), rather
            // than its page edge x747: no horizontal spur remains at the turn.
            Stroke(layer,camera,false,PenHandoff,21760, -74,432, -2,432, 8,236, 80,236);
            Stroke(layer,camera,true,PenHandoff,21760, -75,469, -3,469, 8,260, 80,260);
            Stroke(layer,camera,false,21760,Hurt, 80,236, 164,236, 246,236, 330,236);
            Stroke(layer,camera,true,21760,Hurt, 80,260, 164,260, 246,260, 330,260);
            // Allocate duration by arc length, not lyric/cubic boundaries:
            // blue stays ~294px/s, pink's separation/approach stays ~384px/s.
            // The faster heart clock starts only on its actual contour.
            Stroke(layer,camera,false,Hurt,23280, 330,236, 430,236, 530,172, 640,172);
            Stroke(layer,camera,true,Hurt,23056, 330,260, 430,260, 550,330, 650,330);
            Stroke(layer,camera,false,23280,24678, 640,172, 785,172, 835,380, 980,380);
            Stroke(layer,camera,false,24678,Route, 980,380, 1125,380, 1265,380, 1410,380);
            Stroke(layer,camera,true,23056,23767, 650,330, 760,330, 820,270, 915,270,
                overpass: new Vector2(821.4f,288.1f));
            Stroke(layer,camera,true,23767,24400, 915,270, 1000,270, 1080,300, 1140,220);
            // One cursive heart: equal lobes, aligned vertical side tangents and
            // a rounded bottom. The incoming and outgoing strokes cross cleanly.
            Stroke(layer,camera,true,24400,24680, 1140,220, 1200,140, 1280,140, 1280,220);
            Stroke(layer,camera,true,24680,24970, 1280,220, 1280,300, 1180,350, 1140,350);
            Stroke(layer,camera,true,24970,25260, 1140,350, 1100,350, 1000,300, 1000,220,
                overpass: new Vector2(1017.2f,275.5f));
            Stroke(layer,camera,true,25260,Heart, 1000,220, 1000,140, 1080,140, 1140,220,
                overpass: new Vector2(1140,220));
            Stroke(layer,camera,true,Heart,Route, 1140,220, 1200,300, 1360,315, 1450,315,
                overpass: new Vector2(1140,220), overpass2: new Vector2(1252.8f,289.1f));
            // The newly drawn outgoing section becomes graphic routing, not a morph
            // of the existing heart. Physical cord stays behind, flat lines begin ahead.
            Stroke(layer,camera,false,Route,26600, 1410,380, 1535,380, 1485,252, 1610,252);
            Stroke(layer,camera,true,Route,26660, 1450,315, 1515,315, 1560,302, 1634,302,
                overpass: new Vector2(1512.7f,311.4f));
            Stroke(layer,camera,false,26600,26960, 1610,252, 1710,252, 1810,252, 1930,252,true);
            Stroke(layer,camera,true,26660,27000, 1634,302, 1734,302, 1834,302, 1930,302,true);
        }

        static void Stroke(StoryboardLayer layer, StageCamera camera, bool pink, int from, int to,
            float ax, float ay, float bx, float by, float cx, float cy, float dx, float dy,
            bool flat = false, Vector2? overpass = null, Vector2? overpass2 = null)
        {
            var a = new Vector2(ax,ay); var b = new Vector2(bx,by);
            var c = new Vector2(cx,cy); var d = new Vector2(dx,dy);
            var steps = Math.Max(12, Math.Min(90, (int)(((b-a).Length+(c-b).Length+(d-c).Length)/5)));
            var points = new List<Vector2>(); var lengths = new List<float>(); float total = 0;
            for (var i = 0; i <= steps; i++)
            {
                var t = i/(float)steps; var v = 1-t;
                var p = a*v*v*v+b*3*v*v*t+c*3*v*t*t+d*t*t*t;
                if (i>0) total += (p-points[i-1]).Length;
                points.Add(p); lengths.Add(total);
            }
            for (var i = 1; i < points.Count; i++)
            {
                var p = points[i-1]; var delta = points[i]-p; var mid = p+delta*.5f;
                // Missing fibers belong to the drawn record and never fade back in.
                if (pink && ((mid.X>175 && mid.X<193 && mid.Y<280)
                    || (mid.X>510 && mid.X<540 && mid.Y>300))) continue;
                var begin = from+(int)((to-from)*lengths[i-1]/total);
                var finish = Math.Max(begin+16,from+(int)((to-from)*lengths[i]/total));
                var path = flat ? "sb/px.png" : pink ? "sb/memory-editorial/memory-cord.png" : "sb/memory-editorial/blue-cord.png";
                var sx = flat ? delta.Length+1.8f : (delta.Length+1.8f)/16;
                var sy = flat ? pink ? 3.4f : 3.8f : 12/96f;
                // The entire rope remains present. A narrow shadow beneath the
                // later stroke separates it from the earlier, farther crossing.
                var distance = Math.Min(overpass.HasValue ? (mid-overpass.Value).Length : float.MaxValue,
                    overpass2.HasValue ? (mid-overpass2.Value).Length : float.MaxValue);
                if (distance < 16)
                {
                    var shadow = Sprite(layer,path,OsbOrigin.CentreLeft);
                    shadow.Color(begin,93/255.0,66/255.0,59/255.0);
                    shadow.Fade(begin,.30 * Math.Min(1,(16-distance)/6));
                    shadow.ScaleVec(OsbEasing.None,begin,finish,0,sy*1.8f,sx,sy*1.8f);
                    shadow.Rotate(begin,Math.Atan2(delta.Y,delta.X));
                    FollowPoint(shadow,camera,begin,PageX+p.X,p.Y+.6f);
                }
                var sprite = Sprite(layer,path,OsbOrigin.CentreLeft);
                sprite.Fade(begin,1);
                if (flat) sprite.Color(begin,pink?239/255.0:84/255.0,pink?98/255.0:159/255.0,pink?143/255.0:200/255.0);
                // Linear arc-length clock and linear short-segment growth: the
                // pen never eases to a halt at every cubic or sampled segment.
                sprite.ScaleVec(OsbEasing.None,begin,finish,0,sy,sx,sy);
                sprite.Rotate(begin,Math.Atan2(delta.Y,delta.X));
                FollowPoint(sprite,camera,begin,PageX+p.X,p.Y);
            }
        }

        static void FollowPoint(OsbSprite sprite, StageCamera camera, int from, float x, float y)
        {
            // Move only the camera projection, leaving ScaleVec's native pen curve intact.
            var times = new SortedSet<int>{from,End};
            for (var t=from;t<End;t+=32) times.Add(t);
            foreach(var t in new[]{Arrive,Hurt,Apart,Love,Heart,Route}) if(t>from) times.Add(t);
            int last=-1; (float x,float y) previous=(0,0);
            foreach(var t in times)
            {
                var p=camera.ToScreen(t,x,y);
                if(last<0) sprite.Move(t,p.x,p.y);
                else sprite.Move(last,t,previous.x,previous.y,p.x,p.y);
                previous=p;last=t;
            }
        }

        static double Progress(int t,int from,int to)
            => OsbEasing.OutCubic.Ease(Math.Max(0,Math.Min(1,(t-from)/(double)(to-from))));

        static void Picture(StoryboardLayer layer, StageCamera camera,
            string name, float x, float width, int from, int to)
        {
            var height=width*9/16;
            var y=24+height/2;
            var matte=Sprite(layer,"sb/px.png");
            matte.Color(from,1,252/255.0,246/255.0);
            matte.Fade(OsbEasing.OutSine,from,from+240,0,1);
            if(to<End) matte.Fade(OsbEasing.InSine,to-140,to,1,0);
            var image=Sprite(layer,Assets+name+".png");
            image.Fade(OsbEasing.OutSine,from,from+240,0,1);
            if(to<End) image.Fade(OsbEasing.InSine,to-140,to,1,0);
            var poses=new List<StageCamera.Pose>();
            var mattePoses=new List<StageCamera.Pose>();
            for(var t=from;t<=from+288;t+=24)
            {
                var p=Progress(t,from,from+288);
                poses.Add(new StageCamera.Pose(t,PageX+x,y+(float)(9*(1-p)),
                    width/768,height/432,0));
                mattePoses.Add(new StageCamera.Pose(t,PageX+x,y+(float)(9*(1-p)),
                    width+8,height+8,0));
            }
            poses.Add(new StageCamera.Pose(to,PageX+x,y,width/768,height/432,0));
            mattePoses.Add(new StageCamera.Pose(to,PageX+x,y,width+8,height+8,0));
            camera.PlaceKeys(matte,mattePoses);
            camera.PlaceKeys(image,poses);
        }

        static void Station(StoryboardLayer layer,StageCamera camera,float x,float y,int from)
        {
            var station=Sprite(layer,Assets+"station.png");
            station.Fade(OsbEasing.OutSine,from,from+150,0,1);
            var poses=new List<StageCamera.Pose>();
            var finish=Math.Min(from+170,End-1);
            for(var t=from;t<finish;t+=32)
                poses.Add(new StageCamera.Pose(t,PageX+x,y,(float)(.04+.18*Progress(t,from,finish))));
            poses.Add(new StageCamera.Pose(finish,PageX+x,y,.22f));
            poses.Add(new StageCamera.Pose(End,PageX+x,y,.22f));
            camera.PlaceKeys(station,poses);
        }
    }
}
