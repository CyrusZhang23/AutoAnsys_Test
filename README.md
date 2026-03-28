# AutoAnsys_Test — 矩形波导 T 结参数化工具

围绕 **矩形波导 T 型结**（ModelDescribe 规范）提供：**几何定义**、**本地三维预览**、**HFSS 自动建模与求解**、**S 参数导出与作图**、**顶面场分布导出**。参数与几何以 `config/params.json` 与 `ModelDescribe/ModelDescribe.md` 为权威来源。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 冻结几何 | `geometry.py` 与 `ModelDescribe.md` §4 一致；改结构须同步文档与参数。 |
| 参数校验 | `params.py` 读取 JSON，合并默认 `simulation`，校验范围与字段。 |
| 无 HFSS 预览 | `wg-preview`：trimesh 布尔并/差 + PyVista 窗口。 |
| HFSS 建模 | `wg-hfss`：三臂盒子 → 并集 → 可选开槽相减；真空体、PEC、Port1–3、Setup/Sweep。 |
| 求解与 S 参 | `wg-solve-export` 或 `wg-hfss --solve`：驱动模求解，CSV（分号分隔）写入 `output/results/`。 |
| S 曲线图 | `wg-plot-s`：从 CSV 绘制 S11/S21/S31（dB），默认 JPG。 |
| 顶面场图 | `wg-field-top` 或 `wg-run-sim --field-top`：HFSS 场图或场计算器网格 + Matplotlib 回退。 |
| 一键流程 | `wg-run-sim`：无 GUI 下建模 → 求解 → CSV → S 曲线 JPG（可选顶面场）。 |

---

## 推荐工作流程（端到端）

