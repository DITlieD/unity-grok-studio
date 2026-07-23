using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

namespace UnityGrok.UITools
{
    // grab the active view (game or scene, edit or play), freeze it, draw points/arrows/lines/boxes
    // with a note each, then export one clipboard block that points claude at the png + the marks +
    // the unity object under each mark. companion math + self-test live in ViewProbeCore.
    public class ViewProbe : EditorWindow
    {
        const int Cap = 2048;

        Texture2D _frame;
        int _nativeW, _nativeH, _imgW, _imgH;
        float _scale = 1f;
        string _view = "", _mode = "", _camera = "", _pngAbs = "";
        readonly List<Mark> _marks = new List<Mark>();
        List<ElementRect> _els = new List<ElementRect>();

        MarkType _tool = MarkType.Arrow;
        bool _dragging;
        Vector2 _dragStartImg, _dragCurImg;
        Mark _free;
        Vector2 _scroll;
        readonly Stack<List<Mark>> _undo = new Stack<List<Mark>>();
        readonly Stack<List<Mark>> _redo = new Stack<List<Mark>>();

        bool _capturing;
        string _rawAbs, _ts;
        double _capStart;

        [MenuItem("Tools/UI Tools/View Probe")]
        static void Open() => GetWindow<ViewProbe>("View Probe").minSize = new Vector2(420, 360);

        static string ProjectDir => Directory.GetParent(Application.dataPath).FullName;
        static string ProbeDir => Path.Combine(ProjectDir, "ViewProbe");

        void OnGUI()
        {
            HandleShortcuts();
            DrawToolbar();
            if (_frame == null)
            {
                EditorGUILayout.HelpBox(_capturing
                    ? "Grabbing the game view, waiting for the frame to write..."
                    : "Hit Grab Game (play or edit mode) or Grab Scene, then draw on the frozen frame.",
                    MessageType.Info);
                return;
            }
            Rect disp = DrawFrame();
            HandleMouse(disp);
            DrawMarks(disp);
            DrawMarkList();
        }

        void DrawToolbar()
        {
            using (new EditorGUILayout.HorizontalScope(EditorStyles.toolbar))
            {
                if (GUILayout.Button("Grab Game", EditorStyles.toolbarButton, GUILayout.Width(80))) GrabGame();
                if (GUILayout.Button("Grab Scene", EditorStyles.toolbarButton, GUILayout.Width(80))) GrabScene();
                GUILayout.Space(12);
                foreach (MarkType t in Enum.GetValues(typeof(MarkType)))
                {
                    bool on = _tool == t;
                    if (GUILayout.Toggle(on, t.ToString(), EditorStyles.toolbarButton, GUILayout.Width(64)) && !on)
                        _tool = t;
                }
                GUILayout.FlexibleSpace();
                using (new EditorGUI.DisabledScope(_undo.Count == 0))
                    if (GUILayout.Button("Undo", EditorStyles.toolbarButton, GUILayout.Width(50))) Undo();
                using (new EditorGUI.DisabledScope(_redo.Count == 0))
                    if (GUILayout.Button("Redo", EditorStyles.toolbarButton, GUILayout.Width(50))) Redo();
                using (new EditorGUI.DisabledScope(_marks.Count == 0))
                    if (GUILayout.Button("Clear", EditorStyles.toolbarButton, GUILayout.Width(50)))
                        { PushUndo(); _marks.Clear(); }
                using (new EditorGUI.DisabledScope(_frame == null))
                    if (GUILayout.Button("Export + Copy", EditorStyles.toolbarButton, GUILayout.Width(100)))
                        Export();
            }
        }

        Rect DrawFrame()
        {
            float availH = position.height - 220;
            Rect area = GUILayoutUtility.GetRect(position.width, Mathf.Max(120, availH));
            float s = Mathf.Min(area.width / _imgW, area.height / _imgH);
            float w = _imgW * s, h = _imgH * s;
            Rect disp = new Rect(area.x + (area.width - w) * 0.5f, area.y, w, h);
            GUI.DrawTexture(disp, _frame, ScaleMode.StretchToFill);
            return disp;
        }

