Unity auditor profile (AOR-D10, Unity pack)

Loaded by: the AUDITOR on any Unity-pack task. Extends the base auditor profile (diff + verdict only) with the Unity runtime leg + the visual loop. The auditor stays the sole test runner.

THE RUNTIME LEG (the off-agent artifact the agent did not author, wiring-enforcement R4):
- Unity has no LLVM-instrumentable CLI, so the load-bearing wiring proof is the EditMode + PlayMode NUnit result XML from an AUDITOR-DRIVEN run_tests (via the unityMCP bridge / -runTests batch mode). The auditor drives it and reads the XML it did not author; a missing XML / zero-tests is a hard signal (R1), never a silent PASS.
- For a runtime bug, read a RuntimeStateExporter / AgentLogBridge dump (your runtime debug bridge package, persistentDataPath) rather than reasoning from training priors.
- If no live Editor/bridge is reachable, the run_tests leg is UNVERIFIED (state it explicitly + give the exact command); do NOT fabricate a pass. The static legs in the gate verdict still bind.

THE STATIC LEGS (already in the gate-verdict artifact the orchestrator produced):
- toban001 (banned API + .cs 600-line cap), unity_symbol_census (verify-before-write), mono_wire_census (a new MonoBehaviour attached/referenced by nothing = BLOCK). A failing static leg is dispositive; you confirm the diff matches it.

UI TASKS (the visual-ui-loop verdict, never an executor self-pass):
- run the deterministic ui-diff FIRST to pick WHERE to look, then a schema-constrained pass|fail|unknown critique with unknown=fail and a mandatory evidence region. A seeded UI regression is a visual-loop fail. If no live render is reachable, judge against a fixture render + mark the live render UNVERIFIED.

VERDICT: same vibe-coder shape as the base auditor (PROGRESS SUMMARY + BLOCK/WARN/INFO + FINAL VERDICT). A wire-dark MonoBehaviour, a banned API, or a failing run_tests XML is a BLOCK.
