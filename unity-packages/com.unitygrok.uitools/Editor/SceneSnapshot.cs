using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools
{
    public static class SceneSnapshot
    {
        const float MinPixelSize = 2f;

        [MenuItem("Tools/UnityGrok/Snapshot Scene Geometry")]
        public static void SnapshotSceneMenu()
        {
            Debug.Log($"SceneSnapshot wrote {SnapshotScene()}");
        }

        public static string SnapshotScene(Camera cam = null, float minPixelSize = MinPixelSize)
        {
            cam = cam != null ? cam : ResolveCamera();
            var sb = new StringBuilder();
            sb.Append("{\"system\":\"scene\",\"pxOrigin\":\"top-left\"");
            if (cam == null)
            {
                sb.Append(",\"camera\":null,\"objects\":[]}");
                return WriteOut("scene", sb.ToString());
            }

            var planes = GeometryUtility.CalculateFrustumPlanes(cam);
            sb.Append(",\"camera\":{\"name\":").Append(Str(cam.name))
              .Append(",\"position\":").Append(V3(cam.transform.position))
              .Append(",\"eulerAngles\":").Append(V3(cam.transform.eulerAngles))
              .Append(",\"orthographic\":").Append(cam.orthographic ? "true" : "false")
              .Append(",\"orthoSize\":").Append(F(cam.orthographicSize))
              .Append(",\"fov\":").Append(F(cam.fieldOfView))
              .Append(",\"pixelWidth\":").Append(cam.pixelWidth)
              .Append(",\"pixelHeight\":").Append(cam.pixelHeight).Append('}');

            sb.Append(",\"objects\":[");
            var renderers = Object.FindObjectsByType<Renderer>();
            bool first = true;
            for (int i = 0; i < renderers.Length; i++)
            {
                var r = renderers[i];
                if (r == null || !r.enabled || !r.gameObject.activeInHierarchy) continue;
                var b = r.bounds;
                bool onScreen = GeometryUtility.TestPlanesAABB(planes, b);
                var px = ProjectBounds(cam, b);
                if (onScreen && px != null && (px[2] < minPixelSize || px[3] < minPixelSize)) continue;

                if (!first) sb.Append(',');
                first = false;
                sb.Append("{\"name\":").Append(Str(r.name))
                  .Append(",\"path\":").Append(Str(HierarchyPath(r.transform)))
                  .Append(",\"rendererType\":").Append(Str(r.GetType().Name))
                  .Append(",\"worldPos\":").Append(V3(r.transform.position))
                  .Append(",\"boundsCenter\":").Append(V3(b.center))
                  .Append(",\"boundsExtents\":").Append(V3(b.extents))
                  .Append(",\"onScreen\":").Append(onScreen ? "true" : "false")
                  .Append(",\"distance\":").Append(F(Vector3.Distance(cam.transform.position, b.center)));
                if (px != null)
                {
                    sb.Append(",\"pxRect\":{\"x\":").Append(F(px[0])).Append(",\"y\":").Append(F(px[1]))
                      .Append(",\"w\":").Append(F(px[2])).Append(",\"h\":").Append(F(px[3])).Append('}');
                }
                else
                {
                    sb.Append(",\"pxRect\":null");
                }
                sb.Append('}');
            }
            sb.Append("]}");
            return WriteOut("scene", sb.ToString());
        }

        static Camera ResolveCamera()
        {
            var cam = Camera.main;
            if (cam != null) return cam;
            var all = Object.FindObjectsByType<Camera>();
            foreach (var c in all)
            {
                if (c.enabled && c.gameObject.activeInHierarchy) return c;
            }
            return all.Length > 0 ? all[0] : null;
        }

        static float[] ProjectBounds(Camera cam, Bounds b)
        {
            var c = b.center;
            var e = b.extents;
            float minX = float.MaxValue, minY = float.MaxValue;
            float maxX = float.MinValue, maxY = float.MinValue;
            int inFront = 0;
            for (int i = 0; i < 8; i++)
            {
                var corner = new Vector3(
                    c.x + ((i & 1) == 0 ? -e.x : e.x),
                    c.y + ((i & 2) == 0 ? -e.y : e.y),
                    c.z + ((i & 4) == 0 ? -e.z : e.z));
                var sp = cam.WorldToScreenPoint(corner);
                if (sp.z <= 0f) continue;
                inFront++;
                if (sp.x < minX) minX = sp.x;
                if (sp.x > maxX) maxX = sp.x;
                if (sp.y < minY) minY = sp.y;
                if (sp.y > maxY) maxY = sp.y;
            }
            if (inFront == 0) return null;
            float topLeftY = cam.pixelHeight - maxY;
            return new[] { minX, topLeftY, maxX - minX, maxY - minY };
        }

        static string HierarchyPath(Transform t)
        {
            var sb = new StringBuilder(t.name);
            var p = t.parent;
            while (p != null)
            {
                sb.Insert(0, '/').Insert(0, p.name);
                p = p.parent;
            }
            return sb.ToString();
        }

        static string V3(Vector3 v) =>
            $"{{\"x\":{F(v.x)},\"y\":{F(v.y)},\"z\":{F(v.z)}}}";

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
