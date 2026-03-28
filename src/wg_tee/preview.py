"""
三维几何预览（无 HFSS）

- ``build_preview_mesh``：与 HFSS 相同布尔顺序 — 三臂 ``union``，再可选 ``difference`` 槽（manifold 引擎）。
- ``run_preview``：``pv.wrap`` 转 PyVista，等轴测相机 + 网格边线。

改几何逻辑只应改 ``wg_tee.geometry`` 与 ModelDescribe；本文件仅负责网格与显示参数。

CLI：``wg-preview``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pyvista as pv
import trimesh
from trimesh import transformations

from wg_tee.geometry import spec_arm_x, spec_arm_y_neg, spec_arm_y_pos, spec_slot_tool, spec_to_center_extents
from wg_tee.params import load_wg_params
from wg_tee.paths import default_params_path


def _box_trimesh(extents: tuple[float, float, float], center: tuple[float, float, float]) -> trimesh.Trimesh:
    return trimesh.creation.box(
        extents=extents,
        transform=transformations.translation_matrix(center),
    )


def _trimesh_from_spec(spec) -> trimesh.Trimesh:
    ex, ctr = spec_to_center_extents(spec)
    return _box_trimesh(ex, ctr)


def build_arm_solids(a: float, b: float, L: float) -> tuple[trimesh.Trimesh, trimesh.Trimesh, trimesh.Trimesh]:
    return (
        _trimesh_from_spec(spec_arm_x(a, b, L)),
        _trimesh_from_spec(spec_arm_y_pos(a, b, L)),
        _trimesh_from_spec(spec_arm_y_neg(a, b, L)),
    )


def build_slot_solid(a: float, X: float, D: float, b: float, offset: float) -> trimesh.Trimesh:
    return _trimesh_from_spec(spec_slot_tool(a, X, D, b, offset))


def build_preview_mesh(
    a: float,
    b: float,
    L: float,
    enable_slot: bool,
    X: float,
    D: float,
    offset: float,
) -> trimesh.Trimesh:
    arm_x, arm_py, arm_ny = build_arm_solids(a, b, L)
    body = trimesh.boolean.union([arm_x, arm_py, arm_ny], engine="manifold")

    if enable_slot:
        slot = build_slot_solid(a, X, D, b, offset)
        body = trimesh.boolean.difference([body, slot], engine="manifold")

    return body


def run_preview(params_path: Path) -> None:
    p, units = load_wg_params(params_path)
    if units != "mm":
        print(f"Warning: expected units 'mm', got {units!r}", file=sys.stderr)

    try:
        tm = build_preview_mesh(p.a, p.b, p.L, p.enable_slot, p.X, p.D, p.offset)
    except Exception as exc:
        print(f"Boolean CSG failed: {exc}", file=sys.stderr)
        raise

    mesh = pv.wrap(tm)

    plotter = pv.Plotter(title="Waveguide T-junction preview (united solid, slot subtracted)")
    label = "T-junction (arms united"
    label += ", slot cut out)" if p.enable_slot else ")"
    plotter.add_mesh(
        mesh,
        color="#4e79a7",
        opacity=1.0,
        smooth_shading=True,
        show_edges=True,
        edge_color="k",
        line_width=1.2,
        label=label,
    )

    plotter.add_axes(line_width=4)
    plotter.show_grid()
    plotter.add_legend(bcolor="w", face="r", size=[0.15, 0.15])
    plotter.camera_position = "iso"
    plotter.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="3D preview of T-junction from params.json")
    parser.add_argument(
        "params",
        nargs="?",
        type=Path,
        default=default_params_path(),
        help=f"Path to params.json (default: {default_params_path()})",
    )
    args = parser.parse_args()
    if not args.params.is_file():
        print(f"Error: params file not found: {args.params}", file=sys.stderr)
        sys.exit(1)
    run_preview(args.params)


if __name__ == "__main__":
    main()
