using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UnityGrok.UITools.Placement
{
    public static class SceneValidator
    {
        public const int SchemaVersion = 1;
        public const float DefaultGroundTolerance = 0.05f;
        public const float DefaultGroundSearch = 5f;
        const float RayLift = 0.25f;

        public class Options
        {
            public string filter;
            public List<string> targets;
            public float groundTolerance = DefaultGroundTolerance;
            public float groundSearch = DefaultGroundSearch;
            public bool hasGroundY;
            public float groundY;
        }

        public class ObjectReport
        {
            public string path;
            public int rendererCount;
            public bool hasCollider;
            public bool groundFound;
            public bool grounded;
            public bool floating;
            public bool buried;
            public float? clearance;
            public float[] suggestedFix;
        }

        public class PenetrationPair
        {
            public string a;
            public string b;
            public float[] direction;
            public float depth;
            public string method;
        }

        public class ContainmentPair
        {
            public string outer;
            public string inner;
        }

        public class InvalidEntry
        {
            public string path;
            public string reason;
        }

        public class Report
        {
            public int schemaVersion = SchemaVersion;
            public string scene;
            public int objectCount;
            public List<ObjectReport> objects = new List<ObjectReport>();
            public List<PenetrationPair> penetrationPairs = new List<PenetrationPair>();
            public List<ContainmentPair> containmentPairs = new List<ContainmentPair>();
            public List<InvalidEntry> invalid = new List<InvalidEntry>();
            public object summary;
            public string reportFile;
        }

        class Item
        {
            public string path;
            public Transform root;
            public Bounds bounds;
            public bool hasBounds;
            public int rendererCount;
            public Collider col;
        }

        public static Report Validate(Options opt)
        {
            opt = opt ?? new Options();
            var report = new Report { scene = SceneManager.GetActiveScene().name };
            var items = GatherItems(opt, report);
            report.objectCount = items.Count;
            ClassifyGrounding(items, opt, report);
            DetectPairwiseDefects(items, opt, report);
            report.summary = Summarize(report);
            report.reportFile = WriteOut(report);
            return report;
        }

        static List<Item> GatherItems(Options opt, Report report)
        {
            var renderers = Object.FindObjectsByType<Renderer>();
            var byRoot = new Dictionary<Transform, Item>();
            foreach (var r in renderers)
            {
                if (r == null) continue;
                var root = ResolveItemRoot(r.transform);
                if (!byRoot.TryGetValue(root, out var item))
                {
                    item = new Item { root = root, path = HierarchyPath(root), col = ResolveCollider(root) };
                    byRoot[root] = item;
                }
                item.rendererCount++;
                var b = r.bounds;
                if (!PlacementGeometry.IsValid(b) || (b.size.x == 0f && b.size.y == 0f && b.size.z == 0f)) continue;
                if (!item.hasBounds) { item.bounds = b; item.hasBounds = true; }
                else item.bounds.Encapsulate(b);
            }

            var items = new List<Item>();
            foreach (var it in byRoot.Values)
            {
                if (!MatchesFilter(it.path, it.root.name, opt)) continue;
                if (!it.hasBounds)
                {
                    report.invalid.Add(new InvalidEntry { path = it.path, reason = "no_valid_renderer_bounds" });
                    continue;
                }
                if (it.col != null) it.bounds.Encapsulate(it.col.bounds);
                items.Add(it);
            }
            return items;
        }

        static void ClassifyGrounding(List<Item> items, Options opt, Report report)
        {
            foreach (var it in items)
            {
                var rep = new ObjectReport { path = it.path, rendererCount = it.rendererCount, hasCollider = it.col != null };
                Vector3 bottom = PlacementGeometry.BottomCenter(it.bounds);
                float surfaceY;
                if (TryGround(it, bottom, opt, out surfaceY))
                {
                    float clr = bottom.y - surfaceY;
                    rep.groundFound = true;
                    rep.clearance = clr;
                    rep.grounded = Mathf.Abs(clr) <= opt.groundTolerance;
                    rep.floating = clr > opt.groundTolerance;
                    rep.buried = clr < -opt.groundTolerance;
                    rep.suggestedFix = new[] { 0f, -clr, 0f };
                }
                else
                {
                    rep.groundFound = false;
                    rep.grounded = false;
                    rep.floating = true;
                    rep.clearance = null;
                    rep.suggestedFix = new[] { 0f, 0f, 0f };
                }
                report.objects.Add(rep);
            }
        }

        static void DetectPairwiseDefects(List<Item> items, Options opt, Report report)
        {
            for (int i = 0; i < items.Count; i++)
            {
                for (int j = i + 1; j < items.Count; j++)
                {
                    var a = items[i];
                    var b = items[j];
                    if (!PlacementGeometry.Overlaps(a.bounds, b.bounds)) continue;

                    if (PlacementGeometry.Contains(a.bounds, b.bounds))
                        report.containmentPairs.Add(new ContainmentPair { outer = a.path, inner = b.path });
                    else if (PlacementGeometry.Contains(b.bounds, a.bounds))
                        report.containmentPairs.Add(new ContainmentPair { outer = b.path, inner = a.path });

                    var pp = ComputePair(a, b, opt);
                    if (pp != null) report.penetrationPairs.Add(pp);
                }
            }
        }

        static object Summarize(Report report)
        {
            return new
            {
                grounded = report.objects.Count(o => o.grounded),
                floating = report.objects.Count(o => o.floating),
                buried = report.objects.Count(o => o.buried),
                penetratingPairs = report.penetrationPairs.Count,
                containmentPairs = report.containmentPairs.Count,
                invalid = report.invalid.Count
            };
        }

        static Transform ResolveItemRoot(Transform t)
        {
            var prefabRoot = PrefabUtility.GetOutermostPrefabInstanceRoot(t.gameObject);
            if (prefabRoot != null) return prefabRoot.transform;
            var col = t.GetComponentInParent<Collider>();
            if (col != null) return col.transform;
            return t;
        }

        static Collider ResolveCollider(Transform root)
        {
            var cols = root.GetComponentsInChildren<Collider>();
            foreach (var c in cols)
                if (c.enabled && !c.isTrigger) return c;
            return null;
        }

        static bool TryGround(Item it, Vector3 bottom, Options opt, out float surfaceY)
        {
            surfaceY = 0f;
            var origin = bottom + Vector3.up * RayLift;
            var hits = Physics.RaycastAll(origin, Vector3.down, opt.groundSearch + RayLift, ~0, QueryTriggerInteraction.Ignore);
            float topSurface = float.NegativeInfinity;
            bool found = false;
            foreach (var h in hits)
            {
                if (IsSelf(h.collider, it.root)) continue;
                if (h.point.y > topSurface)
                {
                    topSurface = h.point.y;
                    found = true;
                }
            }
            if (found) { surfaceY = topSurface; return true; }
            if (opt.hasGroundY) { surfaceY = opt.groundY; return true; }
            return false;
        }

        static bool IsSelf(Collider c, Transform root)
        {
            var ct = c.transform;
            return ct == root || ct.IsChildOf(root);
        }

        static PenetrationPair ComputePair(Item a, Item b, Options opt)
        {
            if (a.col != null && b.col != null)
            {
                if (PlacementOps.IsConvexForPenetration(a.col) || PlacementOps.IsConvexForPenetration(b.col))
                {
                    Vector3 dir;
                    float dist;
                    bool ok = Physics.ComputePenetration(
                        a.col, a.col.transform.position, a.col.transform.rotation,
                        b.col, b.col.transform.position, b.col.transform.rotation,
                        out dir, out dist);
                    if (ok && dist > opt.groundTolerance)
                        return new PenetrationPair { a = a.path, b = b.path, direction = new[] { dir.x, dir.y, dir.z }, depth = dist, method = "collider" };
                }
                return null;
            }

            var mtv = PlacementGeometry.MinimumTranslationVector(a.bounds, b.bounds);
            if (mtv != Vector3.zero)
            {
                float mag = mtv.magnitude;
                if (mag > opt.groundTolerance)
                {
                    var n = mtv.normalized;
                    return new PenetrationPair { a = a.path, b = b.path, direction = new[] { n.x, n.y, n.z }, depth = mag, method = "aabb" };
                }
            }
            return null;
        }

        static bool MatchesFilter(string path, string name, Options opt)
        {
            if (opt.targets != null && opt.targets.Count > 0)
                return opt.targets.Any(t => path == t || path.EndsWith("/" + t) || name == t);
            if (string.IsNullOrEmpty(opt.filter)) return true;
            return path.IndexOf(opt.filter, System.StringComparison.OrdinalIgnoreCase) >= 0
                || name.IndexOf(opt.filter, System.StringComparison.OrdinalIgnoreCase) >= 0;
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

        static string WriteOut(Report r)
        {
            var dir = Path.Combine(Directory.GetParent(Application.dataPath).FullName, "UISnapshots");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, "scene.validation.json");
            File.WriteAllText(path, JsonConvert.SerializeObject(r, Formatting.Indented));
            return path;
        }
    }
}
