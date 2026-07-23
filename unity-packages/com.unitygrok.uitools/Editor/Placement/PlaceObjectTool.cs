using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools.Placement
{
    internal static class PlacementParams
    {
        public static float GetFloat(JObject p, string key, float fallback)
        {
            var t = p?[key];
            return (t == null || t.Type == JTokenType.Null) ? fallback : t.Value<float>();
        }

        public static int GetInt(JObject p, string key, int fallback)
        {
            var t = p?[key];
            return (t == null || t.Type == JTokenType.Null) ? fallback : t.Value<int>();
        }

        public static bool TryVec3(JToken t, out Vector3 v)
        {
            v = Vector3.zero;
            if (t == null || t.Type == JTokenType.Null) return false;
            if (t is JArray a && a.Count == 3)
            {
                v = new Vector3(a[0].Value<float>(), a[1].Value<float>(), a[2].Value<float>());
                return true;
            }
            if (t is JObject o && o["x"] != null && o["y"] != null && o["z"] != null)
            {
                v = new Vector3(o["x"].Value<float>(), o["y"].Value<float>(), o["z"].Value<float>());
                return true;
            }
            return false;
        }

        public static object Vec(Vector3 v) => new { x = v.x, y = v.y, z = v.z };

        public static float? NullableClearance(float c) => float.IsNaN(c) ? (float?)null : c;
    }

    [McpForUnityTool("place_object")]
    public static class PlaceObjectTool
    {
        public class Parameters
        {
            [ToolParameter("Prefab asset path (Assets/...) to instantiate; supply this OR 'object'", Required = false)]
            public string prefab { get; set; }

            [ToolParameter("Hierarchy path of an existing scene object to move; supply this OR 'prefab'", Required = false)]
            public string @object { get; set; }

            [ToolParameter("Rough target position as {x,y,z} or [x,y,z]; snapped + depenetrated from here", Required = false)]
            public object target { get; set; }

            [ToolParameter("Fallback ground plane Y used when no collider is found below the object", Required = false)]
            public float? ground_y { get; set; }

            [ToolParameter("Max downward ray distance when searching for ground (default 5)", Required = false)]
            public float? ground_search { get; set; }

            [ToolParameter("Grounded + penetration tolerance in meters (default 0.05)", Required = false)]
            public float? ground_tolerance { get; set; }

            [ToolParameter("Broadphase margin for gathering nearby colliders to depenetrate from (default 0.02)", Required = false)]
            public float? overlap_margin { get; set; }

            [ToolParameter("Depenetration iteration cap (default 8)", Required = false)]
            public int? max_iterations { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string prefabPath = @params?["prefab"]?.ToString();
            string objectPath = @params?["object"]?.ToString();
            bool hasTarget = PlacementParams.TryVec3(@params?["target"], out Vector3 target);

            float groundSearch = PlacementParams.GetFloat(@params, "ground_search", 5f);
            float tol = PlacementParams.GetFloat(@params, "ground_tolerance", 0.05f);
            var gyTok = @params?["ground_y"];
            bool hasGroundY = gyTok != null && gyTok.Type != JTokenType.Null;
            float groundY = hasGroundY ? gyTok.Value<float>() : 0f;
            float margin = PlacementParams.GetFloat(@params, "overlap_margin", 0.02f);
            int maxIters = PlacementParams.GetInt(@params, "max_iterations", 8);

            GameObject go;
            bool created = false;
            Undo.IncrementCurrentGroup();
            int group = Undo.GetCurrentGroup();
            Undo.SetCurrentGroupName("place_object");

            if (!string.IsNullOrEmpty(prefabPath))
            {
                var asset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (asset == null) return new ErrorResponse($"prefab_not_found: {prefabPath}");
                go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
                if (go == null) return new ErrorResponse($"instantiate_failed: {prefabPath}");
                Undo.RegisterCreatedObjectUndo(go, "place_object");
                created = true;
            }
            else if (!string.IsNullOrEmpty(objectPath))
            {
                go = PlacementOps.FindByPath(objectPath);
                if (go == null) return new ErrorResponse($"object_not_found: {objectPath}");
                Undo.RecordObject(go.transform, "place_object");
            }
            else
            {
                return new ErrorResponse("place_object requires 'prefab' (asset path) or 'object' (hierarchy path)");
            }

            PlacementOps.PipelineResult r;
            try
            {
                r = PlacementOps.RunPipeline(go, hasTarget, hasTarget ? target : go.transform.position,
                    groundSearch, tol, hasGroundY, groundY, margin, maxIters);
            }
            catch (System.Exception ex)
            {
                Undo.CollapseUndoOperations(group);
                return new ErrorResponse($"place_object_failed: {ex.Message}");
            }
            Undo.CollapseUndoOperations(group);

            string msg = r.grounded && !r.unresolved
                ? $"place_object: grounded, {r.remainingPairs} penetrations"
                : $"place_object: grounded={r.grounded} unresolved={r.unresolved} penetrationsRemaining={r.remainingPairs} noGround={r.noGround}";

            return new SuccessResponse(msg, new
            {
                placed = go.name,
                created,
                grounded = r.grounded,
                noGround = r.noGround,
                clearance = PlacementParams.NullableClearance(r.clearance),
                penetrationsRemaining = r.remainingPairs,
                unresolved = r.unresolved,
                overlapCandidates = r.overlapCandidates,
                position = PlacementParams.Vec(r.finalPosition)
            });
        }
    }
}
