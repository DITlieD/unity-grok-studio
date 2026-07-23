from .brick import gen_brick_material
from .metal import gen_metal_material
from .stone import gen_stone_material
from .trim import gen_trim_material
from .wood import gen_wood_material

__all__ = [
    "gen_brick_material",
    "gen_stone_material",
    "gen_wood_material",
    "gen_metal_material",
    "gen_trim_material",
]
