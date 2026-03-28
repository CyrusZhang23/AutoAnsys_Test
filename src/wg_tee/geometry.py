"""
规范几何 — ModelDescribe.md §4（冻结）

**坐标**：原点 T 结中心；+X Port1，±Y Port2/3，Z 为波导高向。

**表示**：每个盒子用 ``BoxSpec`` — ``origin`` = 最小角点 (xmin,ymin,zmin)，
``sizes`` = 沿 +X/+Y/+Z 的边长。HFSS 用 ``create_box(origin, sizes)``；
预览用 ``spec_to_center_extents`` 转成 trimesh 的 box 中心与全尺寸。

**布尔顺序**（在 ``hfss_build`` / ``preview`` 中）：三臂并集 → 可选减去槽体（§4.3）。

修改本节公式须同步 ``ModelDescribe.md`` 与 ``preview.py``。
"""

from __future__ import annotations

from typing import NamedTuple


class BoxSpec(NamedTuple):
    """Inclusive-aligned box: corner at origin, edge lengths sizes."""

    origin: tuple[float, float, float]
    sizes: tuple[float, float, float]


def spec_arm_x(a: float, b: float, L: float) -> BoxSpec:
    """Arm_X (Port 1, +X): x∈[0,L], y∈[-a/2,a/2], z∈[-b/2,b/2]."""
    return BoxSpec((0.0, -a / 2, -b / 2), (L, a, b))


def spec_arm_y_pos(a: float, b: float, L: float) -> BoxSpec:
    """Arm_Y+ (Port 2, +Y): x∈[-a/2,a/2], y∈[0,L], z∈[-b/2,b/2]."""
    return BoxSpec((-a / 2, 0.0, -b / 2), (a, L, b))


def spec_arm_y_neg(a: float, b: float, L: float) -> BoxSpec:
    """Arm_Y− (Port 3, −Y): x∈[-a/2,a/2], y∈[-L,0], z∈[-b/2,b/2]."""
    return BoxSpec((-a / 2, -L, -b / 2), (a, L, b))


def spec_slot_tool(a: float, X: float, D: float, b: float, offset: float) -> BoxSpec:
    """SlotTool §4.3: x∈[-a/2,-a/2+D], y∈[offset-X/2,offset+X/2], z∈[-b/2,b/2]."""
    return BoxSpec((-a / 2, offset - X / 2, -b / 2), (D, X, b))


def spec_to_center_extents(spec: BoxSpec) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """(extents_xyz, center_xyz) for trimesh.creation.box(extents=..., transform=translation(center))."""
    ox, oy, oz = spec.origin
    sx, sy, sz = spec.sizes
    return (sx, sy, sz), (ox + sx / 2, oy + sy / 2, oz + sz / 2)
