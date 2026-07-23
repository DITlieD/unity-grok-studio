Verify-before-write (HARD RULE, Unity pack)

Loaded by: any task writing C# that uses a version-sensitive or package-gated Unity symbol.

Unity APIs drift across versions and many live in optional packages. Before USING a symbol that could be absent on the target Unity version / project, VERIFY it exists:
- clear it via the unity_reflect MCP tool (reflect the type/member against the live Editor) or unity_docs (the versioned manual), THEN record a receipt: a // UNITY-VERIFY[<symbol>] marker on the use, or a row in the session receipt ledger.
- the unity_symbol_census gate BLOCKs a deny-tier symbol (e.g. FindObjectsByType, Awaitable) used with NO receipt; a verify-tier symbol (e.g. InputSystem, Addressables, Burst) without a receipt is a WARN.
- the policy table is .claude/unity-symbol-policy.json (frozen, R8). Extend it out-of-band, never inside a run.

This is the same discipline as the general anti-slopsquatting rule (never assume an API exists, verify first), specialized for Unity's version-drift surface.
