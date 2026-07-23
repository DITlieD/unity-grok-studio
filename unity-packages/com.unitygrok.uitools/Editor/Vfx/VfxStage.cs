using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace UnityGrok.UITools.Vfx
{
    public sealed class VfxStageRequest
    {
        public string prefabPath;
        public string tag = "preview";
        public string camera = "close";
        public string background = "gray";
        public string tier;
        public float windowSeconds = 3f;
        public float[] timestamps;
        public float[] normalized;
        public uint seed;
        public string performanceRpPath = "Assets/Settings/Mobile_RPAsset.asset";
        public string highQualityRpPath = "Assets/Settings/Mobile_HighQuality_RPAsset.asset";
        public string performanceVolumePath = "Assets/Settings/SampleSceneProfile.asset";
        public string highQualityVolumePath = "Assets/Settings/HighQuality_VolumeProfile.asset";
        public int zoomRes = 1024;
        public int tileRes = 512;
        public int instanceCount = 1;
    }

    public sealed class VfxStagePerf
    {
        public string mode;
        public int? particleCount;
        public float? drawCalls;
        public float? batches;
        public float? gpuMs;
        public float? renderThreadMs;
        public float? mainThreadMs;
        public string warning;
        public bool available;
    }

    public sealed class VfxStageResult
    {
        public bool ok;
        public string error;
        public string prefabPath;
        public string prefabName;
        public bool looping;
        public float duration;
        public uint seed;
        public string camera;
        public float orthographicSize;
        public string background;
        public string tier;
        public string sheetPath;
        public string metadataPath;
        public string[] framePaths;
        public float[] timestamps;
        public float[] normalized;
        public string tierLimitation;
        public bool isolatedStage;
        public int instanceCount = 1;
        public int particleCountEstimate;
        public VfxStagePerf perf;
    }

    public static class VfxStage
    {
        public static readonly float[] DefaultNormalized = { 0f, 0.10f, 0.25f, 0.50f, 0.75f, 1.00f };

        public static VfxStageResult Capture(VfxStageRequest request)
        {
            if (request == null)
                return Fail("request is null");
            if (string.IsNullOrEmpty(request.prefabPath))
                return Fail("prefabPath required");
            return VfxStageCapture.Run(request);
        }

        public static VfxStageResult Fail(string error) => new VfxStageResult { ok = false, error = error };

        public static float ComputeDuration(ParticleSystem[] systems, bool looping, float windowSeconds)
        {
            float max = 0f;
            if (systems != null)
            {
                for (int i = 0; i < systems.Length; i++)
                {
                    ParticleSystem.MainModule m = systems[i].main;
                    float d = m.startDelay.constantMax + m.duration + m.startLifetime.constantMax;
                    if (d > max) max = d;
                }
            }
            if (looping) return Mathf.Max(0.05f, windowSeconds);
            return Mathf.Max(0.05f, max);
        }

        public static float[] ResolveTimestamps(VfxStageRequest request, float duration)
        {
            if (request.timestamps != null && request.timestamps.Length > 0)
                return (float[])request.timestamps.Clone();
            float[] norms = request.normalized != null && request.normalized.Length > 0
                ? request.normalized
                : DefaultNormalized;
            float[] times = new float[norms.Length];
            for (int i = 0; i < norms.Length; i++)
                times[i] = Mathf.Clamp01(norms[i]) * duration;
            return times;
        }

        public static float[] ResolveNormalized(VfxStageRequest request, float[] times, float duration)
        {
            if (request.normalized != null && request.normalized.Length > 0 &&
                (request.timestamps == null || request.timestamps.Length == 0))
                return (float[])request.normalized.Clone();
            float denom = duration <= 0f ? 1f : duration;
            float[] n = new float[times.Length];
            for (int i = 0; i < times.Length; i++)
                n[i] = Mathf.Clamp01(times[i] / denom);
            return n;
        }

        public static string WriteMetadata(VfxStageResult r)
        {
            var sb = new StringBuilder(512);
            sb.Append("{\"system\":\"vfx-stage\"");
            sb.Append(",\"ok\":").Append(r.ok ? "true" : "false");
            if (!string.IsNullOrEmpty(r.error)) sb.Append(",\"error\":").Append(Str(r.error));
            sb.Append(",\"prefab\":").Append(Str(r.prefabName));
            sb.Append(",\"prefabPath\":").Append(Str(r.prefabPath));
            sb.Append(",\"seed\":").Append(r.seed.ToString(CultureInfo.InvariantCulture));
            sb.Append(",\"looping\":").Append(r.looping ? "true" : "false");
            sb.Append(",\"duration\":").Append(F(r.duration));
            sb.Append(",\"camera\":").Append(Str(r.camera));
            sb.Append(",\"orthographicSize\":").Append(F(r.orthographicSize));
            sb.Append(",\"background\":").Append(Str(r.background));
            sb.Append(",\"tier\":").Append(Str(r.tier ?? "none"));
            sb.Append(",\"isolatedStage\":").Append(r.isolatedStage ? "true" : "false");
            if (!string.IsNullOrEmpty(r.tierLimitation))
                sb.Append(",\"tierLimitation\":").Append(Str(r.tierLimitation));
            sb.Append(",\"instanceCount\":").Append(r.instanceCount.ToString(CultureInfo.InvariantCulture));
            sb.Append(",\"particleCount\":").Append(r.particleCountEstimate.ToString(CultureInfo.InvariantCulture));
            AppendPerf(sb, r.perf);
            sb.Append(",\"sheet\":").Append(Str(Slash(r.sheetPath)));
            sb.Append(",\"metadata\":").Append(Str(Slash(r.metadataPath)));
            sb.Append(",\"timestamps\":");
            AppendFloats(sb, r.timestamps);
            sb.Append(",\"normalized\":");
            AppendFloats(sb, r.normalized);
            sb.Append(",\"frames\":");
            AppendStrings(sb, r.framePaths);
            sb.Append('}');
            string path = r.metadataPath;
            if (string.IsNullOrEmpty(path) && !string.IsNullOrEmpty(r.sheetPath))
                path = Path.ChangeExtension(r.sheetPath, ".json");
            if (!string.IsNullOrEmpty(path))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(path) ?? ".");
                File.WriteAllText(path, sb.ToString());
                r.metadataPath = path;
            }
            return path;
        }

        public static string Summarize(VfxStageResult r)
        {
            if (r == null) return "null result";
            if (!r.ok) return $"{r.prefabName ?? r.prefabPath}: {r.error}";
            var sb = new StringBuilder();
            sb.Append(r.prefabName).Append(r.looping ? " [loop]" : " [oneshot]");
            sb.Append(" frames:");
            if (r.timestamps != null)
                for (int i = 0; i < r.timestamps.Length; i++)
                    sb.Append(' ').Append(Ms(r.timestamps[i]));
            if (!string.IsNullOrEmpty(r.sheetPath)) sb.Append(" sheet=").Append(r.sheetPath);
            if (!string.IsNullOrEmpty(r.metadataPath)) sb.Append(" meta=").Append(r.metadataPath);
            return sb.ToString();
        }

        public static string Ms(float t) => Mathf.RoundToInt(t * 1000f).ToString("D4");

        public static string Slash(string p) => string.IsNullOrEmpty(p) ? p : p.Replace('\\', '/');

        public static string F(float v) => v.ToString("0.####", CultureInfo.InvariantCulture);

        public static string Str(string s)
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

        static void AppendFloats(StringBuilder sb, float[] a)
        {
            sb.Append('[');
            if (a != null)
                for (int i = 0; i < a.Length; i++)
                {
                    if (i > 0) sb.Append(',');
                    sb.Append(F(a[i]));
                }
            sb.Append(']');
        }

        static void AppendStrings(StringBuilder sb, string[] a)
        {
            sb.Append('[');
            if (a != null)
                for (int i = 0; i < a.Length; i++)
                {
                    if (i > 0) sb.Append(',');
                    sb.Append(Str(Slash(a[i])));
                }
            sb.Append(']');
        }

        static void AppendPerf(StringBuilder sb, VfxStagePerf p)
        {
            if (p == null)
            {
                sb.Append(",\"perf\":null");
                return;
            }
            sb.Append(",\"perf\":{");
            sb.Append("\"available\":").Append(p.available ? "true" : "false");
            sb.Append(",\"mode\":").Append(Str(p.mode ?? "unknown"));
            sb.Append(",\"particleCount\":");
            if (p.particleCount.HasValue) sb.Append(p.particleCount.Value.ToString(CultureInfo.InvariantCulture));
            else sb.Append("null");
            sb.Append(",\"drawCalls\":");
            AppendNullable(sb, p.drawCalls);
            sb.Append(",\"batches\":");
            AppendNullable(sb, p.batches);
            sb.Append(",\"gpuMs\":");
            AppendNullable(sb, p.gpuMs);
            sb.Append(",\"renderThreadMs\":");
            AppendNullable(sb, p.renderThreadMs);
            sb.Append(",\"mainThreadMs\":");
            AppendNullable(sb, p.mainThreadMs);
            if (!string.IsNullOrEmpty(p.warning))
                sb.Append(",\"warning\":").Append(Str(p.warning));
            else
                sb.Append(",\"warning\":null");
            sb.Append('}');
        }

        static void AppendNullable(StringBuilder sb, float? v)
        {
            if (v.HasValue) sb.Append(F(v.Value));
            else sb.Append("null");
        }
    }
}
