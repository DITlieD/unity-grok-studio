using UnityEngine;

namespace UnityGrok.UITools.Placement
{
    public static class PlacementGeometry
    {
        public const float Eps = 1e-5f;

        public static bool IsValid(Bounds b)
        {
            return IsFinite(b.center) && IsFinite(b.size)
                && b.size.x >= 0f && b.size.y >= 0f && b.size.z >= 0f;
        }

        public static bool Overlaps(Bounds a, Bounds b)
        {
            if (!IsValid(a) || !IsValid(b)) return false;
            Vector3 d = a.center - b.center;
            return (a.extents.x + b.extents.x) - Mathf.Abs(d.x) > Eps
                && (a.extents.y + b.extents.y) - Mathf.Abs(d.y) > Eps
                && (a.extents.z + b.extents.z) - Mathf.Abs(d.z) > Eps;
        }

        public static Vector3 MinimumTranslationVector(Bounds mover, Bounds fixedBounds)
        {
            if (!IsValid(mover) || !IsValid(fixedBounds)) return Vector3.zero;
            Vector3 d = mover.center - fixedBounds.center;
            float px = (mover.extents.x + fixedBounds.extents.x) - Mathf.Abs(d.x);
            float py = (mover.extents.y + fixedBounds.extents.y) - Mathf.Abs(d.y);
            float pz = (mover.extents.z + fixedBounds.extents.z) - Mathf.Abs(d.z);

            if (px <= Eps || py <= Eps || pz <= Eps) return Vector3.zero;

            if (px <= py && px <= pz) return new Vector3(d.x < 0f ? -px : px, 0f, 0f);
            if (py <= pz) return new Vector3(0f, d.y < 0f ? -py : py, 0f);
            return new Vector3(0f, 0f, d.z < 0f ? -pz : pz);
        }

        public static Vector3 BottomCenter(Bounds b)
        {
            return new Vector3(b.center.x, b.min.y, b.center.z);
        }

        public static bool Contains(Bounds outer, Bounds inner)
        {
            return outer.min.x <= inner.min.x && outer.max.x >= inner.max.x
                && outer.min.y <= inner.min.y && outer.max.y >= inner.max.y
                && outer.min.z <= inner.min.z && outer.max.z >= inner.max.z;
        }

        public static float ClearanceAbove(Bounds b, float surfaceY)
        {
            return b.min.y - surfaceY;
        }

        static bool IsFinite(Vector3 v)
        {
            return !(float.IsNaN(v.x) || float.IsInfinity(v.x)
                || float.IsNaN(v.y) || float.IsInfinity(v.y)
                || float.IsNaN(v.z) || float.IsInfinity(v.z));
        }
    }
}
