using System.IO;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace UnityGrok.UITools.Anim
{
    [McpForUnityTool("anim_snapshot")]
    public static class AnimSnapshotTool
    {
        public class Parameters
        {
            [ToolParameter("AnimatorController asset path (Assets/...); supply this OR 'object'", Required = false)]
            public string controller { get; set; }

            [ToolParameter("Hierarchy path (or leaf name) of a scene GameObject carrying an Animator; supply this OR 'controller'", Required = false)]
            public string @object { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string controllerPath = @params?["controller"]?.ToString();
            string objectPath = @params?["object"]?.ToString();

            string outFile;
            string label;
            try
            {
                if (!string.IsNullOrEmpty(controllerPath))
                {
                    var ac = AssetDatabase.LoadAssetAtPath<AnimatorController>(controllerPath);
                    if (ac == null) return new ErrorResponse($"controller_not_found: {controllerPath}");
                    outFile = AnimGraphSnapshot.SnapshotController(ac, controllerPath);
                    label = ac.name;
                }
                else if (!string.IsNullOrEmpty(objectPath))
                {
                    var go = FindByPath(objectPath);
                    if (go == null) return new ErrorResponse($"object_not_found: {objectPath}");
                    var an = go.GetComponentInChildren<Animator>();
                    if (an == null) return new ErrorResponse($"no_animator_on: {objectPath}");
                    outFile = AnimGraphSnapshot.SnapshotAnimator(an);
                    if (outFile == null) return new ErrorResponse($"animator_has_no_controller: {objectPath}");
                    label = an.name;
                }
                else
                {
                    return new ErrorResponse("anim_snapshot requires 'controller' (asset path) or 'object' (hierarchy path)");
                }
            }
            catch (System.Exception ex)
            {
                return new ErrorResponse($"anim_snapshot_failed: {ex.Message}");
            }

            string graph = File.ReadAllText(outFile);
            JObject parsed = JObject.Parse(graph);
            int layerCount = (parsed["layers"] as JArray)?.Count ?? 0;
            int paramCount = (parsed["parameters"] as JArray)?.Count ?? 0;

            return new SuccessResponse(
                $"anim_snapshot: {label} dumped, {layerCount} layers, {paramCount} params -> {outFile}",
                new { graphFile = outFile, name = label, layerCount, paramCount, graph = parsed });
        }

        static GameObject FindByPath(string path)
        {
            var direct = GameObject.Find(path);
            if (direct != null) return direct;
            var all = Object.FindObjectsByType<GameObject>();
            foreach (var g in all)
            {
                if (g.name == path) return g;
                if (Full(g.transform).EndsWith(path)) return g;
            }
            return null;
        }

        static string Full(Transform t)
        {
            var s = t.name;
            var p = t.parent;
            while (p != null) { s = p.name + "/" + s; p = p.parent; }
            return s;
        }
    }
}