1. **安装依赖**：本机安装 **Ansys Electronics Desktop**（与 PyAEDT 版本匹配）；安装 [uv](https://docs.astral.sh/uv/)，在仓库根执行 `uv sync`。
2. **编辑参数**：修改 `config/params.json`（几何与可选 `simulation`）。需要后处理场量时设 `"save_fields": true` 并**重新建模求解**（扫频上的“保存场”随 `wg-hfss` 写入工程）。
3. **预览几何**（可选）：`uv run wg-preview`。
4. **建模 + 求解 + 出图**（常用）：`uv run wg-run-sim`，需要顶面场时加 `--field-top`。
5. **仅对已有工程再算一遍**：`uv run wg-run-sim --existing-only`（不重建几何）。
6. **仅补场图**（已求解、已存场）：`uv run wg-field-top --non-graphical`。

新建工程：删除或指定新的 `--project output\名称.aedt` 后运行 `wg-run-sim` / `wg-hfss` 即可；脚本会在同一路径下重建模型（并对已有 `.aedt` 先清理同名 Setup/边界/几何，避免重复分配 PEC 失败）。

---

## 仓库与包结构

```
AutoAnsys_Test/
├── README.md                      # 本说明
├── pyproject.toml                 # 包名、依赖、控制台脚本入口
├── config/params.json             # 几何 + simulation（默认被各 CLI 读取）
├── output/                        # 默认 HFSS 工程目录
│   └── results/                   # S 参 CSV、S 曲线 JPG、顶面场 JPG
├── ModelDescribe/ModelDescribe.md   # 坐标系、几何、参数、HFSS 约定（权威）
└── src/wg_tee/                    # Python 包（唯一源码包）
```

### 源码分类说明

| 分类 | 文件 | 作用 |
|------|------|------|
| **路径与约定** | `paths.py` | 推算仓库根目录；默认 `params.json`、`.aedt`、`output/results/` 下产物路径解析。 |
| **几何规范** | `geometry.py` | §4 轴对齐盒子：`BoxSpec`、`spec_arm_*`、`spec_slot_tool`、预览用中心与尺寸转换。 |
| **参数** | `params.py` | `WGParams`、`SimulationParams`；`load_wg_params` 解析并校验 JSON。 |
| **HFSS 会话** | `hfss_session.py` | `launch_hfss`：Modal HFSS、工程路径、可选无图形/版本。 |
| **建模** | `hfss_build.py` | 清理旧构建、建几何、PEC/端口/Setup/Sweep；CLI `wg-hfss`。 |
| **求解导出** | `hfss_export.py` | `solve_and_export_s_params`、`setup_sweep_string`；CLI `wg-solve-export`。 |
| **场图** | `hfss_field_export.py` | 顶面场频率解析、HFSS 场图或 `export_field_file_on_grid` 回退；CLI `wg-field-top`。 |
| **后处理作图** | `plot_s_params.py` | 读分号 CSV、`load_s_csv`、`plot_s_params`；CLI `wg-plot-s`。 |
| **预览** | `preview.py` | trimesh + PyVista；CLI `wg-preview`。 |
| **编排** | `run_simulation.py` | 一键：`build_hfss_model` 或 `run_solve_export_cli` + `plot_s_params`；CLI `wg-run-sim`。 |
| **包入口** | `__init__.py` | 包说明字符串。 |

---

## 控制台命令一览

在仓库根目录、已 `uv sync` 的前提下：

| 命令 | 典型用途 |
|------|----------|
| `uv run wg-preview` | 三维预览（读默认 `config/params.json`）。 |
| `uv run wg-hfss` | 建模型并保存默认 `output/t_junction.aedt`。 |
| `uv run wg-hfss --geometry-only` | 仅 §4 几何，无端口/PEC/求解设置。 |
| `uv run wg-hfss --non-graphical --solve` | 无 GUI 建模并求解，导出 CSV。 |
| `uv run wg-hfss --non-graphical --solve --field-top` | 上一条 + 顶面场 JPG。 |
| `uv run wg-solve-export --non-graphical` | 打开已有 `.aedt`，只求解并导出 CSV（可选 `--field-top`）。 |
| `uv run wg-run-sim` | **一键**：建模 + 求解 + CSV + S 曲线 JPG（无 HFSS 界面）。 |
| `uv run wg-run-sim --field-top` | 一键 + 顶面场 JPG。 |
| `uv run wg-run-sim --existing-only` | 不重建几何，只求解 + 导出 + S 曲线。 |
| `uv run wg-field-top --non-graphical` | 仅导出顶面场（需已求解；场数据依赖 `save_fields`）。 |
| `uv run wg-plot-s` | 从已有 CSV 画 S11/S21/S31 JPG。 |

通用参数：`--project path\to\file.aedt` 指定工程文件；`--aedt-version 2024.2` 等指定 AEDT 版本。

也可用模块方式：`uv run python -m wg_tee.hfss_build`（与其余入口同理）。

---

## `config/params.json` 要点

- **几何**：`units`（应为 `"mm"`）、`a`、`b`、`L`、`enable_slot`、槽参数 `X`、`D`、`offset` 等（见 ModelDescribe §6）。
- **`simulation`**（可选，缺省项由 `params.py` 内建默认补全）：
  - **`setup_name` / `sweep_name`**：HFSS 分析与扫频名称。
  - **`adaptive_frequency_ghz`**：自适应求解频率；也作场图默认频率的后备。
  - **`sweep_*`**：扫频起止、步长、类型（Discrete / Interpolating / Fast）。
  - **`save_fields` / `save_rad_fields`**：是否在扫频上保存场；后处理场图、场计算器导出需 **`save_fields: true`** 并重新建模求解。
  - **`body_material`**：波导腔体材料名（如 `vacuum`）。
  - **`pec_boundary_name`**：脚本创建的 Perfect E 边界名称。
  - **`sparam_csv_filename`**：CSV 文件名（仅 basename，置于 `output/results/`）；默认 `{工程stem}_s_params.csv`。
  - **`field_top_freq_ghz`**：顶面场频率（GHz）；`null` 时可按 **`field_top_use_s11_min`** 从 CSV 取 S11 最小点频率，否则用 `adaptive_frequency_ghz`。
  - **`field_top_quantity`**：场量（如 `Mag_E`）。
  - **`field_top_image_basename`**：顶面场 JPG 文件名（可选）。

---

## 输出文件约定

- **HFSS 工程**：默认 `output/t_junction.aedt`（或由 `--project` 指定）。
- **S 参数 CSV**：`output/results/<stem>_s_params.csv`（分号分隔，表头含 `Freq` 与 `dB(S(i,j))`）。
- **S 曲线图**：与 CSV 同主名、扩展名 `.jpg`（`wg-run-sim` / `wg-plot-s`）。
- **顶面场图**：默认 `output/results/<stem>_field_top.jpg`。

---

## 设计约定摘要

- **原点**：T 结中心；**+X** = Port1，**±Y** = Port2/3，**Z** = 波导高向。
- **布尔顺序**：三臂 **并集** → 若 `enable_slot` 再 **减去** 槽体盒子。
- **端口**：波端口在三个外伸端面；其余外表面 **PEC**（名称见 `pec_boundary_name`）。

---

## 常见问题

- **`wg-hfss` / `wg-run-sim` 第二次运行报 Perfect E 失败**  
  当前代码会在非 `--geometry-only` 构建前删除同名 Setup、Port1–3、PEC 及旧几何，再重建。若仍失败，可关闭 HFSS 后删除 `output\*.aedt` 再跑，或换新 `--project` 路径。

- **无图形下场图为空或失败**  
  脚本会先尝试 HFSS 场图导出，失败则使用场计算器 **网格 `.fld` + Matplotlib**。若仍报错，确认 **`save_fields: true`** 并已对工程重新求解。

- **图形模式跑完 HFSS 里「像没工程」**  
  脚本在图形模式下 `release_desktop(..., close_projects=False)`，工程应仍打开；若未显示，用 **文件 → 打开** 加载 `output\t_junction.aedt`。

---

## 许可证与归属

包名见 `pyproject.toml`（`autoansys-test`）。对外发布请自行补充许可证与版权声明。
