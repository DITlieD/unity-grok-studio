using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools.Placement
{
    [McpForUnityTool("adjust_object")]
    public static class AdjustObjectTool
    {
        public class Parameters
        {
            [ToolParameter("Hierarchy path of the object to adjust")]
            public string @object { get; set; }

            [ToolParameter("Operation: snap | depenetrate | face | align")]
            public string op { get; set; }

            [ToolParameter("For op=face: world point to face as {x,y,z} or [x,y,z]", Required = false)]
            public object target { get; set; }

            [ToolParameter("For op=align: surface normal as {x,y,z}; omit to raycast down and sample it", Required = false)]
            public object normal { get; set; }

            [ToolParameter("Fallback ground plane Y for op=snap when no collider is found below", Required = false)]
            public float? ground_y { get; set; }

            [ToolParameter("Max downward ray distance for op=snap (default 5)", Required = false)]
            public float? ground_search { get; set; }

            [ToolParameter("Tolerance in meters (default 0.05)", Required = false)]
            public float? ground_tolerance { get; set; }

            [ToolParameter("For op=depenetrate: broadphase margin for nearby colliders (default 0.02)", Required = false)]
            public float? overlap_margin { get; set; }

            [ToolParameter("For op=depenetrate: iteration cap (default 8)", Required = false)]
            public int? max_iterations { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string objectPath = @params?["object"]?.ToString();
            string op = @params?["op"]?.ToString();
            if (string.IsNullOrEmpty(objectPath)) return new ErrorResponse("adjust_object requires 'object' (hierarchy path)");
            if (string.IsNullOrEmpty(op)) return new ErrorResponse("adjust_object requires 'op' (snap | depenetrate | face | align)");

            var go = PlacementOps.FindByPath(objectPath);
            if (go == null) return new ErrorResponse($"object_not_found: {objectPath}");
            float tol = PlacementParams.GetFloat(@params, "ground_tolerance", 0.05f);

            Undo.IncrementCurrentGroup();
            int group = Undo.GetCurrentGroup();
            Undo.SetCurrentGroupName($"adjust_object:{op}");
            Undo.RecordObject(go.transform, $"adjust_object:{op}");

            object result;
            switch (op)
            {
                case "snap": result = SnapOp(go, @params, tol); break;
                case "depenetrate": result = DepenetrateOp(go, @params); break;
                case "face": result = FaceOp(go, @params); break;
                case "align": result = AlignOp(go, @params); break;
                default: result = new ErrorResponse($"adjust_object: unknown op '{op}' (snap | depenetrate | face | align)"); break;
            }

            Undo.CollapseUndoOperations(group);
            return result;
        }

        static object SnapOp(GameObject go, JObject p, float tol)
        {
            float groundSearch = PlacementParams.GetFloat(p, "ground_search", 5f);
            var gyTok = p?["ground_y"];
            bool hasGroundY = gyTok != null && gyTok.Type != JTokenType.Null;
            float groundY = hasGroundY ? gyTok.Value<float>() : 0f;
            var res = PlacementOps.SnapToGround(go, groundSearch, tol, hasGroundY, groundY, false);
            return new SuccessResponse(
                res.noGround ? "adjust_object snap: no ground found, position unchanged" : "adjust_object snap: done",
                new
                {
                    op = "snap",
                    noGround = res.noGround,
                    clearanceAfter = PlacementParams.NullableClearance(res.clearanceAfter),
                    appliedDeltaY = res.appliedDeltaY,
                    position = PlacementParams.Vec(go.transform.position)
                });
        }

        static object DepenetrateOp(GameObject go, JObject p)
        {
            float margin = PlacementParams.GetFloat(p, "overlap_margin", 0.02f);
            int maxIters = PlacementParams.GetInt(p, "max_iterations", 8);
            int candidateCount = PlacementOps.OverlappingColliders(go, margin).Count;
            var res = PlacementOps.Depenetrate(go, null, maxIters, false, margin);
            return new SuccessResponse(
                res.unresolved ? "adjust_object depenetrate: unresolved after cap" : "adjust_object depenetrate: clear",
                new
                {
                    op = "depenetrate",
                    overlapCandidates = candidateCount,
                    iterations = res.iterations,
                    unresolved = res.unresolved,
                    remainingPairs = res.remainingPairs,
                    position = PlacementParams.Vec(go.transform.position)
                });
        }

        static object FaceOp(GameObject go, JObject p)
        {
            if (!PlacementParams.TryVec3(p?["target"], out var target))
                return new ErrorResponse("adjust_object op=face requires 'target' [x,y,z]");
            PlacementOps.FaceToward(go, target, false);
            return new SuccessResponse("adjust_object face: done", new
            {
                op = "face",
                forward = PlacementParams.Vec(go.transform.forward),
                eulerAngles = PlacementParams.Vec(go.transform.eulerAngles)
            });
        }

        static object AlignOp(GameObject go, JObject p)
        {
            if (!PlacementParams.TryVec3(p?["normal"], out var normal))
            {
                if (!PlacementOps.TryWorldBounds(go, out var b))
                    return new ErrorResponse("adjust_object op=align: object has no bounds and no 'normal' given");
                var origin = PlacementGeometry.BottomCenter(b) + Vector3.up * 0.05f;
                if (!Physics.Raycast(origin, Vector3.down, out var hit, 10f, ~0, QueryTriggerInteraction.Ignore))
                    return new ErrorResponse("adjust_object op=align: no surface below to sample a normal, pass 'normal' explicitly");
                normal = hit.normal;
            }
            PlacementOps.AlignToSurfaceNormal(go, normal, false);
            return new SuccessResponse("adjust_object align: done", new
            {
                op = "align",
                up = PlacementParams.Vec(go.transform.up),
                eulerAngles = PlacementParams.Vec(go.transform.eulerAngles)
            });
        }
    }
}
