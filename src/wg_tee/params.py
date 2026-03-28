"""
参数加载 — ModelDescribe.md §6

- **几何**：``a, b, L``、``enable_slot``、槽 ``X, D, offset`` 等由 JSON 顶层字段读入。
- **simulation**：可选对象；缺省键由 ``_DEFAULT_SIMULATION`` 补全，再校验范围与类型。
- 返回 ``(WGParams, units_str)``；当前脚本假定单位为 ``mm``。

与 ``paths.resolve_*`` 配合可得到 CSV/场图输出路径（可由 ``simulation`` 里 basename 覆盖）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SimulationParams:
    """HFSS 脚本化配置（频率除另有说明外均为 GHz）。"""

    setup_name: str
    sweep_name: str
    adaptive_frequency_ghz: float
    sweep_start_ghz: float
    sweep_stop_ghz: float
    sweep_step_ghz: float
    sweep_type: str
    save_fields: bool
    save_rad_fields: bool
    body_material: str
    modes_per_port: int
    pec_boundary_name: str
    sparam_csv_filename: str | None
    field_top_freq_ghz: float | None
    field_top_use_s11_min: bool
    field_top_quantity: str
    field_top_image_basename: str | None


@dataclass(frozen=True)
class WGParams:
    """几何参数 + 嵌套的 ``simulation``（HFSS 设置）。"""

    a: float
    b: float
    L: float
    enable_slot: bool
    X: float
    D: float
    offset: float
    simulation: SimulationParams


_DEFAULT_SIMULATION: dict = {
    "setup_name": "Setup1",
    "sweep_name": "Sweep_0_10GHz",
    "adaptive_frequency_ghz": 5.0,
    "sweep_start_ghz": 0.0,
    "sweep_stop_ghz": 10.0,
    "sweep_step_ghz": 0.1,
    "sweep_type": "Discrete",
    "save_fields": False,
    "save_rad_fields": False,
    "body_material": "vacuum",
    "modes_per_port": 1,
    "pec_boundary_name": "PEC_WaveguideWalls",
    "sparam_csv_filename": None,
    "field_top_freq_ghz": None,
    "field_top_use_s11_min": True,
    "field_top_quantity": "Mag_E",
    "field_top_image_basename": None,
}

_ALLOWED_SWEEP_TYPES = frozenset({"Discrete", "Interpolating", "Fast"})


def _parse_simulation(overrides: dict) -> SimulationParams:
    m = {**_DEFAULT_SIMULATION, **overrides}
    setup_name = str(m["setup_name"]).strip()
    sweep_name = str(m["sweep_name"]).strip()
    if not setup_name or not sweep_name:
        raise ValueError("simulation.setup_name and simulation.sweep_name must be non-empty strings")

    adaptive = float(m["adaptive_frequency_ghz"])
    f0 = float(m["sweep_start_ghz"])
    f1 = float(m["sweep_stop_ghz"])
    step = float(m["sweep_step_ghz"])
    sweep_type = str(m["sweep_type"]).strip()

    if adaptive <= 0:
        raise ValueError(f"simulation.adaptive_frequency_ghz must be positive, got {adaptive}")
    if f1 < f0:
        raise ValueError(
            f"simulation.sweep_stop_ghz ({f1}) must be >= sweep_start_ghz ({f0})"
        )
    if step <= 0:
        raise ValueError(f"simulation.sweep_step_ghz must be positive, got {step}")
    if sweep_type not in _ALLOWED_SWEEP_TYPES:
        raise ValueError(
            f"simulation.sweep_type must be one of {_ALLOWED_SWEEP_TYPES}, got {sweep_type!r}"
        )

    body_material = str(m["body_material"]).strip()
    if not body_material:
        raise ValueError("simulation.body_material must be non-empty")

    modes = int(m["modes_per_port"])
    if modes < 1:
        raise ValueError(f"simulation.modes_per_port must be >= 1, got {modes}")

    pec_name = str(m["pec_boundary_name"]).strip()
    if not pec_name:
        raise ValueError("simulation.pec_boundary_name must be non-empty")

    scfn = m.get("sparam_csv_filename")
    if scfn is not None and str(scfn).strip() != "":
        scfn = str(scfn).strip()
        if any(sep in scfn for sep in "/\\:"):
            raise ValueError("simulation.sparam_csv_filename must be a basename only (no path separators)")
    else:
        scfn = None

    ft_freq = m.get("field_top_freq_ghz")
    if ft_freq is not None and str(ft_freq).strip() != "":
        ft_freq = float(ft_freq)
        if ft_freq <= 0:
            raise ValueError(f"simulation.field_top_freq_ghz must be positive, got {ft_freq}")
    else:
        ft_freq = None

    ft_q = str(m.get("field_top_quantity", "Mag_E")).strip()
    if not ft_q:
        raise ValueError("simulation.field_top_quantity must be non-empty")

    ft_img = m.get("field_top_image_basename")
    if ft_img is not None and str(ft_img).strip() != "":
        ft_img = str(ft_img).strip()
        if any(sep in ft_img for sep in "/\\:"):
            raise ValueError("simulation.field_top_image_basename must be a basename only")
    else:
        ft_img = None

    return SimulationParams(
        setup_name=setup_name,
        sweep_name=sweep_name,
        adaptive_frequency_ghz=adaptive,
        sweep_start_ghz=f0,
        sweep_stop_ghz=f1,
        sweep_step_ghz=step,
        sweep_type=sweep_type,
        save_fields=bool(m["save_fields"]),
        save_rad_fields=bool(m["save_rad_fields"]),
        body_material=body_material,
        modes_per_port=modes,
        pec_boundary_name=pec_name,
        sparam_csv_filename=scfn,
        field_top_freq_ghz=ft_freq,
        field_top_use_s11_min=bool(m.get("field_top_use_s11_min", True)),
        field_top_quantity=ft_q,
        field_top_image_basename=ft_img,
    )


def load_wg_params(path: Path) -> tuple[WGParams, str]:
    """
    Returns (params, units_string). Raises ValueError if geometry violates §6.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    units = raw.get("units", "mm")

    a = float(raw["a"])
    b = float(raw["b"])
    L = float(raw["L"])
    enable_slot = bool(raw["enable_slot"])
    X = float(raw.get("X", 0.0))
    D = float(raw.get("D", 0.0))
    offset = float(raw.get("offset", 0.0))

    for name, v in ("a", a), ("b", b), ("L", L):
        if v <= 0:
            raise ValueError(f"{name} must be positive per ModelDescribe §6, got {v}")

    if enable_slot:
        for name, v in ("X", X), ("D", D):
            if v <= 0:
                raise ValueError(f"{name} must be positive when enable_slot is true (§6), got {v}")

    sim_raw = raw.get("simulation")
    if sim_raw is None:
        sim_raw = {}
    if not isinstance(sim_raw, dict):
        raise ValueError("'simulation' must be a JSON object when present")

    return (
        WGParams(
            a=a,
            b=b,
            L=L,
            enable_slot=enable_slot,
            X=X,
            D=D,
            offset=offset,
            simulation=_parse_simulation(sim_raw),
        ),
        units,
    )
