Responsive UI + UI foundation practices (HARD RULE for UI layout work)

Loaded by: any task that builds, redesigns, or fixes runtime game UI layout, aspect-ratio / multi-resolution behavior, safe-area handling, HUD anchoring, UI scaling, or lays a UI base for a new game/feature. Pairs with unity-architecture.md (PRESENTATION CHOICE + LAYERED ARCHITECTURE, where UI logic lives), visual-ui-loop.md (the screenshot-compare loop), design-taste.md (the look/anti-slop layer that sits ON TOP of these mechanics: this file makes the UI not break, design-taste makes it not look generic), performance-testing.md (canvas perf), and the UI/UX trigger in conditional-routing.md.

Why this exists

ZC shipped its UI with no aspect-ratio strategy, then got patched fast with a FixedDesignFrame that uniform-scales the whole UI as one block to fit the screen. It never breaks, and it is the wrong primitive. It produced a postcard-in-the-middle UI, dead bars on off-ratio screens, a HUD that pulls away from the real screen edge, a second scaling stage stacked on CanvasScaler, and a prefab-hostile wrapper tool that reparents inherited children (the exact thing Unity prefab variants forbid). EO UI is bigger in magnitude, so the base has to be right from the first screen. This file is the grounded default so the next UI solution is a proper one, not another frankenstein patch.

THE ONE LINE
Unity UI is two contracts, not one rigid frame: edge HUD anchored to the safe-area edges, and centered content in a max-width responsive region. Scale for density, anchor/reflow for shape. Never uniform-scale the whole UI as a block.

BANNED PRIMITIVE (BLOCK as a foundation)
A FixedDesignFrame-style component that takes a fixed design rect and uniform-scales the entire UI (contain-fit, localScale = min(parentW/designW, parentH/designH)) to fit the screen is BLOCK as the UI foundation. It is acceptable ONLY for a genuinely fixed-aspect one-off (a kiosk, a single cutscene overlay) where letterbox is the intended spec. Reasons it fails as a base:
- it underfills one axis on any screen not matching the design aspect (dead bars: ~119px top/bottom on 1920x1080 under a 2173x954 frame, ~50px sides on 21:9, ~920px each side on 32:9, ~224px top/bottom on 4:3)
- it cannot glue HUD to real screen edges: children anchor to the shrunken wrapper, not the screen, so edge elements pull inward on off-ratio displays
- it is a second global scaling stage on top of CanvasScaler (two coordinate systems), and it scales art/text down soft instead of reflowing
- the wrapper tool reparents children into generated nodes, which Unity prefab variants forbid for inherited children, so it breaks on nested and zero-rect prefabs
Do not port FixedDesignFrame to EO or any new game. Retire it as a default.

RESPONSIVE RULES (the proper approach)
1 SPLIT-CONTRACT. Classify every widget up front as one of: edge-HUD, center-composition, or world/effect. Never let a widget float between contracts. One layout rule does not serve both edge-anchoring and centered composition.
2 EDGE HUD anchors to Screen.safeArea edges, never to a fake frame. Put a SafeAreaRoot container at the top of the HUD canvas that applies the safe-area insets, then edge rail containers (left/right/top/bottom) anchored to it. safe area == full screen on normal desktop, shrinks on mobile/TV/notch. uGUI: set anchorMin/anchorMax from the normalized safe rect (safe.position and safe.position+safe.size each divided by Screen.width/height), offsets zero. UI Toolkit: pad a root element; invert Y because Screen.safeArea is bottom-left origin while UI Toolkit is top-left.
3 CENTER CONTENT (menus, inventory, pause, settings, dialogs) lives in a max-width region that reflows/scrolls inside. On ultrawide the sides become margin/gutter, never one panel stretched edge-to-edge, never uniform-scaled as a postcard.
4 CANVASSCALER once per canvas, mode Scale With Screen Size, referenceResolution == the ACTUAL authored design resolution (1920x1080 for 16:9 desktop). The ZC mismatch (1920x1080 ref under a 2173x954 frame) is part of why it got messy. Match start at 0.5 for menus; for a desktop edge HUD test a height bias 0.75-1.0 first, since ultrawide adds width not height and a height bias keeps HUD widget size stabler as width grows. Never stack a second localScale wrapper on top of the scaler.
5 SCALE FOR DENSITY ONLY. CanvasScaler is a size policy so things are not tiny/huge across screens; it is not a layout system. The actual layout adaptation is anchors (uGUI) or flex/reflow (UI Toolkit). Trying to fix layout by scaling is the trap.
6 ANCHOR INTENTIONALLY. Center-anchored corner elements drift off-screen when the aspect ratio changes (center is the uGUI default, so this happens by accident constantly). Use anchor presets, pin corners/edges deliberately, mind the pivot (fitters resize around the pivot).
7 PLAYER-FACING UI SCALE option early, especially on PC. It is an accessibility win and cheap to add at the foundation, expensive to retrofit.
8 TEST MATRIX before declaring responsive: 1920x1080 baseline, 2560x1080 or 3440x1440 ultrawide, 1440x1080 4:3, plus a safe-area sim if UI is shared toward mobile. Use Device Simulator for safe-area/layout checks (it is not a perf simulator).

