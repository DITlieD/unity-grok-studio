// Sample clean Unity-style C# for gate smoke (no banned APIs).
using UnityEngine;

namespace Studio.Sample
{
    public class CleanSample : MonoBehaviour
    {
        [SerializeField] private Transform _anchor;

        public void Ping()
        {
            if (_anchor != null)
            {
                _anchor.position = Vector3.zero;
            }
        }
    }
}
