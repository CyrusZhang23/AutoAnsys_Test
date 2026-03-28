"""
顶面场分布导出（z = +b/2，外法向 +Z）

频率选择（``resolve_field_plot_freq_ghz``）
----------------------------------------
1. ``simulation.field_top_freq_ghz`` 若指定则用之。
2. 否则若 ``field_top_use_s11_min`` 且 S 参 CSV 存在，取 S11 最小值对应频率。
3. 否则 ``adaptive_frequency_ghz``。

导出策略（``export_top_surface_field_jpg``）
------------------------------------------
1. 优先：HFSS 表面场图或 z=+b/2 切割面场图 + ``export_image``（适合有 GUI 或 AEDT 支持时）。
2. 若失败（常见于 ``--non-graphical``）：``post.export_field_file_on_grid`` 在 xy 平面采样场量，
   解析 ``.fld`` 后用 Matplotlib ``tricontourf`` 写 JPG。需扫频上 ``save_fields`` 已求解。

CLI：``wg-field-top``；``wg-hfss --field-top`` / ``wg-run-sim --field-top`` 在求解后调用本模块。
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np

from wg_tee.hfss_build import NAME_ARM_X
from wg_tee.hfss_export import setup_sweep_string
from wg_tee.hfss_session import launch_hfss
from wg_tee.params import WGParams, load_wg_params
from wg_tee.paths import (
    default_hfss_project_path,
    default_params_path,
    resolve_field_top_jpg,
    resolve_s_params_csv,
)


def top_z_outward_faces(body, b: float) -> list:
    """FacePrimitives on z = +b/2 with outward normal along +Z."""
    ztop = b / 2.0
    tol = max(0.25, 0.02 * b)
    faces: list = []
    for f in body.faces:
        cz = float(f.center[2])
        if abs(cz - ztop) > tol:
            continue
        n = f.normal
        if n is None:
            continue
        if float(n[2]) > 0.35:
            faces.append(f)
    return faces


def _t_junction_xy_bounds(wg: WGParams) -> tuple[float, float, float, float]:
    """Bounding box in mm for the united T body (ModelDescribe §4)."""
    a, L = wg.a, wg.L
    margin = max(1.0, 0.02 * max(a, L))
    return (-a / 2.0 - margin, L + margin, -L - margin, L + margin)


def _parse_fld_points_scalar(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read HFSS .fld from ExportOnGrid: x y z scalar (space-separated)."""
    xs: list[float] = []
    ys: list[float] = []
    vs: list[float] = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith("unit"):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                x, y, _z, v = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
            except ValueError:
                continue
            xs.append(x)
            ys.append(y)
            vs.append(v)
    if not xs:
        raise RuntimeError(f"No numeric samples in field file: {path}")
    return np.asarray(xs), np.asarray(ys), np.asarray(vs)


def _export_top_field_grid_jpg(
    app,
    wg: WGParams,
    sweep: str,
    intrinsics: dict[str, str],
    out_jpg: Path,
) -> Path:
    """Field calculator ExportOnGrid + Matplotlib (works without HFSS GUI field plots)."""
    sim = wg.simulation
    qty = sim.field_top_quantity
    xmin, xmax, ymin, ymax = _t_junction_xy_bounds(wg)
    z0 = wg.b / 2.0
    nx = ny = 96
    dx = (xmax - xmin) / max(nx - 1, 1)
    dy = (ymax - ymin) / max(ny - 1, 1)
    # Non-zero z step avoids degenerate grids in some AEDT builds.
    dz = max(1e-4, 0.001 * wg.b)
    fld_path = Path(app.working_directory) / f"wg_field_top_{secrets.token_hex(4)}.fld"
    ret = app.post.export_field_file_on_grid(
        quantity=qty,
        solution=sweep,
        file_name=str(fld_path),
        grid_type="Cartesian",
        grid_start=[xmin, ymin, z0 - dz / 2],
        grid_stop=[xmax, ymax, z0 + dz / 2],
        grid_step=[dx, dy, dz],
        is_vector=False,
        intrinsics=intrinsics,
    )
    written = Path(ret) if isinstance(ret, str) and ret else fld_path
    if ret is False or not written.is_file():
        raise RuntimeError(
            "export_field_file_on_grid failed. Set simulation.save_fields=true, re-solve, and retry."
        )
    try:
        x, y, v = _parse_fld_points_scalar(written)
    finally:
        try:
            written.unlink(missing_ok=True)
        except OSError:
            pass

    fghz_str = intrinsics.get("Freq", "")
    title = f"{qty} @ {fghz_str} (cut z≈{z0:g} mm, grid)"

    fig, ax = plt.subplots(figsize=(10, 8), dpi=120)
    triang = mtri.Triangulation(x, y)
    tcf = ax.tricontourf(triang, v, levels=64, cmap="viridis")
    fig.colorbar(tcf, ax=ax, label=qty)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(title)
    ax.set_aspect("equal")
    fig.tight_layout()
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_jpg, format="jpg", bbox_inches="tight")
    plt.close(fig)
    return out_jpg


def resolve_field_plot_freq_ghz(wg: WGParams, project_path: Path) -> float:
    """场图使用的频率（GHz）：显式参数 > S11 最小点 > 自适应频率。"""
    sim = wg.simulation
    if sim.field_top_freq_ghz is not None:
        return float(sim.field_top_freq_ghz)
    csv_path = resolve_s_params_csv(project_path, sim.sparam_csv_filename)
    if sim.field_top_use_s11_min and csv_path.is_file():
        from wg_tee.plot_s_params import load_s_csv

        freq, series = load_s_csv(csv_path)
        s11 = series.get("S11")
        if s11 and len(s11) == len(freq):
            k = min(range(len(s11)), key=lambda i: s11[i])
            return float(freq[k])
    return float(sim.adaptive_frequency_ghz)


