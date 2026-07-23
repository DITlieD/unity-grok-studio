using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools.Vfx
{
    public sealed class VfxCensusSystemFact
    {
        public string path;
        public string name;
        public float maxStartColorChannel;
        public float maxColorOverLifetimeChannel;
        public float maxMaterialTintChannel;
        public float maxColorChannel;
        public string startColorMode;
        public string[] colorOverLifetimeModes;
        public bool hasRandomColor;
        public bool randomColorFixed;
        public string[] shaderKeywords;
        public bool softParticlesOn;
        public bool fadingOn;
        public string shaderName;
        public string materialName;
        public string materialPath;
        public int sortingOrder;
        public string sortingLayer;
        public string scalingMode;
        public float sizeMin;
        public float sizeMax;
        public int maxParticles;
        public bool additiveHint;
        public bool hasTrail;
        public bool trailEnabled;
        public string[] textureRefs;
        public bool allowlist;
    }

    public sealed class VfxCensusPrefabFact
    {
        public string prefabPath;
        public string prefabName;
        public bool ok;
        public string error;
        public bool allowlist;
        public List<VfxCensusSystemFact> systems = new List<VfxCensusSystemFact>();
    }

    public sealed class VfxCensusResult
    {
        public bool ok;
        public string error;
        public string dumpPath;
        public int prefabCount;
        public int systemCount;
        public List<VfxCensusPrefabFact> prefabs = new List<VfxCensusPrefabFact>();
    }

    public static class VfxPrefabCensus
    {
        static readonly string[] SoftKeywords = { "_SOFTPARTICLES_ON", "_FADING_ON" };

        public static VfxCensusResult Dump(IList<string> prefabPaths, string dumpPath)
        {
            var result = new VfxCensusResult { ok = true, dumpPath = dumpPath };
            if (prefabPaths == null || prefabPaths.Count == 0)
            {
                result.ok = false;
                result.error = "prefabPaths empty";
                return result;
            }
            if (string.IsNullOrEmpty(dumpPath))
            {
                result.ok = false;
                result.error = "dumpPath required";
                return result;
            }

            for (int i = 0; i < prefabPaths.Count; i++)
            {
                string path = prefabPaths[i];
                if (string.IsNullOrWhiteSpace(path)) continue;
                result.prefabs.Add(CensusOne(path.Replace('\\', '/')));
            }

            result.prefabCount = result.prefabs.Count;
            int systems = 0;
            for (int i = 0; i < result.prefabs.Count; i++)
                systems += result.prefabs[i].systems != null ? result.prefabs[i].systems.Count : 0;
            result.systemCount = systems;

            try
            {
                string dir = Path.GetDirectoryName(dumpPath);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                File.WriteAllText(dumpPath, ToJson(result));
            }
            catch (Exception ex)
            {
                result.ok = false;
                result.error = "write_failed: " + ex.Message;
            }
            return result;
        }

        public static VfxCensusResult DumpFolder(string folder, string dumpPath, string search = "t:Prefab")
        {
            if (string.IsNullOrEmpty(folder))
                return new VfxCensusResult { ok = false, error = "folder required" };
            string[] guids = AssetDatabase.FindAssets(search, new[] { folder.Replace('\\', '/') });
            var paths = new List<string>(guids.Length);
            for (int i = 0; i < guids.Length; i++)
            {
                string p = AssetDatabase.GUIDToAssetPath(guids[i]);
                if (!string.IsNullOrEmpty(p) && p.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                    paths.Add(p);
            }
            paths.Sort(StringComparer.OrdinalIgnoreCase);
            return Dump(paths, dumpPath);
        }

        static VfxCensusPrefabFact CensusOne(string prefabPath)
        {
            var fact = new VfxCensusPrefabFact
            {
                prefabPath = prefabPath,
                prefabName = Path.GetFileNameWithoutExtension(prefabPath),
                ok = true
            };
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefab == null)
            {
                fact.ok = false;
                fact.error = "prefab_not_found";
                return fact;
            }

            fact.allowlist = HasAllowlist(prefab);
            ParticleSystem[] systems = prefab.GetComponentsInChildren<ParticleSystem>(true);
            if (systems == null || systems.Length == 0)
            {
                fact.ok = false;
                fact.error = "no_particle_systems";
                return fact;
            }

            for (int i = 0; i < systems.Length; i++)
                fact.systems.Add(CensusSystem(systems[i], prefab.transform));
            return fact;
        }

        static VfxCensusSystemFact CensusSystem(ParticleSystem ps, Transform root)
        {
            var main = ps.main;
            ps.TryGetComponent(out ParticleSystemRenderer renderer);
            var fact = new VfxCensusSystemFact
            {
                name = ps.name,
                path = RelPath(ps.transform, root),
                maxParticles = main.maxParticles,
                scalingMode = main.scalingMode.ToString(),
                startColorMode = main.startColor.mode.ToString(),
                sizeMin = ReadMin(main.startSize),
                sizeMax = ReadMax(main.startSize),
                allowlist = HasAllowlist(ps.gameObject)
            };

            fact.maxStartColorChannel = MaxChannel(main.startColor);
            SampleColorOverLifetime(ps, fact);
            SampleRenderer(renderer, fact);

            var trails = ps.trails;
            fact.hasTrail = true;
            fact.trailEnabled = trails.enabled;
            float trailMax = 0f;
            if (trails.enabled)
                trailMax = MaxChannel(trails.colorOverLifetime);

            fact.maxColorChannel = Math.Max(fact.maxStartColorChannel,
                Math.Max(fact.maxColorOverLifetimeChannel,
                    Math.Max(fact.maxMaterialTintChannel, trailMax)));
            return fact;
        }

        static void SampleColorOverLifetime(ParticleSystem ps, VfxCensusSystemFact fact)
        {
            var col = ps.colorOverLifetime;
            var modes = new List<string>(2);
            float max = 0f;
            bool hasRandom = false;
            bool randomFixed = true;

            if (col.enabled)
            {
                modes.Add(col.color.mode.ToString());
                max = Math.Max(max, MaxChannel(col.color));
                if (col.color.mode == ParticleSystemGradientMode.RandomColor)
                {
                    hasRandom = true;
                    randomFixed = IsFixedGradient(col.color);
                }
            }

            fact.colorOverLifetimeModes = modes.ToArray();
            fact.maxColorOverLifetimeChannel = max;
            fact.hasRandomColor = hasRandom || mainIsRandom(ps.main.startColor);
            if (mainIsRandom(ps.main.startColor))
            {
                fact.hasRandomColor = true;
                if (!IsFixedGradient(ps.main.startColor))
                    randomFixed = false;
            }
            fact.randomColorFixed = !fact.hasRandomColor || randomFixed;
        }

        static bool mainIsRandom(ParticleSystem.MinMaxGradient g) =>
            g.mode == ParticleSystemGradientMode.RandomColor;

        static void SampleRenderer(ParticleSystemRenderer renderer, VfxCensusSystemFact fact)
        {
            if (renderer == null)
            {
                fact.shaderKeywords = Array.Empty<string>();
                fact.textureRefs = Array.Empty<string>();
                fact.sortingOrder = 0;
                fact.sortingLayer = "";
                fact.shaderName = "";
                fact.materialName = "";
                fact.materialPath = "";
                return;
            }

            fact.sortingOrder = renderer.sortingOrder;
            fact.sortingLayer = renderer.sortingLayerName ?? "";

            Material mat = renderer.sharedMaterial;
            var keywords = new List<string>();
            var textures = new List<string>();
            float tintMax = 0f;
            bool additive = false;

            if (mat != null)
            {
                fact.materialName = mat.name;
                fact.shaderName = mat.shader != null ? mat.shader.name : "";
                fact.materialPath = AssetDatabase.GetAssetPath(mat) ?? "";
                string[] kws = mat.shaderKeywords;
                if (kws != null)
                {
                    for (int i = 0; i < kws.Length; i++)
                    {
                        if (string.IsNullOrEmpty(kws[i])) continue;
                        keywords.Add(kws[i]);
                        if (kws[i] == "_SOFTPARTICLES_ON") fact.softParticlesOn = true;
                        if (kws[i] == "_FADING_ON") fact.fadingOn = true;
                    }
                }
                if (!fact.softParticlesOn && mat.IsKeywordEnabled("_SOFTPARTICLES_ON"))
                {
                    fact.softParticlesOn = true;
                    if (!keywords.Contains("_SOFTPARTICLES_ON")) keywords.Add("_SOFTPARTICLES_ON");
                }
                if (!fact.fadingOn && mat.IsKeywordEnabled("_FADING_ON"))
                {
                    fact.fadingOn = true;
                    if (!keywords.Contains("_FADING_ON")) keywords.Add("_FADING_ON");
                }

                if (mat.HasProperty("_Color"))
                    tintMax = Math.Max(tintMax, MaxRgb(mat.GetColor("_Color")));
                if (mat.HasProperty("_BaseColor"))
                    tintMax = Math.Max(tintMax, MaxRgb(mat.GetColor("_BaseColor")));
                if (mat.HasProperty("_TintColor"))
                    tintMax = Math.Max(tintMax, MaxRgb(mat.GetColor("_TintColor")));
                if (mat.HasProperty("_EmissionColor"))
                    tintMax = Math.Max(tintMax, MaxRgb(mat.GetColor("_EmissionColor")));

                CollectTex(mat, "_MainTex", textures);
                CollectTex(mat, "_BaseMap", textures);
                CollectTex(mat, "_BumpMap", textures);
                CollectTex(mat, "_EmissionMap", textures);

                string matName = (mat.name ?? "") + " " + fact.shaderName;
                string lower = matName.ToLowerInvariant();
                additive = lower.Contains("add") || lower.Contains("additive") ||
                           lower.Contains("particles/additive") || lower.Contains("particles/standard unlit");
                if (mat.HasProperty("_SrcBlend") && mat.HasProperty("_DstBlend"))
                {
                    int src = mat.GetInt("_SrcBlend");
                    int dst = mat.GetInt("_DstBlend");
                    if (src == (int)UnityEngine.Rendering.BlendMode.SrcAlpha &&
                        dst == (int)UnityEngine.Rendering.BlendMode.One)
                        additive = true;
                    if (src == (int)UnityEngine.Rendering.BlendMode.One &&
                        dst == (int)UnityEngine.Rendering.BlendMode.One)
                        additive = true;
                }
            }
            else
            {
                fact.materialName = "";
                fact.shaderName = "";
                fact.materialPath = "";
            }

            fact.shaderKeywords = keywords.ToArray();
            fact.textureRefs = textures.ToArray();
            fact.maxMaterialTintChannel = tintMax;
            fact.additiveHint = additive;
        }

        static void CollectTex(Material mat, string prop, List<string> textures)
        {
            if (!mat.HasProperty(prop)) return;
            Texture t = mat.GetTexture(prop);
            if (t == null) return;
            string p = AssetDatabase.GetAssetPath(t);
            if (string.IsNullOrEmpty(p)) p = t.name;
            if (!string.IsNullOrEmpty(p) && !textures.Contains(p)) textures.Add(p.Replace('\\', '/'));
        }

        static bool HasAllowlist(GameObject go)
        {
            if (go == null) return false;
            var comps = go.GetComponentsInChildren<Component>(true);
            for (int i = 0; i < comps.Length; i++)
            {
                Component c = comps[i];
                if (c == null) continue;
                string n = c.GetType().Name;
                if (n == "VfxLintAllowlist") return true;
            }
            return false;
        }

        static float MaxChannel(ParticleSystem.MinMaxGradient g)
        {
            float max = 0f;
            switch (g.mode)
            {
                case ParticleSystemGradientMode.Color:
                    max = MaxRgb(g.color);
                    break;
                case ParticleSystemGradientMode.TwoColors:
                    max = Math.Max(MaxRgb(g.colorMin), MaxRgb(g.colorMax));
                    break;
                case ParticleSystemGradientMode.Gradient:
                case ParticleSystemGradientMode.RandomColor:
                    max = Math.Max(max, MaxGradient(g.gradient));
                    break;
                case ParticleSystemGradientMode.TwoGradients:
                    max = Math.Max(MaxGradient(g.gradientMin), MaxGradient(g.gradientMax));
                    break;
            }
            return max;
        }

        static float MaxGradient(Gradient g)
        {
            if (g == null) return 0f;
            float max = 0f;
            GradientColorKey[] keys = g.colorKeys;
            if (keys != null)
            {
                for (int i = 0; i < keys.Length; i++)
                    max = Math.Max(max, MaxRgb(keys[i].color));
            }
            return max;
        }

        static bool IsFixedGradient(ParticleSystem.MinMaxGradient g)
        {
            switch (g.mode)
            {
                case ParticleSystemGradientMode.Gradient:
                case ParticleSystemGradientMode.RandomColor:
                    return g.gradient != null && g.gradient.mode == GradientMode.Fixed;
                case ParticleSystemGradientMode.TwoGradients:
                    bool a = g.gradientMin != null && g.gradientMin.mode == GradientMode.Fixed;
                    bool b = g.gradientMax != null && g.gradientMax.mode == GradientMode.Fixed;
                    return a && b;
                default:
                    return true;
            }
        }

        static float MaxRgb(Color c) => Math.Max(c.r, Math.Max(c.g, c.b));

        static float ReadMin(ParticleSystem.MinMaxCurve c)
        {
            switch (c.mode)
            {
                case ParticleSystemCurveMode.Constant: return c.constant;
                case ParticleSystemCurveMode.TwoConstants: return Math.Min(c.constantMin, c.constantMax);
                case ParticleSystemCurveMode.Curve: return c.constant;
                case ParticleSystemCurveMode.TwoCurves: return Math.Min(c.constantMin, c.constantMax);
                default: return c.constant;
            }
        }

        static float ReadMax(ParticleSystem.MinMaxCurve c)
        {
            switch (c.mode)
            {
                case ParticleSystemCurveMode.Constant: return c.constant;
                case ParticleSystemCurveMode.TwoConstants: return Math.Max(c.constantMin, c.constantMax);
                case ParticleSystemCurveMode.Curve: return c.constantMax != 0f ? c.constantMax : c.constant;
                case ParticleSystemCurveMode.TwoCurves: return Math.Max(c.constantMin, c.constantMax);
                default: return c.constant;
            }
        }

        static string RelPath(Transform t, Transform root)
        {
            if (t == null) return "";
            if (t == root) return t.name;
            var parts = new List<string>();
            Transform cur = t;
            while (cur != null)
            {
                parts.Add(cur.name);
                if (cur == root) break;
                cur = cur.parent;
            }
            parts.Reverse();
            return string.Join("/", parts);
        }

        static string ToJson(VfxCensusResult r)
        {
            var sb = new StringBuilder(4096);
            sb.Append("{\"system\":\"vfx-census\"");
            sb.Append(",\"ok\":").Append(r.ok ? "true" : "false");
            if (!string.IsNullOrEmpty(r.error)) sb.Append(",\"error\":").Append(Str(r.error));
            sb.Append(",\"dumpPath\":").Append(Str(Slash(r.dumpPath)));
            sb.Append(",\"prefabCount\":").Append(r.prefabCount.ToString(CultureInfo.InvariantCulture));
            sb.Append(",\"systemCount\":").Append(r.systemCount.ToString(CultureInfo.InvariantCulture));
            sb.Append(",\"prefabs\":[");
            for (int i = 0; i < r.prefabs.Count; i++)
            {
                if (i > 0) sb.Append(',');
                AppendPrefab(sb, r.prefabs[i]);
            }
            sb.Append("]}");
            return sb.ToString();
        }

        static void AppendPrefab(StringBuilder sb, VfxCensusPrefabFact p)
        {
            sb.Append("{\"prefabPath\":").Append(Str(Slash(p.prefabPath)));
            sb.Append(",\"prefabName\":").Append(Str(p.prefabName));
            sb.Append(",\"ok\":").Append(p.ok ? "true" : "false");
            if (!string.IsNullOrEmpty(p.error)) sb.Append(",\"error\":").Append(Str(p.error));
            sb.Append(",\"allowlist\":").Append(p.allowlist ? "true" : "false");
            sb.Append(",\"systems\":[");
            if (p.systems != null)
            {
                for (int i = 0; i < p.systems.Count; i++)
                {
                    if (i > 0) sb.Append(',');
                    AppendSystem(sb, p.systems[i]);
                }
            }
            sb.Append("]}");
        }

        static void AppendSystem(StringBuilder sb, VfxCensusSystemFact s)
        {
            sb.Append("{\"path\":").Append(Str(s.path));
            sb.Append(",\"name\":").Append(Str(s.name));
            sb.Append(",\"maxStartColorChannel\":").Append(F(s.maxStartColorChannel));
            sb.Append(",\"maxColorOverLifetimeChannel\":").Append(F(s.maxColorOverLifetimeChannel));
            sb.Append(",\"maxMaterialTintChannel\":").Append(F(s.maxMaterialTintChannel));
            sb.Append(",\"maxColorChannel\":").Append(F(s.maxColorChannel));
            sb.Append(",\"startColorMode\":").Append(Str(s.startColorMode));
            sb.Append(",\"colorOverLifetimeModes\":");
            AppendStrings(sb, s.colorOverLifetimeModes);
            sb.Append(",\"hasRandomColor\":").Append(s.hasRandomColor ? "true" : "false");
            sb.Append(",\"randomColorFixed\":").Append(s.randomColorFixed ? "true" : "false");
            sb.Append(",\"shaderKeywords\":");
            AppendStrings(sb, s.shaderKeywords);
            sb.Append(",\"softParticlesOn\":").Append(s.softParticlesOn ? "true" : "false");
            sb.Append(",\"fadingOn\":").Append(s.fadingOn ? "true" : "false");
            sb.Append(",\"shaderName\":").Append(Str(s.shaderName));
            sb.Append(",\"materialName\":").Append(Str(s.materialName));
            sb.Append(",\"materialPath\":").Append(Str(Slash(s.materialPath)));
            sb.Append(",\"sortingOrder\":").Append(s.sortingOrder.ToString(CultureInfo.InvariantCulture));
            sb.Append(",\"sortingLayer\":").Append(Str(s.sortingLayer));
            sb.Append(",\"scalingMode\":").Append(Str(s.scalingMode));
            sb.Append(",\"sizeMin\":").Append(F(s.sizeMin));
            sb.Append(",\"sizeMax\":").Append(F(s.sizeMax));
            sb.Append(",\"maxParticles\":").Append(s.maxParticles.ToString(CultureInfo.InvariantCulture));
            sb.Append(",\"additiveHint\":").Append(s.additiveHint ? "true" : "false");
            sb.Append(",\"hasTrail\":").Append(s.hasTrail ? "true" : "false");
            sb.Append(",\"trailEnabled\":").Append(s.trailEnabled ? "true" : "false");
            sb.Append(",\"textureRefs\":");
            AppendStrings(sb, s.textureRefs);
            sb.Append(",\"allowlist\":").Append(s.allowlist ? "true" : "false");
            sb.Append('}');
        }

        static void AppendStrings(StringBuilder sb, string[] a)
        {
            sb.Append('[');
            if (a != null)
            {
                for (int i = 0; i < a.Length; i++)
                {
                    if (i > 0) sb.Append(',');
                    sb.Append(Str(a[i]));
                }
            }
            sb.Append(']');
        }

        static string Slash(string p) => string.IsNullOrEmpty(p) ? p : p.Replace('\\', '/');

        static string F(float v) => v.ToString("0.######", CultureInfo.InvariantCulture);

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
    }
}
