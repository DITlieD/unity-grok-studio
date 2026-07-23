using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace UnityGrok.UITools.Anim
{
    public static class AnimGraphSnapshot
    {
        [MenuItem("Tools/UnityGrok/Snapshot Animator Graph")]
        public static void SnapshotSelectionMenu()
        {
            var sel = Selection.activeObject;
            var ac = sel as AnimatorController;
            if (ac == null && sel is GameObject go)
            {
                var an = go.GetComponentInChildren<Animator>();
                if (an != null) { Debug.Log($"AnimGraphSnapshot wrote {SnapshotAnimator(an)}"); return; }
            }
            if (ac == null)
            {
                Debug.LogWarning("AnimGraphSnapshot: select an AnimatorController asset or a GameObject with an Animator");
                return;
            }
            Debug.Log($"AnimGraphSnapshot wrote {SnapshotController(ac)}");
        }

        public static string SnapshotControllerPath(string assetPath)
        {
            var ac = AssetDatabase.LoadAssetAtPath<AnimatorController>(assetPath);
            if (ac == null) return null;
            return SnapshotController(ac, assetPath);
        }

        public static string SnapshotAnimator(Animator animator)
        {
            if (animator == null) return null;
            var rac = animator.runtimeAnimatorController;
            var ac = rac as AnimatorController;
            AnimatorOverrideController ovr = rac as AnimatorOverrideController;
            if (ac == null && ovr != null) ac = ResolveBase(ovr);
            if (ac == null) return null;
            string src = ovr != null ? "override" : "animator";
            var path = AssetDatabase.GetAssetPath(ac);
            return Emit(ac, animator.name, src, path, ovr);
        }

        public static string SnapshotController(AnimatorController ac, string assetPath = null)
        {
            assetPath = assetPath ?? AssetDatabase.GetAssetPath(ac);
            return Emit(ac, ac.name, "controller", assetPath, null);
        }

        static AnimatorController ResolveBase(AnimatorOverrideController ovr)
        {
            var b = ovr.runtimeAnimatorController;
            while (b is AnimatorOverrideController inner) b = inner.runtimeAnimatorController;
            return b as AnimatorController;
        }

        static string Emit(AnimatorController ac, string name, string source, string path, AnimatorOverrideController ovr)
        {
            var sb = new StringBuilder();
            sb.Append("{\"system\":\"anim\",\"source\":").Append(Str(source))
              .Append(",\"name\":").Append(Str(name))
              .Append(",\"path\":").Append(Str(path));

            sb.Append(",\"parameters\":[");
            var ps = ac.parameters;
            for (int i = 0; i < ps.Length; i++)
            {
                if (i > 0) sb.Append(',');
                var p = ps[i];
                sb.Append("{\"name\":").Append(Str(p.name))
                  .Append(",\"type\":").Append(Str(p.type.ToString()))
                  .Append(",\"default\":").Append(DefaultOf(p)).Append('}');
            }
            sb.Append(']');

            sb.Append(",\"layers\":[");
            var layers = ac.layers;
            for (int i = 0; i < layers.Length; i++)
            {
                if (i > 0) sb.Append(',');
                EmitLayer(sb, layers[i], i);
            }
            sb.Append(']');

            if (ovr != null)
            {
                var list = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<AnimationClip, AnimationClip>>();
                ovr.GetOverrides(list);
                sb.Append(",\"overrides\":[");
                bool f = true;
                foreach (var kv in list)
                {
                    if (kv.Value == null) continue;
                    if (!f) sb.Append(',');
                    f = false;
                    sb.Append("{\"original\":").Append(Str(kv.Key != null ? kv.Key.name : ""))
                      .Append(",\"override\":").Append(Str(kv.Value.name)).Append('}');
                }
                sb.Append(']');
            }

            sb.Append('}');
            return WriteOut(name, sb.ToString());
        }

        static void EmitLayer(StringBuilder sb, AnimatorControllerLayer layer, int index)
        {
            var sm = layer.stateMachine;
            sb.Append("{\"name\":").Append(Str(layer.name))
              .Append(",\"index\":").Append(index)
              .Append(",\"defaultWeight\":").Append(F(layer.defaultWeight))
              .Append(",\"blendingMode\":").Append(Str(layer.blendingMode.ToString()))
              .Append(",\"ikPass\":").Append(layer.iKPass ? "true" : "false")
              .Append(",\"syncedLayerIndex\":").Append(layer.syncedLayerIndex)
              .Append(",\"avatarMask\":").Append(MaskJson(layer.avatarMask))
              .Append(",\"defaultState\":").Append(Str(sm != null && sm.defaultState != null ? sm.defaultState.name : ""));

            sb.Append(",\"anyStateTransitions\":[");
            if (sm != null)
            {
                var any = sm.anyStateTransitions;
                for (int i = 0; i < any.Length; i++)
                {
                    if (i > 0) sb.Append(',');
                    EmitTransition(sb, any[i]);
                }
            }
            sb.Append(']');

            sb.Append(",\"states\":[");
            var collected = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, AnimatorState>>();
            CollectStates(sm, "", collected);
            for (int i = 0; i < collected.Count; i++)
            {
                if (i > 0) sb.Append(',');
                EmitState(sb, collected[i].Value, collected[i].Key);
            }
            sb.Append("]}");
        }

        static void CollectStates(AnimatorStateMachine sm, string prefix, System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, AnimatorState>> outList)
        {
            if (sm == null) return;
            var states = sm.states;
            for (int i = 0; i < states.Length; i++)
                outList.Add(new System.Collections.Generic.KeyValuePair<string, AnimatorState>(prefix, states[i].state));
            var subs = sm.stateMachines;
            for (int i = 0; i < subs.Length; i++)
            {
                var child = subs[i].stateMachine;
                CollectStates(child, prefix.Length == 0 ? child.name : prefix + "/" + child.name, outList);
            }
        }

        static void EmitState(StringBuilder sb, AnimatorState st, string prefix)
        {
            sb.Append("{\"name\":").Append(Str(prefix.Length == 0 ? st.name : prefix + "/" + st.name))
              .Append(",\"tag\":").Append(Str(st.tag))
              .Append(",\"speed\":").Append(F(st.speed))
              .Append(",\"speedParam\":").Append(Str(st.speedParameterActive ? st.speedParameter : ""))
              .Append(",\"cycleOffset\":").Append(F(st.cycleOffset))
              .Append(",\"mirror\":").Append(st.mirror ? "true" : "false")
              .Append(",\"writeDefaults\":").Append(st.writeDefaultValues ? "true" : "false")
              .Append(",\"motion\":").Append(MotionJson(st.motion));

            sb.Append(",\"transitions\":[");
            var tr = st.transitions;
            for (int i = 0; i < tr.Length; i++)
            {
                if (i > 0) sb.Append(',');
                EmitTransition(sb, tr[i]);
            }
            sb.Append("]}");
        }

        static void EmitTransition(StringBuilder sb, AnimatorStateTransition t)
        {
            sb.Append("{\"to\":").Append(Str(DestName(t)))
              .Append(",\"hasExitTime\":").Append(t.hasExitTime ? "true" : "false")
              .Append(",\"exitTime\":").Append(F(t.exitTime))
              .Append(",\"duration\":").Append(F(t.duration))
              .Append(",\"fixedDuration\":").Append(t.hasFixedDuration ? "true" : "false")
              .Append(",\"offset\":").Append(F(t.offset))
              .Append(",\"interruption\":").Append(Str(t.interruptionSource.ToString()))
              .Append(",\"canToSelf\":").Append(t.canTransitionToSelf ? "true" : "false")
              .Append(",\"conditions\":").Append(ConditionsJson(t.conditions))
              .Append('}');
        }

        static string DestName(AnimatorTransitionBase t)
        {
            if (t.isExit) return "[Exit]";
            if (t.destinationState != null) return t.destinationState.name;
            if (t.destinationStateMachine != null) return "[SM]" + t.destinationStateMachine.name;
            return "";
        }

        static string ConditionsJson(AnimatorCondition[] cs)
        {
            var sb = new StringBuilder("[");
            for (int i = 0; i < cs.Length; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append("{\"param\":").Append(Str(cs[i].parameter))
                  .Append(",\"mode\":").Append(Str(cs[i].mode.ToString()))
                  .Append(",\"threshold\":").Append(F(cs[i].threshold)).Append('}');
            }
            sb.Append(']');
            return sb.ToString();
        }

        static string MotionJson(Motion m)
        {
            if (m == null) return "null";
            if (m is AnimationClip clip)
            {
                var sb = new StringBuilder();
                sb.Append("{\"type\":\"clip\",\"name\":").Append(Str(clip.name))
                  .Append(",\"length\":").Append(F(clip.length))
                  .Append(",\"frameRate\":").Append(F(clip.frameRate))
                  .Append(",\"isLooping\":").Append(clip.isLooping ? "true" : "false")
                  .Append(",\"wrapMode\":").Append(Str(clip.wrapMode.ToString()))
                  .Append(",\"events\":").Append(EventsJson(clip)).Append('}');
                return sb.ToString();
            }
            if (m is BlendTree bt)
            {
                var sb = new StringBuilder();
                sb.Append("{\"type\":\"blendtree\",\"name\":").Append(Str(bt.name))
                  .Append(",\"blendType\":").Append(Str(bt.blendType.ToString()))
                  .Append(",\"blendParameter\":").Append(Str(bt.blendParameter))
                  .Append(",\"blendParameterY\":").Append(Str(bt.blendParameterY))
                  .Append(",\"children\":[");
                var ch = bt.children;
                for (int i = 0; i < ch.Length; i++)
                {
                    if (i > 0) sb.Append(',');
                    sb.Append("{\"threshold\":").Append(F(ch[i].threshold))
                      .Append(",\"position\":{\"x\":").Append(F(ch[i].position.x)).Append(",\"y\":").Append(F(ch[i].position.y)).Append('}')
                      .Append(",\"timeScale\":").Append(F(ch[i].timeScale))
                      .Append(",\"motion\":").Append(MotionJson(ch[i].motion)).Append('}');
                }
                sb.Append("]}");
                return sb.ToString();
            }
            return "{\"type\":\"unknown\",\"name\":" + Str(m.name) + "}";
        }

        static string EventsJson(AnimationClip clip)
        {
            var evs = AnimationUtility.GetAnimationEvents(clip);
            var sb = new StringBuilder("[");
            for (int i = 0; i < evs.Length; i++)
            {
                if (i > 0) sb.Append(',');
                var e = evs[i];
                sb.Append("{\"function\":").Append(Str(e.functionName))
                  .Append(",\"time\":").Append(F(e.time))
                  .Append(",\"normalizedTime\":").Append(F(clip.length > 0f ? e.time / clip.length : 0f))
                  .Append(",\"float\":").Append(F(e.floatParameter))
                  .Append(",\"int\":").Append(e.intParameter)
                  .Append(",\"string\":").Append(Str(e.stringParameter))
                  .Append(",\"object\":").Append(Str(e.objectReferenceParameter != null ? e.objectReferenceParameter.name : "")).Append('}');
            }
            sb.Append(']');
            return sb.ToString();
        }

        static string MaskJson(AvatarMask mask)
        {
            if (mask == null) return "null";
            int total = mask.transformCount;
            int active = 0;
            for (int i = 0; i < total; i++) if (mask.GetTransformActive(i)) active++;
            return "{\"name\":" + Str(mask.name) + ",\"activeTransforms\":" + active + ",\"totalTransforms\":" + total + "}";
        }

        static string DefaultOf(AnimatorControllerParameter p)
        {
            switch (p.type)
            {
                case AnimatorControllerParameterType.Float: return F(p.defaultFloat);
                case AnimatorControllerParameterType.Int: return p.defaultInt.ToString(CultureInfo.InvariantCulture);
                case AnimatorControllerParameterType.Bool: return p.defaultBool ? "true" : "false";
                default: return "false";
            }
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

        static string WriteOut(string name, string json)
        {
            var dir = Path.Combine(Directory.GetParent(Application.dataPath).FullName, "UISnapshots");
            Directory.CreateDirectory(dir);
            var safe = new StringBuilder();
            foreach (char c in name) safe.Append(char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_');
            var path = Path.Combine(dir, $"anim.{safe}.graph.json");
            File.WriteAllText(path, json);
            return path;
        }
    }
}
