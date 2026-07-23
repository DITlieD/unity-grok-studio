#!/usr/bin/env python3
"""blender-gen MCP — typed seeded generators (not raw blender exec).

Params are JSON-injected as data, never code-concatenated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

LIB = Path(__file__).resolve().parent / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from blender_gen import version_info  # noqa: E402
from blender_gen.mats import (  # noqa: E402
    gen_brick_material,
    gen_metal_material,
    gen_stone_material,
    gen_trim_material,
    gen_wood_material,
)
from blender_gen.mesh import (  # noqa: E402
    gen_arch,
    gen_crate,
    gen_parametric_wall,
    gen_pipes,
    gen_stairs,
)
from blender_gen.meshy_wrap import mesh_retexture, mesh_text_to_3d  # noqa: E402
from blender_gen.review_loop import generate_with_review, save_run_record  # noqa: E402

mcp = FastMCP("blender-gen")


@mcp.tool()
def blender_gen_version() -> dict[str, Any]:
    """Return SDK version dict (hello / health)."""
    return version_info()


@mcp.tool()
def gen_brick_material_tool(
    game_slug: str = "default",
    seed: int = 184,
    size: int = 2048,
    mortar: float = 0.02,
    variation: float = 0.15,
    final: bool = False,
    review: bool = False,
) -> dict[str, Any]:
    """Generate tileable brick PBR material maps + diagnostics + manifest."""
    params = {
        "game_slug": game_slug,
        "size": size,
        "mortar": mortar,
        "variation": variation,
        "final": final,
    }
    if review:
        def _gen(**kw):
            p = {**params, **{k: v for k, v in kw.items() if k != "seed"}}
            return gen_brick_material(seed=kw["seed"], **p)

        rec = generate_with_review(_gen, seed=seed, base_params=params)
        out = Path(rec["result"]["out_dir"]) / "review_record.json"
        save_run_record(out, rec)
        rec["review_record"] = str(out)
        return rec
    return gen_brick_material(seed=seed, **params)


@mcp.tool()
def gen_stone_material_tool(game_slug: str = "default", seed: int = 184, size: int = 2048) -> dict:
    return gen_stone_material(game_slug=game_slug, seed=seed, size=size)


@mcp.tool()
def gen_wood_material_tool(game_slug: str = "default", seed: int = 184, size: int = 2048) -> dict:
    return gen_wood_material(game_slug=game_slug, seed=seed, size=size)


@mcp.tool()
def gen_metal_material_tool(game_slug: str = "default", seed: int = 184, size: int = 2048) -> dict:
    return gen_metal_material(game_slug=game_slug, seed=seed, size=size)


@mcp.tool()
def gen_trim_material_tool(game_slug: str = "default", seed: int = 184, size: int = 2048) -> dict:
    return gen_trim_material(game_slug=game_slug, seed=seed, size=size)


@mcp.tool()
def gen_parametric_wall_tool(
    game_slug: str = "default",
    seed: int = 184,
    length: float = 12.0,
    height: float = 4.0,
    depth: float = 0.5,
    gate_w: float = 0.0,
    gate_h: float = 0.0,
    gate_arch: bool = False,
    buttresses: bool = False,
    battlements: bool = False,
) -> dict:
    """Parametric brick wall + GLB + mesh_stats + 3-view."""
    gate = None
    if gate_w > 0 and gate_h > 0:
        gate = {"w": gate_w, "h": gate_h, "arch": gate_arch}
    return gen_parametric_wall(
        game_slug=game_slug,
        seed=seed,
        length=length,
        height=height,
        depth=depth,
        gate=gate,
        buttresses=buttresses,
        battlements=battlements,
    )


@mcp.tool()
def gen_crate_tool(game_slug: str = "default", seed: int = 184, size: float = 1.0) -> dict:
    return gen_crate(game_slug=game_slug, seed=seed, size=size)


@mcp.tool()
def gen_arch_tool(game_slug: str = "default", seed: int = 184, width: float = 4.0, height: float = 3.0) -> dict:
    return gen_arch(game_slug=game_slug, seed=seed, width=width, height=height)


@mcp.tool()
def gen_pipes_tool(game_slug: str = "default", seed: int = 184, length: float = 4.0) -> dict:
    return gen_pipes(game_slug=game_slug, seed=seed, length=length)


@mcp.tool()
def gen_stairs_tool(game_slug: str = "default", seed: int = 184, steps: int = 8) -> dict:
    return gen_stairs(game_slug=game_slug, seed=seed, steps=steps)


@mcp.tool()
def mesh_retexture_tool(
    game_slug: str = "default",
    input_glb: str = "",
    style_prompt: str = "weathered stone",
    seed: int = 0,
) -> dict:
    """Meshy retexture wrapper (requires MESHY_API_KEY; else unavailable + procedural fallback)."""
    return mesh_retexture(game_slug, input_glb, style_prompt=style_prompt, seed=seed)


@mcp.tool()
def mesh_text_to_3d_tool(game_slug: str = "default", prompt: str = "", seed: int = 0) -> dict:
    return mesh_text_to_3d(game_slug, prompt, seed=seed)


@mcp.tool()
def generate_with_review_tool(
    kind: str = "brick",
    game_slug: str = "default",
    seed: int = 184,
    mortar: float = 0.06,
    variation: float = 0.15,
    max_iters: int = 3,
) -> dict:
    """Bounded review loop for materials. Default mortar=0.06 is the seeded-defect case."""
    gens = {
        "brick": gen_brick_material,
        "stone": gen_stone_material,
        "wood": gen_wood_material,
        "metal": gen_metal_material,
        "trim": gen_trim_material,
    }
    gen = gens.get(kind, gen_brick_material)
    base = {"game_slug": game_slug, "mortar": mortar, "variation": variation, "size": 512}

    def _gen(**kw):
        p = {k: v for k, v in {**base, **kw}.items() if k in ("game_slug", "size", "mortar", "variation", "final") or k == "seed"}
        # brick accepts mortar; others ignore extras via ** not — call carefully
        if kind == "brick":
            return gen_brick_material(
                game_slug=p.get("game_slug", game_slug),
                seed=kw["seed"],
                size=int(p.get("size", 512)),
                mortar=float(p.get("mortar", 0.02)),
                variation=float(p.get("variation", 0.15)),
            )
        return gen(game_slug=game_slug, seed=kw["seed"], size=int(p.get("size", 512)))

    rec = generate_with_review(_gen, seed=seed, base_params=base, max_iters=max_iters)
    out = Path(rec["result"]["out_dir"]) / "review_record.json"
    save_run_record(out, rec)
    rec["review_record"] = str(out)
    return rec


if __name__ == "__main__":
    mcp.run(transport="stdio")