        void HandleMouse(Rect disp)
        {
            Event e = Event.current;
            if (!disp.Contains(e.mousePosition)) return;
            float s = disp.width / _imgW;
            Vector2 Img(Vector2 m) => new Vector2(
                Mathf.Clamp((m.x - disp.x) / s, 0, _imgW),
                Mathf.Clamp((m.y - disp.y) / s, 0, _imgH));

            if (e.type == EventType.MouseDown && e.button == 0)
            {
                var p = Img(e.mousePosition);
                if (_tool == MarkType.Point) { AddMark(MarkType.Point, new List<Vector2> { p }, p); }
                else if (_tool == MarkType.Freehand) { _free = new Mark { Type = MarkType.Freehand }; _free.Pts.Add(p); _dragging = true; }
                else { _dragging = true; _dragStartImg = p; _dragCurImg = p; }
                e.Use();
            }
            else if (e.type == EventType.MouseDrag && _dragging)
            {
                var p = Img(e.mousePosition);
                if (_tool == MarkType.Freehand) _free.Pts.Add(p);
                else _dragCurImg = p;
                e.Use(); Repaint();
            }
            else if (e.type == EventType.MouseUp && _dragging)
            {
                _dragging = false;
                if (_tool == MarkType.Freehand)
                {
                    if (_free.Pts.Count > 1) { PushUndo(); _free.Target = Resolve(_free.Pts[_free.Pts.Count - 1]); _marks.Add(_free); }
                    _free = null;
                }
                else
                {
                    var pts = new List<Vector2> { _dragStartImg, _dragCurImg };
                    AddMark(_tool, pts, Anchor(_tool, pts));
                }
                e.Use(); Repaint();
            }
        }

        static Vector2 Anchor(MarkType t, List<Vector2> p) => t switch
        {
            MarkType.Arrow => p[1],
            MarkType.Line => (p[0] + p[1]) * 0.5f,
            MarkType.Box => (p[0] + p[1]) * 0.5f,
            _ => p[p.Count - 1],
        };

        void AddMark(MarkType t, List<Vector2> pts, Vector2 anchor)
        {
            PushUndo();
            _marks.Add(new Mark { Type = t, Pts = pts, Target = Resolve(anchor) });
        }

        string Resolve(Vector2 imgPt) => ViewProbeCore.ResolveTopmost(imgPt, _els);

        List<Mark> Snapshot()
        {
            var s = new List<Mark>(_marks.Count);
            foreach (var m in _marks)
                s.Add(new Mark { Type = m.Type, Pts = new List<Vector2>(m.Pts), Note = m.Note, Target = m.Target });
            return s;
        }

        void PushUndo() { _undo.Push(Snapshot()); _redo.Clear(); }

        void Undo()
        {
            if (_undo.Count == 0) return;
            _redo.Push(Snapshot());
            _marks.Clear(); _marks.AddRange(_undo.Pop());
            GUI.FocusControl(null); Repaint();
        }

        void Redo()
        {
            if (_redo.Count == 0) return;
            _undo.Push(Snapshot());
            _marks.Clear(); _marks.AddRange(_redo.Pop());
            GUI.FocusControl(null); Repaint();
        }

        void HandleShortcuts()
        {
            var e = Event.current;
            if (e.type != EventType.KeyDown || !(e.control || e.command)) return;
            if (e.keyCode == KeyCode.Z) { if (e.shift) Redo(); else Undo(); e.Use(); }
            else if (e.keyCode == KeyCode.Y) { Redo(); e.Use(); }
        }

        void DrawMarks(Rect disp)
        {
            float s = disp.width / _imgW;
            Vector2 G(Vector2 p) => new Vector2(disp.x + p.x * s, disp.y + p.y * s);
            for (int i = 0; i < _marks.Count; i++) DrawOne(_marks[i], i + 1, G);
            if (_dragging && _tool != MarkType.Freehand)
                DrawOne(new Mark { Type = _tool, Pts = { _dragStartImg, _dragCurImg } }, 0, G);
            if (_dragging && _free != null) DrawOne(_free, 0, G);
        }

        void DrawOne(Mark m, int num, Func<Vector2, Vector2> G)
        {
            Handles.color = new Color(1f, 0.25f, 0.2f);
            var p = m.Pts;
            switch (m.Type)
            {
                case MarkType.Point: Dot(G(p[0])); break;
                case MarkType.Arrow: Arrow(G(p[0]), G(p[1])); break;
                case MarkType.Line: Handles.DrawAAPolyLine(4, G(p[0]), G(p[1])); Tick(G(p[0])); Tick(G(p[1])); break;
                case MarkType.Box: BoxOutline(G(p[0]), G(p[1])); break;
                default:
                    for (int i = 1; i < p.Count; i++) Handles.DrawAAPolyLine(3, G(p[i - 1]), G(p[i]));
                    break;
            }
            if (num > 0)
            {
                Vector2 at = G(ViewProbeCore.BBoxMin(p)) + new Vector2(-2, -16);
                var st = new GUIStyle(EditorStyles.boldLabel) { normal = { textColor = Color.white } };
                GUI.Label(new Rect(at.x, at.y, 22, 16), num.ToString(), st);
            }
        }

