using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.UIElements;

namespace UnityGrok.UITools
{
    public static class UISnapshot
    {
        [MenuItem("Tools/UI Tools/Snapshot Active UI Toolkit Documents")]
        public static void SnapshotUIToolkitMenu()
        {
            Debug.Log($"UISnapshot wrote {SnapshotUIToolkit()}");
        }

        [MenuItem("Tools/UI Tools/Snapshot Active uGUI Canvases")]
        public static void SnapshotUGUIMenu()
        {
            Debug.Log($"UISnapshot wrote {SnapshotUGUI()}");
        }

        public static string SnapshotUIToolkit()
        {
            var docs = Object.FindObjectsByType<UIDocument>();
            var sb = new StringBuilder();
            sb.Append("{\"system\":\"uitoolkit\",\"documents\":[");
            for (int i = 0; i < docs.Length; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append("{\"name\":").Append(Str(docs[i].name)).Append(",\"tree\":");
                DumpVisualElement(docs[i].rootVisualElement, sb);
                sb.Append('}');
            }
            sb.Append("]}");
            return WriteOut("uitoolkit", sb.ToString());
        }

        public static string SnapshotUGUI()
        {
            var canvases = Object.FindObjectsByType<Canvas>();
            var sb = new StringBuilder();
            sb.Append("{\"system\":\"ugui\",\"canvases\":[");
            for (int i = 0; i < canvases.Length; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append("{\"name\":").Append(Str(canvases[i].name));
                if (canvases[i].TryGetComponent<CanvasScaler>(out var scaler))
                {
                    sb.Append(",\"scaler\":{\"mode\":").Append(Str(scaler.uiScaleMode.ToString()))
                      .Append(",\"referenceResolution\":{\"x\":").Append(F(scaler.referenceResolution.x))
                      .Append(",\"y\":").Append(F(scaler.referenceResolution.y)).Append('}')
                      .Append(",\"matchWidthOrHeight\":").Append(F(scaler.matchWidthOrHeight)).Append('}');
                }
                sb.Append(",\"tree\":");
                DumpRect(canvases[i].transform as RectTransform, sb);
                sb.Append('}');
            }
            sb.Append("]}");
            return WriteOut("ugui", sb.ToString());
        }

        static void DumpVisualElement(VisualElement ve, StringBuilder sb)
        {
            if (ve == null) { sb.Append("null"); return; }
            var b = ve.worldBound;
            sb.Append("{\"name\":").Append(Str(ve.name))
              .Append(",\"type\":").Append(Str(ve.GetType().Name))
              .Append(",\"classes\":[");
            bool first = true;
            foreach (var c in ve.GetClasses())
            {
                if (!first) sb.Append(',');
                sb.Append(Str(c));
                first = false;
            }
            sb.Append("],\"rect\":{\"x\":").Append(F(b.x)).Append(",\"y\":").Append(F(b.y))
              .Append(",\"w\":").Append(F(b.width)).Append(",\"h\":").Append(F(b.height)).Append('}')
              .Append(",\"display\":").Append(Str(ve.resolvedStyle.display.ToString()))
              .Append(",\"flexDirection\":").Append(Str(ve.resolvedStyle.flexDirection.ToString()))
              .Append(",\"children\":[");
            for (int i = 0; i < ve.childCount; i++)
            {
                if (i > 0) sb.Append(',');
                DumpVisualElement(ve[i], sb);
            }
            sb.Append("]}");
        }

        static void DumpRect(RectTransform rt, StringBuilder sb)
        {
            if (rt == null) { sb.Append("null"); return; }
            var corners = new Vector3[4];
            rt.GetWorldCorners(corners);
            sb.Append("{\"name\":").Append(Str(rt.name))
              .Append(",\"anchorMin\":{\"x\":").Append(F(rt.anchorMin.x)).Append(",\"y\":").Append(F(rt.anchorMin.y)).Append('}')
              .Append(",\"anchorMax\":{\"x\":").Append(F(rt.anchorMax.x)).Append(",\"y\":").Append(F(rt.anchorMax.y)).Append('}')
              .Append(",\"pivot\":{\"x\":").Append(F(rt.pivot.x)).Append(",\"y\":").Append(F(rt.pivot.y)).Append('}')
              .Append(",\"anchoredPosition\":{\"x\":").Append(F(rt.anchoredPosition.x)).Append(",\"y\":").Append(F(rt.anchoredPosition.y)).Append('}')
              .Append(",\"sizeDelta\":{\"x\":").Append(F(rt.sizeDelta.x)).Append(",\"y\":").Append(F(rt.sizeDelta.y)).Append('}')
              .Append(",\"worldCorners\":[");
            for (int i = 0; i < 4; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append("{\"x\":").Append(F(corners[i].x)).Append(",\"y\":").Append(F(corners[i].y)).Append('}');
            }
            sb.Append("],\"children\":[");
            bool first = true;
            for (int i = 0; i < rt.childCount; i++)
            {
                var c = rt.GetChild(i) as RectTransform;
                if (c == null) continue;
                if (!first) sb.Append(',');
                DumpRect(c, sb);
                first = false;
            }
            sb.Append("]}");
        }

        static string F(float v) => v.ToString("0.##", CultureInfo.InvariantCulture);

        static string Str(string s)
        {
            if (s == null) return "\"\"";
            var sb = new StringBuilder("\"");
            foreach (char c in s)
            {
                if (c == '"' || c == '\\') sb.Append('\\').Append(c);
                else if (c == '\n') sb.Append("\\n");
                else if (c == '\r') sb.Append("\\r");
                else sb.Append(c);
            }
            sb.Append('"');
            return sb.ToString();
        }

        static string WriteOut(string tag, string json)
        {
            var dir = Path.Combine(Directory.GetParent(Application.dataPath).FullName, "UISnapshots");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, $"{tag}.layout.json");
            File.WriteAllText(path, json);
            return path;
        }
    }
}
