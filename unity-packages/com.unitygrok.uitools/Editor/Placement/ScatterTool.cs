using System;
using System.Collections.Generic;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools.Placement
{
    public class ScatterOptions
    {
        public float groundSearch = 5f;
        public float tolerance = 0.05f;
        public float overlapMargin = 0.02f;
        public float slopeLimit = 30f;
        public int maxIterations = 8;
        public int attemptsPerInstance = 8;
    }

    public struct ScatterRegion
    {
        public bool isBox;
        public Vector3 center;
        public Vector3 size;
        public float radius;

        public static ScatterRegion Box(Vector3 center, Vector3 size)
            => new ScatterRegion { isBox = true, center = center, size = size };

        public static ScatterRegion Radius(Vector3 center, float radius)
            => new ScatterRegion { isBox = false, center = center, radius = radius };

        public Vector3 Sample(System.Random rng)
        {
            if (isBox)
                return new Vector3(
                    center.x + ((float)rng.NextDouble() - 0.5f) * size.x,
                    center.y,
                    center.z + ((float)rng.NextDouble() - 0.5f) * size.z);

            double ang = rng.NextDouble() * Math.PI * 2.0;
            double rr = Math.Sqrt(rng.NextDouble()) * radius;
            return new Vector3(center.x + (float)(Math.Cos(ang) * rr), center.y, center.z + (float)(Math.Sin(ang) * rr));
        }

        public bool ContainsXZ(Vector3 p)
        {
            if (isBox)
                return Mathf.Abs(p.x - center.x) <= size.x * 0.5f + 0.01f
                    && Mathf.Abs(p.z - center.z) <= size.z * 0.5f + 0.01f;
            float dx = p.x - center.x, dz = p.z - center.z;
            float r = radius + 0.01f;
            return dx * dx + dz * dz <= r * r;
        }
    }

    public static class ScatterEngine
    {
        public struct Instance
        {
            public GameObject go;
            public bool grounded;
            public Vector3 position;
        }

        public class Result
        {
            public List<Instance> placed = new List<Instance>();
            public int rejected;
        }

        public static Result Scatter(Func<int, GameObject> spawn, ScatterRegion region, int count, int seed, ScatterOptions opt)
        {
            opt = opt ?? new ScatterOptions();
            var rng = new System.Random(seed);
            var result = new Result();

            for (int i = 0; i < count; i++)
            {
                bool kept = false;
                for (int a = 0; a < opt.attemptsPerInstance && !kept; a++)
                {
                    var pt = region.Sample(rng);
                    var go = spawn(i);
                    if (go == null) break;
                    go.transform.position = pt;
                    Physics.SyncTransforms();

                    var pipe = PlacementOps.RunPipeline(go, true, pt,
                        opt.groundSearch, opt.tolerance, false, 0f, opt.overlapMargin, opt.maxIterations);

                    bool inRegion = region.ContainsXZ(go.transform.position);
                    bool slopeOk = SlopeOk(go, opt);

                    if (pipe.grounded && !pipe.unresolved && inRegion && slopeOk)
                    {
                        result.placed.Add(new Instance { go = go, grounded = true, position = go.transform.position });
                        kept = true;
                    }
                    else
                    {
                        UnityEngine.Object.DestroyImmediate(go);
                    }
                }
                if (!kept) result.rejected++;
            }
            return result;
        }

        static bool SlopeOk(GameObject go, ScatterOptions opt)
        {
            if (!PlacementOps.TryWorldBounds(go, out var b)) return true;
            var origin = new Vector3(b.center.x, b.min.y + 0.05f, b.center.z);
            var hits = Physics.RaycastAll(origin, Vector3.down, opt.groundSearch + 0.1f, ~0, QueryTriggerInteraction.Ignore);
            float top = float.NegativeInfinity;
            Vector3 normal = Vector3.up;
            bool found = false;
            foreach (var h in hits)
            {
                var ct = h.collider.transform;
                if (ct == go.transform || ct.IsChildOf(go.transform)) continue;
                if (h.point.y > top) { top = h.point.y; normal = h.normal; found = true; }
            }
            if (!found) return true;
            return Vector3.Angle(normal, Vector3.up) <= opt.slopeLimit;
        }
    }

    [McpForUnityTool("scatter_objects")]
    public static class ScatterTool
    {
        public class Parameters
        {
            [ToolParameter("Array of prefab asset paths (Assets/...) to draw instances from")]
            public string[] prefabs { get; set; }

            [ToolParameter("Region kind: box | radius (default box)", Required = false)]
            public string region { get; set; }

            [ToolParameter("Region center as {x,y,z} or [x,y,z]; ground level is fine, drop_height is added", Required = false)]
            public object center { get; set; }

            [ToolParameter("Anchor hierarchy path to center the region on (overrides 'center')", Required = false)]
            public string anchor { get; set; }

            [ToolParameter("For region=box: extent as {x,y,z} or [x,y,z] (y ignored)", Required = false)]
            public object size { get; set; }

            [ToolParameter("For region=radius: radius in meters", Required = false)]
            public float? radius { get; set; }

            [ToolParameter("Number of instances to place")]
            public int count { get; set; }

            [ToolParameter("RNG seed; identical seed + scene gives identical layout")]
            public int seed { get; set; }

            [ToolParameter("Drop height above the region center to spawn from (default 20)", Required = false)]
            public float? drop_height { get; set; }

            [ToolParameter("Max ground slope in degrees before an instance is rejected (default 30)", Required = false)]
            public float? slope_limit { get; set; }

            [ToolParameter("Tolerance in meters (default 0.05)", Required = false)]
            public float? ground_tolerance { get; set; }

            [ToolParameter("Broadphase margin for depenetration (default 0.02)", Required = false)]
            public float? overlap_margin { get; set; }

            [ToolParameter("Depenetration iteration cap per instance (default 8)", Required = false)]
            public int? max_iterations { get; set; }

            [ToolParameter("Placement attempts per instance before it is counted rejected (default 8)", Required = false)]
            public int? attempts { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            var prefabsTok = @params?["prefabs"] as JArray;
            if (prefabsTok == null || prefabsTok.Count == 0)
                return new ErrorResponse("scatter_objects requires 'prefabs' (array of asset paths)");

            var assets = new List<GameObject>();
            foreach (var p in prefabsTok)
            {
                var a = AssetDatabase.LoadAssetAtPath<GameObject>(p.ToString());
                if (a != null) assets.Add(a);
            }
            if (assets.Count == 0) return new ErrorResponse("scatter_objects: no valid prefab assets resolved from 'prefabs'");

            int count = PlacementParams.GetInt(@params, "count", 0);
            if (count <= 0) return new ErrorResponse("scatter_objects requires 'count' > 0");
            int seed = PlacementParams.GetInt(@params, "seed", 0);
            float dropHeight = PlacementParams.GetFloat(@params, "drop_height", 20f);

            Vector3 center;
            var anchorPath = @params?["anchor"]?.ToString();
            if (!string.IsNullOrEmpty(anchorPath))
            {
                var anc = PlacementOps.FindByPath(anchorPath);
                if (anc == null) return new ErrorResponse($"anchor_not_found: {anchorPath}");
                center = anc.transform.position;
            }
            else if (!PlacementParams.TryVec3(@params?["center"], out center))
            {
                return new ErrorResponse("scatter_objects requires 'center' [x,y,z] or 'anchor'");
            }
            center.y += dropHeight;

            string regionType = @params?["region"]?.ToString() ?? "box";
            ScatterRegion region;
            if (regionType == "radius")
            {
                float radius = PlacementParams.GetFloat(@params, "radius", 5f);
                region = ScatterRegion.Radius(center, radius);
            }
            else
            {
                if (!PlacementParams.TryVec3(@params?["size"], out var size)) size = new Vector3(10f, 0f, 10f);
                region = ScatterRegion.Box(center, size);
            }

            var opt = new ScatterOptions
            {
                groundSearch = dropHeight + 10f,
                tolerance = PlacementParams.GetFloat(@params, "ground_tolerance", 0.05f),
                overlapMargin = PlacementParams.GetFloat(@params, "overlap_margin", 0.02f),
                slopeLimit = PlacementParams.GetFloat(@params, "slope_limit", 30f),
                maxIterations = PlacementParams.GetInt(@params, "max_iterations", 8),
                attemptsPerInstance = PlacementParams.GetInt(@params, "attempts", 8)
            };

            var pickRng = new System.Random(seed ^ 0x2545F491);
            Func<int, GameObject> spawn = i => (GameObject)PrefabUtility.InstantiatePrefab(assets[pickRng.Next(assets.Count)]);

            Undo.IncrementCurrentGroup();
            int group = Undo.GetCurrentGroup();
            Undo.SetCurrentGroupName("scatter_objects");

            ScatterEngine.Result result;
            try
            {
                result = ScatterEngine.Scatter(spawn, region, count, seed, opt);
            }
            catch (Exception ex)
            {
                Undo.CollapseUndoOperations(group);
                return new ErrorResponse($"scatter_objects_failed: {ex.Message}");
            }

            foreach (var inst in result.placed)
                Undo.RegisterCreatedObjectUndo(inst.go, "scatter_objects");
            Undo.CollapseUndoOperations(group);

            var instances = new List<object>();
            foreach (var inst in result.placed)
                instances.Add(new { path = inst.go.name, position = PlacementParams.Vec(inst.position) });

            return new SuccessResponse(
                $"scatter_objects: placed {result.placed.Count}/{count}, rejected {result.rejected}",
                new { placed = result.placed.Count, requested = count, rejected = result.rejected, instances });
        }
    }
}
