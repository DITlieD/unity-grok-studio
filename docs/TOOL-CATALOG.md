# Tool catalog

## blender-gen (MCP)
- Materials: gen_brick|stone|wood|metal|trim_material_tool
- Meshes: gen_parametric_wall|crate|arch|pipes|stairs_tool
- Review: generate_with_review_tool
- Optional cloud: mesh_retexture_tool, mesh_text_to_3d_tool (MESHY_API_KEY)
- blender_gen_version
- Outputs: `$UNITY_PROJECT/Assets/Generated` or `$CWD/Generated`

## img2threejs
- Skill-driven staged pipeline under `tools/img2threejs/`
- Requires vision (FreeLLMAPI or vision-check)

## SFX (`tools/sfx/`)
- analyze_audio.py, sfx_search.py, sfx_generate.py, assemble_sfx.py, render_audition_report.py
- Doctrine: retrieval before generation; human audition is done-gate
- `SFX_LIB` defaults to `$UNITY_GROK_ROOT/sfx_library`

## ARDY
- ardy_client.py (+ --synthetic), ardy_to_bvh.py, ardy_skeleton.py

## Unity Editor toolkit (after UPM install)
- ViewProbe, UISnapshot, SceneSnapshot
- Placement: scene_validate, place_object, adjust_object, place_relative, scatter_objects
- Anim: anim_snapshot, anim_filmstrip, anim_fit_state_speed, anim_clip_events
- VFX helpers

## Unity MCP (CoplayDev)
- Full editor surface when Unity + MCP For Unity listening

## Gates
- toban001, unity_symbol_census, mono_wire_census, scan_unity_patterns

## vision-check (MCP)
- vision_describe(image_path|base64, question) via FreeLLMAPI
