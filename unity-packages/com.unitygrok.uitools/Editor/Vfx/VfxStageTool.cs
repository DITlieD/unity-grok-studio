using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace UnityGrok.UITools.Vfx
{
    [McpForUnityTool("vfx_preview")]
    public static class VfxStageTool
    {
        public class Parameters
        {
            [ToolParameter("Prefab asset path (Assets/...) of the VFX to capture", Required = true)]
            public string prefabPath { get; set; }

            [ToolParameter("Output tag folder under UISnapshots/vfx/ (default preview)", Required = false)]
            public string tag { get; set; }

            [ToolParameter("Camera preset: close (ortho 3.5 DEFAULT for judgment), game (ortho 7), side", Required = false)]
            public string camera { get; set; }

            [ToolParameter("Background: gray (DEFAULT judgment), black|bright|gameplay (gameplay needs open-scene camera)", Required = false)]
            public string background { get; set; }

            [ToolParameter("Tier: Performance|HighQuality (swaps RP+volume, forces allowHDR)", Required = false)]
            public string tier { get; set; }

            [ToolParameter("Looping sample window seconds (default 3)", Required = false)]
            public float? windowSeconds { get; set; }

            [ToolParameter("Absolute timestamps override array (seconds)", Required = false)]
            public object timestamps { get; set; }

            [ToolParameter("Normalized timestamps 0..1 (default 0/0.1/0.25/0.5/0.75/1)", Required = false)]
            public object normalized { get; set; }

            [ToolParameter("Deterministic seed (0 = FNV of prefab name)", Required = false)]
            public int? seed { get; set; }

            [ToolParameter("Simultaneous instance count for concurrency stress (default 1)", Required = false)]
            public int? instanceCount { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string prefabPath = @params?["prefabPath"]?.ToString() ?? @params?["prefab"]?.ToString();
            if (string.IsNullOrEmpty(prefabPath))
                return new ErrorResponse("vfx_preview requires 'prefabPath' (asset path)");

            var request = new VfxStageRequest
            {
                prefabPath = prefabPath,
                tag = StrOr(@params, "tag", "preview"),
                camera = StrOr(@params, "camera", "close"),
                background = StrOr(@params, "background", "gray"),
                tier = NullIfEmpty(@params?["tier"]?.ToString()),
                windowSeconds = GetFloat(@params, "windowSeconds", 3f),
                seed = (uint)Mathf.Max(0, GetInt(@params, "seed", 0)),
                timestamps = ReadFloats(@params?["timestamps"]),
                normalized = ReadFloats(@params?["normalized"]),
                instanceCount = Mathf.Max(1, GetInt(@params, "instanceCount", 1))
            };

            VfxStageResult result;
            try
            {
                result = VfxStage.Capture(request);
            }
            catch (System.Exception ex)
            {
                return new ErrorResponse($"vfx_preview_failed: {ex.Message}");
            }

            if (!result.ok)
                return new ErrorResponse(result.error ?? "vfx_preview_failed");

            return new SuccessResponse(VfxStage.Summarize(result), new
            {
                ok = true,
                prefab = result.prefabName,
                prefabPath = result.prefabPath,
                looping = result.looping,
                duration = result.duration,
                seed = result.seed,
                camera = result.camera,
                orthographicSize = result.orthographicSize,
                background = result.background,
                tier = result.tier,
                sheet = result.sheetPath,
                metadata = result.metadataPath,
                frames = result.framePaths,
                timestamps = result.timestamps,
                normalized = result.normalized,
                tierLimitation = result.tierLimitation,
                isolatedStage = result.isolatedStage,
                instanceCount = result.instanceCount,
                particleCount = result.particleCountEstimate,
                perf = result.perf
            });
        }

        static string StrOr(JObject p, string key, string fallback)
        {
            string v = p?[key]?.ToString();
            return string.IsNullOrEmpty(v) ? fallback : v;
        }

        static string NullIfEmpty(string s) => string.IsNullOrWhiteSpace(s) ? null : s;

        static float GetFloat(JObject p, string key, float fallback)
        {
            var t = p?[key];
            return (t == null || t.Type == JTokenType.Null) ? fallback : t.Value<float>();
        }

        static int GetInt(JObject p, string key, int fallback)
        {
            var t = p?[key];
            return (t == null || t.Type == JTokenType.Null) ? fallback : t.Value<int>();
        }

        static float[] ReadFloats(JToken t)
        {
            if (t == null || t.Type == JTokenType.Null) return null;
            if (t is JArray a)
            {
                float[] r = new float[a.Count];
                for (int i = 0; i < a.Count; i++) r[i] = a[i].Value<float>();
                return r;
            }
            return null;
        }
    }
}