SYSTEM CHOICE (Unity 6, nuanced, not doctrinaire)
Unity 6.4 comparison: uGUI is the recommended general runtime system (established, production-proven); UI Toolkit is recommended for editor UI AND for intensive multi-resolution menu/HUD projects; uGUI is still stronger for world-space UI, custom materials/shaders, and Animator/Timeline-keyframed UI. So the choice is feature/workflow-driven, not "UI Toolkit for everything".
Default split: uGUI for HUD, world-space, and effect-heavy UI; UI Toolkit for menu-heavy front-end (settings, inventory, codex, store) if the team is comfortable with UXML/USS. If standardizing on one runtime system, choose uGUI baseline + strict discipline. Do not follow pre-6 "use UI Toolkit for all new UI" advice blindly; verify world-space/shader support against the exact 6000.x minor before committing.

ARCHITECTURE (thin views, cross-ref unity-architecture.md + codeRules 21-24)
- Views raise intents and render the state they are given. A view (MonoBehaviour or UIDocument controller) NEVER calls save/inventory/quest/network systems or singletons directly. That wiring spaghetti is half the ZC mess.
- A Presenter/Controller/ViewModel owns orchestration: MVP for uGUI screens/HUD, MVVM-lite for data-heavy UI Toolkit (Unity 6 runtime binding binds plain C# objects). Do not force a pattern onto a trivial widget.
- Events/observer for cross-cutting notifications (inventory changed, quest updated, locale changed); direct presenter-to-view calls for local screen logic; an event aggregator only when the subscription graph genuinely gets noisy. Do not default everything to a project-wide broadcast bus.
- Screen management is split, never one god UIManager: a ScreenRegistry (id > prefab/UXML/addressable), a ScreenNavigator (push/pop/replace + back-stack), a ModalService (blocking overlay + focus trap), a TransitionService (animation policy).

PREFAB DISCIPLINE (cross-ref unity-asset-hygiene.md + unity-mcp-and-builders.md)
- Tier UI as Screens / Panels / Widgets, separate folders + prefabs (uGUI) or UXML templates + USS classes (UI Toolkit).
- Prefab variants for controlled reuse: one variant hop by default, justify any deeper chain (the risk is override readability, not a numeric depth cap).
- FORBID any tool that reparents inherited prefab children or generates wrapper nodes inside a variant hierarchy (the SafeFrameWrapper failure mode). Build prefabs via the Procedural Builder pattern or Unity MCP, never hand-edited YAML.

PERFORMANCE (cross-ref performance-testing.md)
- Split canvases by update frequency: static UI and fast-changing HUD on separate (sub-)canvases, because any change rebuilds the whole canvas for batching.
- Disable Raycast Target on non-interactive graphics; remove the Graphic Raycaster from non-interactive canvases.
- uGUI: prefer anchors over layout groups on hot/dynamic UI; Grid Layout Group ignores child min/preferred/flexible size (uses its own cell), so it is wrong for content-sized cells; do not fight driven (read-only) layout properties by hand.
- UI Toolkit: move elements with style.translate not top/left/width/height/flex (those trigger layout recalc); set usageHints=DynamicTransform on frequent movers; use a dynamic/sprite atlas to cut batch breaks.

INPUT / A11Y / LOCALIZATION (foundation, not polish)
- Every interactive screen must work with mouse, keyboard, and gamepad before it is "done", and must declare a default focused element + a Back/Cancel contract. UI Toolkit needs explicit initial focus set on load, and re-set after a UIDocument disable/enable (the visual tree is recreated).
- Never bake user-facing text into a sprite if it could be localized, scaled, contrasted, or narrated. All strings go through Localization tables; run pseudo-localization before content lock.
- Encode minimum text size, 4.5:1 contrast for standard text, configurable UI scale, and subtitle background into the design-system tokens up front.

SELF-CHECK before declaring a UI solution proper
1 Does each widget belong to exactly one contract (edge / center / world)?
2 Is edge HUD anchored to the safe area, not a contained frame?
3 Is there exactly one CanvasScaler per canvas with referenceResolution == the real design res, and no second localScale wrapper on top?
4 Is layout done by anchors/reflow and scaling used only for density?
5 Do views stay thin (raise intent, render state, zero direct singleton/save/quest calls)?
6 No tool reparenting inherited prefab children?
If any answer is no, it is not proper yet.

Grounding: Unity 6.4 UI system comparison, com.unity.ugui docs (Canvas, CanvasScaler, RectTransform, Basic Layout, Auto Layout, multi-resolution guide), Screen.safeArea + Device Simulator docs, UI Toolkit runtime/layout/binding docs, Unity prefab-variant docs, Unity design-patterns course (MVP/MVVM/observer), plus direct inspection of ZC FixedDesignFrame.cs + SafeFrameWrapper.cs. Two ChatGPT deep-research reports synthesized this (2026-06-08).
