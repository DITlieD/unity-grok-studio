using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools.Anim
{
    public static class AnimClipFilmstrip
    {
        public struct Result
        {
            public string pngPath;
            public string jsonPath;
            public int samples;
            public float poseSpreadMeters;
        }

        static readonly HumanBodyBones[] KeyBones =
        {
            HumanBodyBones.Hips, HumanBodyBones.Spine, HumanBodyBones.Head,
            HumanBodyBones.LeftHand, HumanBodyBones.RightHand,
            HumanBodyBones.LeftFoot, HumanBodyBones.RightFoot,
        };

        public static Result Capture(AnimationClip clip, GameObject model, Camera cam, int samples, int tileW, int tileH)
        {
            if (clip == null) throw new System.ArgumentException("clip is null");
            if (model == null) throw new System.ArgumentException("model is null");
            if (cam == null) throw new System.ArgumentException("no camera");
            samples = Mathf.Max(1, samples);

            var probes = ResolveProbes(model);
            var poseRows = new List<string>(samples);
            var tiles = new Texture2D[samples];
            var perSampleProbeWorld = new List<Vector3[]>(samples);

            var rt = new RenderTexture(tileW, tileH, 24, RenderTextureFormat.ARGB32);
            var prevTarget = cam.targetTexture;
            var prevActive = RenderTexture.active;

            bool started = false;
            try
            {
                AnimationMode.StartAnimationMode();
                started = true;
                for (int k = 0; k < samples; k++)
                {
                    float norm = samples == 1 ? 0f : (float)k / (samples - 1);
                    float t = norm * clip.length;

                    AnimationMode.BeginSampling();
                    AnimationMode.SampleAnimationClip(model, clip, t);
                    AnimationMode.EndSampling();

                    cam.targetTexture = rt;
                    cam.Render();
                    RenderTexture.active = rt;
                    var tile = new Texture2D(tileW, tileH, TextureFormat.RGB24, false);
                    tile.ReadPixels(new Rect(0, 0, tileW, tileH), 0, 0);
                    tile.Apply();
                    tiles[k] = tile;

                    var world = new Vector3[probes.Count];
                    for (int b = 0; b < probes.Count; b++)
                        world[b] = probes[b].tr != null ? probes[b].tr.position : Vector3.zero;
                    perSampleProbeWorld.Add(world);
                    poseRows.Add(PoseRow(k, norm, t, probes, world));
                }
            }
            finally
            {
                cam.targetTexture = prevTarget;
                RenderTexture.active = prevActive;
                if (started) AnimationMode.StopAnimationMode();
            }

            string safe = Sanitize(clip.name);
            string png = ComposeSheet(tiles, tileW, tileH, safe);
            foreach (var tx in tiles) if (tx != null) Object.DestroyImmediate(tx);
            rt.Release();
            Object.DestroyImmediate(rt);

            float spread = PoseSpread(perSampleProbeWorld);
            string json = WriteJson(safe, clip, samples, probes, poseRows, spread, png);

            return new Result { pngPath = png, jsonPath = json, samples = samples, poseSpreadMeters = spread };
        }

        struct Probe { public string name; public Transform tr; }

        static List<Probe> ResolveProbes(GameObject model)
        {
            var list = new List<Probe>();
            var an = model.GetComponentInChildren<Animator>();
            if (an != null && an.isHuman)
            {
                foreach (var hb in KeyBones)
                {
                    var tr = an.GetBoneTransform(hb);
                    if (tr != null) list.Add(new Probe { name = hb.ToString(), tr = tr });
                }
                if (list.Count > 0) return list;
            }
            var seen = new HashSet<Transform>();
            foreach (var b in AnimationUtility.GetCurveBindings(GetAnyClipFallback(model)))
            {
                if (string.IsNullOrEmpty(b.path)) continue;
                var tr = model.transform.Find(b.path);
                if (tr != null && seen.Add(tr)) list.Add(new Probe { name = b.path, tr = tr });
                if (list.Count >= 24) break;
            }
            if (list.Count == 0) list.Add(new Probe { name = model.name, tr = model.transform });
            return list;
        }

        static AnimationClip GetAnyClipFallback(GameObject model)
        {
            var an = model.GetComponentInChildren<Animator>();
            if (an != null && an.runtimeAnimatorController != null && an.runtimeAnimatorController.animationClips.Length > 0)
                return an.runtimeAnimatorController.animationClips[0];
            return new AnimationClip();
        }

        static string ComposeSheet(Texture2D[] tiles, int tileW, int tileH, string safe)
        {
            int n = tiles.Length;
            int cols = Mathf.CeilToInt(Mathf.Sqrt(n));
            int rows = Mathf.CeilToInt((float)n / cols);
            var sheet = new Texture2D(cols * tileW, rows * tileH, TextureFormat.RGB24, false);
            var clear = new Color32[cols * tileW * rows * tileH];
            for (int i = 0; i < clear.Length; i++) clear[i] = new Color32(20, 20, 24, 255);
            sheet.SetPixels32(clear);
            for (int k = 0; k < n; k++)
            {
                if (tiles[k] == null) continue;
                int col = k % cols;
                int row = k / cols;
                int px = col * tileW;
                int py = (rows - 1 - row) * tileH;
                sheet.SetPixels(px, py, tileW, tileH, tiles[k].GetPixels());
            }
            sheet.Apply();
            var bytes = sheet.EncodeToPNG();
            Object.DestroyImmediate(sheet);
            var dir = OutDir();
            var path = Path.Combine(dir, $"anim.{safe}.filmstrip.png");
            File.WriteAllBytes(path, bytes);
            return path;
        }

        static float PoseSpread(List<Vector3[]> perSample)
        {
            if (perSample.Count < 2) return 0f;
            int probes = perSample[0].Length;
            float maxDelta = 0f;
            for (int b = 0; b < probes; b++)
            {
                for (int k = 1; k < perSample.Count; k++)
                {
                    float d = Vector3.Distance(perSample[k][b], perSample[0][b]);
                    if (d > maxDelta) maxDelta = d;
                }
            }
            return maxDelta;
        }

        static string PoseRow(int index, float norm, float t, List<Probe> probes, Vector3[] world)
        {
            var sb = new StringBuilder();
            sb.Append("{\"index\":").Append(index)
              .Append(",\"normTime\":").Append(F(norm))
              .Append(",\"time\":").Append(F(t))
              .Append(",\"bones\":[");
            for (int b = 0; b < probes.Count; b++)
            {
                if (b > 0) sb.Append(',');
                sb.Append("{\"name\":").Append(Str(probes[b].name))
                  .Append(",\"worldPos\":{\"x\":").Append(F(world[b].x)).Append(",\"y\":").Append(F(world[b].y)).Append(",\"z\":").Append(F(world[b].z)).Append("}}");
            }
            sb.Append("]}");
            return sb.ToString();
        }

        static string WriteJson(string safe, AnimationClip clip, int samples, List<Probe> probes, List<string> rows, float spread, string png)
        {
            var sb = new StringBuilder();
            sb.Append("{\"system\":\"anim-filmstrip\",\"clip\":").Append(Str(clip.name))
              .Append(",\"length\":").Append(F(clip.length))
              .Append(",\"samples\":").Append(samples)
              .Append(",\"probeCount\":").Append(probes.Count)
              .Append(",\"poseSpreadMeters\":").Append(F(spread))
              .Append(",\"contactSheet\":").Append(Str(png.Replace('\\', '/')))
              .Append(",\"frames\":[");
            for (int i = 0; i < rows.Count; i++) { if (i > 0) sb.Append(','); sb.Append(rows[i]); }
            sb.Append("]}");
            var path = Path.Combine(OutDir(), $"anim.{safe}.filmstrip.json");
            File.WriteAllText(path, sb.ToString());
            return path;
        }

        static string OutDir()
        {
            var dir = Path.Combine(Directory.GetParent(Application.dataPath).FullName, "UISnapshots");
            Directory.CreateDirectory(dir);
            return dir;
        }

        static string Sanitize(string name)
        {
            var sb = new StringBuilder();
            foreach (char c in name) sb.Append(char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_');
            return sb.ToString();
        }

        static string F(float v) => v.ToString("0.####", CultureInfo.InvariantCulture);

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
