"""
路径解析 — 所有 CLI 的默认文件位置由此统一推算，避免硬编码盘符。

约定目录（相对仓库根）
----------------------
- ``config/params.json``          几何与 simulation 参数。
- ``output/``                     默认 HFSS 工程 ``t_junction.aedt``。
- ``output/results/``             S 参 CSV、matplotlib 曲线 JPG、顶面场 JPG。

``repo_root()`` 通过 ``wg_tee/paths.py`` 向上两级定位到含 ``src/`` 的仓库根。
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """仓库根：``…/src/wg_tee/paths.py`` → ``parents[2]``。"""
    return Path(__file__).resolve().parents[2]


def default_params_path() -> Path:
    """默认 ``config/params.json``。"""
    return repo_root() / "config" / "params.json"


def default_hfss_project_path() -> Path:
    """默认 HFSS 工程：``output/t_junction.aedt``。"""
    return repo_root() / "output" / "t_junction.aedt"


def default_results_dir() -> Path:
    """``output/results/``：求解与绘图产物目录。"""
    return repo_root() / "output" / "results"


def resolve_field_top_jpg(project_path: Path, basename: str | None) -> Path:
    """
    顶面场 JPG 的完整路径。

    - ``basename`` 为 ``None`` 时：``{工程文件主名}_field_top.jpg``。
    - 仅允许文件名（不含路径分隔符）；扩展名可省略，会补 ``.jpg``。
    """
    default_results_dir().mkdir(parents=True, exist_ok=True)
    name = basename or f"{project_path.stem}_field_top.jpg"
    name = name.strip()
    if not name.lower().endswith((".jpg", ".jpeg")):
        name += ".jpg"
    return default_results_dir() / name


def resolve_s_params_csv(project_path: Path, basename: str | None) -> Path:
    """
    S 参数 CSV 的完整路径。

    - ``basename`` 为 ``None`` 时：``{工程文件主名}_s_params.csv``。
    - 可与 ``params.json`` 里 ``simulation.sparam_csv_filename`` 覆盖默认主名。
    """
    default_results_dir().mkdir(parents=True, exist_ok=True)
    name = basename or f"{project_path.stem}_s_params.csv"
    name = name.strip()
    if not name.lower().endswith(".csv"):
        name += ".csv"
    return default_results_dir() / name
