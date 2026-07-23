using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools.Anim
{
    [McpForUnityTool("anim_filmstrip")]
    public static class AnimFilmstripTool
    {
        public class Parameters
        {
            [ToolParameter("Asset path of the clip: an .anim, or an .fbx/.controller containing the clip", Required = true)]
            public string clip { get; set; }

            [ToolParameter("Clip name when the asset path holds several clips (fbx/controller)", Required = false)]
            public string clip_name { get; set; }

            [ToolParameter("Hierarchy path of the scene GameObject to pose; supply this OR 'prefab'", Required = false)]
            public string model { get; set; }

            [ToolParameter("Prefab asset path to instantiate, sample, then destroy; supply this OR 'model'", Required = false)]
            public string prefab { get; set; }

            [ToolParameter("Hierarchy path of the camera to render from (default Camera.main or first camera)", Required = false)]
            public string camera { get; set; }

            [ToolParameter("Number of samples across the clip (default 6)", Required = false)]
            public int? samples { get; set; }

            [ToolParameter("Per-tile pixel size (default 256)", Required = false)]
            public int? tile { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string clipPath = @params?["clip"]?.ToString();
            string clipName = @params?["clip_name"]?.ToString();
            string modelPath = @params?["model"]?.ToString();
            string prefabPath = @params?["prefab"]?.ToString();
            string cameraPath = @params?["camera"]?.ToString();
            int samples = @params?["samples"] != null && @params["samples"].Type != JTokenType.Null ? @params["samples"].Value<int>() : 6;
            int tile = @params?["tile"] != null && @params["tile"].Type != JTokenType.Null ? @params["tile"].Value<int>() : 256;

            if (string.IsNullOrEmpty(clipPath)) return new ErrorResponse("anim_filmstrip requires 'clip' (asset path)");
            var clip = LoadClip(clipPath, clipName);
            if (clip == null) return new ErrorResponse($"clip_not_found: {clipPath} name={clipName}");

            var cam = ResolveCamera(cameraPath);
            if (cam == null) return new ErrorResponse("no_camera_available");

            GameObject model;
            bool temp = false;
            if (!string.IsNullOrEmpty(prefabPath))
            {
                var asset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (asset == null) return new ErrorResponse($"prefab_not_found: {prefabPath}");
                model = (GameObject)PrefabUtility.InstantiatePrefab(asset);
                temp = true;
            }
            else if (!string.IsNullOrEmpty(modelPath))
            {
                model = FindByPath(modelPath);
                if (model == null) return new ErrorResponse($"model_not_found: {modelPath}");
            }
            else
            {
                return new ErrorResponse("anim_filmstrip requires 'model' (scene path) or 'prefab' (asset path)");
            }

            AnimClipFilmstrip.Result r;
            try
            {
                r = AnimClipFilmstrip.Capture(clip, model, cam, samples, tile, tile);
            }
            catch (System.Exception ex)
            {
                if (temp && model != null) Object.DestroyImmediate(model);
                return new ErrorResponse($"anim_filmstrip_failed: {ex.Message}");
            }
            if (temp && model != null) Object.DestroyImmediate(model);

            string note = r.poseSpreadMeters < 0.001f
                ? "WARNING pose did not move across samples (clip may not retarget to this model)"
                : "pose varied across samples";
            return new SuccessResponse(
                $"anim_filmstrip: {clip.name} x{r.samples} spread={r.poseSpreadMeters:0.###}m ({note}) -> {r.pngPath}",
                new { contactSheet = r.pngPath, poseJson = r.jsonPath, samples = r.samples, poseSpreadMeters = r.poseSpreadMeters });
        }

        static AnimationClip LoadClip(string path, string name)
        {
            var direct = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
            if (direct != null && (string.IsNullOrEmpty(name) || direct.name == name)) return direct;
            var all = AssetDatabase.LoadAllAssetsAtPath(path);
            AnimationClip first = null;
            foreach (var o in all)
            {
                if (o is AnimationClip c && !c.name.StartsWith("__preview__"))
                {
                    if (!string.IsNullOrEmpty(name) && c.name == name) return c;
                    if (first == null) first = c;
                }
            }
            return string.IsNullOrEmpty(name) ? (direct ?? first) : null;
        }

        static Camera ResolveCamera(string path)
        {
            if (!string.IsNullOrEmpty(path))
            {
                var go = FindByPath(path);
                if (go != null)
                {
                    var c = go.GetComponent<Camera>() ?? go.GetComponentInChildren<Camera>();
                    if (c != null) return c;
                }
            }
            if (Camera.main != null) return Camera.main;
            var all = Object.FindObjectsByType<Camera>();
            foreach (var c in all) if (c.enabled && c.gameObject.activeInHierarchy) return c;
            return all.Length > 0 ? all[0] : null;
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
