using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace UnityGrok.AgentDebug
{
    public class RuntimeStateExporter : MonoBehaviour
    {
        public KeyCode captureKey = KeyCode.F9;
        public float autoIntervalSeconds = 0f;
        public bool writeLatestAlias = true;
        public string subFolder = "AgentDebug";

        public List<Transform> watchedTransforms = new List<Transform>();
        public List<Animator> watchedAnimators = new List<Animator>();
        public List<Rigidbody> watchedRigidbodies = new List<Rigidbody>();

        readonly Dictionary<string, Func<string>> _watches = new Dictionary<string, Func<string>>();
        float _nextAuto;

        public void RegisterWatch(string key, Func<string> getter)
        {
            if (string.IsNullOrEmpty(key) || getter == null) return;
            _watches[key] = getter;
        }

        public void ClearWatch(string key)
        {
            _watches.Remove(key);
        }

        void Update()
        {
            if (captureKey != KeyCode.None && Input.GetKeyDown(captureKey)) Capture("manual");
            if (autoIntervalSeconds > 0f && Time.unscaledTime >= _nextAuto)
            {
                _nextAuto = Time.unscaledTime + autoIntervalSeconds;
                Capture("auto");
            }
        }

        public string Capture(string label = "capture")
        {
            var dto = new SnapshotDTO
            {
                label = label,
                frame = Time.frameCount,
                time = Time.time,
                scene = gameObject.scene.name,
            };

            foreach (var t in watchedTransforms)
            {
                if (t == null) continue;
                dto.transforms.Add(new TransformDTO
                {
                    name = t.name,
                    position = t.position,
                    eulerAngles = t.eulerAngles,
                    localScale = t.localScale,
                });
            }

            foreach (var a in watchedAnimators)
            {
                if (a == null) continue;
                var dt = new AnimatorDTO { name = a.name };
                if (a.layerCount > 0 && a.runtimeAnimatorController != null)
                {
                    var info = a.GetCurrentAnimatorStateInfo(0);
                    dt.stateHash = info.fullPathHash;
                    dt.normalizedTime = info.normalizedTime;
                }
                var ps = a.parameters;
                var lines = new List<string>(ps.Length);
                foreach (var p in ps)
                {
                    string v;
                    switch (p.type)
                    {
                        case AnimatorControllerParameterType.Float: v = a.GetFloat(p.nameHash).ToString("0.###"); break;
                        case AnimatorControllerParameterType.Int: v = a.GetInteger(p.nameHash).ToString(); break;
                        case AnimatorControllerParameterType.Bool: v = a.GetBool(p.nameHash).ToString(); break;
                        default: v = "trigger"; break;
                    }
                    lines.Add(p.name + "=" + v);
                }
                dt.parameters = lines.ToArray();
                dto.animators.Add(dt);
            }

            foreach (var rb in watchedRigidbodies)
            {
                if (rb == null) continue;
                dto.rigidbodies.Add(new RigidbodyDTO
                {
                    name = rb.name,
                    velocity = rb.linearVelocity,
                    angularVelocity = rb.angularVelocity,
                    isKinematic = rb.isKinematic,
                    sleeping = rb.IsSleeping(),
                });
            }

            foreach (var kv in _watches)
            {
                string val;
                try { val = kv.Value(); } catch (Exception e) { val = "ERR:" + e.Message; }
                dto.watches.Add(new WatchDTO { key = kv.Key, value = val });
            }

            string json = JsonUtility.ToJson(dto, true);
            string dir = Path.Combine(Application.persistentDataPath, subFolder);
            Directory.CreateDirectory(dir);
            string path = Path.Combine(dir, $"snapshot-{dto.frame}.json");
            File.WriteAllText(path, json);
            if (writeLatestAlias) File.WriteAllText(Path.Combine(dir, "latest.json"), json);
            return path;
        }

        [Serializable]
        public class SnapshotDTO
        {
            public string label;
            public int frame;
            public float time;
            public string scene;
            public List<TransformDTO> transforms = new List<TransformDTO>();
            public List<AnimatorDTO> animators = new List<AnimatorDTO>();
            public List<RigidbodyDTO> rigidbodies = new List<RigidbodyDTO>();
            public List<WatchDTO> watches = new List<WatchDTO>();
        }

        [Serializable]
        public class TransformDTO
        {
            public string name;
            public Vector3 position;
            public Vector3 eulerAngles;
            public Vector3 localScale;
        }

        [Serializable]
        public class AnimatorDTO
        {
            public string name;
            public int stateHash;
            public float normalizedTime;
            public string[] parameters;
        }

        [Serializable]
        public class RigidbodyDTO
        {
            public string name;
            public Vector3 velocity;
            public Vector3 angularVelocity;
            public bool isKinematic;
            public bool sleeping;
        }

        [Serializable]
        public class WatchDTO
        {
            public string key;
            public string value;
        }
    }
}