        static void Dot(Vector2 c) => Handles.DrawSolidDisc(c, Vector3.forward, 5f);
        static void Tick(Vector2 c) => Handles.DrawSolidDisc(c, Vector3.forward, 3f);

        static void Arrow(Vector2 a, Vector2 b)
        {
            Handles.DrawAAPolyLine(4, a, b);
            Vector2 d = (b - a).normalized;
            Vector2 n = new Vector2(-d.y, d.x);
            Handles.DrawAAPolyLine(4, b, b - d * 12 + n * 7);
            Handles.DrawAAPolyLine(4, b, b - d * 12 - n * 7);
        }

        static void BoxOutline(Vector2 a, Vector2 b)
        {
            var tl = new Vector2(Mathf.Min(a.x, b.x), Mathf.Min(a.y, b.y));
            var br = new Vector2(Mathf.Max(a.x, b.x), Mathf.Max(a.y, b.y));
            var tr = new Vector2(br.x, tl.y); var bl = new Vector2(tl.x, br.y);
            Handles.DrawAAPolyLine(4, tl, tr, br, bl, tl);
        }

        void DrawMarkList()
        {
            EditorGUILayout.LabelField($"Marks: {_marks.Count}   (tool: {_tool})", EditorStyles.miniBoldLabel);
            _scroll = EditorGUILayout.BeginScrollView(_scroll, GUILayout.Height(120));
            int remove = -1;
            for (int i = 0; i < _marks.Count; i++)
            {
                using (new EditorGUILayout.HorizontalScope())
                {
                    GUILayout.Label($"[{i + 1}] {_marks[i].Type}", GUILayout.Width(90));
                    _marks[i].Note = EditorGUILayout.TextField(_marks[i].Note);
                    if (GUILayout.Button("x", GUILayout.Width(22))) remove = i;
                }
                if (!string.IsNullOrEmpty(_marks[i].Target))
                    EditorGUILayout.LabelField("   -> " + _marks[i].Target, EditorStyles.miniLabel);
            }
            if (remove >= 0) { PushUndo(); _marks.RemoveAt(remove); }
            EditorGUILayout.EndScrollView();
        }

        // ---- capture ----

        void GrabGame()
        {
            if (!Application.isPlaying)
            {
                Debug.LogWarning("View Probe: Grab Game needs Play mode (Unity only captures the game-view framebuffer while playing). Enter Play, or use Grab Scene.");
                return;
            }
            Directory.CreateDirectory(ProbeDir);
            _ts = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            _rawAbs = Path.Combine(ProbeDir, $"probe_{_ts}_raw.png");   // absolute: CaptureScreenshot with a relative path can land in persistentDataPath instead
            if (File.Exists(_rawAbs)) File.Delete(_rawAbs);
            _view = "GameView";
            _mode = "Play";
            _camera = Camera.main != null ? Camera.main.name : "none";
            var gvType = Type.GetType("UnityEditor.GameView,UnityEditor");
            if (gvType != null) GetWindow(gvType);   // game view must be the focused view or ScreenCapture grabs an empty frame
            ScreenCapture.CaptureScreenshot(_rawAbs, 1);
            _capturing = true;
            _capStart = EditorApplication.timeSinceStartup;
            EditorApplication.update += PollCapture;
        }

        void PollCapture()
        {
            if (!_capturing) { EditorApplication.update -= PollCapture; return; }
            if (EditorApplication.timeSinceStartup - _capStart > 8.0)
            {
                _capturing = false; EditorApplication.update -= PollCapture;
                Debug.LogError($"View Probe: game view capture timed out after 8s. Expected {_rawAbs} (exists={File.Exists(_rawAbs)}). Need Play mode with a Game view open.");
                return;
            }
            if (!File.Exists(_rawAbs)) return;
            byte[] bytes;
            try { bytes = File.ReadAllBytes(_rawAbs); } catch { return; }   // still being written
            if (bytes.Length == 0) return;
            var raw = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            if (!raw.LoadImage(bytes)) return;
            _capturing = false; EditorApplication.update -= PollCapture;
            FinishCapture(raw, ComputeUGUIRects);
            try { File.Delete(_rawAbs); } catch { /* leftover raw is harmless */ }
            Focus();   // bring View Probe back in front so the grabbed frame is visible
        }

