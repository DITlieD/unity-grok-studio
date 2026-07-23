UNITY PACK GATE CHECKLIST (read + run by the core auditor when the unity pack is active, C4)

The core auditor reads this file during AUDITING when projects.toml lists "unity" in the active project packs. Verdicts feed the audit as BLOCK/WARN.

GATE U1 console-clean. After a play-mode / edit-mode pass, the Unity console must be free of errors and of new warnings introduced by the changeset. Any compile error or new error-level console entry = BLOCK.

GATE U2 C# symbol verification (verify-before-write.md). Every C# symbol the changeset references (type, method, field, UnityEngine/package API) must exist before it is written. A referenced symbol that does not resolve = BLOCK. The blacklist of non-existent-but-plausible APIs in verify-before-write.md is checked.

GATE U3 playmode smoke. The affected scene/feature drives through its real entry (a scene load, a builder invocation, an AiTools call) without throwing. A NullReferenceException / missing-component / missing-asset on the smoke path = BLOCK.

GATE U4 asset hygiene (unity-asset-hygiene.md). No orphaned .meta, no broken GUID reference, no asset imported outside the project conventions introduced by the changeset = WARN (BLOCK if a broken reference breaks the build).

The maintainability scan and CoVe review are UNCONDITIONAL language-general legs in the core auditor and run regardless of pack.