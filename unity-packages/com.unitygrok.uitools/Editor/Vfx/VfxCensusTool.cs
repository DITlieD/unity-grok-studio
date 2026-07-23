using System.Collections.Generic;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace UnityGrok.UITools.Vfx
{
    [McpForUnityTool("vfx_census")]
    public static class VfxCensusTool
    {
        public class Parameters
        {
            [ToolParameter("Comma-separated prefab asset paths, or omit when folder is set", Required = false)]
            public string prefabPaths { get; set; }

            [ToolParameter("Folder under Assets/ to FindAssets prefabs from", Required = false)]
            public string folder { get; set; }

            [ToolParameter("Absolute or project-relative dump json path", Required = true)]
            public string dumpPath { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string dumpPath = @params?["dumpPath"]?.ToString() ?? @params?["out"]?.ToString();
            if (string.IsNullOrEmpty(dumpPath))
                return new ErrorResponse("vfx_census requires 'dumpPath'");

            string folder = NullIfEmpty(@params?["folder"]?.ToString());
            List<string> paths = ReadPaths(@params);

            VfxCensusResult result;
            try
            {
                if (paths.Count > 0)
                    result = VfxPrefabCensus.Dump(paths, dumpPath);
                else if (!string.IsNullOrEmpty(folder))
                    result = VfxPrefabCensus.DumpFolder(folder, dumpPath);
                else
                    return new ErrorResponse("vfx_census requires 'prefabPaths' or 'folder'");
            }
            catch (System.Exception ex)
            {
                return new ErrorResponse($"vfx_census_failed: {ex.Message}");
            }

            if (!result.ok)
                return new ErrorResponse(result.error ?? "vfx_census_failed");

            return new SuccessResponse(
                $"vfx_census: {result.prefabCount} prefabs / {result.systemCount} systems > {result.dumpPath}",
                new
                {
                    ok = true,
                    dumpPath = result.dumpPath,
                    prefabCount = result.prefabCount,
                    systemCount = result.systemCount,
                    prefabs = Summarize(result)
                });
        }

        static List<string> ReadPaths(JObject p)
        {
            var list = new List<string>();
            if (p == null) return list;
            JToken t = p["prefabPaths"] ?? p["paths"] ?? p["prefabs"];
            if (t == null || t.Type == JTokenType.Null) return list;
            if (t is JArray arr)
            {
                for (int i = 0; i < arr.Count; i++)
                {
                    string s = arr[i]?.ToString();
                    if (!string.IsNullOrWhiteSpace(s)) list.Add(s.Trim());
                }
                return list;
            }
            string raw = t.ToString();
            if (string.IsNullOrWhiteSpace(raw)) return list;
            string[] parts = raw.Split(new[] { ',', ';', '\n', '\r' }, System.StringSplitOptions.RemoveEmptyEntries);
            for (int i = 0; i < parts.Length; i++)
            {
                string s = parts[i].Trim();
                if (s.Length > 0) list.Add(s);
            }
            return list;
        }

        static object Summarize(VfxCensusResult r)
        {
            var rows = new List<object>(r.prefabs.Count);
            for (int i = 0; i < r.prefabs.Count; i++)
            {
                VfxCensusPrefabFact p = r.prefabs[i];
                float maxCh = 0f;
                bool soft = false;
                bool fade = false;
                int maxOrder = 0;
                if (p.systems != null)
                {
                    for (int j = 0; j < p.systems.Count; j++)
                    {
                        VfxCensusSystemFact s = p.systems[j];
                        if (s.maxColorChannel > maxCh) maxCh = s.maxColorChannel;
                        if (s.softParticlesOn) soft = true;
                        if (s.fadingOn) fade = true;
                        if (System.Math.Abs(s.sortingOrder) > System.Math.Abs(maxOrder)) maxOrder = s.sortingOrder;
                    }
                }
                rows.Add(new
                {
                    prefabPath = p.prefabPath,
                    prefabName = p.prefabName,
                    ok = p.ok,
                    error = p.error,
                    allowlist = p.allowlist,
                    systemCount = p.systems != null ? p.systems.Count : 0,
                    maxColorChannel = maxCh,
                    softParticlesOn = soft,
                    fadingOn = fade,
                    sortingOrder = maxOrder
                });
            }
            return rows;
        }

        static string NullIfEmpty(string s) => string.IsNullOrWhiteSpace(s) ? null : s;
    }
}
