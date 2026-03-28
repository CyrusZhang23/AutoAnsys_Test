"""
HFSS 驱动模求解与 S 参数导出

- ``solve_and_export_s_params``：对 ``sim.setup_name`` 做阻塞求解，再从扫频域导出
  ``dB(S(1,1))``、``dB(S(2,1))``、``dB(S(3,1))`` 到 CSV。
- CSV **分隔符为分号**，避免表头里 ``dB(S(1,1))`` 的逗号破坏列。
- ``setup_sweep_string``：PyAEDT 要求的 ``"Setup : Sweep"`` 格式（冒号两侧有空格）。

CLI：``wg-solve-export``；也被 ``wg-hfss --solve``、``wg-run-sim`` 间接调用。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wg_tee.hfss_session import launch_hfss
from wg_tee.params import SimulationParams, load_wg_params
from wg_tee.paths import (
    default_hfss_project_path,
    default_params_path,
    resolve_s_params_csv,
)

# Modal ports Port1–Port3 → S(1,1), S(2,1), S(3,1) in dB (single-mode excitation convention).
SPARAM_DB_EXPRESSIONS = ("dB(S(1,1))", "dB(S(2,1))", "dB(S(3,1))")


def setup_sweep_string(sim: SimulationParams) -> str:
    """PyAEDT nominal sweep string: ``\"Setup : Sweep\"`` (spaces around colon)."""
    return f"{sim.setup_name} : {sim.sweep_name}"


def solve_and_export_s_params(app, sim: SimulationParams, csv_path: Path) -> None:
    """Blocking solve + export. Raises ``RuntimeError`` if analysis or export fails."""
    csv_path = csv_path.resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    app.active_setup = sim.setup_name
    if not app.analyze_setup(sim.setup_name, blocking=True):
        raise RuntimeError(f"HFSS analysis failed for setup {sim.setup_name!r}")

    sol = app.post.get_solution_data(
        expressions=list(SPARAM_DB_EXPRESSIONS),
        setup_sweep_name=setup_sweep_string(sim),
        domain="Sweep",
        primary_sweep_variable="Freq",
    )
    # Semicolon: commas inside ``dB(S(1,1))`` break comma-separated CSV.
    if not sol.export_data_to_csv(str(csv_path), delimiter=";"):
        raise RuntimeError(f"Failed to write CSV: {csv_path}")


def run_solve_export_cli(
    params_path: Path,
    project_path: Path,
    *,
    design_name: str,
    non_graphical: bool,
    specified_version: str | None,
    csv_path: Path | None,
    field_top: bool = False,
) -> Path:
    p, units = load_wg_params(params_path)
    if units != "mm":
        print(f"Warning: expected units 'mm', got {units!r}", file=sys.stderr)

    out = csv_path or resolve_s_params_csv(project_path, p.simulation.sparam_csv_filename)

    app = launch_hfss(project_path, design_name, non_graphical, specified_version)
    try:
        app.modeler.model_units = "mm"
        solve_and_export_s_params(app, p.simulation, out)
        if field_top:
            from wg_tee.hfss_field_export import export_top_surface_field_jpg

            fp = export_top_surface_field_jpg(app, p, project_path)
            print(f"Field top JPG: {fp}", file=sys.stderr)
        app.save_project()
    finally:
        if non_graphical:
            app.release_desktop(close_projects=True, close_desktop=True)
        else:
            app.release_desktop(close_projects=False, close_desktop=False)

    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open HFSS project, solve Setup1 sweep, export S11/S21/S31 (dB) to CSV"
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
        help=f"Existing .aedt (default: {default_hfss_project_path()})",
    )
    parser.add_argument("--design", type=str, default="T_Junction", help="HFSS design name")
    parser.add_argument("--non-graphical", action="store_true", help="Run AEDT without GUI")
    parser.add_argument("--aedt-version", type=str, default=None, help="e.g. 2024.2")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Output CSV path (default: output/results/<stem>_s_params.csv or simulation.sparam_csv_filename)",
    )
    parser.add_argument(
        "--field-top",
        action="store_true",
        help="After solve, export top-surface field JPG (see simulation.field_top_*)",
    )
    args = parser.parse_args()

    if not args.params.is_file():
        print(f"Error: params file not found: {args.params}", file=sys.stderr)
        sys.exit(1)
    if not args.project.is_file():
        print(f"Error: HFSS project not found: {args.project}", file=sys.stderr)
        sys.exit(1)

    out = run_solve_export_cli(
        args.params,
        args.project,
        design_name=args.design,
        non_graphical=args.non_graphical,
        specified_version=args.aedt_version,
        csv_path=args.csv,
        field_top=args.field_top,
    )
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
