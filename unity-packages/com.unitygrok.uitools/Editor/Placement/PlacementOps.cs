using System.Collections.Generic;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace UnityGrok.UITools.Placement
{
    public static class PlacementOps
    {
        const float GroundRayLift = 0.25f;

        public struct SnapResult
        {
            public bool noGround;
            public float clearanceBefore;
            public float clearanceAfter;
            public float appliedDeltaY;
        }

        public struct DepenetrateResult
        {
            public int iterations;
            public bool unresolved;
            public int remainingPairs;
            public Vector3 totalDelta;
        }

        public struct PipelineResult
        {
            public bool grounded;
            public bool noGround;
            public float clearance;
            public bool unresolved;
            public int remainingPairs;
            public int overlapCandidates;
            public Vector3 finalPosition;
        }

        public static bool TryWorldBounds(GameObject go, out Bounds bounds)
        {
            bounds = default;
            bool has = false;
            Physics.SyncTransforms();
            var renderers = go.GetComponentsInChildren<Renderer>();
            foreach (var r in renderers)
            {
                if (r == null || !r.enabled) continue;
                var b = r.bounds;
                if (!PlacementGeometry.IsValid(b) || (b.size.x == 0f && b.size.y == 0f && b.size.z == 0f)) continue;
                if (!has) { bounds = b; has = true; }
                else bounds.Encapsulate(b);
            }
            var col = PrimaryCollider(go);
            if (col != null)
            {
                if (!has) { bounds = col.bounds; has = true; }
                else bounds.Encapsulate(col.bounds);
            }
            return has;
        }

        public static SnapResult SnapToGround(GameObject go, float groundSearch, float tolerance, bool hasGroundY, float groundY, bool record)
        {
            var res = new SnapResult();
            Physics.SyncTransforms();
            if (!TryWorldBounds(go, out var b)) { res.noGround = true; return res; }

            Vector3 bottom = PlacementGeometry.BottomCenter(b);
            float surfaceY;
            bool found = RaycastGround(go.transform, bottom, groundSearch, GroundRayLift, out surfaceY);
            if (!found && hasGroundY) { surfaceY = groundY; found = true; }
            if (!found) { res.noGround = true; return res; }

            res.clearanceBefore = bottom.y - surfaceY;
            float deltaY = surfaceY - bottom.y;
            if (record) Undo.RecordObject(go.transform, "Snap To Ground");
            go.transform.position += new Vector3(0f, deltaY, 0f);
            res.appliedDeltaY = deltaY;

            Physics.SyncTransforms();
            TryWorldBounds(go, out b);
            res.clearanceAfter = PlacementGeometry.BottomCenter(b).y - surfaceY;
            return res;
        }

        public static DepenetrateResult Depenetrate(GameObject go, IList<Collider> against, int maxIterations, bool record, float requeryMargin = 0.02f)
        {
            var res = new DepenetrateResult();
            var self = PrimaryCollider(go);
            if (record) Undo.RecordObject(go.transform, "Depenetrate");

            for (int iter = 0; iter < maxIterations; iter++)
            {
                Physics.SyncTransforms();
                var candidates = against ?? OverlappingColliders(go, requeryMargin);
                Vector3 deepest = Vector3.zero;
                float deepestMag = 0f;
                int pairs = 0;
                foreach (var other in candidates)
                {
                    if (other == null || other == self) continue;
                    if (TryPairSeparation(go, self, other, out var mtv))
                    {
                        pairs++;
                        float m = mtv.magnitude;
                        if (m > deepestMag) { deepestMag = m; deepest = mtv; }
                    }
                }
                res.iterations = iter + 1;
                if (pairs == 0) { res.unresolved = false; res.remainingPairs = 0; return res; }
                go.transform.position += deepest;
                res.totalDelta += deepest;
            }

            Physics.SyncTransforms();
            var finalCandidates = against ?? OverlappingColliders(go, requeryMargin);
            int remaining = 0;
            foreach (var other in finalCandidates)
            {
                if (other == null || other == self) continue;
                if (TryPairSeparation(go, self, other, out _)) remaining++;
            }
            res.remainingPairs = remaining;
            res.unresolved = remaining > 0;
            return res;
        }

        public static void FaceToward(GameObject go, Vector3 target, bool record)
        {
            Vector3 dir = target - go.transform.position;
            dir.y = 0f;
            if (dir.sqrMagnitude < 1e-6f) return;
            if (record) Undo.RecordObject(go.transform, "Face Toward");
            go.transform.rotation = Quaternion.LookRotation(dir.normalized, Vector3.up);
        }

        public static void AlignToSurfaceNormal(GameObject go, Vector3 normal, bool record)
        {
            if (normal.sqrMagnitude < 1e-6f) return;
            if (record) Undo.RecordObject(go.transform, "Align To Surface");
            go.transform.rotation = Quaternion.FromToRotation(go.transform.up, normal.normalized) * go.transform.rotation;
        }

        public static PipelineResult RunPipeline(GameObject go, bool hasTarget, Vector3 target,
            float groundSearch, float tolerance, bool hasGroundY, float groundY, float overlapMargin, int maxIterations, bool doGroundSnap = true)
        {
            if (hasTarget) go.transform.position = target;
            Physics.SyncTransforms();

            if (doGroundSnap) SnapToGround(go, groundSearch, tolerance, hasGroundY, groundY, false);
            var initialCandidates = OverlappingColliders(go, overlapMargin);
            var dep = Depenetrate(go, null, maxIterations, false, overlapMargin);

            var r = new PipelineResult { overlapCandidates = initialCandidates.Count, unresolved = dep.unresolved, remainingPairs = dep.remainingPairs };

            Physics.SyncTransforms();
            float clearance = float.NaN;
            bool groundFound = false;
            if (TryWorldBounds(go, out var fb))
            {
                Vector3 bottom = PlacementGeometry.BottomCenter(fb);
                if (RaycastGround(go.transform, bottom, groundSearch, GroundRayLift, out var sy)) { clearance = bottom.y - sy; groundFound = true; }
                else if (hasGroundY) { clearance = bottom.y - groundY; groundFound = true; }
            }
            r.noGround = !groundFound;
            r.clearance = clearance;
            r.grounded = groundFound && Mathf.Abs(clearance) <= tolerance && !dep.unresolved;
            r.finalPosition = go.transform.position;
            return r;
        }

        public static List<Collider> OverlappingColliders(GameObject go, float margin)
        {
            var list = new List<Collider>();
            if (!TryWorldBounds(go, out var b)) return list;
            var hits = Physics.OverlapBox(b.center, b.extents + Vector3.one * margin, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore);
            foreach (var c in hits)
            {
                var ct = c.transform;
                if (ct == go.transform || ct.IsChildOf(go.transform)) continue;
                list.Add(c);
            }
            return list;
        }

        public static GameObject FindByPath(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var direct = GameObject.Find(path);
            if (direct != null) return direct;
            var all = Object.FindObjectsByType<Transform>(FindObjectsInactive.Include);
            foreach (var t in all)
                if (HierarchyPath(t) == path) return t.gameObject;
            foreach (var t in all)
                if (HierarchyPath(t).EndsWith("/" + path) || t.name == path) return t.gameObject;
            return null;
        }

        public static Collider PrimaryCollider(GameObject go)
        {
            var cols = go.GetComponentsInChildren<Collider>();
            Collider firstAny = null;
            foreach (var c in cols)
            {
                if (!c.enabled || c.isTrigger) continue;
                if (firstAny == null) firstAny = c;
                if (IsConvexForPenetration(c)) return c;
            }
            return firstAny;
        }

        public static bool IsConvexForPenetration(Collider c)
        {
            if (c is BoxCollider || c is SphereCollider || c is CapsuleCollider) return true;
            if (c is MeshCollider mc) return mc.convex;
            return false;
        }

        static bool TryPairSeparation(GameObject go, Collider self, Collider other, out Vector3 mtv)
        {
            mtv = Vector3.zero;
            if (self != null && (IsConvexForPenetration(self) || IsConvexForPenetration(other)))
            {
                Vector3 dir;
                float dist;
                if (Physics.ComputePenetration(
                        self, self.transform.position, self.transform.rotation,
                        other, other.transform.position, other.transform.rotation,
                        out dir, out dist) && dist > PlacementGeometry.Eps)
                {
                    mtv = dir * dist;
                    return true;
                }
                return false;
            }

            if (TryWorldBounds(go, out var gb))
            {
                var v = PlacementGeometry.MinimumTranslationVector(gb, other.bounds);
                if (v.magnitude > PlacementGeometry.Eps) { mtv = v; return true; }
            }
            return false;
        }

        static bool RaycastGround(Transform root, Vector3 bottom, float groundSearch, float lift, out float surfaceY)
        {
            surfaceY = 0f;
            var origin = bottom + Vector3.up * lift;
            var hits = Physics.RaycastAll(origin, Vector3.down, groundSearch + lift, ~0, QueryTriggerInteraction.Ignore);
            float top = float.NegativeInfinity;
            bool found = false;
            foreach (var h in hits)
            {
                var ct = h.collider.transform;
                if (ct == root || ct.IsChildOf(root)) continue;
                if (h.point.y > top) { top = h.point.y; found = true; }
            }
            if (found) surfaceY = top;
            return found;
        }

        static string HierarchyPath(Transform t)
        {
            var sb = new StringBuilder(t.name);
            var p = t.parent;
            while (p != null)
            {
                sb.Insert(0, '/').Insert(0, p.name);
                p = p.parent;
            }
            return sb.ToString();
        }
    }
}
