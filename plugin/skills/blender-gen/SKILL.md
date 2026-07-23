---
name: blender-gen
description: Parametric Blender materials and meshes via the blender-gen MCP. Use for brick/stone/wood/metal materials and wall/crate/arch/pipes/stairs meshes.
---
# blender-gen

MCP server: `blender-gen` (wrapper `$UNITY_GROK_ROOT/mcp/wrappers/blender-gen.sh`).

## Tools
- Materials: `gen_brick|stone|wood|metal|trim_material_tool`
- Meshes: `gen_parametric_wall|crate|arch|pipes|stairs_tool`
- Review: `generate_with_review_tool`
- Optional cloud: `mesh_retexture_tool`, `mesh_text_to_3d_tool` (needs MESHY_API_KEY)
- Version: `blender_gen_version`

## Output roots
- If `UNITY_PROJECT` points at a Unity project (has `Assets/`): `$UNITY_PROJECT/Assets/Generated/`
- Else: `$CWD/Generated/`

## Requirements
- Blender 5.x on PATH (or BLENDER_BIN)
- Package venv from `./scripts/bootstrap.sh`

Without Blender, tools should fail soft with install hints. Run `./scripts/doctor.sh`.
