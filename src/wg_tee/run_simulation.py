"""
一键仿真流水线（默认 **无 HFSS 图形界面**）

分支
----
- **默认**：``build_hfss_model(..., non_graphical=True, solve=True)`` — 完整重建几何、求解、写 CSV；
  若 ``--field-top`` 则再导出顶面场 JPG。
- **``--existing-only``**：不调用 ``build_hfss_model``，仅 ``run_solve_export_cli`` 打开已有 ``.aedt`` 求解并导出。

之后始终根据 ``resolve_s_params_csv`` 定位 CSV，再 ``plot_s_params`` 生成 S 曲线 JPG。

CLI：``wg-run-sim``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wg_tee.hfss_build import build_hfss_model
from wg_tee.hfss_export import run_solve_export_cli
from wg_tee.params import load_wg_params
from wg_tee.paths import default_hfss_project_path, default_params_path, resolve_s_params_csv
from wg_tee.plot_s_params import plot_s_params


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HFSS non-graphical: model + solve → CSV, then plot S11/S21/S31 to JPG"
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
        help=f"Output/read .aedt (default: {default_hfss_project_path()})",
    )
    parser.add_argument("--design", type=str, default="T_Junction", help="HFSS design name")
    parser.add_argument("--aedt-version", type=str, default=None, help="e.g. 2024.2")
    parser.add_argument(
        "--existing-only",
        action="store_true",
        help="Do not rebuild geometry; only open existing project, solve, export CSV, plot JPG",
    )
    parser.add_argument(
        "--plot-title",
        type=str,
        default=None,
        help="Matplotlib figure title (default: CSV basename)",
    )
    parser.add_argument(
        "--field-top",
        action="store_true",
        help="After HFSS solve, export top-surface field JPG (see simulation.field_top_* in params.json)",
    )
    args = parser.parse_args()

    if not args.params.is_file():
        print(f"Error: params not found: {args.params}", file=sys.stderr)
        sys.exit(1)

    p, units = load_wg_params(args.params)
    if units != "mm":
        print(f"Warning: expected units 'mm', got {units!r}", file=sys.stderr)

    if args.existing_only:
        if not args.project.is_file():
            print(f"Error: project not found: {args.project}", file=sys.stderr)
            sys.exit(1)
        run_solve_export_cli(
            args.params,
            args.project,
            design_name=args.design,
            non_graphical=True,
            specified_version=args.aedt_version,
            csv_path=None,
            field_top=args.field_top,
        )
    else:
        build_hfss_model(
            args.params,
            args.project,
            design_name=args.design,
            non_graphical=True,
            specified_version=args.aedt_version,
            geometry_only=False,
            solve=True,
            field_top=args.field_top,
        )

    csv_path = resolve_s_params_csv(args.project, p.simulation.sparam_csv_filename)
    if not csv_path.is_file():
        print(f"Error: expected CSV after solve: {csv_path}", file=sys.stderr)
        sys.exit(1)

    jpg_path = csv_path.with_suffix(".jpg")
    plot_s_params(csv_path, jpg_path, title=args.plot_title, image_format="jpeg")
    print(str(csv_path))
    print(str(jpg_path))


if __name__ == "__main__":
    main()
