Performance testing and profiling (Unity mobile)

Loaded when: writing performance-sensitive code, optimizing, adding profiling, setting up CI performance gates.
Research basis: Gemini Deep Research 2026-04-13, Unity Performance Testing Extension docs.


Profiling tools (use in this order):

1. Unity Profiler (built-in, free): first pass for CPU frame time, GC allocations, rendering stats.
   - Add Profiler.BeginSample("SystemName")/EndSample() markers around critical paths (AI, physics, procgen, asset loading).
   - Deep profiling: ON for allocation tracing, OFF for timing (deep profiling alters perf characteristics).

2. Memory Profiler (com.unity.memoryprofiler, free): managed + native memory snapshots with diffing.
   - Leak detection workflow: snapshot empty scene -> load gameplay -> snapshot -> unload -> snapshot -> diff 1st vs 3rd.

3. Frame Debugger (built-in): for draw call analysis. Cannot run headless — editor only.
   - For CI: use RenderDoc or Android GPU Inspector (AGI) with command-line capture on device.

4. Unity Project Auditor (com.unity.project-auditor v1.0, free): batch-mode static analysis.
   - Checks: non-power-of-two textures, meshes exceeding vertex budgets, audio missing mobile compression.
   - CI integration: ProjectAuditorCI.AuditAndExport -> JSON report.
   - Docs: https://docs.unity3d.com/Packages/com.unity.project-auditor@1.0/manual/index.html


Performance Testing Extension (com.unity.test-framework.performance v3.1.x):

Setup: add Assembly Definition referencing Unity.PerformanceTesting assembly.
CI gotcha: Managed Code Stripping strips the framework via reflection. Fix with link.xml:
  <assembly fullname="Unity.PerformanceTesting" preserve="all"/>

Use [Performance] attribute on test methods. Measure with:
  Measure.Method(() => { ... }).Run();
  Measure.ProfilerMarkers(new SampleGroupDefinition("MarkerName"));
  Measure.Frames().WarmupCount(5).MeasurementCount(30).Run();

Regression detection: Unity Performance Benchmark Reporter (free, open-source).
  CLI: dotnet UnityPerformanceBenchmarkReporter.dll --baseline=baseline.xml --results=current/ --reportdirpath=report/
  Threshold: set in SampleGroupDefinition (e.g. 0.15f = 15% regression = fail).
  Dynamic: fail only if current median > trailing 5 successful runs median (filters hardware variance).
  Source: https://github.com/Unity-Technologies/PerformanceBenchmarkReporter


Roslyn analyzers for GC prevention (CI-integrated):

Microsoft.Unity.Analyzers (free, open-source): baseline checks (empty Update, etc.).
HotPathAllocationAnalyzer: https://github.com/Abc-Arbitrage/HotPathAllocationAnalyzer
  - Scans AST for allocations/boxing/closures in hot paths. Whitelisting config for acceptable allocs.
  - Add TreatWarningsAsErrors in csc.rsp to make heap alloc in Update() a build break.


Frame budget enforcement:

60 FPS = 16.67ms; 30 FPS = 33.33ms. Enforce on MILLISECOND thresholds, not FPS averages.
FPS is non-linear and hides micro-stutters: 59 frames in 0.75s + 1 frame in 0.25s = 60 FPS average but 250ms freeze.
Measure 99th percentile frame time, not just median. Spikes kill user experience.
Unity exit codes do NOT auto-fail CI. Capture $LastExitCode (PowerShell) or throw BuildFailedException.

Per-system budgets:
  Any single system consistently >2ms: needs profiling and optimization or frame-spreading.
  Draw calls: <150-200/frame for low-end mobile (Mali-G52, Adreno 610).
  Triangles: <100,000/frame on screen.
  Texture memory: <200MB total for low-end (2-3GB RAM devices). OS reserves rest; OOM kill beyond ~300-512MB usable.


Hard budgets (BLOCK if exceeded without justification):

Memory budget for low-end compatibility: <150MB total app memory.
Draw calls: <200/frame.
Frame time 99th percentile: <33.33ms (for 30fps target) or <16.67ms (for 60fps target).
Build size: monitor with Build Report Inspector (com.unity.build-report-inspector, free).


Device testing matrix (minimum for indie, 3-4 physical devices):

1. Baseline Android: older device, Android 11, 2-3GB RAM (catches strict memory limits).
2. Modern Mainstream Android: mid-range SoC (Adreno 610 / Mali-G52 class).
3. OEM-Specific: Xiaomi MIUI or Samsung One UI (aggressive background process killers).
4. Baseline iOS: older iPhone (Apple RAM limits + Metal compliance).

Unity Device Simulator (com.unity.device-simulator): simulates screen layouts/notches/safe areas ONLY. Runs on host GPU/CPU, NOT ARM architecture. Does NOT simulate tile-based rendering, mobile memory bandwidth, or thermal throttling. Never trust it for performance validation.

Cloud device farms for extended coverage:
  Firebase Test Lab: paid + generous free tier, native game loop testing, gcloud CLI integration.
  AWS Device Farm: paid per device-minute, hundreds of models, complex setup.


Adaptive performance:

Use Unity Adaptive Performance APIs for real-time thermal state callbacks.
On throttling warning: step down framerate, lower LOD bias, disable post-processing.
NEVER ship with uncapped framerate on mobile — thermal throttling drops 60 FPS to 15 FPS after 3 minutes of sustained load. Cap to 30 FPS as default, let user opt into 60 FPS.