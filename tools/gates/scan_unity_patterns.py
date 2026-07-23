#!/usr/bin/env python3
"""Static scanner for Unity C# anti-patterns.

Scans .cs files for common Unity mobile performance and correctness issues.
Uses regex-based pattern matching (not a full C# AST parser).

Exit codes:
  0 = all clear
  1 = findings detected (WARN or BLOCK)
  2 = usage error

Usage:
  python scan_unity_patterns.py <path> [--severity WARN|BLOCK]
"""

import sys
import re
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    severity: str  # WARN or BLOCK
    message: str


# Patterns that indicate we are inside Update/FixedUpdate/LateUpdate
UPDATE_METHOD_RE = re.compile(
    r'\b(void\s+)?(Update|FixedUpdate|LateUpdate|OnTriggerEnter|OnTriggerStay|'
    r'OnCollisionEnter|OnCollisionStay)\s*\('
)

# --- BLOCK-level patterns (always bad) ---

BLOCK_PATTERNS = [
    # Allocations that are always wrong in hot paths
    (
        re.compile(r'\bCamera\.main\b'),
        "CAMERA_MAIN_HOT",
        "Camera.main in potential hot path — calls FindGameObjectWithTag. Cache in Awake/Start.",
    ),
    (
        re.compile(r'\bSendMessage\s*\(|BroadcastMessage\s*\('),
        "SEND_MESSAGE",
        "SendMessage/BroadcastMessage uses reflection and allocates. Use events or direct calls.",
    ),
    (
        re.compile(r'\bResources\.Load\b'),
        "RESOURCES_LOAD",
        "Resources.Load in runtime code. Use Addressables for async loading.",
    ),
    (
        re.compile(r'\bApplication\.LoadLevel\b'),
        "DEPRECATED_LOADLEVEL",
        "Application.LoadLevel is deprecated. Use SceneManager.LoadSceneAsync.",
    ),
    (
        re.compile(r'\bOnGUI\s*\(\s*\)'),
        "ONGUI_RUNTIME",
        "OnGUI() is for editor only. Use UI Toolkit or Unity UI for runtime.",
    ),
    (
        re.compile(r'\bInput\.GetKey|Input\.GetAxis|Input\.GetButton|Input\.GetMouseButton'),
        "LEGACY_INPUT",
        "Legacy Input API. Use Input System package (InputAction).",
    ),
    (
        re.compile(r'\bWWW\b(?!\.)'),
        "DEPRECATED_WWW",
        "WWW class is removed. Use UnityWebRequest.",
    ),
    (
        re.compile(r'\bGUIText\b|GUITexture\b'),
        "DEPRECATED_GUI",
        "GUIText/GUITexture removed in Unity 2022+. Use TextMeshPro.",
    ),
    # Research-grounded additions (Gemini 2026-04-13)
    (
        re.compile(r'\bFindObjectOfType\s*<'),
        "DEPRECATED_FIND",
        "FindObjectOfType deprecated. Use FindFirstObjectByType (Unity 2023+).",
    ),
    (
        re.compile(r'\bPhysicMaterialCombine\b'),
        "DEPRECATED_PHYSIC_TYPO",
        "PhysicMaterialCombine renamed to PhysicsMaterialCombine. COMPILE_ERROR.",
    ),
    (
        re.compile(r'\basync\s+Task\b|\basync\s+void\b(?!.*Main)'),
        "ASYNC_TASK_UNITY",
        "async Task/void in Unity bypasses PlayerLoop (thread pool). Use async Awaitable or UniTask.",
    ),
    (
        re.compile(r'UnityEngine\.Social\b'),
        "REMOVED_SOCIAL",
        "UnityEngine.Social removed in Unity 6. Use third-party SDKs.",
    ),
    (
        re.compile(r'\bComponentSystem\b'),
        "DEPRECATED_DOTS",
        "ComponentSystem (DOTS legacy). Use partial struct : ISystem (DOTS 1.0+).",
    ),
    (
        re.compile(r'\bZenject\b|\bExtenject\b'),
        "ZENJECT_MOBILE",
        "Zenject/Extenject uses runtime reflection — slow startup, IL2CPP unsafe on mobile. Use VContainer or Reflex.",
    ),
    (
        re.compile(r'\.PreventDefault\s*\('),
        "DEPRECATED_PREVENT_DEFAULT",
        "evt.PreventDefault() deprecated in UI Toolkit. Use evt.StopPropagation().",
    ),
    (
        re.compile(r'Debug\.Log\b(?!Error|Warning|Exception)'),
        "DEBUG_LOG_PROD",
        "Debug.Log in potential production code — allocates (boxing + string). Guard with #if UNITY_EDITOR or strip.",
    ),
]

