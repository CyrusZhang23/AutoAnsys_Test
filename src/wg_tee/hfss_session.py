"""
HFSS 会话启动 — 被 ``hfss_build``、``hfss_export``、``hfss_field_export`` 共用。

说明
----
- **Modal**：``solution_type="Modal"``，与波端口 S 参一致。
- **工程路径**：父目录不存在时会创建；指向 ``.aedt`` 时 PyAEDT 打开或新建该工程。
- **兼容性**：优先 ``new_desktop`` / ``version``；旧版 PyAEDT 用 ``TypeError`` 回退到 ``new_desktop_session`` / ``specified_version``。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

def _version_token_from_spec(specified_version: str | None) -> str | None:
    """Map version spec (e.g. 2025.2 or 252) to AEDT token (252)."""
    if not specified_version:
        return None
    raw = specified_version.strip()
    if raw.isdigit() and len(raw) == 3:
        return raw
    m = re.fullmatch(r"20(\d{2})\.(\d)", raw)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return None


def _discover_aedt_roots() -> dict[str, str]:
    """Discover installed AEDT roots under /opt/ansys_inc/v*/AnsysEM."""
    base = Path("/opt/ansys_inc")
    found: dict[str, str] = {}
    if not base.is_dir():
        return found
    for em_dir in sorted(base.glob("v*/AnsysEM")):
        token = em_dir.parent.name.removeprefix("v")
        if len(token) == 3 and token.isdigit() and em_dir.is_dir():
            found[token] = str(em_dir)
    return found


def _has_valid_aedt_env() -> bool:
    for key, val in os.environ.items():
        if (key.startswith("ANSYSEM_ROOT") or key.startswith("AWP_ROOT")) and Path(val).is_dir():
            return True
    return False


def _ensure_aedt_env(specified_version: str | None) -> None:
    """Ensure PyAEDT can discover local AEDT install via env vars."""
    if _has_valid_aedt_env():
        return

    roots = _discover_aedt_roots()
    if not roots:
        return

    requested = _version_token_from_spec(specified_version)
    token = requested if requested in roots else sorted(roots.keys())[-1]
    root_path = roots[token]

    os.environ.setdefault(f"ANSYSEM_ROOT{token}", root_path)
    os.environ.setdefault(f"AWP_ROOT{token}", root_path)


def launch_hfss(
    project_path: Path,
    design_name: str,
    non_graphical: bool,
    specified_version: str | None,
):
    """
    启动 PyAEDT ``Hfss`` 应用实例。

    Parameters
    ----------
    project_path
        ``.aedt`` 文件的绝对或相对路径。
    design_name
        HFSS 设计名（如 ``T_Junction``）。
    non_graphical
        ``True`` 时不启动 AEDT 图形界面（批处理/远程常用）。
    specified_version
        例如 ``"2024.2"``；``None`` 时使用系统默认 AEDT。
    """
    _ensure_aedt_env(specified_version)
    from ansys.aedt.core import Hfss

    project_path = project_path.resolve()
    project_path.parent.mkdir(parents=True, exist_ok=True)

    kw: dict = {
        "project": str(project_path),
        "design": design_name,
        "solution_type": "Modal",
        "non_graphical": non_graphical,
        "new_desktop": True,
    }
    if specified_version is not None:
        kw["version"] = specified_version
    try:
        return Hfss(**kw)
    except TypeError:
        kw.pop("new_desktop", None)
        kw.pop("version", None)
        return Hfss(
            project=str(project_path),
            design=design_name,
            solution_type="Modal",
            non_graphical=non_graphical,
            new_desktop_session=True,
            specified_version=specified_version,
        )
