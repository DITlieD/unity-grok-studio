using System.Collections.Generic;
using System.IO;
using Unity.Profiling;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace UnityGrok.UITools.Vfx
{
    public static class VfxStageCapture
    {
        const float CamDistance = 40f;
        const float GameOrtho = 7f;
        const float CloseOrtho = 3.5f;

        public static VfxStageResult Run(VfxStageRequest request)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(request.prefabPath);
            if (prefab == null)
                return VfxStage.Fail($"prefab_not_found: {request.prefabPath}");

            string prefabName = Path.GetFileNameWithoutExtension(request.prefabPath);
            string bg = (request.background ?? "gray").Trim().ToLowerInvariant();
            string camPreset = (request.camera ?? "game").Trim().ToLowerInvariant();
            string tier = string.IsNullOrWhiteSpace(request.tier) ? null : request.tier.Trim();
            bool isolated = bg != "gameplay";
            int instanceCount = Mathf.Max(1, request.instanceCount);

            Camera refCam = ResolveGameCamera();
            if (!isolated && refCam == null)
                return VfxStage.Fail("background=gameplay requires a camera in the open scene");

            Vector3 stage = isolated ? Vector3.zero : StagePoint(refCam);
            var instances = new List<GameObject>(instanceCount);
            for (int n = 0; n < instanceCount; n++)
            {
                Vector3 offset = stage + new Vector3(n * 0.05f, 0f, n * 0.05f);
                GameObject go = Object.Instantiate(prefab, offset, Quaternion.identity);
                go.name = "VfxStageInstance_" + prefabName + "_" + n;
                instances.Add(go);
            }

            GameObject camGo = new GameObject("VfxStageCam");
            GameObject bgGo = null;
            GameObject volGo = null;
            GameObject lightGo = null;
            RenderPipelineAsset prevDefault = GraphicsSettings.defaultRenderPipeline;
            RenderPipelineAsset prevQuality = QualitySettings.renderPipeline;
            bool swappedRp = false;
            string tierLimitation = null;

            try
            {
                var allSystems = new List<ParticleSystem>();
                for (int n = 0; n < instances.Count; n++)
                {
                    ParticleSystem[] child = instances[n].GetComponentsInChildren<ParticleSystem>(true);
                    if (child != null)
                        for (int i = 0; i < child.Length; i++) allSystems.Add(child[i]);
                }
                ParticleSystem[] systems = allSystems.ToArray();
                if (systems == null || systems.Length == 0)
                    return VfxStage.Fail($"no_particle_systems: {request.prefabPath}");

                bool looping = false;
                uint seed = request.seed != 0 ? request.seed : Fnv(prefabName);
                int maxParticlesSum = 0;
                for (int i = 0; i < systems.Length; i++)
                {
                    ParticleSystem ps = systems[i];
                    ps.useAutoRandomSeed = false;
                    ps.randomSeed = request.seed != 0 ? seed : Fnv(prefabName + ps.name + i);
                    if (ps.main.loop) looping = true;
                    maxParticlesSum += ps.main.maxParticles;
                }
                if (request.seed == 0) seed = Fnv(prefabName);

                List<ParticleSystem> roots = TopLevel(systems);
                float duration = VfxStage.ComputeDuration(systems, looping, request.windowSeconds);
                float[] times = VfxStage.ResolveTimestamps(request, duration);
                float[] norms = VfxStage.ResolveNormalized(request, times, duration);
                VfxStagePerf perf = SamplePerf(maxParticlesSum);

                Camera cam = camGo.AddComponent<Camera>();
                float ortho;
                if (isolated)
                {
                    cam.orthographic = true;
                    cam.clearFlags = CameraClearFlags.SolidColor;
                    cam.backgroundColor = BgColor(bg);
                    cam.nearClipPlane = 0.01f;
                    cam.farClipPlane = 200f;
                    cam.aspect = 1f;
                    Quaternion rot = Quaternion.Euler(55f, 0f, 0f);
                    if (camPreset == "side")
                        rot = Quaternion.Euler(20f, 90f, 0f);
                    cam.transform.rotation = rot;
                    cam.transform.position = stage - cam.transform.forward * CamDistance;
                    cam.allowHDR = false;
                    UniversalAdditionalCameraData urp = camGo.AddComponent<UniversalAdditionalCameraData>();
                    urp.renderPostProcessing = true;
                    urp.renderShadows = false;
                    urp.SetRenderer(0);
                    lightGo = new GameObject("VfxStageLight");
                    Light lit = lightGo.AddComponent<Light>();
                    lit.type = LightType.Directional;
                    lit.intensity = 1f;
                    lit.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
                }
                else
                {
                    cam.CopyFrom(refCam);
                    cam.transform.rotation = refCam.transform.rotation;
                    if (camPreset == "side")
                    {
                        Vector3 right = refCam.transform.right;
                        cam.transform.position = stage - right * CamDistance;
                        cam.transform.rotation = Quaternion.LookRotation((stage - cam.transform.position).normalized, Vector3.up);
                    }
                    else
                    {
                        cam.transform.position = stage - refCam.transform.forward * CamDistance;
                    }
                    CopyUrpData(refCam, cam);
                }

                ortho = camPreset == "close" ? CloseOrtho : GameOrtho;
                if (!isolated && camPreset == "game" && refCam.orthographic)
                    ortho = refCam.orthographicSize;
                cam.orthographic = true;
                cam.orthographicSize = ortho;
                cam.enabled = false;

                if (isolated)
                {
                    bgGo = BuildBackgroundPlane(cam, stage, BgColor(bg));
                }

                if (!string.IsNullOrEmpty(tier))
                {
                    bool high = IsHighQuality(tier);
                    cam.allowHDR = high;
                    string rpPath = high ? request.highQualityRpPath : request.performanceRpPath;
                    string volPath = high ? request.highQualityVolumePath : request.performanceVolumePath;
                    var rp = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>(rpPath);
                    if (rp != null)
                    {
                        GraphicsSettings.defaultRenderPipeline = rp;
                        QualitySettings.renderPipeline = rp;
                        swappedRp = true;
                    }
                    else
                    {
                        tierLimitation = $"rp_asset_missing: {rpPath}";
                    }

                    var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(volPath);
                    if (profile != null)
                    {
                        volGo = new GameObject("VfxStageVolume");
                        Volume vol = volGo.AddComponent<Volume>();
                        vol.isGlobal = true;
                        vol.priority = 100f;
                        vol.sharedProfile = profile;
                        if (isolated && string.IsNullOrEmpty(tierLimitation))
                            tierLimitation = "tier volume injected in isolated stage; edit-mode postfx may not match gameplay";
                    }
                    else if (string.IsNullOrEmpty(tierLimitation))
                    {
                        tierLimitation = $"volume_profile_missing: {volPath}";
                    }
                }

                string outDir = OutDir(request.tag, prefabName);
                Directory.CreateDirectory(outDir);
                int tileRes = Mathf.Max(64, request.tileRes);
                int zoomRes = Mathf.Max(tileRes, request.zoomRes);
                int cols = 3;
                int rows = Mathf.Max(1, Mathf.CeilToInt(times.Length / (float)cols));
                Texture2D sheet = new Texture2D(tileRes * cols, tileRes * rows, TextureFormat.RGB24, false);
                Color32[] clear = new Color32[sheet.width * sheet.height];
                Color32 fill = isolated
                    ? (Color32)BgColor(bg)
                    : new Color32(0, 0, 0, 255);
                for (int i = 0; i < clear.Length; i++) clear[i] = fill;
                sheet.SetPixels32(clear);

                string[] framePaths = new string[times.Length];
                for (int i = 0; i < times.Length; i++)
                {
                    Scrub(roots, times[i]);
                    cam.orthographicSize = ortho;
                    Texture2D frame = Render(cam, zoomRes, zoomRes);
                    string framePath = Path.Combine(outDir, $"frame_{VfxStage.Ms(times[i])}.png");
                    File.WriteAllBytes(framePath, frame.EncodeToPNG());
                    framePaths[i] = framePath;
                    int col = i % cols;
                    int rowFromTop = i / cols;
                    int row = rows - 1 - rowFromTop;
                    BlitTile(sheet, frame, col, row, tileRes);
                    Object.DestroyImmediate(frame);
                    RefreshPerf(ref perf, maxParticlesSum);
                }

                sheet.Apply();
                string sheetPath = Path.Combine(OutRoot(request.tag), prefabName + "_sheet.png");
                File.WriteAllBytes(sheetPath, sheet.EncodeToPNG());
                Object.DestroyImmediate(sheet);

                var result = new VfxStageResult
                {
                    ok = true,
                    prefabPath = request.prefabPath,
                    prefabName = prefabName,
                    looping = looping,
                    duration = duration,
                    seed = seed,
                    camera = camPreset,
                    orthographicSize = ortho,
                    background = bg,
                    tier = tier ?? "none",
                    sheetPath = sheetPath,
                    framePaths = framePaths,
                    timestamps = times,
                    normalized = norms,
                    tierLimitation = tierLimitation,
                    isolatedStage = isolated,
                    instanceCount = instanceCount,
                    particleCountEstimate = maxParticlesSum,
                    perf = perf,
                    metadataPath = Path.Combine(OutRoot(request.tag), prefabName + "_meta.json")
                };
                VfxStage.WriteMetadata(result);
                return result;
            }
            finally
            {
                if (swappedRp)
                {
                    GraphicsSettings.defaultRenderPipeline = prevDefault;
                    QualitySettings.renderPipeline = prevQuality;
                }
                for (int i = 0; i < instances.Count; i++)
                    if (instances[i] != null) Object.DestroyImmediate(instances[i]);
                if (camGo != null) Object.DestroyImmediate(camGo);
                if (bgGo != null) Object.DestroyImmediate(bgGo);
                if (volGo != null) Object.DestroyImmediate(volGo);
                if (lightGo != null) Object.DestroyImmediate(lightGo);
            }
        }

        static VfxStagePerf SamplePerf(int particleCountEstimate)
        {
            var perf = new VfxStagePerf
            {
                mode = "edit",
                particleCount = particleCountEstimate,
                available = false
            };
            try
            {
                TrySampleRecorders(perf);
            }
            catch (System.Exception ex)
            {
                perf.available = false;
                perf.warning = "profiler_unavailable: " + ex.GetType().Name + " " + ex.Message;
            }
            if (!perf.available && string.IsNullOrEmpty(perf.warning))
                perf.warning = "profiler_unavailable: edit-mode recorders empty; particleCount estimate only";
            return perf;
        }

        static void RefreshPerf(ref VfxStagePerf perf, int particleCountEstimate)
        {
            if (perf == null)
            {
                perf = SamplePerf(particleCountEstimate);
                return;
            }
            perf.particleCount = particleCountEstimate;
            try
            {
                TrySampleRecorders(perf);
            }
            catch (System.Exception ex)
            {
                if (!perf.available)
                    perf.warning = "profiler_unavailable: " + ex.GetType().Name + " " + ex.Message;
            }
        }

        static void TrySampleRecorders(VfxStagePerf perf)
        {
            float? draw = ReadRecorderAvg("Draw Calls Count", false);
            float? batches = ReadRecorderAvg("Batches Count", false);
            float? main = ReadRecorderAvg("Main Thread", true);
            float? render = ReadRecorderAvg("Render Thread", true);
            float? gpu = ReadRecorderAvg("GPU Frame Time", true);
            if (!gpu.HasValue) gpu = ReadRecorderAvg("Gfx.WaitForPresentOnGfxThread", true);

            bool any = draw.HasValue || batches.HasValue || main.HasValue || render.HasValue || gpu.HasValue;
            if (!any)
            {
                perf.available = false;
                if (string.IsNullOrEmpty(perf.warning))
                    perf.warning = "profiler_unavailable: no Recorder samples in edit mode";
                return;
            }

            if (draw.HasValue) perf.drawCalls = MaxOr(perf.drawCalls, draw.Value);
            if (batches.HasValue) perf.batches = MaxOr(perf.batches, batches.Value);
            if (main.HasValue) perf.mainThreadMs = MaxOr(perf.mainThreadMs, main.Value);
            if (render.HasValue) perf.renderThreadMs = MaxOr(perf.renderThreadMs, render.Value);
            if (gpu.HasValue) perf.gpuMs = MaxOr(perf.gpuMs, gpu.Value);
            perf.available = true;
            perf.mode = "edit";
            perf.warning = null;
        }

        static float? MaxOr(float? prev, float next)
        {
            if (!prev.HasValue) return next;
            return next > prev.Value ? next : prev.Value;
        }

        static float? ReadRecorderAvg(string marker, bool timeNs)
        {
            try
            {
                using (var rec = ProfilerRecorder.StartNew(ProfilerCategory.Render, marker, 8))
                {
                    if (!rec.Valid || rec.Count == 0)
                    {
                        using (var rec2 = ProfilerRecorder.StartNew(ProfilerCategory.Internal, marker, 8))
                        {
                            if (!rec2.Valid || rec2.Count == 0) return null;
                            return AverageSamples(rec2, timeNs);
                        }
                    }
                    return AverageSamples(rec, timeNs);
                }
            }
            catch
            {
                return null;
            }
        }

        static float AverageSamples(ProfilerRecorder rec, bool timeNs)
        {
            long sum = 0;
            int n = 0;
            int count = rec.Count;
            for (int i = 0; i < count; i++)
            {
                sum += rec.GetSample(i).Value;
                n++;
            }
            if (n == 0) return 0f;
            double avg = sum / (double)n;
            if (timeNs) avg /= 1000000.0;
            return (float)avg;
        }

        static Color BgColor(string bg)
        {
            switch (bg)
            {
                case "black": return Color.black;
                case "bright": return new Color(0.92f, 0.92f, 0.94f, 1f);
                case "white": return Color.white;
                case "gray":
                case "grey":
                default: return new Color(0.45f, 0.45f, 0.48f, 1f);
            }
        }

        static bool IsHighQuality(string tier)
        {
            string t = tier.Trim().ToLowerInvariant();
            return t == "highquality" || t == "high" || t == "hq" || t == "high_quality";
        }

        static GameObject BuildBackgroundPlane(Camera cam, Vector3 stage, Color color)
        {
            float dist = Vector3.Dot(stage - cam.transform.position, cam.transform.forward);
            if (dist < 0.1f) dist = CamDistance;
            float planeDist = dist + 2f;
            Vector3[] corners = new Vector3[4];
            cam.CalculateFrustumCorners(new Rect(0f, 0f, 1f, 1f), planeDist, Camera.MonoOrStereoscopicEye.Mono, corners);
            for (int i = 0; i < 4; i++)
                corners[i] = cam.transform.TransformPoint(corners[i]);

            Vector3 bl = corners[0];
            Vector3 tl = corners[1];
            Vector3 tr = corners[2];
            Vector3 br = corners[3];
            Vector3 center = (bl + tl + tr + br) * 0.25f;
            float width = Vector3.Distance(bl, br);
            float height = Vector3.Distance(bl, tl);
            if (width < 0.01f) width = cam.orthographicSize * 2f * cam.aspect;
            if (height < 0.01f) height = cam.orthographicSize * 2f;

            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Quad);
            go.name = "VfxStageBackground";
            if (go.TryGetComponent(out Collider col)) Object.DestroyImmediate(col);
            go.transform.position = center;
            go.transform.rotation = Quaternion.LookRotation(cam.transform.forward, cam.transform.up);
            go.transform.localScale = new Vector3(width, height, 1f);

            var shader = Shader.Find("Universal Render Pipeline/Unlit");
            if (shader == null) shader = Shader.Find("Unlit/Color");
            if (shader == null) shader = Shader.Find("Sprites/Default");
            var mat = new Material(shader);
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
            if (mat.HasProperty("_Color")) mat.SetColor("_Color", color);
            go.TryGetComponent(out MeshRenderer r);
            r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            return go;
        }

        static void Scrub(List<ParticleSystem> roots, float t)
        {
            for (int i = 0; i < roots.Count; i++) roots[i].Simulate(0f, true, true, true);
            int steps = Mathf.Max(1, Mathf.RoundToInt(t / (1f / 60f)));
            for (int s = 0; s < steps; s++)
                for (int i = 0; i < roots.Count; i++) roots[i].Simulate(1f / 60f, true, false, true);
        }

        static List<ParticleSystem> TopLevel(ParticleSystem[] systems)
        {
            var roots = new List<ParticleSystem>();
            for (int i = 0; i < systems.Length; i++)
            {
                ParticleSystem ps = systems[i];
                bool hasPsAncestor = false;
                Transform p = ps.transform.parent;
                while (p != null)
                {
                    if (p.TryGetComponent(out ParticleSystem _)) { hasPsAncestor = true; break; }
                    p = p.parent;
                }
                if (!hasPsAncestor) roots.Add(ps);
            }
            return roots;
        }

        static Texture2D Render(Camera cam, int w, int h)
        {
            RenderTexture rt = RenderTexture.GetTemporary(w, h, 24, RenderTextureFormat.ARGB32);
            RenderTexture prev = RenderTexture.active;
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            Texture2D tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            cam.targetTexture = null;
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            return tex;
        }

        static void BlitTile(Texture2D sheet, Texture2D src, int col, int row, int tileRes)
        {
            Texture2D small = Downscale(src, tileRes, tileRes);
            sheet.SetPixels(col * tileRes, row * tileRes, tileRes, tileRes, small.GetPixels());
            Object.DestroyImmediate(small);
        }

        static Texture2D Downscale(Texture2D src, int w, int h)
        {
            RenderTexture rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32);
            RenderTexture prev = RenderTexture.active;
            Graphics.Blit(src, rt);
            RenderTexture.active = rt;
            Texture2D tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            return tex;
        }

        static Camera ResolveGameCamera()
        {
            Camera main = Camera.main;
            if (main != null) return main;
            Camera[] all = Object.FindObjectsByType<Camera>();
            for (int i = 0; i < all.Length; i++)
            {
                Camera c = all[i];
                if (c != null && c.gameObject.name != "VfxStageCam" && c.gameObject.name != "VfxPreviewCam")
                    return c;
            }
            return null;
        }

        static Vector3 StagePoint(Camera main)
        {
            Vector3 center;
            Ray ray = new Ray(main.transform.position, main.transform.forward);
            if (Physics.Raycast(ray, out RaycastHit hit, 200f)) center = hit.point;
            else
            {
                float dy = main.transform.position.y;
                float denom = -main.transform.forward.y;
                center = denom > 0.001f
                    ? main.transform.position + main.transform.forward * (dy / denom)
                    : main.transform.position + main.transform.forward * 20f;
            }
            Vector3 side = center + main.transform.right * 4f;
            if (Physics.Raycast(side + Vector3.up * 15f, Vector3.down, out RaycastHit ground, 60f))
                return ground.point + Vector3.up * 0.5f;
            return side + Vector3.up * 0.5f;
        }

        static void CopyUrpData(Camera src, Camera dst)
        {
            if (!src.TryGetComponent(out UniversalAdditionalCameraData s)) return;
            if (!dst.TryGetComponent(out UniversalAdditionalCameraData d))
                d = dst.gameObject.AddComponent<UniversalAdditionalCameraData>();
            d.renderPostProcessing = s.renderPostProcessing;
            d.antialiasing = s.antialiasing;
            d.renderShadows = s.renderShadows;
            d.volumeLayerMask = s.volumeLayerMask;
            d.SetRenderer(0);
        }

        static string OutRoot(string tag)
        {
            string root = Path.Combine(Directory.GetParent(Application.dataPath).FullName, "UISnapshots", "vfx", tag);
            Directory.CreateDirectory(root);
            return root;
        }

        static string OutDir(string tag, string prefabName) => Path.Combine(OutRoot(tag), prefabName);

        static uint Fnv(string s)
        {
            uint h = 2166136261u;
            foreach (char c in s) { h ^= c; h *= 16777619u; }
            return h == 0 ? 1u : h;
        }
    }
}
