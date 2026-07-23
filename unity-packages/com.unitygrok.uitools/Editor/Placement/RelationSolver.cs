using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using Newtonsoft.Json.Linq;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;

namespace UnityGrok.UITools.Placement
{
    public interface IPlacementRelation
    {
        string Name { get; }

        bool ComputeTarget(GameObject subject, IList<GameObject> anchors, JObject args,
            out Vector3 position, out bool groundSnap, out Vector3? faceToward, out string error);
    }

    public static class RelationRegistry
    {
        static Dictionary<string, IPlacementRelation> _map;

        public static IPlacementRelation Resolve(string name)
        {
            if (_map == null) Build();
            if (string.IsNullOrEmpty(name)) return null;
            return _map.TryGetValue(name.ToLowerInvariant(), out var r) ? r : null;
        }

        public static IEnumerable<string> Names()
        {
            if (_map == null) Build();
            return _map.Keys;
        }

        static void Build()
        {
            _map = new Dictionary<string, IPlacementRelation>();
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (asm.IsDynamic) continue;
                Type[] types;
                try { types = asm.GetTypes(); }
                catch (Exception ex) { Debug.LogWarning($"[Placement] assembly {asm.FullName} could not be reflected: {ex.Message}"); continue; }
                foreach (var t in types)
                {
                    if (t.IsInterface || t.IsAbstract) continue;
                    if (!typeof(IPlacementRelation).IsAssignableFrom(t)) continue;
                    if (t.GetConstructor(Type.EmptyTypes) == null) continue;
                    try
                    {
                        var inst = (IPlacementRelation)Activator.CreateInstance(t);
                        if (!string.IsNullOrEmpty(inst.Name)) _map[inst.Name.ToLowerInvariant()] = inst;
                    }
                    catch (Exception ex)
                    {
                        Debug.LogWarning($"[Placement] relation type {t.FullName} could not be instantiated: {ex.Message}");
                    }
                }
            }
        }

        internal static float SupportExtent(Bounds b, Vector3 horizontalDir)
            => Mathf.Abs(horizontalDir.x) * b.extents.x + Mathf.Abs(horizontalDir.z) * b.extents.z;

