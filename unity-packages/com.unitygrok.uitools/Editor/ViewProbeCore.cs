using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools
{
    public enum MarkType { Point, Arrow, Line, Box, Freehand }

    public class Mark
    {
        public MarkType Type;
        public List<Vector2> Pts = new List<Vector2>();   // image-space px, top-left origin
        public string Note = "";
        public string Target = "";                         // resolved hierarchy path or ""
    }

    // a drawable UI element captured at grab time, stored in image-space px so resolve is pure
    public struct ElementRect
    {
        public string Path;
        public Rect ImgRect;
        public int Order;   // higher = drawn on top
    }

    // pure helpers: the coordinate + export math, kept off the EditorWindow so it is testable
    public static class ViewProbeCore
    {
        // fit a native capture under a max long-edge, preserving aspect. scale==1 when already within cap.
        public static (int w, int h, float scale) FitToCap(int w, int h, int cap)
        {
            int longEdge = Mathf.Max(w, h);
            if (longEdge <= cap || longEdge == 0) return (w, h, 1f);
            float s = (float)cap / longEdge;
            return (Mathf.RoundToInt(w * s), Mathf.RoundToInt(h * s), s);
        }

        public static string Norm(Vector2 p, int w, int h)
        {
            float nx = w > 0 ? p.x / w : 0f;
            float ny = h > 0 ? p.y / h : 0f;
            return $"({F3(nx)},{F3(ny)})";
        }

        // topmost element whose rect contains the point; tie-break smallest area. "" if none.
        public static string ResolveTopmost(Vector2 imgPt, List<ElementRect> els)
        {
            string best = "";
            int bestOrder = int.MinValue;
            float bestArea = float.MaxValue;
            if (els != null)
            {
                foreach (var e in els)
                {
                    if (!e.ImgRect.Contains(imgPt)) continue;
                    float area = e.ImgRect.width * e.ImgRect.height;
                    if (e.Order > bestOrder || (e.Order == bestOrder && area < bestArea))
                    {
                        best = e.Path; bestOrder = e.Order; bestArea = area;
                    }
                }
            }
            return best;
        }

        // full-screen effect layers (brightness dim, vignette) sit on top with a high sortingOrder and a
        // screen-sized rect, so they swallow every probe hit. drop path-matches before resolve; add a token to ignore another.
        public static readonly string[] OverlayIgnoreTokens = { "BrightnessOverlay" };

        public static bool IsIgnoredOverlay(string path)
        {
            if (string.IsNullOrEmpty(path)) return false;
            foreach (var tok in OverlayIgnoreTokens)
                if (path.IndexOf(tok, System.StringComparison.OrdinalIgnoreCase) >= 0) return true;
            return false;
        }

        public static Vector2 BBoxMin(List<Vector2> pts)
        {
            var m = new Vector2(float.MaxValue, float.MaxValue);
            foreach (var p in pts) { m.x = Mathf.Min(m.x, p.x); m.y = Mathf.Min(m.y, p.y); }
            return m;
        }

        public static Vector2 BBoxMax(List<Vector2> pts)
        {
            var m = new Vector2(float.MinValue, float.MinValue);
            foreach (var p in pts) { m.x = Mathf.Max(m.x, p.x); m.y = Mathf.Max(m.y, p.y); }
            return m;
        }

        public static string BuildExport(string absPng, string view, int nativeW, int nativeH,
            int imgW, int imgH, float scale, string mode, string camera, List<Mark> marks)
        {
            var sb = new StringBuilder();
            sb.Append("Look at the screenshot at: ").Append(absPng).Append('\n');
            sb.Append("view: ").Append(view)
              .Append(" | native: ").Append(nativeW).Append('x').Append(nativeH)
              .Append(" | image: ").Append(imgW).Append('x').Append(imgH)
              .Append(" (scale ").Append(F3(scale)).Append(')')
              .Append(" | aspect: ").Append(Aspect(nativeW, nativeH))
              .Append(" | mode: ").Append(mode)
              .Append(" | camera: ").Append(camera).Append('\n');
            if (marks == null || marks.Count == 0)
            {
                sb.Append("(no marks)\n");
                return sb.ToString();
            }
            for (int i = 0; i < marks.Count; i++)
            {
                var m = marks[i];
                sb.Append('[').Append(i + 1).Append("] ").Append(m.Type.ToString().ToUpperInvariant()).Append(' ');
                AppendGeom(sb, m, imgW, imgH, scale);
                sb.Append(" target: ").Append(string.IsNullOrEmpty(m.Target) ? "none (world/empty)" : m.Target);
                sb.Append(" note: \"").Append(m.Note ?? "").Append("\"\n");
            }
            return sb.ToString();
        }

        static void AppendGeom(StringBuilder sb, Mark m, int w, int h, float scale)
        {
            var p = m.Pts;
            float inv = scale > 0 ? 1f / scale : 1f;
            switch (m.Type)
            {
                case MarkType.Point:
                    sb.Append("img").Append(Pt(p[0])).Append(" norm").Append(Norm(p[0], w, h));
                    break;
                case MarkType.Arrow:
                    sb.Append("img").Append(Pt(p[0])).Append("->").Append(Pt(p[1]))
                      .Append(" norm").Append(Norm(p[0], w, h)).Append("->").Append(Norm(p[1], w, h));
                    break;
                case MarkType.Line:
                {
                    float lenImg = Vector2.Distance(p[0], p[1]);
                    sb.Append("img").Append(Pt(p[0])).Append('-').Append(Pt(p[1]))
                      .Append(" norm").Append(Norm(p[0], w, h)).Append('-').Append(Norm(p[1], w, h))
                      .Append(" lenImg=").Append(Mathf.RoundToInt(lenImg))
                      .Append(" lenNative=").Append(Mathf.RoundToInt(lenImg * inv)).Append("px");
                    break;
                }
                case MarkType.Box:
                {
                    var mn = new Vector2(Mathf.Min(p[0].x, p[1].x), Mathf.Min(p[0].y, p[1].y));
                    var mx = new Vector2(Mathf.Max(p[0].x, p[1].x), Mathf.Max(p[0].y, p[1].y));
                    float bw = mx.x - mn.x, bh = mx.y - mn.y;
                    sb.Append("img").Append(Pt(mn)).Append('-').Append(Pt(mx))
                      .Append(" norm").Append(Norm(mn, w, h)).Append('-').Append(Norm(mx, w, h))
                      .Append(" sizeImg=").Append(Mathf.RoundToInt(bw)).Append('x').Append(Mathf.RoundToInt(bh))
                      .Append(" sizeNative=").Append(Mathf.RoundToInt(bw * inv)).Append('x').Append(Mathf.RoundToInt(bh * inv)).Append("px");
                    break;
                }
                default: // Freehand
                {
                    var mn = BBoxMin(p); var mx = BBoxMax(p);
                    sb.Append(p.Count).Append(" pts, bbox img").Append(Pt(mn)).Append('-').Append(Pt(mx));
                    break;
                }
            }
        }

        static string Pt(Vector2 p) => $"({Mathf.RoundToInt(p.x)},{Mathf.RoundToInt(p.y)})";
        static string F3(float v) => v.ToString("0.###", CultureInfo.InvariantCulture);

        static string Aspect(int w, int h)
        {
            if (w <= 0 || h <= 0) return "?";
            int g = Gcd(w, h);
            return $"{w / g}:{h / g}";
        }

        static int Gcd(int a, int b) { while (b != 0) { (a, b) = (b, a % b); } return a == 0 ? 1 : a; }

        [MenuItem("Tools/UnityGrok/View Probe Self-Test")]
        static void SelfTest()
        {
            int pass = 0, fail = 0;
            void Check(bool ok, string label) { if (ok) pass++; else { fail++; Debug.LogError($"View Probe self-test FAIL: {label}"); } }

            var (w, h, s) = FitToCap(4000, 2000, 2048);
            Check(w == 2048 && h == 1024 && Mathf.Approximately(s, 0.512f), "FitToCap downscale");
            var fit2 = FitToCap(1920, 1080, 2048);
            Check(fit2.w == 1920 && fit2.scale == 1f, "FitToCap passthrough");

            Check(Norm(new Vector2(512, 256), 1024, 512) == "(0.5,0.5)", "Norm center");

            var els = new List<ElementRect>
            {
                new ElementRect { Path = "Canvas/Panel", ImgRect = new Rect(0, 0, 500, 500), Order = 1 },
                new ElementRect { Path = "Canvas/Panel/Button", ImgRect = new Rect(100, 100, 80, 40), Order = 2 },
            };
            Check(ResolveTopmost(new Vector2(120, 110), els) == "Canvas/Panel/Button", "resolve topmost-smallest");
            Check(ResolveTopmost(new Vector2(450, 450), els) == "Canvas/Panel", "resolve outer only");
            Check(ResolveTopmost(new Vector2(900, 900), els) == "", "resolve miss");

            Check(IsIgnoredOverlay("BrightnessController/BrightnessOverlayCanvas/Overlay"), "ignore brightness overlay");
            Check(!IsIgnoredOverlay("GameUI/SafeAreaRoot/OptionsButton"), "keep normal element");

            var marks = new List<Mark>
            {
                new Mark { Type = MarkType.Line, Pts = { new Vector2(0,0), new Vector2(100,0) }, Note = "this long", Target = "" },
            };
            var ex = BuildExport("C:/x/p.png", "GameView", 2048, 0, 2048, 0, 0.5f, "Play", "Main", marks);
            Check(ex.Contains("lenNative=200px"), "line native length via scale");
            Check(ex.StartsWith("Look at the screenshot at: C:/x/p.png"), "export header path");

            Debug.Log($"View Probe self-test: {pass} passed, {fail} failed");
        }
    }
}
