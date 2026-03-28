"""
HFSS 三维建模 — ModelDescribe §4–§8

流程概览
--------
1. ``launch_hfss`` 打开/创建工程。
2. 非 ``geometry-only`` 时 ``_clear_previous_t_junction_build``：删掉上次脚本的 Setup、PEC/端口、几何，避免重复建边界失败。
3. 按 ``geometry.spec_arm_*`` 建三臂盒子 → ``unite`` → 可选 ``subtract`` 槽。
4. ``_apply_ports_pec_setup``：材料、PEC（除三个端口面外全部表面）、波端口 Port1(+X)/Port2(+Y)/Port3(−Y)、Setup、线性扫频。
5. ``save_project``；若 ``solve`` 则调用 ``hfss_export.solve_and_export_s_params``；可选 ``field_top`` 调 ``hfss_field_export``。
6. ``release_desktop``：无图形时关工程与桌面；有图形时保留工程打开（避免界面「全空」）。

依赖：本机 Ansys Electronics Desktop；``uv sync`` 安装 pyaedt。

CLI：``wg-hfss``（见 ``main()``）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wg_tee.geometry import spec_arm_x, spec_arm_y_neg, spec_arm_y_pos, spec_slot_tool
from wg_tee.hfss_export import solve_and_export_s_params
from wg_tee.hfss_session import launch_hfss
from wg_tee.params import SimulationParams, load_wg_params
from wg_tee.paths import default_hfss_project_path, default_params_path, resolve_s_params_csv

# HFSS 模型中的对象命名（与布尔后唯一体名称一致；并集后主体名为 WG_Arm_X）
NAME_ARM_X = "WG_Arm_X"
NAME_ARM_Y_POS = "WG_Arm_Ypos"
NAME_ARM_Y_NEG = "WG_Arm_Yneg"
NAME_SLOT = "WG_SlotTool"


def _clear_previous_t_junction_build(app, sim: SimulationParams) -> None:
    """
    Remove setup, scripted boundaries, and united body from a prior run.

    Re-running ``wg-run-sim`` / ``wg-hfss`` on an existing ``.aedt`` without this
    leaves old Perfect E / ports / setup; creating them again can make
    ``AssignPerfectE`` fail (duplicate name or stale state on AEDT 2025.x gRPC).
    """
    # 1. Analysis setup (removes frequency sweep tied to it)
    try:
        if sim.setup_name in app.setup_names:
            app.delete_setup(sim.setup_name)
    except Exception:
        pass

    # 2. Boundaries and wave ports from a previous scripted build
    targets = {sim.pec_boundary_name, "Port1", "Port2", "Port3"}
    for _ in range(6):
        removed = False
        try:
            for b in list(app.boundaries):
                if getattr(b, "name", None) in targets:
                    try:
                        b.delete()
                        removed = True
                    except Exception:
                        pass
        except Exception:
            break
        if not removed:
            break

    # 3. Geometry (after unite only WG_Arm_X remains; optional slot tool if present)
    try:
        names = list(app.modeler.object_names)
    except Exception:
        names = []
    for obj_name in (NAME_SLOT, NAME_ARM_Y_NEG, NAME_ARM_Y_POS, NAME_ARM_X):
        if obj_name in names:
            try:
                app.modeler.delete(obj_name)
            except Exception:
                pass


def _find_outer_cap_faces(body, L: float, a: float, b: float):
    """Return (face +X at x=L, face +Y at y=L, face −Y at y=−L) as FacePrimitive."""
    ha = a / 2.0
    hb = b / 2.0
    tol_plane = max(0.5, 0.01 * L)
    tol_t = max(0.5, 0.01 * max(a, b))

    def in_cross_x(cy: float, cz: float) -> bool:
        return abs(cy) <= ha + tol_t and abs(cz) <= hb + tol_t

    def in_cross_y(cx: float, cz: float) -> bool:
        return abs(cx) <= ha + tol_t and abs(cz) <= hb + tol_t

    cand_x, cand_yp, cand_yn = [], [], []
    for f in body.faces:
        cx, cy, cz = (float(f.center[0]), float(f.center[1]), float(f.center[2]))
        if abs(cx - L) < tol_plane and in_cross_x(cy, cz):
            cand_x.append(f)
        if abs(cy - L) < tol_plane and in_cross_y(cx, cz):
            cand_yp.append(f)
        if abs(cy + L) < tol_plane and in_cross_y(cx, cz):
            cand_yn.append(f)

    def pick_largest(label: str, faces: list):
        if not faces:
            raise RuntimeError(f"No outer face matched for {label} (check geometry vs §4).")
        return max(faces, key=lambda ff: float(ff.area))

    return (
        pick_largest("+X (x=L)", cand_x),
        pick_largest("+Y (y=L)", cand_yp),
        pick_largest("−Y (y=−L)", cand_yn),
    )


def _apply_ports_pec_setup(
    app,
    body_name: str,
    *,
    L: float,
    a: float,
    b: float,
    sim: SimulationParams,
) -> None:
    body = app.modeler[body_name]
    body.material_name = sim.body_material

    f1, f2, f3 = _find_outer_cap_faces(body, L, a, b)
    port_ids = {f1.id, f2.id, f3.id}
    pec_ids = [f.id for f in body.faces if f.id not in port_ids]
    if pec_ids:
        app.assign_perfect_e(pec_ids, name=sim.pec_boundary_name)

    m = sim.modes_per_port
    app.wave_port(f1.id, name="Port1", modes=m)
    app.wave_port(f2.id, name="Port2", modes=m)
    app.wave_port(f3.id, name="Port3", modes=m)

    freq = f"{sim.adaptive_frequency_ghz}GHz"
    app.create_setup(name=sim.setup_name, Frequency=freq)
    app.create_linear_step_sweep(
        setup=sim.setup_name,
        unit="GHz",
        start_frequency=sim.sweep_start_ghz,
        stop_frequency=sim.sweep_stop_ghz,
        step_size=sim.sweep_step_ghz,
        name=sim.sweep_name,
        sweep_type=sim.sweep_type,
        save_fields=sim.save_fields,
        save_rad_fields=sim.save_rad_fields,
    )


def build_hfss_model(
    params_path: Path,
    project_path: Path,
    *,
    design_name: str = "T_Junction",
    non_graphical: bool = False,
    specified_version: str | None = None,
    geometry_only: bool = False,
    solve: bool = False,
    field_top: bool = False,
) -> None:
    """
    从 params 建 HFSS 模型并保存工程。

    ``geometry_only`` 为真时只做布尔几何，不分配材料/PEC/端口/求解设置。
    ``field_top`` 仅在 ``solve`` 为真时生效（需先有解再导场）。
    """
    p, units = load_wg_params(params_path)
    if units != "mm":
        print(f"Warning: expected units 'mm', got {units!r}", file=sys.stderr)

    app = launch_hfss(project_path, design_name, non_graphical, specified_version)
    try:
        app.modeler.model_units = "mm"

        if not geometry_only:
            _clear_previous_t_junction_build(app, p.simulation)

        sx = spec_arm_x(p.a, p.b, p.L)
        sy = spec_arm_y_pos(p.a, p.b, p.L)
        sn = spec_arm_y_neg(p.a, p.b, p.L)

        mat = p.simulation.body_material

        def _create(name: str, spec):
            obj = app.modeler.create_box(
                origin=list(spec.origin),
                sizes=list(spec.sizes),
                name=name,
                material=mat,
            )
            if obj is False or obj is None:
                raise RuntimeError(f"create_box failed for {name!r}")
            return obj

        o_x = _create(NAME_ARM_X, sx)
        o_yp = _create(NAME_ARM_Y_POS, sy)
        o_yn = _create(NAME_ARM_Y_NEG, sn)
        o_x.unite([o_yp, o_yn])

        if p.enable_slot:
            st = spec_slot_tool(p.a, p.X, p.D, p.b, p.offset)
            o_slot = _create(NAME_SLOT, st)
            o_x.subtract(o_slot, keep_originals=False)

        if not geometry_only:
            _apply_ports_pec_setup(app, NAME_ARM_X, L=p.L, a=p.a, b=p.b, sim=p.simulation)
            print(
                "Ports: Port1 (+X), Port2 (+Y), Port3 (−Y). "
                f"After solving {p.simulation.setup_name}/{p.simulation.sweep_name}, plot S11, S21, S31.",
                file=sys.stderr,
            )

        app.save_project()

        if not geometry_only and solve:
            csv_out = resolve_s_params_csv(project_path, p.simulation.sparam_csv_filename)
            solve_and_export_s_params(app, p.simulation, csv_out)
            print(f"S-parameters CSV: {csv_out}", file=sys.stderr)
            if field_top:
                from wg_tee.hfss_field_export import export_top_surface_field_jpg

                fp = export_top_surface_field_jpg(app, p, project_path)
                print(f"Field top JPG: {fp}", file=sys.stderr)
            app.save_project()
        # 刷新 3D 视图（部分版本需显式 fit）
        try:
            app.modeler.fit_all()
        except Exception:
            pass
    finally:
        # release_desktop 默认 close_projects=True：图形模式下会关掉当前工程，界面看起来「全空」。
        if non_graphical:
            app.release_desktop(close_projects=True, close_desktop=True)
        else:
            app.release_desktop(close_projects=False, close_desktop=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build T-junction HFSS model (PyAEDT) from params.json")
    parser.add_argument(
        "params",
        nargs="?",
        type=Path,
        default=default_params_path(),
        help=f"Path to params.json (default: {default_params_path()})",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=default_hfss_project_path(),
        help=f"Output .aedt path (default: {default_hfss_project_path()})",
    )
    parser.add_argument("--design", type=str, default="T_Junction", help="HFSS design name")
    parser.add_argument("--non-graphical", action="store_true", help="Run AEDT without GUI")
    parser.add_argument("--aedt-version", type=str, default=None, help="e.g. 2024.2")
    parser.add_argument(
        "--geometry-only",
        action="store_true",
        help="Only build §4 geometry (no vacuum/PEC/ports/sweep)",
    )
    parser.add_argument(
        "--solve",
        action="store_true",
        help="After save, run HFSS solve and export S11/S21/S31 (dB) to output/results/",
    )
    parser.add_argument(
        "--field-top",
        action="store_true",
        help="After solve, export top-surface field JPG (implies --solve); see simulation.field_top_* in params.json",
    )
    args = parser.parse_args()

    if not args.params.is_file():
        print(f"Error: params file not found: {args.params}", file=sys.stderr)
        sys.exit(1)

    build_hfss_model(
        args.params,
        args.project,
        design_name=args.design,
        non_graphical=args.non_graphical,
        specified_version=args.aedt_version,
        geometry_only=args.geometry_only,
        solve=(args.solve or args.field_top) and not args.geometry_only,
        field_top=args.field_top and not args.geometry_only,
    )
    print(f"Saved: {args.project.resolve()}")


if __name__ == "__main__":
    main()