def _create_field_plot(
    app, wg: WGParams, sweep: str, intrinsics: dict[str, str], plot_name: str
):
    """
    尝试创建 HFSS 场图对象（用于 ``export_image``）。

    顺序：顶面最大外表面 → 全部顶面 → 水平切割面 + ``filter_objects``。

    Returns
    -------
    (plot, cut_plane_name)
        ``plot`` 为假表示两步均失败（将走网格回退）；若 ``cut_plane_name`` 非空，导出后需删辅助面。
    """
    sim = wg.simulation
    body = app.modeler[NAME_ARM_X]
    qty = sim.field_top_quantity

    candidates = top_z_outward_faces(body, wg.b)
    if not candidates:
        raise RuntimeError(
            "No top (+Z) faces found for field plot; check geometry or increase tolerance."
        )

    largest = max(candidates, key=lambda f: float(f.area))
    for group in ([largest], candidates):
        plot = app.post.create_fieldplot_surface(
            group,
            quantity=qty,
            setup=sweep,
            intrinsics=intrinsics,
            plot_name=plot_name + "_surf",
        )
        if plot:
            return plot, None

    # Fallback: horizontal cut plane at z = +b/2 clipped to the body.
    b = wg.b
    plane_name = f"FieldTopPlane_{secrets.token_hex(4)}"
    app.modeler.create_plane(
        name=plane_name,
        plane_base_x="0mm",
        plane_base_y="0mm",
        plane_base_z=f"{b / 2.0}mm",
        plane_normal_x="0mm",
        plane_normal_y="0mm",
        plane_normal_z="1mm",
    )
    plot = app.post.create_fieldplot_cutplane(
        [plane_name],
        quantity=qty,
        setup=sweep,
        intrinsics=intrinsics,
        plot_name=plot_name + "_cut",
        filter_objects=[NAME_ARM_X],
    )
    if plot:
        return plot, plane_name
    try:
        app.modeler.delete(plane_name)
    except Exception:
        pass
    return False, None


def export_top_surface_field_jpg(app, wg: WGParams, project_path: Path) -> Path:
    """Create field plot (surface or cut-plane) and export JPG, or grid+Matplotlib fallback."""
    sim = wg.simulation
    fghz = resolve_field_plot_freq_ghz(wg, project_path)
    intrinsics: dict[str, str] = {"Freq": f"{fghz}GHz", "Phase": "0deg"}
    sweep = setup_sweep_string(sim)
    plot_name = f"TopField_{secrets.token_hex(3)}"

    out = resolve_field_top_jpg(project_path, sim.field_top_image_basename)
    out.parent.mkdir(parents=True, exist_ok=True)

    plot, cut_plane_temp = _create_field_plot(app, wg, sweep, intrinsics, plot_name)
    ret = False
    if plot:
        try:
            try:
                app.modeler.fit_all()
            except Exception:
                pass
            ret = plot.export_image(
                full_path=str(out),
                orientation="top",
                width=1920,
                height=1080,
                selections=[NAME_ARM_X],
            )
        finally:
            try:
                plot.delete()
            except Exception:
                pass
            if cut_plane_temp:
                try:
                    app.modeler.delete(cut_plane_temp)
                except Exception:
                    pass

    if ret is not False and ret is not None:
        return Path(ret) if isinstance(ret, str) else out

    # Non-graphical / batch: HFSS field plot + export_image often fails; use field calculator grid.
    return _export_top_field_grid_jpg(app, wg, sweep, intrinsics, out)


def run_field_export_cli(
    params_path: Path,
    project_path: Path,
    *,
    design_name: str,
    non_graphical: bool,
    specified_version: str | None,
) -> Path:
    """Open existing solved project and export top-surface field JPG only."""
    p, units = load_wg_params(params_path)
    if units != "mm":
        print(f"Warning: expected units 'mm', got {units!r}", file=sys.stderr)

    app = launch_hfss(project_path, design_name, non_graphical, specified_version)
    try:
        app.modeler.model_units = "mm"
        path = export_top_surface_field_jpg(app, p, project_path)
        app.save_project()
    finally:
        if non_graphical:
            app.release_desktop(close_projects=True, close_desktop=True)
        else:
            app.release_desktop(close_projects=False, close_desktop=False)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export cavity top-surface field plot (JPG) at resonance / S11-min / adaptive frequency"
    )
    parser.add_argument(
        "params",
        nargs="?",
        type=Path,
        default=default_params_path(),
        help=f"params.json (default: {default_params_path()})",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=default_hfss_project_path(),
        help=f"Solved .aedt (default: {default_hfss_project_path()})",
    )
    parser.add_argument("--design", type=str, default="T_Junction", help="HFSS design name")
    parser.add_argument("--non-graphical", action="store_true", help="Run AEDT without GUI")
    parser.add_argument("--aedt-version", type=str, default=None, help="e.g. 2024.2")
    args = parser.parse_args()

    if not args.params.is_file():
        print(f"Error: params not found: {args.params}", file=sys.stderr)
        sys.exit(1)
    if not args.project.is_file():
        print(f"Error: project not found: {args.project}", file=sys.stderr)
        sys.exit(1)

    out = run_field_export_cli(
        args.params,
        args.project,
        design_name=args.design,
        non_graphical=args.non_graphical,
        specified_version=args.aedt_version,
    )
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
