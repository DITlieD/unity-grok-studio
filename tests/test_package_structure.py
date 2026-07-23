import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = [
  'README.md','LICENSE','EXCLUDE.md','NOTICE',
  'scripts/bootstrap.sh','scripts/doctor.sh','scripts/hygiene_grep.sh',
  'scripts/install-deps.sh','scripts/wire-unity-project.sh','scripts/apply_models.sh',
  'plugin/plugin.json','plugin/.mcp.json','plugin/AGENTS.md','plugin/hooks/hooks.json',
  'plugin/hooks/bin/vision-predescribe.sh','plugin/hooks/bin/lia-pretool.sh',
  'mcp/blender-gen/server.py','mcp/vision-check/server.py',
  'mcp/wrappers/blender-gen.sh','mcp/wrappers/vision-check.sh',
  'tools/anim/ardy_client.py','tools/anim/ardy_to_bvh.py',
  'tools/sfx/analyze_audio.py','tools/gates/run_unity_static_gates.sh',
  'tools/free_chat_shim.py',
  'unity-packages/com.unitygrok.uitools/package.json',
  'sfx_library/README.md',
  'docs/TOOL-CATALOG.md','docs/UNITY-INSTALL.md','docs/VISION-ROUTING.md','docs/DEPENDENCIES.md',
]
def test_required_paths_exist():
    missing = [r for r in REQUIRED if not (ROOT/r).exists()]
    assert not missing, missing
def test_skills_present():
    skills = ROOT/'plugin'/'skills'
    for name in ['unity-scaffold','unity-gates','unity-toolkit','blender-gen','sfx-forge','img2threejs','anim-ardy','cheap-harness','install-deps']:
        assert (skills/name/'SKILL.md').is_file(), name
def test_package_json_ids():
    import json
    for pkg in ['com.unitygrok.uitools','com.unitygrok.agentdebug']:
        data = json.loads((ROOT/'unity-packages'/pkg/'package.json').read_text())
        assert data['name'] == pkg
