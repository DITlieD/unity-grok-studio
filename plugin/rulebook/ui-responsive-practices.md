# UI responsive practices (Unity uGUI / UI Toolkit)

## Default strategy
Do **not** ship a single uniform whole-UI scale wrapper (postcard-in-the-middle, dead bars
on off-ratio screens, HUD pulled away from screen edges, second scale stage stacked on
CanvasScaler, prefab-hostile reparent wrappers). Prefer proper responsive layout.

## Rules
1. One **CanvasScaler** per canvas, mode Scale With Screen Size.
2. `referenceResolution` matches the **actual authored** design resolution (e.g. 1920×1080 for 16:9).
3. Match width/height bias: start ~0.5 for menus; for edge HUDs try height bias 0.75–1.0
   (ultrawide adds width, not height).
4. Never stack a second localScale wrapper on top of the scaler.
5. Use anchors, layout groups, and safe area (`Screen.safeArea`) for device notches.
6. Views raise intents and render state they are given — never call save/inventory/quest/
   network systems or singletons directly from views.
7. Prefer prefab-friendly hierarchy; do not reparent inherited children in ways prefab
   variants forbid.

## UI Toolkit
Prefer Flex layout + USS for multi-resolution; keep design tokens (spacing, type scale)
in shared USS. Bind views to view-models rather than global singletons.

## Testing
Exercise at least 16:9, 16:10, 21:9, and a tall mobile aspect in Device Simulator / game view
before claiming UI done.
