using System.Collections.Generic;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools.Anim
{
    [McpForUnityTool("anim_clip_events")]
    public static class AnimClipEventsTool
    {
        public class Parameters
        {
            [ToolParameter("Asset path of the clip: an .anim, or an .fbx containing the clip", Required = true)]
            public string clip { get; set; }

            [ToolParameter("Clip name when the asset holds several clips (fbx)", Required = false)]
            public string clip_name { get; set; }

            [ToolParameter("'get' (read events) or 'set' (replace events). Default 'get'", Required = false)]
            public string action { get; set; }

            [ToolParameter("Events for 'set': array of {function, time or normalizedTime, float, int, string}", Required = false)]
            public object[] events { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string path = @params?["clip"]?.ToString();
            string clipName = @params?["clip_name"]?.ToString();
            string action = (@params?["action"]?.ToString() ?? "get").ToLowerInvariant();

            if (string.IsNullOrEmpty(path)) return new ErrorResponse("missing 'clip'");
            var importer = AssetImporter.GetAtPath(path);
            bool isModel = importer is ModelImporter;

            var clip = LoadClip(path, clipName);
            if (clip == null) return new ErrorResponse($"clip_not_found: {path} name={clipName}");

            if (action == "get")
            {
                return new SuccessResponse($"anim_clip_events: {clip.name} has {AnimationUtility.GetAnimationEvents(clip).Length} events",
                    new { clip = clip.name, imported = isModel, events = Dump(clip) });
            }

            if (action != "set") return new ErrorResponse($"unknown action: {action}");

            var arr = @params?["events"] as JArray;
            if (arr == null) return new ErrorResponse("'set' requires 'events' array");
            var built = Build(arr, clip.length, out string err);
            if (err != null) return new ErrorResponse(err);

            if (isModel)
            {
                var mi = (ModelImporter)importer;
                var clips = mi.clipAnimations;
                if (clips == null || clips.Length == 0) clips = mi.defaultClipAnimations;
                bool matched = false;
                foreach (var ca in clips)
                {
                    if (ca.name == clip.name || (!string.IsNullOrEmpty(clipName) && ca.name == clipName))
                    {
                        ca.events = built;
                        matched = true;
                    }
                }
                if (!matched) return new ErrorResponse($"clip_not_in_importer: {clip.name} (available: {Names(clips)})");
                mi.clipAnimations = clips;
                mi.SaveAndReimport();
            }
            else
            {
                AnimationUtility.SetAnimationEvents(clip, built);
                EditorUtility.SetDirty(clip);
                AssetDatabase.SaveAssets();
            }

            var reread = LoadClip(path, clipName);
            return new SuccessResponse($"anim_clip_events: set {built.Length} events on {clip.name} ({(isModel ? "reimported fbx" : "anim asset")})",
                new { clip = clip.name, imported = isModel, wrote = built.Length, events = Dump(reread) });
        }

        static AnimationEvent[] Build(JArray arr, float length, out string err)
        {
            err = null;
            var list = new List<AnimationEvent>(arr.Count);
            for (int i = 0; i < arr.Count; i++)
            {
                var e = arr[i] as JObject;
                if (e == null) { err = $"event[{i}] not an object"; return null; }
                string fn = e["function"]?.ToString();
                if (string.IsNullOrEmpty(fn)) { err = $"event[{i}] missing 'function'"; return null; }
                float time;
                if (e["normalizedTime"] != null && e["normalizedTime"].Type != JTokenType.Null)
                    time = e["normalizedTime"].Value<float>() * length;
                else if (e["time"] != null && e["time"].Type != JTokenType.Null)
                    time = e["time"].Value<float>();
                else { err = $"event[{i}] needs 'time' or 'normalizedTime'"; return null; }
                var ev = new AnimationEvent { functionName = fn, time = time };
                if (e["float"] != null && e["float"].Type != JTokenType.Null) ev.floatParameter = e["float"].Value<float>();
                if (e["int"] != null && e["int"].Type != JTokenType.Null) ev.intParameter = e["int"].Value<int>();
                if (e["string"] != null && e["string"].Type != JTokenType.Null) ev.stringParameter = e["string"].ToString();
                list.Add(ev);
            }
            list.Sort((a, b) => a.time.CompareTo(b.time));
            return list.ToArray();
        }

        static object Dump(AnimationClip clip)
        {
            var evs = AnimationUtility.GetAnimationEvents(clip);
            var outList = new List<object>(evs.Length);
            foreach (var e in evs)
                outList.Add(new
                {
                    function = e.functionName,
                    time = e.time,
                    normalizedTime = clip.length > 0f ? e.time / clip.length : 0f,
                    floatParam = e.floatParameter,
                    intParam = e.intParameter,
                    stringParam = e.stringParameter
                });
            return outList;
        }

        static string Names(ModelImporterClipAnimation[] clips)
        {
            var sb = new System.Text.StringBuilder();
            foreach (var c in clips) sb.Append(c.name).Append(' ');
            return sb.ToString().Trim();
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
    }
}