        void GrabScene()
        {
            var sv = SceneView.lastActiveSceneView;
            if (sv == null || sv.camera == null) { Debug.LogError("View Probe: no active Scene view."); return; }
            var cam = sv.camera;
            int w = Mathf.Max(1, cam.pixelWidth), h = Mathf.Max(1, cam.pixelHeight);
            float up = Mathf.Max(1f, 1920f / Mathf.Max(w, h));
            w = Mathf.RoundToInt(w * up); h = Mathf.RoundToInt(h * up);
            var rt = new RenderTexture(w, h, 24);
            var prevTarget = cam.targetTexture; var prevActive = RenderTexture.active;
            cam.targetTexture = rt; cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGBA32, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0); tex.Apply();
            cam.targetTexture = prevTarget; RenderTexture.active = prevActive; rt.Release();
            _ts = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            _view = "SceneView"; _mode = Application.isPlaying ? "Play" : "Edit"; _camera = "SceneCamera";
            FinishCapture(tex, (_, __, ___) => new List<ElementRect>());
        }

        void FinishCapture(Texture2D raw, Func<int, int, float, List<ElementRect>> rects)
        {
            _nativeW = raw.width; _nativeH = raw.height;
            var fit = ViewProbeCore.FitToCap(_nativeW, _nativeH, Cap);
            _imgW = fit.w; _imgH = fit.h; _scale = fit.scale;
            _frame = _scale < 1f ? Downscale(raw, _imgW, _imgH) : raw;
            if (_frame != raw) DestroyImmediate(raw);
            _els = rects(_nativeW, _nativeH, _scale);
            Directory.CreateDirectory(ProbeDir);
            _pngAbs = Path.Combine(ProbeDir, $"probe_{_ts}.png");
            File.WriteAllBytes(_pngAbs, _frame.EncodeToPNG());
            _marks.Clear();
            _undo.Clear(); _redo.Clear();
            Repaint();
        }

        static Texture2D Downscale(Texture2D src, int w, int h)
        {
            var tmp = RenderTexture.GetTemporary(w, h);
            var prev = RenderTexture.active;
            Graphics.Blit(src, tmp);
            RenderTexture.active = tmp;
            var dst = new Texture2D(w, h, TextureFormat.RGBA32, false);
            dst.ReadPixels(new Rect(0, 0, w, h), 0, 0); dst.Apply();
            RenderTexture.active = prev; RenderTexture.ReleaseTemporary(tmp);
            return dst;
        }

        List<ElementRect> ComputeUGUIRects(int nativeW, int nativeH, float scale)
        {
            var list = new List<ElementRect>();
            var corners = new Vector3[4];
            int order = 0;
            foreach (var canvas in UnityEngine.Object.FindObjectsByType<Canvas>())
            {
                Camera cam = canvas.renderMode == RenderMode.ScreenSpaceOverlay
                    ? null : (canvas.worldCamera != null ? canvas.worldCamera : Camera.main);
                foreach (var rt in canvas.GetComponentsInChildren<RectTransform>(false))
                {
                    if (!rt.TryGetComponent<Graphic>(out var g) || !g.enabled) continue;
                    string path = HierarchyPath(rt.transform);
                    if (ViewProbeCore.IsIgnoredOverlay(path)) continue;   // brightness dim would swallow every hit
                    rt.GetWorldCorners(corners);
                    float minX = float.MaxValue, minY = float.MaxValue, maxX = float.MinValue, maxY = float.MinValue;
                    for (int k = 0; k < 4; k++)
                    {
                        Vector2 sp = cam == null
                            ? new Vector2(corners[k].x, corners[k].y)
                            : (Vector2)RectTransformUtility.WorldToScreenPoint(cam, corners[k]);
                        minX = Mathf.Min(minX, sp.x); maxX = Mathf.Max(maxX, sp.x);
                        minY = Mathf.Min(minY, sp.y); maxY = Mathf.Max(maxY, sp.y);
                    }
                    var img = new Rect(minX * scale, (nativeH - maxY) * scale,
                        (maxX - minX) * scale, (maxY - minY) * scale);
                    list.Add(new ElementRect { Path = path, ImgRect = img, Order = canvas.sortingOrder * 100000 + order++ });
                }
            }
            return list;
        }

        static string HierarchyPath(Transform t)
        {
            string p = t.name;
            while (t.parent != null) { t = t.parent; p = t.name + "/" + p; }
            return p;
        }

        void Export()
        {
            string md = ViewProbeCore.BuildExport(_pngAbs.Replace('\\', '/'), _view,
                _nativeW, _nativeH, _imgW, _imgH, _scale, _mode, _camera, _marks);
            string mdPath = System.IO.Path.Combine(ProbeDir, $"probe_{_ts}.md");
            File.WriteAllText(mdPath, md);
            EditorGUIUtility.systemCopyBuffer = md;
            Debug.Log($"View Probe: exported {mdPath} and copied to clipboard.\n{md}");
        }
    }
}