# --- Patterns that are BLOCK only inside Update-like methods ---

UPDATE_BLOCK_PATTERNS = [
    (
        re.compile(r'\bnew\s+(?![\s(])(?!NativeArray|NativeList|NativeSlice)\w+'),
        "ALLOC_IN_UPDATE",
        "Heap allocation (new) in hot path. Pre-allocate or use pooling.",
    ),
    (
        re.compile(r'\.Where\s*\(|\.Select\s*\(|\.OrderBy\s*\(|\.ToList\s*\(|\.ToArray\s*\(|\.Any\s*\(|\.Count\s*\('),
        "LINQ_IN_UPDATE",
        "LINQ in hot path allocates. Use manual loops.",
    ),
    (
        re.compile(r'"\s*\+\s*\w|\w\s*\+\s*"|\$"'),
        "STRING_CONCAT_UPDATE",
        "String concatenation/interpolation in hot path allocates. Use StringBuilder or cached strings.",
    ),
    (
        re.compile(r'\bFindObjectOfType\b|FindObjectsOfType\b'),
        "FIND_IN_UPDATE",
        "FindObjectOfType in hot path is O(n) per call. Cache references.",
    ),
    (
        re.compile(r'\bGetComponent\s*<|GetComponent\s*\('),
        "GETCOMPONENT_UPDATE",
        "GetComponent in hot path. Cache in Awake/Start.",
    ),
    (
        re.compile(r'\.material\b(?!\s*=)'),
        "MATERIAL_COPY",
        "Renderer.material creates a copy per access. Use sharedMaterial or MaterialPropertyBlock.",
    ),
    (
        re.compile(r'Instantiate\s*\('),
        "INSTANTIATE_UPDATE",
        "Instantiate in hot path. Use object pooling.",
    ),
    (
        re.compile(r'Destroy\s*\('),
        "DESTROY_UPDATE",
        "Destroy in hot path. Use object pooling (return to pool instead).",
    ),
    (
        re.compile(r'Debug\.Log\b'),
        "DEBUG_LOG_UPDATE",
        "Debug.Log in hot path — boxing + string allocation per frame. Strip or guard.",
    ),
    (
        re.compile(r'NavMesh\.CalculatePath\b'),
        "SYNC_NAVMESH_UPDATE",
        "Synchronous NavMesh.CalculatePath in hot path. Use NavMeshQuery + Job System + Burst.",
    ),
    (
        re.compile(r'\.vertices\b|\.normals\b|\.triangles\b|\.uv\b'),
        "MESH_ARRAY_UPDATE",
        "Mesh array property access allocates a new array. Cache in Start/Awake or use NativeArray API.",
    ),
]

# --- WARN-level patterns (context-dependent) ---

WARN_PATTERNS = [
    (
        re.compile(r'Animator\.SetFloat\s*\(\s*"|\bAnimator\.SetBool\s*\(\s*"|\bAnimator\.SetInteger\s*\(\s*"|\bAnimator\.SetTrigger\s*\(\s*"'),
        "STRING_ANIMATOR",
        "String-based Animator parameter. Cache with Animator.StringToHash in static readonly.",
    ),
    (
        re.compile(r'SceneManager\.LoadScene\s*\([^)]*\)\s*;(?!.*Async)'),
        "SYNC_SCENE_LOAD",
        "Synchronous scene load. Use LoadSceneAsync for non-blocking transitions.",
    ),
    (
        re.compile(r'\basync\s+void\b(?!.*Main)'),
        "ASYNC_VOID",
        "async void is fire-and-forget with no error handling. Use async Awaitable or async UniTask.",
    ),
    (
        re.compile(r'PlayerPrefs\.(Set|Get|Delete|Has)'),
        "PLAYERPREFS_USAGE",
        "PlayerPrefs for non-trivial data. Consider serialization system for game state.",
    ),
    (
        re.compile(r'Thread\.Sleep\b'),
        "THREAD_SLEEP",
        "Thread.Sleep blocks the thread. Use coroutines, Awaitable, or UniTask.Delay.",
    ),
    (
        re.compile(r'\bcatch\s*\{\s*\}|\bcatch\s*\([^)]*\)\s*\{\s*\}'),
        "EMPTY_CATCH",
        "Empty catch block silently swallows errors. Log or handle explicitly.",
    ),
    (
        re.compile(r'#region\b'),
        "REGION_USAGE",
        "Regions hide complexity. Split into smaller classes instead.",
    ),
    # Research-grounded additions
    (
        re.compile(r'\bArrayList\b|\bHashtable\b'),
        "NON_GENERIC_COLLECTION",
        "Non-generic collection. Use List<T>, Dictionary<TK,TV>, HashSet<T>.",
    ),
    (
        re.compile(r'Type\.GetType\s*\(|Assembly\.GetTypes\s*\(|\.GetMethod\s*\('),
        "REFLECTION_RUNTIME",
        "Runtime reflection — IL2CPP strips aggressively. MissingMethodException on device. Use AOT-safe patterns.",
    ),
    (
        re.compile(r'record\s+(struct\s+|class\s+)?\w+'),
        "RECORD_SERIALIZATION",
        "Record types: Unity serialization silently drops data (Inspector blank, JsonUtility fails). Don't use for serialized data.",
    ),
]


