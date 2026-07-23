using System.Collections.Generic;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace UnityGrok.UITools.Anim
{
    [McpForUnityTool("anim_fit_state_speed")]
    public static class AnimFitStateSpeedTool
    {
        public class Parameters
        {
            [ToolParameter("AnimatorController asset path (Assets/...)", Required = true)]
            public string controller { get; set; }

            [ToolParameter("Layer name holding the state", Required = true)]
            public string layer { get; set; }

            [ToolParameter("State name to fit", Required = true)]
            public string state { get; set; }

            [ToolParameter("Target playback duration in seconds the clip must fit into (code owns timing)", Required = true)]
            public float? duration { get; set; }

            [ToolParameter("Optional float parameter name to bind as the state speed multiplier so runtime can scale further", Required = false)]
            public string speed_param { get; set; }
        }

        public static object HandleCommand(JObject @params)
        {
            string ctrlPath = @params?["controller"]?.ToString();
            string layerName = @params?["layer"]?.ToString();
            string stateName = @params?["state"]?.ToString();
            var durTok = @params?["duration"];
            string speedParam = @params?["speed_param"]?.ToString();

            if (string.IsNullOrEmpty(ctrlPath)) return new ErrorResponse("missing 'controller'");
            if (durTok == null || durTok.Type == JTokenType.Null) return new ErrorResponse("missing 'duration'");
            float duration = durTok.Value<float>();
            if (duration <= 0f) return new ErrorResponse("duration must be > 0");

            var ac = AssetDatabase.LoadAssetAtPath<AnimatorController>(ctrlPath);
            if (ac == null) return new ErrorResponse($"controller_not_found: {ctrlPath}");

            AnimatorControllerLayer layer = null;
            foreach (var l in ac.layers) if (l.name == layerName) { layer = l; break; }
            if (layer == null) return new ErrorResponse($"layer_not_found: {layerName}");

            var st = FindState(layer.stateMachine, stateName);
            if (st == null) return new ErrorResponse($"state_not_found: {stateName} in layer {layerName}");

            var clip = st.motion as AnimationClip;
            if (clip == null) return new ErrorResponse($"state_motion_not_a_clip: {stateName} (motion={(st.motion == null ? "none" : st.motion.GetType().Name)})");
            if (clip.length <= 0f) return new ErrorResponse($"clip_zero_length: {clip.name}");

            float computed = clip.length / duration;

            if (!string.IsNullOrEmpty(speedParam))
            {
                bool ok = false;
                foreach (var p in ac.parameters) if (p.name == speedParam && p.type == AnimatorControllerParameterType.Float) { ok = true; break; }
                if (!ok) return new ErrorResponse($"speed_param_not_a_float_parameter: {speedParam}");
            }

            Undo.RecordObject(st, "anim_fit_state_speed");
            st.speed = computed;
            if (!string.IsNullOrEmpty(speedParam))
            {
                st.speedParameterActive = true;
                st.speedParameter = speedParam;
            }
            EditorUtility.SetDirty(ac);
            AssetDatabase.SaveAssets();

            float effective = clip.length / st.speed;
            return new SuccessResponse(
                $"anim_fit_state_speed: {stateName} clip={clip.name} len={clip.length:0.###}s speed={st.speed:0.###} -> {effective:0.###}s (target {duration:0.###}s)",
                new
                {
                    state = stateName,
                    clip = clip.name,
                    clipLength = clip.length,
                    targetDuration = duration,
                    computedSpeed = computed,
                    appliedSpeed = st.speed,
                    effectiveDuration = effective,
                    speedParam = st.speedParameterActive ? st.speedParameter : null
                });
        }

        static AnimatorState FindState(AnimatorStateMachine sm, string name)
        {
            if (sm == null) return null;
            foreach (var cs in sm.states) if (cs.state.name == name) return cs.state;
            foreach (var child in sm.stateMachines)
            {
                var r = FindState(child.stateMachine, name);
                if (r != null) return r;
            }
            return null;
        }
    }
}