        internal static float BottomOffset(GameObject go, Bounds worldBounds)
            => go.transform.position.y - worldBounds.min.y;
    }

    public class OnRelation : IPlacementRelation
    {
        public string Name => "on";

        public bool ComputeTarget(GameObject subject, IList<GameObject> anchors, JObject args,
            out Vector3 position, out bool groundSnap, out Vector3? faceToward, out string error)
        {
            position = default; groundSnap = false; faceToward = null; error = null;
            if (anchors == null || anchors.Count < 1 || anchors[0] == null) { error = "on requires an anchor"; return false; }
            if (!PlacementOps.TryWorldBounds(anchors[0], out var ab)) { error = "anchor has no renderer/collider bounds"; return false; }
            if (!PlacementOps.TryWorldBounds(subject, out var sb)) { error = "subject has no renderer/collider bounds"; return false; }
            float bottomOffset = RelationRegistry.BottomOffset(subject, sb);
            position = new Vector3(ab.center.x, ab.max.y + bottomOffset, ab.center.z);
            return true;
        }
    }

    public class BesideRelation : IPlacementRelation
    {
        public string Name => "beside";

        public bool ComputeTarget(GameObject subject, IList<GameObject> anchors, JObject args,
            out Vector3 position, out bool groundSnap, out Vector3? faceToward, out string error)
        {
            position = default; groundSnap = true; faceToward = null; error = null;
            if (anchors == null || anchors.Count < 1 || anchors[0] == null) { error = "beside requires an anchor"; return false; }
            if (!PlacementOps.TryWorldBounds(anchors[0], out var ab)) { error = "anchor has no bounds"; return false; }
            if (!PlacementOps.TryWorldBounds(subject, out var sb)) { error = "subject has no bounds"; return false; }

            Vector3 dir = ParseDirection(args);
            float clearance = args?["clearance"] != null ? args["clearance"].Value<float>() : 0f;
            float offset = RelationRegistry.SupportExtent(ab, dir) + RelationRegistry.SupportExtent(sb, dir) + clearance;
            float bottomOffset = RelationRegistry.BottomOffset(subject, sb);
            position = new Vector3(ab.center.x + dir.x * offset, ab.min.y + bottomOffset, ab.center.z + dir.z * offset);
            return true;
        }

        static Vector3 ParseDirection(JObject args)
        {
            var t = args?["direction"];
            if (t == null || t.Type == JTokenType.Null) return Vector3.right;
            if (t is JArray a && a.Count >= 2)
            {
                var v = new Vector3(a[0].Value<float>(), 0f, a[1].Value<float>());
                return v.sqrMagnitude < 1e-6f ? Vector3.right : v.normalized;
            }
            switch (t.ToString().ToLowerInvariant())
            {
                case "north": case "+z": case "forward": return Vector3.forward;
                case "south": case "-z": case "back": return Vector3.back;
                case "west": case "-x": case "left": return Vector3.left;
                case "east": case "+x": case "right": default: return Vector3.right;
            }
        }
    }

    public class FacingRelation : IPlacementRelation
    {
        public string Name => "facing";

        public bool ComputeTarget(GameObject subject, IList<GameObject> anchors, JObject args,
            out Vector3 position, out bool groundSnap, out Vector3? faceToward, out string error)
        {
            position = default; groundSnap = false; faceToward = null; error = null;
            if (anchors == null || anchors.Count < 1 || anchors[0] == null) { error = "facing requires an anchor"; return false; }
            if (!PlacementOps.TryWorldBounds(anchors[0], out var ab)) { error = "anchor has no bounds"; return false; }
            position = subject.transform.position;
            faceToward = ab.center;
            return true;
        }
    }

    public class BetweenRelation : IPlacementRelation
    {
        public string Name => "between";

        public bool ComputeTarget(GameObject subject, IList<GameObject> anchors, JObject args,
            out Vector3 position, out bool groundSnap, out Vector3? faceToward, out string error)
        {
            position = default; groundSnap = true; faceToward = null; error = null;
            if (anchors == null || anchors.Count < 2 || anchors[0] == null || anchors[1] == null) { error = "between requires two anchors"; return false; }
            if (!PlacementOps.TryWorldBounds(anchors[0], out var a0)) { error = "first anchor has no bounds"; return false; }
            if (!PlacementOps.TryWorldBounds(anchors[1], out var a1)) { error = "second anchor has no bounds"; return false; }
            if (!PlacementOps.TryWorldBounds(subject, out var sb)) { error = "subject has no bounds"; return false; }
            float bottomOffset = RelationRegistry.BottomOffset(subject, sb);
            float y = Mathf.Min(a0.min.y, a1.min.y) + bottomOffset;
            position = new Vector3((a0.center.x + a1.center.x) * 0.5f, y, (a0.center.z + a1.center.z) * 0.5f);
            return true;
        }
    }

    [McpForUnityTool("place_relative")]
    public static class PlaceRelativeTool
    {
        public class Parameters
        {
            [ToolParameter("Hierarchy path of the object to place")]
            public string subject { get; set; }

            [ToolParameter("Relation: on | beside | facing | between")]
            public string relation { get; set; }

            [ToolParameter("Hierarchy path of the anchor object")]
            public string anchor { get; set; }

            [ToolParameter("For relation=between: hierarchy path of the second anchor", Required = false)]
            public string anchor2 { get; set; }

            [ToolParameter("For relation=beside: north|south|east|west or [dx,dz]", Required = false)]
            public object direction { get; set; }

            [ToolParameter("For relation=beside: gap in meters between anchor and subject", Required = false)]
            public float? clearance { get; set; }

            [ToolParameter("Tolerance in meters (default 0.05)", Required = false)]
            public float? ground_tolerance { get; set; }

            [ToolParameter("Broadphase margin for depenetration (default 0.02)", Required = false)]
            public float? overlap_margin { get; set; }

            [ToolParameter("Depenetration iteration cap (default 8)", Required = false)]
            public int? max_iterations { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string subjectPath = @params?["subject"]?.ToString();
            string relationName = @params?["relation"]?.ToString();
            if (string.IsNullOrEmpty(subjectPath)) return new ErrorResponse("place_relative requires 'subject'");
            if (string.IsNullOrEmpty(relationName)) return new ErrorResponse("place_relative requires 'relation' (on | beside | facing | between)");

            var subject = PlacementOps.FindByPath(subjectPath);
            if (subject == null) return new ErrorResponse($"subject_not_found: {subjectPath}");

            var rel = RelationRegistry.Resolve(relationName);
            if (rel == null) return new ErrorResponse($"unknown_relation: {relationName} (have: {string.Join(", ", RelationRegistry.Names())})");

            var anchors = new List<GameObject>();
            var a1 = PlacementOps.FindByPath(@params?["anchor"]?.ToString());
            if (a1 == null) return new ErrorResponse($"anchor_not_found: {@params?["anchor"]}");
            anchors.Add(a1);
            var a2Path = @params?["anchor2"]?.ToString();
            if (!string.IsNullOrEmpty(a2Path))
            {
                var a2 = PlacementOps.FindByPath(a2Path);
                if (a2 == null) return new ErrorResponse($"anchor2_not_found: {a2Path}");
                anchors.Add(a2);
            }

            if (!rel.ComputeTarget(subject, anchors, @params, out var pos, out var groundSnap, out var face, out var relErr))
                return new ErrorResponse($"place_relative:{relationName}: {relErr}");

            float tol = PlacementParams.GetFloat(@params, "ground_tolerance", 0.05f);
            float margin = PlacementParams.GetFloat(@params, "overlap_margin", 0.02f);
            int maxIters = PlacementParams.GetInt(@params, "max_iterations", 8);

            Undo.IncrementCurrentGroup();
            int group = Undo.GetCurrentGroup();
            Undo.SetCurrentGroupName($"place_relative:{relationName}");
            Undo.RecordObject(subject.transform, $"place_relative:{relationName}");

            subject.transform.position = pos;
            if (face.HasValue) PlacementOps.FaceToward(subject, face.Value, false);

            PlacementOps.PipelineResult r;
            try
            {
                r = PlacementOps.RunPipeline(subject, false, subject.transform.position,
                    5f, tol, false, 0f, margin, maxIters, groundSnap);
            }
            catch (Exception ex)
            {
                Undo.CollapseUndoOperations(group);
                return new ErrorResponse($"place_relative_failed: {ex.Message}");
            }
            Undo.CollapseUndoOperations(group);

            return new SuccessResponse(
                $"place_relative {relationName}: grounded={r.grounded} penetrationsRemaining={r.remainingPairs} unresolved={r.unresolved}",
                new
                {
                    placed = subject.name,
                    relation = relationName,
                    grounded = r.grounded,
                    noGround = r.noGround,
                    clearance = PlacementParams.NullableClearance(r.clearance),
                    penetrationsRemaining = r.remainingPairs,
                    unresolved = r.unresolved,
                    position = PlacementParams.Vec(r.finalPosition)
                });
        }
    }
}