def is_in_update_scope(lines: List[str], line_idx: int) -> bool:
    """Heuristic: walk backwards to find if we're inside an Update-like method.

    Looks for Update/FixedUpdate/LateUpdate/OnTrigger*/OnCollision* method
    declarations by scanning backwards for the method signature and tracking
    brace depth.
    """
    # Fixed 2026-07-02 (synced from the liteGAME root): the old walker added the opener
    # line's brace delta and broke on depth<0 BEFORE testing that line for the Update
    # signature, so 'void Update() {' (K&R) and the bare '{' under 'void Update()' (Allman)
    # both escaped detection and every update-scope rule was dead except one-line methods.
    if UPDATE_METHOD_RE.search(lines[line_idx]):
        return True
    depth = 0
    for i in range(line_idx - 1, -1, -1):
        line = lines[i]
        delta = line.count('}') - line.count('{')
        if depth + delta < 0:
            if UPDATE_METHOD_RE.search(line):
                return True
            if line.strip().startswith('{') and i > 0 and UPDATE_METHOD_RE.search(lines[i - 1]):
                return True
            depth = 0
            continue
        depth += delta
    return False


def scan_file(filepath: str) -> List[Finding]:
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except (OSError, IOError):
        return findings

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Skip comments and empty lines
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*') or not stripped:
            continue

        # BLOCK patterns (context-free)
        for pattern, rule, message in BLOCK_PATTERNS:
            if pattern.search(line):
                findings.append(Finding(filepath, line_idx, rule, "BLOCK", message))

        # BLOCK patterns (only in Update-like methods)
        for pattern, rule, message in UPDATE_BLOCK_PATTERNS:
            if pattern.search(line):
                if is_in_update_scope(lines, line_idx - 1):
                    findings.append(Finding(filepath, line_idx, rule, "BLOCK", message))

        # WARN patterns
        for pattern, rule, message in WARN_PATTERNS:
            if pattern.search(line):
                findings.append(Finding(filepath, line_idx, rule, "WARN", message))

    return findings


def scan_directory(path: str) -> List[Finding]:
    all_findings = []
    for root, dirs, files in os.walk(path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in {
            'Library', 'Temp', 'Logs', 'obj', 'bin',
            '.git', 'node_modules', 'Packages',
        }]
        for fname in files:
            if fname.endswith('.cs'):
                fpath = os.path.join(root, fname)
                all_findings.extend(scan_file(fpath))
    return all_findings


def main():
    if len(sys.argv) < 2:
        print("Usage: scan_unity_patterns.py <path> [--severity WARN|BLOCK]", file=sys.stderr)
        sys.exit(2)

    target = sys.argv[1]
    min_severity = "WARN"
    if "--severity" in sys.argv:
        idx = sys.argv.index("--severity")
        if idx + 1 < len(sys.argv):
            min_severity = sys.argv[idx + 1].upper()

    if os.path.isfile(target):
        findings = scan_file(target)
    elif os.path.isdir(target):
        findings = scan_directory(target)
    else:
        print(f"Path not found: {target}", file=sys.stderr)
        sys.exit(2)

    if min_severity == "BLOCK":
        findings = [f for f in findings if f.severity == "BLOCK"]

    # Deduplicate: same file+line+rule
    seen = set()
    unique = []
    for f in findings:
        key = (f.file, f.line, f.rule)
        if key not in seen:
            seen.add(key)
            unique.append(f)

    blocks = [f for f in unique if f.severity == "BLOCK"]
    warns = [f for f in unique if f.severity == "WARN"]

    for f in sorted(unique, key=lambda x: (x.file, x.line)):
        print(f"[{f.severity}] {f.rule} {f.file}:{f.line} — {f.message}")

    print(f"\nSummary: {len(blocks)} BLOCK, {len(warns)} WARN across {len(set(f.file for f in unique))} files")

    if blocks:
        sys.exit(1)
    elif warns:
        sys.exit(0)  # WARN is advisory, not failure
    else:
        print("No findings.")
        sys.exit(0)


if __name__ == "__main__":
    main()