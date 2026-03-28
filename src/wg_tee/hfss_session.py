"""
HFSS 会话启动 — 被 ``hfss_build``、``hfss_export``、``hfss_field_export`` 共用。

说明
----
- **Modal**：``solution_type="Modal"``，与波端口 S 参一致。
- **工程路径**：父目录不存在时会创建；指向 ``.aedt`` 时 PyAEDT 打开或新建该工程。
- **兼容性**：优先 ``new_desktop`` / ``version``；旧版 PyAEDT 用 ``TypeError`` 回退到 ``new_desktop_session`` / ``specified_version``。
"""

from __future__ import annotations

from pathlib import Path


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
